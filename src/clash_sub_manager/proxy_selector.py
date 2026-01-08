"""Proxy selection helper built on Clash API."""

from __future__ import annotations

import sys
from typing import Dict, List, Optional, Tuple

import requests

from .console import Colors


class ClashProxySelector:
    """Interact with Clash proxy groups and nodes via the REST API."""

    def __init__(self, api_url: str, secret: Optional[str] = None):
        self.api_url = api_url.rstrip("/")
        self.secret = secret or ""
        self.headers = {"Authorization": f"Bearer {self.secret}"} if self.secret else {}

    def get_proxies(self) -> Dict:
        """Fetch proxies dict from Clash."""
        try:
            response = requests.get(f"{self.api_url}/proxies", headers=self.headers, timeout=5)
            response.raise_for_status()
            return response.json().get("proxies", {})
        except requests.exceptions.RequestException as exc:
            print(f"{Colors.RED}✗ 无法连接到 Clash API: {exc}{Colors.NC}")
            print(f"{Colors.YELLOW}提示：请确保 Clash 正在运行且 API 已启用{Colors.NC}")
            sys.exit(1)

    def list_proxy_groups(self) -> None:
        """Print all strategy groups and their members."""
        proxies = self.get_proxies()

        print(f"\n{Colors.CYAN}{'='*70}{Colors.NC}")
        print(f"{Colors.CYAN}Clash 代理策略组{Colors.NC}")
        print(f"{Colors.CYAN}{'='*70}{Colors.NC}\n")

        groups = {name: info for name, info in proxies.items() if "all" in info and name != "GLOBAL"}

        if not groups:
            print(f"{Colors.YELLOW}没有找到策略组{Colors.NC}")
            return

        for group_name, group_info in groups.items():
            group_type = group_info.get("type", "unknown")
            current = group_info.get("now", "")
            all_proxies = group_info.get("all", [])

            print(f"📦 {Colors.BLUE}{group_name}{Colors.NC} ({group_type})")
            print(f"   当前选择: {Colors.GREEN}{current}{Colors.NC}")
            print(f"   可用节点: {len(all_proxies)} 个")

            if all_proxies:
                preview = all_proxies[:5]
                print(f"   - {', '.join(preview)}")
                if len(all_proxies) > 5:
                    print(f"   ... 还有 {len(all_proxies) - 5} 个节点")
            print()

    def list_all_nodes(self) -> None:
        """Print all available nodes and their last latency measurement."""
        proxies = self.get_proxies()

        print(f"\n{Colors.CYAN}{'='*70}{Colors.NC}")
        print(f"{Colors.CYAN}所有可用节点{Colors.NC}")
        print(f"{Colors.CYAN}{'='*70}{Colors.NC}\n")

        nodes = {
            name: info
            for name, info in proxies.items()
            if "all" not in info and name not in ["DIRECT", "REJECT", "GLOBAL"]
        }

        if not nodes:
            print(f"{Colors.YELLOW}没有找到节点{Colors.NC}")
            return

        for index, (node_name, node_info) in enumerate(nodes.items(), 1):
            delay_str = format_delay(node_info.get("history", []))
            node_type = node_info.get("type", "unknown")
            print(f"{index:3d}. {Colors.BLUE}{node_name}{Colors.NC} [{node_type}] - 延迟: {delay_str}")

    def test_delay(self, proxy_name: str, timeout: int = 5000) -> Optional[int]:
        """Test a node delay value."""
        try:
            response = requests.get(
                f"{self.api_url}/proxies/{proxy_name}/delay",
                params={"timeout": timeout, "url": "http://www.gstatic.com/generate_204"},
                headers=self.headers,
                timeout=timeout / 1000 + 1,
            )
            response.raise_for_status()
            return response.json().get("delay", 0)
        except Exception:
            return None

    def test_all_delays(self) -> None:
        """Test every available node and print the fastest ones."""
        proxies = self.get_proxies()
        nodes = {
            name: info
            for name, info in proxies.items()
            if "all" not in info and name not in ["DIRECT", "REJECT", "GLOBAL"]
        }

        print(f"\n{Colors.CYAN}{'='*70}{Colors.NC}")
        print(f"{Colors.CYAN}测试节点延迟{Colors.NC}")
        print(f"{Colors.CYAN}{'='*70}{Colors.NC}\n")

        total = len(nodes)
        results: List[Tuple[str, int]] = []
        for index, node_name in enumerate(nodes.keys(), 1):
            print(f"[{index}/{total}] 测试 {node_name}...", end="\r")
            delay = self.test_delay(node_name)
            results.append((node_name, delay if delay is not None else 9999))

        results.sort(key=lambda item: item[1])
        print(f"\n{Colors.GREEN}测试完成！{Colors.NC}\n")

        for idx, (node_name, delay) in enumerate(results[:20], 1):
            delay_str = human_delay(delay)
            print(f"{idx:3d}. {Colors.BLUE}{node_name:40s}{Colors.NC} {delay_str}")

        if len(results) > 20:
            print(f"\n... 还有 {len(results) - 20} 个节点")

    def switch_proxy(self, group_name: str, proxy_name: str) -> bool:
        """Switch the selection for a given proxy group."""
        try:
            response = requests.put(
                f"{self.api_url}/proxies/{group_name}",
                headers={**self.headers, "Content-Type": "application/json"},
                json={"name": proxy_name},
                timeout=5,
            )
            response.raise_for_status()
            print(f"{Colors.GREEN}✓ 已切换 {group_name} 到 {proxy_name}{Colors.NC}")
            return True
        except requests.exceptions.RequestException as exc:
            print(f"{Colors.RED}✗ 切换失败: {exc}{Colors.NC}")
            return False

    def get_current_selections(self) -> None:
        """Display the current selection for each proxy group."""
        proxies = self.get_proxies()

        print(f"\n{Colors.CYAN}{'='*70}{Colors.NC}")
        print(f"{Colors.CYAN}当前代理选择{Colors.NC}")
        print(f"{Colors.CYAN}{'='*70}{Colors.NC}\n")

        groups = {name: info for name, info in proxies.items() if "all" in info and name != "GLOBAL"}

        for group_name, group_info in groups.items():
            current = group_info.get("now", "")
            group_type = group_info.get("type", "")
            delay_str = ""
            if current and current in proxies:
                delay_str = format_delay(proxies[current].get("history", []))

            print(
                f"📦 {Colors.BLUE}{group_name:30s}{Colors.NC} "
                f"[{group_type:10s}] -> {Colors.GREEN}{current}{Colors.NC} {delay_str}"
            )


def format_delay(history: List[Dict]) -> str:
    """Format the latest delay entry with color hints."""
    delay = 0
    if history:
        delay = history[-1].get("delay", 0)

    return human_delay(delay)


def human_delay(delay: int) -> str:
    """Convert delay int into colored string."""
    if delay == 0 or delay >= 9999:
        return f"{Colors.RED}超时{Colors.NC}"
    if delay < 200:
        return f"{Colors.GREEN}{delay}ms{Colors.NC}"
    if delay < 500:
        return f"{Colors.YELLOW}{delay}ms{Colors.NC}"
    return f"{Colors.RED}{delay}ms{Colors.NC}"
