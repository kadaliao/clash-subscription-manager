#!/usr/bin/env python3
"""
Clash 代理节点选择器
通过命令行管理 Clash 代理节点
"""

import json
import sys
import os
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple


def load_api_config(config_file: str = ".clash-api-config") -> Tuple[str, str]:
    """
    从配置文件加载 Clash API 配置

    返回: (api_url, secret)
    """
    # 尝试从脚本所在目录读取配置文件
    script_dir = Path(__file__).parent
    config_path = script_dir / config_file

    if not config_path.exists():
        return "http://127.0.0.1:9090", ""

    api_url = "http://127.0.0.1:9090"
    secret = ""

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 忽略注释和空行
                if not line or line.startswith('#'):
                    continue

                # 解析 KEY=VALUE 格式
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()

                    if key == 'CLASH_API_URL':
                        api_url = value
                    elif key == 'CLASH_API_SECRET':
                        secret = value
    except Exception as e:
        print(f"警告: 无法读取配置文件 {config_path}: {e}", file=sys.stderr)

    return api_url, secret


class Colors:
    """终端颜色"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'


class ClashProxySelector:
    """Clash 代理选择器"""

    def __init__(self, api_url: str = "http://127.0.0.1:9090", secret: str = ""):
        self.api_url = api_url.rstrip('/')
        self.secret = secret
        self.headers = {}
        if secret:
            self.headers['Authorization'] = f'Bearer {secret}'

    def get_proxies(self) -> Dict:
        """获取所有代理信息"""
        try:
            response = requests.get(
                f"{self.api_url}/proxies",
                headers=self.headers,
                timeout=5
            )
            response.raise_for_status()
            return response.json()['proxies']
        except requests.exceptions.RequestException as e:
            print(f"{Colors.RED}✗ 无法连接到 Clash API: {e}{Colors.NC}")
            print(f"{Colors.YELLOW}提示：请确保 Clash 正在运行且 API 已启用{Colors.NC}")
            sys.exit(1)

    def list_proxy_groups(self):
        """列出所有策略组及其节点"""
        proxies = self.get_proxies()

        print(f"\n{Colors.CYAN}{'='*70}{Colors.NC}")
        print(f"{Colors.CYAN}Clash 代理策略组{Colors.NC}")
        print(f"{Colors.CYAN}{'='*70}{Colors.NC}\n")

        # 过滤出策略组（有 all 属性的是策略组）
        groups = {
            name: info for name, info in proxies.items()
            if 'all' in info and name != 'GLOBAL'
        }

        if not groups:
            print(f"{Colors.YELLOW}没有找到策略组{Colors.NC}")
            return

        for group_name, group_info in groups.items():
            group_type = group_info.get('type', 'unknown')
            current = group_info.get('now', '')
            all_proxies = group_info.get('all', [])

            print(f"📦 {Colors.BLUE}{group_name}{Colors.NC} ({group_type})")
            print(f"   当前选择: {Colors.GREEN}{current}{Colors.NC}")
            print(f"   可用节点: {len(all_proxies)} 个")

            # 显示前 5 个节点
            if len(all_proxies) <= 5:
                nodes_to_show = all_proxies
            else:
                nodes_to_show = all_proxies[:5]
                print(f"   - {', '.join(nodes_to_show)}")
                print(f"   ... 还有 {len(all_proxies) - 5} 个节点")

            if len(all_proxies) <= 5:
                print(f"   - {', '.join(nodes_to_show)}")

            print()

    def list_all_nodes(self):
        """列出所有可用节点"""
        proxies = self.get_proxies()

        print(f"\n{Colors.CYAN}{'='*70}{Colors.NC}")
        print(f"{Colors.CYAN}所有可用节点{Colors.NC}")
        print(f"{Colors.CYAN}{'='*70}{Colors.NC}\n")

        # 过滤出实际的节点（不是策略组）
        nodes = {
            name: info for name, info in proxies.items()
            if 'all' not in info and name not in ['DIRECT', 'REJECT', 'GLOBAL']
        }

        if not nodes:
            print(f"{Colors.YELLOW}没有找到节点{Colors.NC}")
            return

        for i, (node_name, node_info) in enumerate(nodes.items(), 1):
            node_type = node_info.get('type', 'unknown')
            delay = node_info.get('history', [])

            # 获取最近的延迟
            if delay:
                last_delay = delay[-1].get('delay', 0)
                if last_delay == 0:
                    delay_str = f"{Colors.RED}超时{Colors.NC}"
                elif last_delay < 200:
                    delay_str = f"{Colors.GREEN}{last_delay}ms{Colors.NC}"
                elif last_delay < 500:
                    delay_str = f"{Colors.YELLOW}{last_delay}ms{Colors.NC}"
                else:
                    delay_str = f"{Colors.RED}{last_delay}ms{Colors.NC}"
            else:
                delay_str = f"{Colors.YELLOW}未测试{Colors.NC}"

            print(f"{i:3d}. {Colors.BLUE}{node_name}{Colors.NC} [{node_type}] - 延迟: {delay_str}")

    def test_delay(self, proxy_name: str, timeout: int = 5000) -> Optional[int]:
        """测试节点延迟"""
        try:
            response = requests.get(
                f"{self.api_url}/proxies/{proxy_name}/delay",
                params={
                    'timeout': timeout,
                    'url': 'http://www.gstatic.com/generate_204'
                },
                headers=self.headers,
                timeout=timeout/1000 + 1
            )
            response.raise_for_status()
            return response.json().get('delay', 0)
        except:
            return None

    def test_all_delays(self):
        """测试所有节点延迟"""
        proxies = self.get_proxies()

        # 只测试实际节点
        nodes = {
            name: info for name, info in proxies.items()
            if 'all' not in info and name not in ['DIRECT', 'REJECT', 'GLOBAL']
        }

        print(f"\n{Colors.CYAN}{'='*70}{Colors.NC}")
        print(f"{Colors.CYAN}测试节点延迟{Colors.NC}")
        print(f"{Colors.CYAN}{'='*70}{Colors.NC}\n")

        results = []
        for i, node_name in enumerate(nodes.keys(), 1):
            print(f"[{i}/{len(nodes)}] 测试 {node_name}...", end='\r')
            delay = self.test_delay(node_name)

            if delay:
                results.append((node_name, delay))
            else:
                results.append((node_name, 9999))  # 超时标记为 9999

        # 按延迟排序
        results.sort(key=lambda x: x[1])

        print(f"\n{Colors.GREEN}测试完成！{Colors.NC}\n")

        for i, (node_name, delay) in enumerate(results[:20], 1):  # 只显示前 20 个
            if delay == 9999:
                delay_str = f"{Colors.RED}超时{Colors.NC}"
            elif delay < 200:
                delay_str = f"{Colors.GREEN}{delay}ms{Colors.NC}"
            elif delay < 500:
                delay_str = f"{Colors.YELLOW}{delay}ms{Colors.NC}"
            else:
                delay_str = f"{Colors.RED}{delay}ms{Colors.NC}"

            print(f"{i:3d}. {Colors.BLUE}{node_name:40s}{Colors.NC} {delay_str}")

        if len(results) > 20:
            print(f"\n... 还有 {len(results) - 20} 个节点")

    def switch_proxy(self, group_name: str, proxy_name: str) -> bool:
        """切换策略组的节点"""
        try:
            response = requests.put(
                f"{self.api_url}/proxies/{group_name}",
                headers={**self.headers, 'Content-Type': 'application/json'},
                json={'name': proxy_name},
                timeout=5
            )
            response.raise_for_status()
            print(f"{Colors.GREEN}✓ 已切换 {group_name} 到 {proxy_name}{Colors.NC}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"{Colors.RED}✗ 切换失败: {e}{Colors.NC}")
            return False

    def get_current_selections(self):
        """显示当前选择的节点"""
        proxies = self.get_proxies()

        print(f"\n{Colors.CYAN}{'='*70}{Colors.NC}")
        print(f"{Colors.CYAN}当前代理选择{Colors.NC}")
        print(f"{Colors.CYAN}{'='*70}{Colors.NC}\n")

        groups = {
            name: info for name, info in proxies.items()
            if 'all' in info and name != 'GLOBAL'
        }

        for group_name, group_info in groups.items():
            current = group_info.get('now', '')
            group_type = group_info.get('type', '')

            # 获取当前节点的延迟
            if current and current in proxies:
                delay_info = proxies[current].get('history', [])
                if delay_info:
                    delay = delay_info[-1].get('delay', 0)
                    if delay == 0:
                        delay_str = f"{Colors.RED}超时{Colors.NC}"
                    elif delay < 200:
                        delay_str = f"{Colors.GREEN}{delay}ms{Colors.NC}"
                    elif delay < 500:
                        delay_str = f"{Colors.YELLOW}{delay}ms{Colors.NC}"
                    else:
                        delay_str = f"{Colors.RED}{delay}ms{Colors.NC}"
                else:
                    delay_str = f"{Colors.YELLOW}未测试{Colors.NC}"
            else:
                delay_str = ""

            print(f"📦 {Colors.BLUE}{group_name:30s}{Colors.NC} [{group_type:10s}] -> {Colors.GREEN}{current}{Colors.NC} {delay_str}")


def main():
    import argparse

    # 从配置文件加载默认值
    default_api_url, default_secret = load_api_config()

    parser = argparse.ArgumentParser(
        description='Clash 代理节点选择器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s groups              # 查看策略组
  %(prog)s nodes               # 查看所有节点
  %(prog)s current             # 查看当前选择
  %(prog)s test                # 测试所有节点延迟
  %(prog)s switch PROXY HK01   # 切换策略组 PROXY 到节点 HK01

配置:
  默认从 .clash-api-config 文件读取 API 配置
  命令行参数可以覆盖配置文件的设置
        '''
    )

    parser.add_argument('--api', default=default_api_url, help=f'Clash API 地址 (默认: {default_api_url})')
    parser.add_argument('--secret', default=default_secret, help='API 密钥')

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    subparsers.add_parser('groups', help='查看策略组')
    subparsers.add_parser('nodes', help='查看所有节点')
    subparsers.add_parser('current', help='查看当前选择')
    subparsers.add_parser('test', help='测试所有节点延迟')

    switch_parser = subparsers.add_parser('switch', help='切换节点')
    switch_parser.add_argument('group', help='策略组名称')
    switch_parser.add_argument('node', help='节点名称')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    selector = ClashProxySelector(args.api, args.secret)

    try:
        if args.command == 'groups':
            selector.list_proxy_groups()
        elif args.command == 'nodes':
            selector.list_all_nodes()
        elif args.command == 'current':
            selector.get_current_selections()
        elif args.command == 'test':
            selector.test_all_delays()
        elif args.command == 'switch':
            selector.switch_proxy(args.group, args.node)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}操作已取消{Colors.NC}")
        sys.exit(1)


if __name__ == '__main__':
    main()
