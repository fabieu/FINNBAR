"""IKEA Ingka API client for product availability."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

_DATA_FILE = Path(__file__).parent / "stores_data.json"
_CLIENT_ID = "da465052-7912-43b2-82fa-9dc39cdccef8"
_BASE_URL = "https://api.ingka.ikea.com"
_TIMEOUT = 10


def _load_data() -> dict[str, Any]:
    with _DATA_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


_DATA = _load_data()
_STORES: list[dict[str, Any]] = _DATA["stores"]
_COUNTRIES: dict[str, str] = _DATA["countries"]


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


def get_country_codes() -> list[str]:
    """Return sorted list of supported country codes."""
    return sorted(_COUNTRIES.keys())


def get_country_name(code: str) -> str:
    """Return country name for a given country code."""
    return _COUNTRIES.get(code, code.upper())


def get_stores(country_code: str) -> list[Store]:
    """Return list of stores for the given country code."""
    cc = country_code.lower().strip()
    return [
        Store(
            bu_code=s["buCode"],
            name=s["name"],
            country_code=s["countryCode"],
            country=s.get("country", ""),
            coordinates=s.get("coordinates", []),
        )
        for s in _STORES
        if s["countryCode"] == cc
    ]


def get_all_stores() -> list[Store]:
    """Return all stores."""
    return [
        Store(
            bu_code=s["buCode"],
            name=s["name"],
            country_code=s["countryCode"],
            country=s.get("country", ""),
            coordinates=s.get("coordinates", []),
        )
        for s in _STORES
    ]


def check_availability(country_code: str, product_ids: list[str]) -> list[StockInfo]:
    """Check product availability across all stores in a country.

    Args:
        country_code: Two-letter country code (e.g. 'de', 'us').
        product_ids: List of IKEA product IDs to check.

    Returns:
        List of StockInfo objects with availability data.

    Raises:
        requests.HTTPError: On HTTP errors.
        ValueError: If the API response is unexpected.
    """
    cc = country_code.lower().strip()
    item_nos = ",".join(p.strip() for p in product_ids)
    url = f"{_BASE_URL}/cia/availabilities/ru/{cc}"
    headers = {
        "x-client-id": _CLIENT_ID,
        "accept": "application/json;version=1",
    }
    params = {
        "expand": "StoresList,Restocks",
        "itemNos": item_nos,
    }
    resp = requests.get(url, headers=headers, params=params, timeout=_TIMEOUT)
    resp.raise_for_status()

    data = resp.json()
    if not isinstance(data.get("availabilities"), list):
        raise ValueError("Unexpected API response structure")

    # Build a lookup for store metadata
    store_lookup: dict[str, Store] = {s.bu_code: s for s in get_stores(cc)}

    results: list[StockInfo] = []
    for item in data["availabilities"]:
        # Only process store-type availability (classUnitType == "STO")
        if item.get("classUnitKey", {}).get("classUnitType") != "STO":
            continue
        bu_code = item.get("classUnitKey", {}).get("classUnitCode", "")
        if bu_code not in store_lookup:
            continue
        store = store_lookup[bu_code]
        product_id = item.get("itemKey", {}).get("itemNo", "")

        stock = 0
        probability = ""
        updated_at = ""

        if item.get("availableForCashCarry"):
            avail = (
                item.get("buyingOption", {})
                .get("cashCarry", {})
                .get("availability", {})
            )
            if avail:
                stock = int(avail.get("quantity", 0) or 0)
                probability = (
                    avail.get("probability", {}).get("thisDay", {}).get("messageType", "")
                )
                updated_at = avail.get("updateDateTime", "")
                # Trim to date only for display
                if "T" in updated_at:
                    updated_at = updated_at.split("T")[0]

        results.append(
            StockInfo(
                product_id=product_id,
                bu_code=bu_code,
                store_name=store.name,
                country_code=store.country_code,
                country=store.country,
                stock=stock,
                probability=probability,
                updated_at=updated_at,
            )
        )

    # Sort by store name then product id
    results.sort(key=lambda x: (x.store_name, x.product_id))
    return results
