"""Core subscription management logic."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import requests
import yaml

from .config import DEFAULT_WORK_DIR, resolve_config_path
from .console import Colors


class ClashSubscriptionManager:
    """Manage downloading, validating, and syncing Clash subscriptions."""

    def __init__(self, config_path: Optional[str | Path] = None):
        self.config_path = Path(resolve_config_path(config_path)).expanduser()
        self.config = self.load_config()

        config_dir = self.config_path.parent

        if "clash_dir" in self.config:
            clash_dir = Path(self.config["clash_dir"]).expanduser()
            self.work_dir = clash_dir
            party_dir = self.config.get("clash_party_dir", self.config["clash_dir"])
        else:
            default_work_dir = Path(self.config.get("work_dir", config_dir)).expanduser()
            self.work_dir = default_work_dir
            party_dir = self.config.get("clash_party_dir")
            if not party_dir:
                raise ValueError("配置缺少 clash_party_dir 字段，请先运行 clash-sub init-config 并填写配置路径")

        self.clash_party_dir = Path(party_dir).expanduser()
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> Dict:
        """Load config JSON and ensure critical sections exist."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"配置文件 {self.config_path} 不存在，请运行 `clash-sub init-config` 初始化"
            )

        with open(self.config_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        data.setdefault("subscriptions", {})
        data.setdefault("backup", {"enabled": True, "max_backups": 5})
        data.setdefault("api", {})
        return data

    def get_api_credentials(self) -> tuple[str, str]:
        api_cfg = self.config.get("api", {}) or {}
        env_url = os.getenv("CLASH_API_URL")
        env_secret = os.getenv("CLASH_API_SECRET")
        cfg_url = api_cfg.get("url")
        cfg_secret = api_cfg.get("secret")

        url = env_url or cfg_url
        secret = env_secret if env_secret is not None else cfg_secret

        if url in (None, ""):
            raise ValueError("config.json 缺少 api.url，请先运行 clash-sub init-config 或手动填写")

        if secret is None:
            secret = ""

        return url, secret

    def save_config(self) -> None:
        """Persist the config file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as handle:
            json.dump(self.config, handle, indent=2, ensure_ascii=False)
        print(f"{Colors.GREEN}✓ 配置已保存{Colors.NC}")

    def list_subscriptions(self) -> None:
        """List configured subscriptions and cache metadata."""
        print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"{Colors.CYAN}订阅列表{Colors.NC}")
        print(f"{Colors.CYAN}{'='*60}{Colors.NC}\n")

        subscriptions = self.config.get("subscriptions", {})
        if not subscriptions:
            print(f"{Colors.YELLOW}没有配置任何订阅{Colors.NC}")
            return

        for name, sub in subscriptions.items():
            status = (
                f"{Colors.GREEN}启用{Colors.NC}"
                if sub.get("enabled", True)
                else f"{Colors.YELLOW}禁用{Colors.NC}"
            )
            url = sub.get("url", "")
            short_url = f"{url[:50]}..." if len(url) > 50 else url
            print(f"📦 {Colors.BLUE}{name}{Colors.NC}")
            print(f"   状态: {status}")
            print(f"   描述: {sub.get('description', '无')}")
            print(f"   URL: {short_url}")

            config_file = self.work_dir / f"{name}.yaml"
            if config_file.exists():
                size = config_file.stat().st_size / 1024
                mtime = datetime.fromtimestamp(config_file.stat().st_mtime)
                print(f"   文件: {Colors.GREEN}存在{Colors.NC} ({size:.1f} KB)")
                print(f"   更新: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"   文件: {Colors.YELLOW}不存在{Colors.NC}")
            print()

    def backup_config(self, config_name: str) -> Optional[Path]:
        """Backup the cached YAML before overwriting."""
        backup_cfg = self.config.get("backup", {})
        if not backup_cfg.get("enabled", True):
            return None

        config_file = self.work_dir / f"{config_name}.yaml"
        if not config_file.exists():
            return None

        backup_dir = self.work_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"{config_name}.{timestamp}.yaml"
        shutil.copy2(config_file, backup_file)
        print(f"{Colors.GREEN}✓ 备份已保存: {backup_file.name}{Colors.NC}")

        self.cleanup_old_backups(config_name)
        return backup_file

    def cleanup_old_backups(self, config_name: str) -> None:
        """Trim old backup files based on config retention count."""
        max_backups = self.config.get("backup", {}).get("max_backups", 5)
        backup_dir = self.work_dir / "backups"

        if not backup_dir.exists() or max_backups <= 0:
            return

        backups = sorted(
            backup_dir.glob(f"{config_name}.*.yaml"),
            key=lambda file: file.stat().st_mtime,
            reverse=True,
        )

        for backup in backups[max_backups:]:
            backup.unlink(missing_ok=True)
            print(f"{Colors.YELLOW}⚠ 已删除旧备份: {backup.name}{Colors.NC}")

    def update_subscription(self, name: str) -> bool:
        """Download and validate a single subscription."""
        subscriptions = self.config.get("subscriptions", {})
        if name not in subscriptions:
            print(f"{Colors.RED}✗ 订阅不存在: {name}{Colors.NC}")
            return False

        sub = subscriptions[name]

        if not sub.get("enabled", True):
            print(f"{Colors.YELLOW}⚠ 订阅已禁用: {name}{Colors.NC}")
            return False

        print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"{Colors.CYAN}更新订阅: {name}{Colors.NC}")
        print(f"{Colors.CYAN}{'='*60}{Colors.NC}\n")

        self.backup_config(name)

        config_file = self.work_dir / f"{name}.yaml"
        temp_file = config_file.with_suffix(".yaml.tmp")

        print(f"{Colors.YELLOW}正在下载配置...{Colors.NC}")

        try:
            headers = {"User-Agent": "clash-verge/v1.3.8"}
            response = requests.get(sub["url"], headers=headers, timeout=30)
            response.raise_for_status()

            if not response.content:
                print(f"{Colors.RED}✗ 下载的配置文件为空{Colors.NC}")
                return False

            with open(temp_file, "wb") as handle:
                handle.write(response.content)

            size = temp_file.stat().st_size
            if size < 100:
                print(f"{Colors.RED}✗ 下载的配置文件异常 (大小: {size} bytes){Colors.NC}")
                temp_file.unlink(missing_ok=True)
                return False

            try:
                with open(temp_file, "r", encoding="utf-8") as handle:
                    config_data = yaml.safe_load(handle) or {}

                if not isinstance(config_data, dict):
                    raise ValueError("不是有效的 YAML 对象")

                if "proxies" not in config_data and "proxy-providers" not in config_data:
                    raise ValueError("缺少 proxies 或 proxy-providers 字段")
            except (yaml.YAMLError, ValueError) as exc:
                print(f"{Colors.RED}✗ 配置文件格式错误: {exc}{Colors.NC}")
                print(f"{Colors.YELLOW}  提示：订阅链接可能不是 Clash 格式{Colors.NC}")
                temp_file.unlink(missing_ok=True)
                return False
            except Exception as exc:
                print(f"{Colors.YELLOW}⚠ 警告：无法验证配置文件格式，继续更新: {exc}{Colors.NC}")

            shutil.move(str(temp_file), str(config_file))
            print(f"{Colors.GREEN}✓ 配置已更新 (大小: {size/1024:.1f} KB){Colors.NC}")

            try:
                with open(config_file, "r", encoding="utf-8") as handle:
                    config_content = yaml.safe_load(handle) or {}
                proxy_count = len(config_content.get("proxies", []))
                print(f"{Colors.GREEN}✓ 代理节点数量: {proxy_count}{Colors.NC}")
            except Exception:
                pass

            self.update_clash_party_profile(config_file, sub["url"])
            return True

        except requests.exceptions.RequestException as exc:
            print(f"{Colors.RED}✗ 下载失败: {exc}{Colors.NC}")
            temp_file.unlink(missing_ok=True)
            return False
        except Exception as exc:
            print(f"{Colors.RED}✗ 更新失败: {exc}{Colors.NC}")
            temp_file.unlink(missing_ok=True)
            return False

    def update_all(self) -> None:
        """Update all enabled subscriptions."""
        print(f"\n{Colors.MAGENTA}{'='*60}{Colors.NC}")
        print(f"{Colors.MAGENTA}更新所有订阅{Colors.NC}")
        print(f"{Colors.MAGENTA}{'='*60}{Colors.NC}")

        enabled = [
            name
            for name, sub in self.config.get("subscriptions", {}).items()
            if sub.get("enabled", True)
        ]

        if not enabled:
            print(f"\n{Colors.YELLOW}没有启用的订阅{Colors.NC}")
            return

        success = 0
        for name in enabled:
            if self.update_subscription(name):
                success += 1

        print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"{Colors.GREEN}✓ 更新完成: {success}/{len(enabled)}{Colors.NC}")
        print(f"{Colors.CYAN}{'='*60}{Colors.NC}\n")

    def update_clash_party_profile(self, config_file: Path, sub_url: str) -> bool:
        """Sync downloaded config into Clash Party profile directory."""
        try:
            profile_yaml = self.clash_party_dir / "profile.yaml"

            if not profile_yaml.exists():
                print(f"{Colors.YELLOW}⚠ 未找到 Clash Party 配置{Colors.NC}")
                return False

            with open(profile_yaml, "r", encoding="utf-8") as handle:
                profile_data = yaml.safe_load(handle) or {}

            matched_profile = None
            for item in profile_data.get("items", []):
                if item.get("url") == sub_url:
                    matched_profile = item
                    break

            if not matched_profile:
                print(f"{Colors.YELLOW}⚠ 未在 Clash Party 中找到此订阅{Colors.NC}")
                print(f"{Colors.YELLOW}  提示: 请先在 Clash Party 中添加 URL 为 {sub_url} 的订阅{Colors.NC}")
                return False

            profile_uid = matched_profile["id"]
            party_profile = self.clash_party_dir / "profiles" / f"{profile_uid}.yaml"
            party_profile.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(config_file, party_profile)

            for item in profile_data.get("items", []):
                if item.get("id") == profile_uid:
                    item["updated"] = int(time.time() * 1000)
                    break

            with open(profile_yaml, "w", encoding="utf-8") as handle:
                yaml.dump(profile_data, handle, allow_unicode=True, default_flow_style=False)

            print(f"{Colors.GREEN}✓ 已更新 Clash Party 配置文件{Colors.NC}")

            if profile_data.get("current") == profile_uid:
                return self.reload_clash_core()

            print(f"{Colors.YELLOW}  提示: 该配置未激活，请在 Clash Party 中切换使用{Colors.NC}")
            return True

        except Exception as exc:
            print(f"{Colors.YELLOW}⚠ 更新 Clash Party 配置失败: {exc}{Colors.NC}")
            return False

    def reload_clash_core(self) -> bool:
        """Trigger Clash to reload configuration via API."""
        try:
            api_url, secret = self.get_api_credentials()
            headers = {"Authorization": f"Bearer {secret}"} if secret else {}

            response = requests.post(f"{api_url}/configs/reload", headers=headers, timeout=5)

            if response.status_code == 404:
                response = requests.patch(
                    f"{api_url}/configs",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"mode": "rule"},
                    timeout=5,
                )

            if response.status_code < 400:
                print(f"{Colors.GREEN}✓ 已通过 API 重新加载配置{Colors.NC}")
                return True

            print(f"{Colors.YELLOW}⚠ API 重载失败 (状态码: {response.status_code})，请手动刷新{Colors.NC}")
            return False

        except Exception as exc:
            print(f"{Colors.YELLOW}⚠ 无法通过 API 重新加载: {exc}{Colors.NC}")
            print(f"{Colors.YELLOW}  提示: 配置已更新，在 Clash Party 中点击「刷新」按钮即可{Colors.NC}")
            return False

    def check_clash_config(self) -> bool:
        """Ensure Clash currently exposes proxies before restarting."""
        try:
            api_url, secret = self.get_api_credentials()
            headers = {"Authorization": f"Bearer {secret}"} if secret else {}

            response = requests.get(f"{api_url}/proxies", headers=headers, timeout=3)
            response.raise_for_status()

            proxies = response.json().get("proxies", {})
            nodes = {
                name: info
                for name, info in proxies.items()
                if "all" not in info and name not in ["DIRECT", "REJECT", "GLOBAL"]
            }
            return len(nodes) > 0

        except Exception:
            return True

    def restart_clash(self, skip_check: bool = False) -> bool:
        """Send HUP to Clash binaries to reload config."""
        if not skip_check and not self.check_clash_config():
            print(f"\n{Colors.YELLOW}⚠ Clash 当前没有加载任何配置，取消重启操作{Colors.NC}")
            print(f"{Colors.YELLOW}  提示: 请在 Clash Party 中启用订阅配置{Colors.NC}")
            print(f"{Colors.YELLOW}  或者先更新订阅: clash-sub update <name>{Colors.NC}")
            return False

        print(f"\n{Colors.YELLOW}正在重启 Clash Party 服务...{Colors.NC}")
        commands = [["pkill", "-HUP", "mihomo"], ["pkill", "-HUP", "clash"]]

        for command in commands:
            try:
                subprocess.run(command, check=True, capture_output=True)
                print(f"{Colors.GREEN}✓ Clash Party 服务已重启{Colors.NC}")
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        print(f"{Colors.YELLOW}⚠ 无法自动重启，请手动重启 Clash Party 应用{Colors.NC}")
        return False

    def _sanitize_name(self, name: str) -> str:
        slug = re.sub(r"[^\w-]+", "-", name.strip())
        slug = slug.strip("-")
        return slug or "subscription"

    def import_subscriptions_from_party(self, overwrite: bool = False, prefix: str = "") -> bool:
        """Import subscriptions listed in Clash Party profile.yaml."""
        profile_yaml = self.clash_party_dir / "profile.yaml"
        if not profile_yaml.exists():
            print(f"{Colors.RED}✗ 未找到 Clash Party 配置文件: {profile_yaml}{Colors.NC}")
            return False

        try:
            with open(profile_yaml, "r", encoding="utf-8") as handle:
                profile_data = yaml.safe_load(handle) or {}
        except yaml.YAMLError as exc:
            print(f"{Colors.RED}✗ 解析 Clash Party 配置失败: {exc}{Colors.NC}")
            return False

        items = profile_data.get("items", [])
        if not items:
            print(f"{Colors.YELLOW}⚠ Clash Party 配置中没有订阅项{Colors.NC}")
            return False

        subscriptions = self.config.setdefault("subscriptions", {})
        imported = 0
        skipped = 0

        for item in items:
            url = item.get("url")
            if not url:
                continue
            name_source = item.get("name") or item.get("title") or item.get("id") or "subscription"
            safe_name = self._sanitize_name(name_source)
            if prefix:
                safe_name = f"{prefix}{safe_name}"

            if safe_name in subscriptions and not overwrite:
                base = safe_name
                counter = 2
                while safe_name in subscriptions:
                    safe_name = f"{base}-{counter}"
                    counter += 1
            elif safe_name in subscriptions and overwrite:
                pass

            subscriptions[safe_name] = {
                "url": url,
                "enabled": item.get("enabled", True),
                "description": item.get("description") or item.get("remarks") or name_source,
            }
            imported += 1

        if not imported:
            print(f"{Colors.YELLOW}⚠ 未导入任何订阅，可能所有订阅都已存在{Colors.NC}")
            return False

        self.save_config()
        print(f"{Colors.GREEN}✓ 已导入 {imported} 个订阅{Colors.NC}")
        return True

    def add_subscription(self, name: str, url: str, description: str = "") -> None:
        """Add a new subscription to config."""
        subscriptions = self.config.setdefault("subscriptions", {})
        if name in subscriptions:
            print(f"{Colors.YELLOW}⚠ 订阅已存在: {name}{Colors.NC}")
            return

        subscriptions[name] = {"url": url, "enabled": True, "description": description}
        self.save_config()
        print(f"{Colors.GREEN}✓ 订阅已添加: {name}{Colors.NC}")

    def remove_subscription(self, name: str) -> None:
        """Remove a subscription from config."""
        subscriptions = self.config.setdefault("subscriptions", {})
        if name not in subscriptions:
            print(f"{Colors.RED}✗ 订阅不存在: {name}{Colors.NC}")
            return

        del subscriptions[name]
        self.save_config()
        print(f"{Colors.GREEN}✓ 订阅已删除: {name}{Colors.NC}")

    def toggle_subscription(self, name: str) -> None:
        """Toggle subscription enabled flag."""
        subscriptions = self.config.setdefault("subscriptions", {})
        if name not in subscriptions:
            print(f"{Colors.RED}✗ 订阅不存在: {name}{Colors.NC}")
            return

        sub = subscriptions[name]
        sub["enabled"] = not sub.get("enabled", True)
        self.save_config()
        status = "启用" if sub["enabled"] else "禁用"
        print(f"{Colors.GREEN}✓ 订阅已{status}: {name}{Colors.NC}")
