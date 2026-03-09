"""Persistent configuration for FINNBAR."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

_CONFIG_DIR = Path.home() / ".config" / "finnbar"
_CONFIG_FILE = _CONFIG_DIR / "config.json"
_ENCODING = "utf-8"


@dataclass
class Config:
    country_code: str | None = None
    bu_code: str | None = None
    product_ids: list[str] = field(default_factory=list)


def _save(cfg: Config) -> None:
    """Persist the given Config to disk."""
    try:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _CONFIG_FILE.write_text(json.dumps(asdict(cfg), indent=2), encoding=_ENCODING)
    except OSError:
        pass


def load() -> Config:
    """Load config from disk. Returns a default Config if the file doesn't exist."""
    try:
        data = json.loads(_CONFIG_FILE.read_text(encoding=_ENCODING))
        return Config(**{k: v for k, v in data.items() if k in Config.__dataclass_fields__})
    except (FileNotFoundError, TypeError, json.JSONDecodeError):
        return Config()


def reset() -> None:
    """Reset the config to defaults and persist to disk."""
    _save(Config())


def update(**kwargs) -> None:
    """Update individual config fields and persist to disk."""
    cfg = load()
    for key, value in kwargs.items():
        if hasattr(cfg, key):
            setattr(cfg, key, value)
    _save(cfg)
