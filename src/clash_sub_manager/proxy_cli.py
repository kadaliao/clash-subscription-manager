"""CLI entry point for proxy selection utilities."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import default_config_display, read_api_from_config, resolve_config_path
from .console import Colors
from .proxy_selector import ClashProxySelector


def build_parser(default_config: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Clash 代理节点选择器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  clash-proxy groups              # 查看策略组
  clash-proxy nodes               # 查看所有节点
  clash-proxy current             # 查看当前选择
  clash-proxy test                # 测试所有节点延迟
  clash-proxy switch PROXY HK01   # 切换节点
        """,
    )

    parser.add_argument("--config", default=default_config, help="配置文件路径")
    parser.add_argument("--api", help="Clash API 地址，覆盖配置文件")
    parser.add_argument("--secret", help="API 密钥，覆盖配置文件")

    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    subparsers.add_parser("groups", help="查看策略组")
    subparsers.add_parser("nodes", help="查看所有节点")
    subparsers.add_parser("current", help="查看当前选择")
    subparsers.add_parser("test", help="测试所有节点延迟")

    switch_parser = subparsers.add_parser("switch", help="切换节点")
    switch_parser.add_argument("group", help="策略组名称")
    switch_parser.add_argument("node", help="节点名称")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser(default_config_display())
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    config_path = resolve_config_path(args.config)
    if not config_path.exists():
        print(f"{Colors.RED}✗ 未找到配置文件: {config_path}{Colors.NC}")
        print(f"{Colors.YELLOW}  提示: 请先运行 clash-sub init-config 生成配置{Colors.NC}")
        return 1

    try:
        file_api, file_secret = read_api_from_config(config_path)
    except Exception as exc:
        print(f"{Colors.RED}✗ 读取 API 配置失败: {exc}{Colors.NC}")
        return 1

    api_url = args.api or file_api
    secret = args.secret if args.secret is not None else file_secret

    selector = ClashProxySelector(api_url=api_url, secret=secret)

    try:
        if args.command == "groups":
            selector.list_proxy_groups()
        elif args.command == "nodes":
            selector.list_all_nodes()
        elif args.command == "current":
            selector.get_current_selections()
        elif args.command == "test":
            selector.test_all_delays()
        elif args.command == "switch":
            selector.switch_proxy(args.group, args.node)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}操作已取消{Colors.NC}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
