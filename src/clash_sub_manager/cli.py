"""CLI entry point for subscription management."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import (
    default_api_config_display,
    default_api_config_path,
    default_config_display,
    default_config_path,
    detect_clash_party_dir,
    resolve_api_config_path,
    resolve_config_path,
    write_sample_config,
)
from .console import Colors
from .subscription_manager import ClashSubscriptionManager


def build_parser(config_display: str, api_display: str) -> argparse.ArgumentParser:
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

    parser.add_argument(
        "--config",
        default=None,
        help=f"配置文件路径 (默认: {config_display})",
    )
    parser.add_argument(
        "--api-config",
        default=None,
        help=f"Clash API 配置文件 (.clash-api-config) (默认: {api_display})",
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
    init_parser.add_argument("--path", help="输出配置路径 (默认: ~/.config/clash-sub-manager/config.json)")
    init_parser.add_argument("--overwrite", action="store_true", help="覆盖已有文件")

    import_api_parser = subparsers.add_parser("import-api", help="将 API 配置写入 .clash-api-config 文件")
    import_api_parser.add_argument("--path", help="API 配置文件输出路径 (默认: ~/.config/clash-sub-manager/.clash-api-config)")

    import_party_parser = subparsers.add_parser("import-party", help="从 Clash Party 导入订阅")
    import_party_parser.add_argument("--overwrite", action="store_true", help="覆盖同名订阅")
    import_party_parser.add_argument("--prefix", default="", help="为导入的订阅名称添加前缀")

    return parser


def humanize_path(path: Path) -> str:
    expanded = path.expanduser()
    try:
        home = Path.home()
        return f"~/{expanded.relative_to(home)}"
    except (ValueError, RuntimeError):
        return str(expanded)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser(default_config_display(), default_api_config_display())
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    config_path = (
        Path(args.config).expanduser()
        if args.config
        else resolve_config_path(None)
    )
    api_config_path = (
        Path(args.api_config).expanduser()
        if args.api_config
        else resolve_api_config_path(None)
    )

    if args.command == "init-config":
        default_target = config_path if args.config else default_config_path()
        target = Path(args.path).expanduser() if args.path else default_target
        overrides = {"work_dir": str(target.parent)}
        detected_party = detect_clash_party_dir()
        if detected_party:
            overrides["clash_party_dir"] = str(detected_party)
            print(
                f"{Colors.GREEN}✓ 已检测到 Clash Party 配置目录: {humanize_path(detected_party)}{Colors.NC}"
            )
        else:
            print(
                f"{Colors.YELLOW}⚠ 未检测到 Clash Party 配置目录，稍后可在配置文件中手动设置 `clash_party_dir`{Colors.NC}"
            )
        try:
            path = write_sample_config(target, overwrite=args.overwrite, overrides=overrides)
            print(f"{Colors.GREEN}✓ 示例配置已写入: {humanize_path(path)}{Colors.NC}")
            return 0
        except FileExistsError:
            print(f"{Colors.YELLOW}⚠ 文件已存在: {humanize_path(target)}，使用 --overwrite 可以覆盖{Colors.NC}")
            return 1
        except OSError as exc:
            print(f"{Colors.RED}✗ 写入示例配置失败: {exc}{Colors.NC}")
            return 1

    if not config_path.exists():
        human_path = humanize_path(config_path)
        hint_cmd = "clash-sub init-config" if not args.config else f"clash-sub init-config --path {human_path}"
        print(f"{Colors.YELLOW}⚠ 未找到配置文件: {human_path}{Colors.NC}")
        print(f"{Colors.YELLOW}  提示: 首次使用请执行 `{hint_cmd}` 并填写订阅信息{Colors.NC}")
        return 1

    try:
        manager = ClashSubscriptionManager(config_path=config_path, api_config_path=api_config_path)
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
        elif args.command == "import-api":
            manager.write_api_config_file(args.path)
        elif args.command == "import-party":
            manager.import_subscriptions_from_party(overwrite=args.overwrite, prefix=args.prefix or "")
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}操作已取消{Colors.NC}")
        return 1
    except Exception as exc:
        print(f"{Colors.RED}✗ 错误: {exc}{Colors.NC}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
