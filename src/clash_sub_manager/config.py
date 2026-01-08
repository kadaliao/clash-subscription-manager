"""Helpers for locating config files and shipping sample templates."""

from __future__ import annotations

import json
import os
from importlib import resources
from pathlib import Path
from typing import Dict, Optional, Tuple

CONFIG_FILENAME = "config.json"
API_CONFIG_FILENAME = ".clash-api-config"
ENV_CONFIG_PATH = "CLASH_SUB_CONFIG"
ENV_API_CONFIG_PATH = "CLASH_API_CONFIG"
DEFAULT_CONFIG_DIR_STR = "~/.config/clash-sub-manager"
DEFAULT_CONFIG_DIR = Path(os.path.expanduser(DEFAULT_CONFIG_DIR_STR))
DEFAULT_WORK_DIR = DEFAULT_CONFIG_DIR
DEFAULT_API_URL = "http://127.0.0.1:9090"
DEFAULT_API_SECRET = ""
SAMPLE_API_CONFIG = {"url": DEFAULT_API_URL, "secret": ""}
COMMON_API_CONFIG_FILES = [
    ".clash-api-config",
    "~/.clash-api-config",
    "~/.config/mihomo-party/.clash-api-config",
    "~/.config/clash-verge/.clash-api-config",
    "~/Library/Application Support/mihomo-party/.clash-api-config",
]
COMMON_PARTY_DIRS = [
    "~/Library/Application Support/mihomo-party",
    "~/Library/Application Support/Clash Verge/mihomo-party",
    "~/.config/mihomo-party",
    "~/.config/clash-verge/mihomo-party",
    "~/AppData/Roaming/mihomo-party",
]


def _expand(path: Path) -> Path:
    return Path(path).expanduser()


def default_config_path() -> Path:
    """Return the standard config path under ~/.config."""
    return _expand(DEFAULT_CONFIG_DIR / CONFIG_FILENAME)


def default_config_display() -> str:
    return f"{DEFAULT_CONFIG_DIR_STR}/{CONFIG_FILENAME}"


def resolve_config_path(path: Optional[str | Path]) -> Path:
    """Return the config path to use, preferring CLI/env overrides."""
    candidate = path or os.getenv(ENV_CONFIG_PATH)
    if candidate:
        return _expand(Path(candidate)).resolve()

    cwd_candidate = Path.cwd() / CONFIG_FILENAME
    if cwd_candidate.exists():
        return cwd_candidate

    return default_config_path()


def get_sample_config_text() -> str:
    """Return the bundled sample config JSON."""
    sample = resources.files(__package__).joinpath("data/config.json.sample")
    return sample.read_text(encoding="utf-8")


def write_sample_config(
    target: Path,
    overwrite: bool = False,
    overrides: Optional[Dict[str, str]] = None,
) -> Path:
    """Write the sample config to the desired path."""
    target = _expand(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists() and not overwrite:
        raise FileExistsError(f"{target} already exists")

    data = json.loads(get_sample_config_text())
    overrides = overrides or {}
    for key, value in overrides.items():
        if value is None:
            continue
        data[key] = value

    data.setdefault("api", SAMPLE_API_CONFIG.copy())
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def detect_clash_party_dir() -> Optional[Path]:
    """Best-effort detection of Clash Party directory."""
    candidates = []
    env_dir = os.getenv("CLASH_PARTY_DIR")
    if env_dir:
        candidates.append(env_dir)

    candidates.extend(COMMON_PARTY_DIRS)

    for candidate in candidates:
        path = _expand(Path(candidate))
        if (path / "profile.yaml").exists():
            return path

    # fallback: scan common roots for profile.yaml
    search_roots = [
        Path(os.path.expanduser("~/Library/Application Support")),
        Path(os.path.expanduser("~/.config")),
        Path(os.path.expanduser("~/AppData/Roaming")),
    ]

    patterns = ["*/profile.yaml", "*/*/profile.yaml"]
    for root in search_roots:
        if not root.exists():
            continue
        for pattern in patterns:
            for sub in root.glob(pattern):
                party_dir = sub.parent
                if party_dir.name == "profiles":
                    party_dir = party_dir.parent
                return party_dir

    return None


def _parse_api_file(path: Path) -> Optional[Tuple[str, str]]:
    try:
        content = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    url = None
    secret = ""
    for line in content:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = [item.strip() for item in line.split("=", 1)]
        if key == "CLASH_API_URL":
            url = value or url
        elif key == "CLASH_API_SECRET":
            secret = value

    if not url:
        return None
    return url, secret


def detect_api_credentials() -> Optional[Tuple[str, str]]:
    env_url = os.getenv("CLASH_API_URL")
    env_secret = os.getenv("CLASH_API_SECRET")
    if env_url:
        return env_url, env_secret or ""

    candidate_paths = []
    env_config = os.getenv(ENV_API_CONFIG_PATH)
    if env_config:
        candidate_paths.append(env_config)
    candidate_paths.extend(COMMON_API_CONFIG_FILES[1:])

    for candidate in candidate_paths:
        path = _expand(Path(candidate))
        if not path.exists():
            continue
        result = _parse_api_file(path)
        if result:
            return result

    return None


def read_api_from_config(path: Optional[str | Path] = None) -> Tuple[str, str]:
    config_path = resolve_config_path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"未找到配置文件: {config_path}")

    with open(config_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    api_cfg = data.get("api", {}) or {}
    url = os.getenv("CLASH_API_URL") or api_cfg.get("url")
    if not url:
        raise ValueError("config.json 中缺少 api.url，请先运行 clash-sub init-config 或手动填写")
    secret = os.getenv("CLASH_API_SECRET", api_cfg.get("secret", ""))

    return url, secret
