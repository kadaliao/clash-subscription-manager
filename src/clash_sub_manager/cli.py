"""CLI entry point for subscription management."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import resolve_api_config_path, resolve_config_path, write_sample_config
from .console import Colors
from .subscription_manager import ClashSubscriptionManager


def build_parser(default_config: Path, default_api_config: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Clash 订阅管理器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  clash-sub list                                    # 列出所有订阅
  clash-sub update x-superflash                     # 更新指定订阅
  clash-sub update-all                              # 更新所有订阅
  clash-sub init-config                             # 生成配置模板
        """,
    )

    parser.add_argument("--config", default=str(default_config), help="配置文件路径")
    parser.add_argument(
        "--api-config",
        default=str(default_api_config),
        help="Clash API 配置文件 (.clash-api-config)",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    subparsers.add_parser("list", help="列出所有订阅")

    update_parser = subparsers.add_parser("update", help="更新指定订阅")
    update_parser.add_argument("name", help="订阅名称")

    subparsers.add_parser("update-all", help="更新所有启用的订阅")

    add_parser = subparsers.add_parser("add", help="添加新订阅")
    add_parser.add_argument("name", help="订阅名称")
    add_parser.add_argument("url", help="订阅URL")
    add_parser.add_argument("description", nargs="?", default="", help="订阅描述")

    remove_parser = subparsers.add_parser("remove", help="删除订阅")
    remove_parser.add_argument("name", help="订阅名称")

    toggle_parser = subparsers.add_parser("toggle", help="启用/禁用订阅")
    toggle_parser.add_argument("name", help="订阅名称")

    restart_parser = subparsers.add_parser("restart", help="重新加载 Clash 服务")
    restart_parser.add_argument("--skip-check", action="store_true", help="跳过 Clash 配置检查")

    init_parser = subparsers.add_parser("init-config", help="生成示例配置")
    init_parser.add_argument("--path", help="输出配置路径 (默认同 --config)")
    init_parser.add_argument("--overwrite", action="store_true", help="覆盖已有文件")

    return parser


def main(argv: list[str] | None = None) -> int:
    default_config = resolve_config_path(None)
    default_api = resolve_api_config_path(None)
    parser = build_parser(default_config, default_api)
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "init-config":
        target = Path(args.path) if args.path else Path(args.config)
        try:
            path = write_sample_config(target, overwrite=args.overwrite)
            print(f"{Colors.GREEN}✓ 示例配置已写入: {path}{Colors.NC}")
            return 0
        except FileExistsError:
            print(f"{Colors.YELLOW}⚠ 文件已存在: {target}，使用 --overwrite 可以覆盖{Colors.NC}")
            return 1
        except OSError as exc:
            print(f"{Colors.RED}✗ 写入示例配置失败: {exc}{Colors.NC}")
            return 1

    config_path = Path(args.config).expanduser()
    if not config_path.exists():
        print(f"{Colors.YELLOW}⚠ 未找到配置文件: {config_path}{Colors.NC}")
        print(
            f"{Colors.YELLOW}  提示: 首次使用请执行 `clash-sub init-config --path {config_path}` 并填写订阅信息{Colors.NC}"
        )
        return 1

    try:
        manager = ClashSubscriptionManager(config_path=config_path, api_config_path=args.api_config)
    except Exception as exc:
        print(f"{Colors.RED}✗ 初始化失败: {exc}{Colors.NC}")
        return 1

    try:
        if args.command == "list":
            manager.list_subscriptions()
        elif args.command == "update":
            manager.update_subscription(args.name)
        elif args.command == "update-all":
            manager.update_all()
        elif args.command == "add":
            manager.add_subscription(args.name, args.url, args.description)
        elif args.command == "remove":
            manager.remove_subscription(args.name)
        elif args.command == "toggle":
            manager.toggle_subscription(args.name)
        elif args.command == "restart":
            manager.restart_clash(skip_check=args.skip_check)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}操作已取消{Colors.NC}")
        return 1
    except Exception as exc:
        print(f"{Colors.RED}✗ 错误: {exc}{Colors.NC}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
