"""Data models for FINNBAR."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Store:
    bu_code: str
    name: str
    country_code: str
    country: str
    coordinates: list[float] = field(default_factory=list)


@dataclass
class StockInfo:
    product_id: str
    bu_code: str
    store_name: str
    country_code: str
    country: str
    stock: int
    probability: str
    updated_at: str
