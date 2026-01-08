"""Helpers for locating config files and shipping sample templates."""

from __future__ import annotations

import os
import json
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
DEFAULT_API_CONFIG_STR = f"{DEFAULT_CONFIG_DIR_STR}/{API_CONFIG_FILENAME}"
DEFAULT_API_URL = "http://127.0.0.1:9090"
DEFAULT_API_SECRET = ""
SAMPLE_API_CONFIG = {"url": DEFAULT_API_URL, "secret": ""}
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


def default_api_config_path() -> Path:
    """Return the standard API config path under ~/.config."""
    return _expand(DEFAULT_CONFIG_DIR / API_CONFIG_FILENAME)


def default_api_config_display() -> str:
    return DEFAULT_API_CONFIG_STR


def resolve_config_path(path: Optional[str | Path]) -> Path:
    """Return the config path to use, preferring CLI/env overrides."""
    candidate = path or os.getenv(ENV_CONFIG_PATH)
    if candidate:
        return _expand(Path(candidate)).resolve()

    cwd_candidate = Path.cwd() / CONFIG_FILENAME
    if cwd_candidate.exists():
        return cwd_candidate

    return default_config_path()


def resolve_api_config_path(path: Optional[str | Path]) -> Path:
    """Return the API config path, respecting overrides and defaults."""
    candidate = path or os.getenv(ENV_API_CONFIG_PATH)
    if candidate:
        return _expand(Path(candidate)).resolve()

    cwd_candidate = Path.cwd() / API_CONFIG_FILENAME
    if cwd_candidate.exists():
        return cwd_candidate

    return default_api_config_path()


def load_api_config(path: Optional[str | Path] = None) -> Tuple[str, str]:
    """Load API config from file/env and fall back to defaults."""
    api_url = os.getenv("CLASH_API_URL", DEFAULT_API_URL)
    secret = os.getenv("CLASH_API_SECRET", DEFAULT_API_SECRET)
    target = resolve_api_config_path(path)

    if not target.exists():
        return api_url, secret

    try:
        with open(target, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = [item.strip() for item in line.split("=", 1)]
                if key == "CLASH_API_URL":
                    api_url = value or api_url
                elif key == "CLASH_API_SECRET":
                    secret = value or secret
    except OSError:
        return api_url, secret

    return api_url, secret


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
