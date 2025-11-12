#!/usr/bin/env python3
"""
Clash 订阅管理器
方便管理和更新 Clash 订阅配置
"""

import json
import os
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import argparse
import requests


class Colors:
    """终端颜色"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


class ClashSubscriptionManager:
    """Clash 订阅管理器"""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.clash_dir = Path(os.path.expanduser(self.config['clash_dir']))

    def load_config(self) -> Dict:
        """加载配置文件"""
        if not self.config_path.exists():
            print(f"{Colors.RED}✗ 配置文件不存在: {self.config_path}{Colors.NC}")
            sys.exit(1)

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"{Colors.RED}✗ 配置文件格式错误: {e}{Colors.NC}")
            sys.exit(1)

    def save_config(self):
        """保存配置文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, indent=2, ensure_ascii=False, fp=f)
        print(f"{Colors.GREEN}✓ 配置已保存{Colors.NC}")

    def list_subscriptions(self):
        """列出所有订阅"""
        print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"{Colors.CYAN}订阅列表{Colors.NC}")
        print(f"{Colors.CYAN}{'='*60}{Colors.NC}\n")

        if not self.config['subscriptions']:
            print(f"{Colors.YELLOW}没有配置任何订阅{Colors.NC}")
            return

        for name, sub in self.config['subscriptions'].items():
            status = f"{Colors.GREEN}启用{Colors.NC}" if sub.get('enabled', True) else f"{Colors.YELLOW}禁用{Colors.NC}"
            print(f"📦 {Colors.BLUE}{name}{Colors.NC}")
            print(f"   状态: {status}")
            print(f"   描述: {sub.get('description', '无')}")
            print(f"   URL: {sub['url'][:50]}...")

            # 检查配置文件是否存在
            config_file = self.clash_dir / f"{name}.yaml"
            if config_file.exists():
                size = config_file.stat().st_size / 1024  # KB
                mtime = datetime.fromtimestamp(config_file.stat().st_mtime)
                print(f"   文件: {Colors.GREEN}存在{Colors.NC} ({size:.1f} KB)")
                print(f"   更新: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"   文件: {Colors.YELLOW}不存在{Colors.NC}")
            print()

    def backup_config(self, config_name: str) -> Optional[Path]:
        """备份配置文件"""
        if not self.config['backup']['enabled']:
            return None

        config_file = self.clash_dir / f"{config_name}.yaml"
        if not config_file.exists():
            return None

        # 创建备份目录
        backup_dir = self.clash_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"{config_name}.{timestamp}.yaml"

        # 复制文件
        shutil.copy2(config_file, backup_file)
        print(f"{Colors.GREEN}✓ 备份已保存: {backup_file.name}{Colors.NC}")

        # 清理旧备份
        self.cleanup_old_backups(config_name)

        return backup_file

    def cleanup_old_backups(self, config_name: str):
        """清理旧备份文件"""
        max_backups = self.config['backup'].get('max_backups', 5)
        backup_dir = self.clash_dir / "backups"

        if not backup_dir.exists():
            return

        # 获取该配置的所有备份文件
        backups = sorted(
            backup_dir.glob(f"{config_name}.*.yaml"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        # 删除超出数量的备份
        for backup in backups[max_backups:]:
            backup.unlink()
            print(f"{Colors.YELLOW}⚠ 已删除旧备份: {backup.name}{Colors.NC}")

    def update_subscription(self, name: str) -> bool:
        """更新指定订阅"""
        if name not in self.config['subscriptions']:
            print(f"{Colors.RED}✗ 订阅不存在: {name}{Colors.NC}")
            return False

        sub = self.config['subscriptions'][name]

        if not sub.get('enabled', True):
            print(f"{Colors.YELLOW}⚠ 订阅已禁用: {name}{Colors.NC}")
            return False

        print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"{Colors.CYAN}更新订阅: {name}{Colors.NC}")
        print(f"{Colors.CYAN}{'='*60}{Colors.NC}\n")

        # 备份当前配置
        self.backup_config(name)

        # 下载新配置
        print(f"{Colors.YELLOW}正在下载配置...{Colors.NC}")
        config_file = self.clash_dir / f"{name}.yaml"
        temp_file = config_file.with_suffix('.yaml.tmp')

        try:
            response = requests.get(sub['url'], timeout=30)
            response.raise_for_status()

            # 检查内容
            if not response.content:
                print(f"{Colors.RED}✗ 下载的配置文件为空{Colors.NC}")
                return False

            # 保存到临时文件
            with open(temp_file, 'wb') as f:
                f.write(response.content)

            # 验证文件大小
            size = temp_file.stat().st_size
            if size < 100:  # 小于100字节可能是错误信息
                print(f"{Colors.RED}✗ 下载的配置文件异常 (大小: {size} bytes){Colors.NC}")
                temp_file.unlink()
                return False

            # 替换原文件
            shutil.move(str(temp_file), str(config_file))
            print(f"{Colors.GREEN}✓ 配置已更新 (大小: {size/1024:.1f} KB){Colors.NC}")

            # 显示节点数量
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    proxy_count = content.count('- {') + content.count('- name:')
                    print(f"{Colors.GREEN}✓ 代理节点数量: {proxy_count}{Colors.NC}")
            except:
                pass

            return True

        except requests.exceptions.RequestException as e:
            print(f"{Colors.RED}✗ 下载失败: {e}{Colors.NC}")
            if temp_file.exists():
                temp_file.unlink()
            return False
        except Exception as e:
            print(f"{Colors.RED}✗ 更新失败: {e}{Colors.NC}")
            if temp_file.exists():
                temp_file.unlink()
            return False

    def update_all(self):
        """更新所有启用的订阅"""
        print(f"\n{Colors.MAGENTA}{'='*60}{Colors.NC}")
        print(f"{Colors.MAGENTA}更新所有订阅{Colors.NC}")
        print(f"{Colors.MAGENTA}{'='*60}{Colors.NC}")

        enabled_subs = [
            name for name, sub in self.config['subscriptions'].items()
            if sub.get('enabled', True)
        ]

        if not enabled_subs:
            print(f"\n{Colors.YELLOW}没有启用的订阅{Colors.NC}")
            return

        success_count = 0
        for name in enabled_subs:
            if self.update_subscription(name):
                success_count += 1

        print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"{Colors.GREEN}✓ 更新完成: {success_count}/{len(enabled_subs)}{Colors.NC}")
        print(f"{Colors.CYAN}{'='*60}{Colors.NC}\n")

    def restart_clash(self):
        """重启 Clash 服务"""
        print(f"\n{Colors.YELLOW}正在重启 Clash 服务...{Colors.NC}")

        commands = [
            ["sudo", "launchctl", "kickstart", "-k", "system/io.github.clash-verge-rev.clash-verge-rev.service"],
            ["pkill", "-HUP", "clash"],
        ]

        for cmd in commands:
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                print(f"{Colors.GREEN}✓ Clash 服务已重启{Colors.NC}")
                return True
            except subprocess.CalledProcessError:
                continue
            except FileNotFoundError:
                continue

        print(f"{Colors.YELLOW}⚠ 无法自动重启，请手动重启 Clash 应用{Colors.NC}")
        return False

    def add_subscription(self, name: str, url: str, description: str = ""):
        """添加新订阅"""
        if name in self.config['subscriptions']:
            print(f"{Colors.YELLOW}⚠ 订阅已存在: {name}{Colors.NC}")
            return

        self.config['subscriptions'][name] = {
            "url": url,
            "enabled": True,
            "description": description
        }
        self.save_config()
        print(f"{Colors.GREEN}✓ 订阅已添加: {name}{Colors.NC}")

    def remove_subscription(self, name: str):
        """删除订阅"""
        if name not in self.config['subscriptions']:
            print(f"{Colors.RED}✗ 订阅不存在: {name}{Colors.NC}")
            return

        del self.config['subscriptions'][name]
        self.save_config()
        print(f"{Colors.GREEN}✓ 订阅已删除: {name}{Colors.NC}")

    def toggle_subscription(self, name: str):
        """启用/禁用订阅"""
        if name not in self.config['subscriptions']:
            print(f"{Colors.RED}✗ 订阅不存在: {name}{Colors.NC}")
            return

        sub = self.config['subscriptions'][name]
        sub['enabled'] = not sub.get('enabled', True)
        self.save_config()

        status = "启用" if sub['enabled'] else "禁用"
        print(f"{Colors.GREEN}✓ 订阅已{status}: {name}{Colors.NC}")


def main():
    parser = argparse.ArgumentParser(
        description='Clash 订阅管理器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s list                                    # 列出所有订阅
  %(prog)s update x-superflash                     # 更新指定订阅
  %(prog)s update-all                              # 更新所有订阅
  %(prog)s add myproxy "https://..." "我的代理"    # 添加新订阅
  %(prog)s remove myproxy                          # 删除订阅
  %(prog)s toggle myproxy                          # 启用/禁用订阅
        '''
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # list 命令
    subparsers.add_parser('list', help='列出所有订阅')

    # update 命令
    update_parser = subparsers.add_parser('update', help='更新指定订阅')
    update_parser.add_argument('name', help='订阅名称')

    # update-all 命令
    subparsers.add_parser('update-all', help='更新所有启用的订阅')

    # add 命令
    add_parser = subparsers.add_parser('add', help='添加新订阅')
    add_parser.add_argument('name', help='订阅名称')
    add_parser.add_argument('url', help='订阅URL')
    add_parser.add_argument('description', nargs='?', default='', help='订阅描述')

    # remove 命令
    remove_parser = subparsers.add_parser('remove', help='删除订阅')
    remove_parser.add_argument('name', help='订阅名称')

    # toggle 命令
    toggle_parser = subparsers.add_parser('toggle', help='启用/禁用订阅')
    toggle_parser.add_argument('name', help='订阅名称')

    # restart 命令
    subparsers.add_parser('restart', help='重启 Clash 服务')

    # 解析参数
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 执行命令
    try:
        manager = ClashSubscriptionManager()

        if args.command == 'list':
            manager.list_subscriptions()

        elif args.command == 'update':
            success = manager.update_subscription(args.name)
            if success and manager.config.get('auto_restart', True):
                manager.restart_clash()

        elif args.command == 'update-all':
            manager.update_all()
            if manager.config.get('auto_restart', True):
                manager.restart_clash()

        elif args.command == 'add':
            manager.add_subscription(args.name, args.url, args.description)

        elif args.command == 'remove':
            manager.remove_subscription(args.name)

        elif args.command == 'toggle':
            manager.toggle_subscription(args.name)

        elif args.command == 'restart':
            manager.restart_clash()

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}操作已取消{Colors.NC}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.RED}✗ 错误: {e}{Colors.NC}")
        sys.exit(1)


if __name__ == '__main__':
    main()
