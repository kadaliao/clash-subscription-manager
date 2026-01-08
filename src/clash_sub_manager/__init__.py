"""Top-level package for Clash Subscription Manager."""

from __future__ import annotations

from importlib import metadata

from .proxy_selector import ClashProxySelector
from .subscription_manager import ClashSubscriptionManager

try:
    __version__ = metadata.version("clash-subscription-manager")
except metadata.PackageNotFoundError:  # pragma: no cover - dev installs
    __version__ = "0.0.0"

__all__ = [
    "ClashSubscriptionManager",
    "ClashProxySelector",
]
