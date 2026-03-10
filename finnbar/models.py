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
class RestockInfo:
    quantity: int
    earliest_date: str
    latest_date: str
    reliability: str  # "HIGH" or "LOW"


@dataclass
class CashCarryAvailability:
    stock: int
    probability: str
    updated_at: str
    restocks: list[RestockInfo] = field(default_factory=list)


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
    restocks: list[RestockInfo] = field(default_factory=list)
