"""Persistent configuration for FINNBAR."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

_CONFIG_DIR = Path.home() / ".finnbar"
_CONFIG_FILE = _CONFIG_DIR / "config.json"
_ENCODING = "utf-8"


@dataclass
class Config:
    country_code: str | None = None
    store: str | None = None
    product_ids: list[str] = field(default_factory=list)


def load() -> Config:
    """Load config from disk. Returns a default Config if the file doesn't exist."""
    try:
        data = json.loads(_CONFIG_FILE.read_text(encoding=_ENCODING))
        return Config(**{k: v for k, v in data.items() if k in Config.__dataclass_fields__})
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return Config()


def save(cfg: Config) -> None:
    """Persist the given Config to disk."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(asdict(cfg), indent=2), encoding=_ENCODING)
