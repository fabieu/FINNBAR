"""IKEA Ingka API client for product availability."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from finnbar.models import CashCarryAvailability, RestockInfo, Store, StockInfo

_CLIENT_ID = "da465052-7912-43b2-82fa-9dc39cdccef8"
_BASE_URL = "https://api.ingka.ikea.com"


def _load_data() -> dict[str, Any]:
    data_file = Path(__file__).parent / "stores.json"

    with data_file.open(encoding="utf-8") as df:
        return json.load(df)


_DATA = _load_data()
_STORES: list[dict[str, Any]] = _DATA["stores"]
_COUNTRIES: dict[str, str] = _DATA["countries"]


def get_country_codes() -> list[str]:
    """Return sorted list of supported country codes."""
    return sorted(_COUNTRIES.keys())


def get_country_name(country_code: str) -> str:
    """Return country name for a given country code."""
    return _COUNTRIES.get(country_code, country_code.upper())


def get_stores(country_code: str) -> list[Store]:
    """Return list of stores for a given country code."""
    return [
        Store(
            bu_code=store["buCode"],
            name=store["name"],
            country_code=store["countryCode"],
            country=store.get("country", ""),
            coordinates=store.get("coordinates", []),
        )
        for store in _STORES
        if store["countryCode"] == country_code.lower().strip()
    ]


def _format_date(dt_str: str | None, fmt: str) -> str:
    """Parse an ISO datetime string and reformat it; return the original on failure."""
    if not dt_str:
        return ""

    try:
        return datetime.fromisoformat(dt_str).strftime(fmt)
    except ValueError:
        return dt_str


def _parse_restock(restock: dict[str, Any]) -> RestockInfo:
    return RestockInfo(
        quantity=int(restock.get("quantity", 0) or 0),
        earliest_date=_format_date(restock.get("earliestDate"), "%Y-%m-%d"),
        latest_date=_format_date(restock.get("latestDate"), "%Y-%m-%d"),
        reliability=restock.get("reliability", ""),
    )


def _parse_cash_carry(item: dict[str, Any]) -> CashCarryAvailability:
    """Extract stock, probability, updated_at and restocks from an availability item."""
    item_available = (
        item.get("buyingOption", {}).get("cashCarry", {}).get("availability", {})
    )

    if item_available:
        return CashCarryAvailability(
            stock=int(item_available.get("quantity", 0) or 0),
            probability=item_available.get("probability", {}).get("thisDay", {}).get("messageType", ""),
            updated_at=_format_date(item_available.get("updateDateTime"), "%Y-%m-%d %H:%M"),
            restocks=[_parse_restock(r) for r in item_available.get("restocks") or []],
        )
    else:
        return CashCarryAvailability(
            stock=0,
            probability="",
            updated_at="",
            restocks=[]
        )


def _parse_availability_item(item: dict[str, Any], store_lookup: dict[str, Store]) -> StockInfo | None:
    """Return a StockInfo for a store-type availability item, or None to skip."""
    if item.get("classUnitKey", {}).get("classUnitType") != "STO":
        return None

    store_code = item.get("classUnitKey", {}).get("classUnitCode", "")
    if store_code not in store_lookup:
        return None

    product_id = item.get("itemKey", {}).get("itemNo", "")

    store = store_lookup[store_code]
    cash_carry_availability = _parse_cash_carry(item)

    return StockInfo(
        product_id=product_id,
        bu_code=store_code,
        store_name=store.name,
        country_code=store.country_code,
        country=store.country,
        stock=cash_carry_availability.stock,
        probability=cash_carry_availability.probability,
        updated_at=cash_carry_availability.updated_at,
        restocks=cash_carry_availability.restocks,
    )


def check_availability(country_code: str, product_ids: list[str], bu_code: str | None = None) -> list[StockInfo]:
    """Check product availability across stores in a country.

    Args:
        country_code: Two-letter country code (e.g. 'de', 'us').
        product_ids: List of IKEA product IDs to check.
        bu_code: Optional store ID to filter results. When omitted, all stores
            in the country are returned.

    Returns:
        List of StockInfo objects with availability data.

    Raises:
        requests.HTTPError: On HTTP errors.
        ValueError: If the API response is unexpected.
    """
    cc = country_code.lower().strip()
    url = f"{_BASE_URL}/cia/availabilities/ru/{cc}"
    headers = {
        "x-client-id": _CLIENT_ID,
        "accept": "application/json;version=1",
    }
    params = {
        "expand": "StoresList,Restocks",
        "itemNos": ",".join(product_id.strip() for product_id in product_ids),
    }
    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    if not isinstance(data.get("availabilities"), list):
        raise ValueError("Unexpected API response structure")

    store_lookup: dict[str, Store] = {store.bu_code: store for store in get_stores(cc)}

    results = [
        parsed for item in data["availabilities"]
        if (parsed := _parse_availability_item(item, store_lookup)) is not None
    ]

    if bu_code:
        results = [result for result in results if result.bu_code == bu_code]

    results.sort(key=lambda x: (x.store_name, x.product_id))

    return results
