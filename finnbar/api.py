"""IKEA Ingka API client for product availability."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from finnbar.models import Store, StockInfo

_DATA_FILE = Path(__file__).parent / "stores.json"
_CLIENT_ID = "da465052-7912-43b2-82fa-9dc39cdccef8"
_BASE_URL = "https://api.ingka.ikea.com"
_TIMEOUT = 10


def _load_data() -> dict[str, Any]:
    with _DATA_FILE.open(encoding="utf-8") as fh:
        return json.load(fh)


_DATA = _load_data()
_STORES: list[dict[str, Any]] = _DATA["stores"]
_COUNTRIES: dict[str, str] = _DATA["countries"]


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


def check_availability(
        country_code: str,
        product_ids: list[str],
        bu_code: str | None = None,
) -> list[StockInfo]:
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
        store_code = item.get("classUnitKey", {}).get("classUnitCode", "")
        if store_code not in store_lookup:
            continue
        store = store_lookup[store_code]
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
                updated_at = avail.get("updateDateTime")
                if updated_at:
                    try:
                        updated_at = datetime.fromisoformat(updated_at).strftime("%Y-%m-%d %H:%M")
                    except ValueError:
                        pass
                # Format datetime for display:
                #   "2024-01-15T04:14:05.302Z" → "2024-01-15 04:14"
                #   date-only string  → unchanged
                if "T" in updated_at:
                    date_part, time_part = updated_at.split("T", 1)
                    # Take up to 5 chars of the time ("HH:MM"); fall back to
                    # the full time string if it's shorter than expected.
                    time_short = time_part[:5] if len(time_part) >= 5 else time_part
                    updated_at = f"{date_part} {time_short}"

        results.append(
            StockInfo(
                product_id=product_id,
                bu_code=store_code,
                store_name=store.name,
                country_code=store.country_code,
                country=store.country,
                stock=stock,
                probability=probability,
                updated_at=updated_at,
            )
        )

    # Sort by store name then product id, and optionally filter by store
    if bu_code:
        results = [r for r in results if r.bu_code == bu_code]
    results.sort(key=lambda x: (x.store_name, x.product_id))
    return results
