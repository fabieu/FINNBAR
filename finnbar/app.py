"""FINNBAR – Textual TUI for checking IKEA product availability."""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    LoadingIndicator,
    Select,
    Static,
)
from textual.containers import Container, Horizontal, Vertical

from finnbar import api

if TYPE_CHECKING:
    pass

_COUNTRIES = api.get_country_codes()
_COUNTRY_OPTIONS: list[tuple[str, str]] = [
    (f"{code.upper()} – {api.get_country_name(code)}", code)
    for code in _COUNTRIES
]

_PROBABILITY_ICONS = {
    "HIGH_IN_STOCK": "🟢",
    "LOW_IN_STOCK": "🟡",
    "OUT_OF_STOCK": "🔴",
}


class FinnbarApp(App[None]):
    """FINNBAR – IKEA availability checker TUI."""

    TITLE = "FINNBAR"
    SUB_TITLE = "IKEA Availability Checker"
    CSS_PATH = "app.tcss"
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+s", "search_stores", "Search Stores", show=True),
        Binding("ctrl+k", "check_stock", "Check Stock", show=True),
        Binding("ctrl+x", "clear", "Clear", show=True),
    ]

    _state: reactive[str] = reactive("idle")  # idle | loading | stores | stock | error

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="app-grid"):
            # ── Sidebar ────────────────────────────────────────────────
            with Vertical(id="sidebar"):
                yield Label("Country")
                yield Select(
                    _COUNTRY_OPTIONS,
                    prompt="Select country…",
                    id="country-select",
                    allow_blank=False,
                    value=_COUNTRY_OPTIONS[0][1],
                )

                yield Label("Product ID(s)")
                yield Input(
                    placeholder="e.g. 40299687, S69022537",
                    id="product-input",
                )

                yield Button("🏪  Search Stores", id="search-stores-btn", variant="primary")
                yield Button("📦  Check Stock", id="check-stock-btn", variant="success")
                yield Button("🗑️  Clear", id="clear-btn")

            # ── Main area ──────────────────────────────────────────────
            with Container(id="main-area"):
                yield Static(
                    "Select a country and press [b]Search Stores[/b] to list stores,\n"
                    "or enter a product ID and press [b]Check Stock[/b] to view availability.",
                    id="empty-state",
                )

        yield Footer()

    # ── Actions ────────────────────────────────────────────────────────

    def action_search_stores(self) -> None:
        self.query_one("#search-stores-btn", Button).press()

    def action_check_stock(self) -> None:
        self.query_one("#check-stock-btn", Button).press()

    def action_clear(self) -> None:
        self.query_one("#clear-btn", Button).press()

    # ── Button handler ─────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search-stores-btn":
            self._do_search_stores()
        elif event.button.id == "check-stock-btn":
            self._do_check_stock()
        elif event.button.id == "clear-btn":
            self._do_clear()

    # ── Helpers ────────────────────────────────────────────────────────

    def _selected_country(self) -> str | None:
        sel = self.query_one("#country-select", Select)
        if sel.value is Select.NULL:
            return None
        return str(sel.value)

    def _product_ids(self) -> list[str]:
        raw = self.query_one("#product-input", Input).value.strip()
        if not raw:
            return []
        return [p.strip() for p in raw.split(",") if p.strip()]

    def _show_loading(self) -> None:
        """Replace main area content with loading indicator."""
        main = self.query_one("#main-area")
        for child in list(main.children):
            child.remove()
        main.mount(LoadingIndicator())

    def _show_empty(self, message: str) -> None:
        main = self.query_one("#main-area")
        for child in list(main.children):
            child.remove()
        widget = Static(message, id="empty-state")
        main.mount(widget)

    def _show_error(self, message: str) -> None:
        main = self.query_one("#main-area")
        for child in list(main.children):
            child.remove()
        widget = Static(f"⚠️  {message}", id="error-state")
        main.mount(widget)

    def _do_clear(self) -> None:
        self.query_one("#product-input", Input).value = ""
        self._show_empty(
            "Select a country and press [b]Search Stores[/b] to list stores,\n"
            "or enter a product ID and press [b]Check Stock[/b] to view availability."
        )
        self.notify("Cleared.", timeout=2)

    # ── Store search ───────────────────────────────────────────────────

    def _do_search_stores(self) -> None:
        country = self._selected_country()
        if not country:
            self.notify("Please select a country first.", severity="warning")
            return
        self._show_loading()
        self._fetch_stores(country)

    @work(thread=True)
    def _fetch_stores(self, country_code: str) -> None:
        stores = api.get_stores(country_code)
        self.call_from_thread(self._render_stores, stores, country_code)

    def _render_stores(self, stores: list[api.Store], country_code: str) -> None:
        main = self.query_one("#main-area")
        for child in list(main.children):
            child.remove()

        if not stores:
            self._show_empty(f"No stores found for country code '{country_code}'.")
            return

        table = DataTable(id="results-table", zebra_stripes=True, cursor_type="row")
        main.mount(table)
        table.add_columns("Store ID", "Name", "Country", "Country Code", "Lat", "Lon")
        for s in stores:
            lat = f"{s.coordinates[1]:.4f}" if len(s.coordinates) >= 2 else ""
            lon = f"{s.coordinates[0]:.4f}" if len(s.coordinates) >= 2 else ""
            table.add_row(s.bu_code, s.name, s.country, s.country_code.upper(), lat, lon)

        country_name = api.get_country_name(country_code)
        self.notify(
            f"Found {len(stores)} store(s) in {country_name}.",
            title="Stores",
            timeout=4,
        )

    # ── Stock check ────────────────────────────────────────────────────

    def _do_check_stock(self) -> None:
        country = self._selected_country()
        if not country:
            self.notify("Please select a country first.", severity="warning")
            return
        product_ids = self._product_ids()
        if not product_ids:
            self.notify(
                "Please enter at least one product ID.", severity="warning"
            )
            return
        self._show_loading()
        self._fetch_stock(country, product_ids)

    @work(thread=True)
    def _fetch_stock(self, country_code: str, product_ids: list[str]) -> None:
        try:
            results = api.check_availability(country_code, product_ids)
            self.call_from_thread(self._render_stock, results, country_code)
        except Exception as exc:  # noqa: BLE001
            self.call_from_thread(
                self._show_error,
                f"Failed to fetch stock data: {exc}",
            )

    def _render_stock(
        self, results: list[api.StockInfo], country_code: str
    ) -> None:
        main = self.query_one("#main-area")
        for child in list(main.children):
            child.remove()

        if not results:
            country_name = api.get_country_name(country_code)
            self._show_empty(
                f"No availability data found for the selected product(s) in {country_name}."
            )
            return

        table = DataTable(id="results-table", zebra_stripes=True, cursor_type="row")
        main.mount(table)
        table.add_columns(
            "Product ID",
            "Store",
            "Country",
            "Stock",
            "Availability",
            "Updated",
        )
        for r in results:
            icon = _PROBABILITY_ICONS.get(r.probability, "⚪")
            stock_str = str(r.stock) if r.probability != "OUT_OF_STOCK" else "0"
            table.add_row(
                r.product_id,
                r.store_name,
                f"{r.country} ({r.country_code.upper()})",
                stock_str,
                f"{icon} {r.probability}",
                r.updated_at,
            )

        self.notify(
            f"Found availability data for {len(results)} store(s).",
            title="Stock",
            timeout=4,
        )
