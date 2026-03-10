"""Rendering helpers for converting API data into Textual table rows."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import ClassVar

from rich.text import Text

from finnbar import api


@dataclass
class StockResult:
    """One table row — fields are declared in header column order."""

    HEADERS: ClassVar[dict[str, str]] = {
        "product_id": "Product ID",
        "country": "Country",
        "store": "Store",
        "stock": "Stock",
        "availability": "Availability",
        "updated": "Updated",
        "restock_period": "Restock Period",
        "restock_quantity": "Restock Quantity",
        "restock_reliability": "Restock Reliability",
    }
    ZERO_STOCK_KEYS: ClassVar[frozenset[str]] = frozenset({"OUT_OF_STOCK"})
    PROBABILITY_DISPLAY: ClassVar[dict[str, tuple[str, str]]] = {
        "HIGH_IN_STOCK": ("High", "bold green"),
        "LOW_IN_STOCK": ("Low", "bold yellow"),
        "OUT_OF_STOCK": ("Unavailable", "bold red"),
    }
    RELIABILITY_DISPLAY: ClassVar[dict[str, tuple[str, str]]] = {
        "HIGH": ("High", "bold green"),
        "LOW": ("Low", "bold yellow"),
    }
    DISPLAY_FALLBACK: ClassVar[tuple[str, str]] = ("Unknown", "dim")

    product_id: str
    country: str
    store: str
    stock: str
    availability: Text
    updated: str
    restock_period: str
    restock_quantity: str
    restock_reliability: str | Text

    @classmethod
    def column_headers(cls) -> tuple[str, ...]:
        return tuple(cls.HEADERS[f.name] for f in dataclasses.fields(cls))

    def cells(self) -> tuple:
        return (
            self.product_id,
            self.country,
            self.store,
            self.stock,
            self.availability,
            self.updated,
            self.restock_period,
            self.restock_quantity,
            self.restock_reliability,
        )


def _build_restock_cells(restocks: list[api.RestockInfo]) -> tuple[str, str, str | Text]:
    if not restocks:
        return "", "", ""

    earliest_restock = restocks[0]
    if earliest_restock.earliest_date and earliest_restock.latest_date and earliest_restock.earliest_date != earliest_restock.latest_date:
        period = f"{earliest_restock.earliest_date} – {earliest_restock.latest_date}"
    else:
        period = earliest_restock.earliest_date or earliest_restock.latest_date

    quantity = str(earliest_restock.quantity) if earliest_restock.quantity else ""

    reliability: str | Text = ""
    if earliest_restock.reliability:
        reliability_label, reliability_color = (
            StockResult.RELIABILITY_DISPLAY.get(earliest_restock.reliability, StockResult.DISPLAY_FALLBACK)
        )
        reliability = Text(reliability_label, style=reliability_color)

    return period, quantity, reliability


def _build_availability_cell(probability: str) -> Text:
    availability_label, availability_color = (
        StockResult.PROBABILITY_DISPLAY.get(probability, StockResult.DISPLAY_FALLBACK)
    )
    return Text(availability_label, style=availability_color)


def build_stock_result(result: api.StockInfo) -> StockResult:
    stock = str(result.stock) if result.probability not in StockResult.ZERO_STOCK_KEYS else "0"
    availability = _build_availability_cell(result.probability)
    restock_period, restock_quantity, restock_reliability = _build_restock_cells(result.restocks)

    return StockResult(
        product_id=result.product_id,
        country=f"{result.country_code.upper()} – {result.country}",
        store=result.store_name,
        stock=stock,
        availability=availability,
        updated=result.updated_at,
        restock_period=restock_period,
        restock_quantity=restock_quantity,
        restock_reliability=restock_reliability,
    )
