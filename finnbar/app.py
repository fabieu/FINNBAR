"""FINNBAR – Textual TUI for checking IKEA product availability."""

from __future__ import annotations

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
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

from finnbar import api

_COUNTRY_OPTIONS: list[tuple[str, str]] = [
    (f"{country_code.upper()} – {api.get_country_name(country_code)}", country_code)
    for country_code in api.get_country_codes()
]
_PROBABILITY_DISPLAY: dict[str, tuple[str, str]] = {
    "HIGH_IN_STOCK": ("High in stock", "bold green"),
    "LOW_IN_STOCK": ("Low in stock", "bold yellow"),
    "OUT_OF_STOCK": ("Out of stock", "bold red"),
}
_PROBABILITY_FALLBACK: tuple[str, str] = ("Unknown", "dim")
_ZERO_STOCK_KEYS: frozenset[str] = frozenset({"OUT_OF_STOCK"})


class FinnbarApp(App[None]):
    """FINNBAR – IKEA availability checker TUI."""

    TITLE = "FINNBAR"
    SUB_TITLE = "IKEA Availability Checker"
    CSS_PATH = "app.tcss"
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+k", "check_stock", "Check Stock", show=True),
        Binding("ctrl+x", "clear", "Clear", show=True),
    ]

    _state: reactive[str] = reactive("idle")  # idle | loading | stock | error

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
                    compact=True,
                )

                yield Label("Store")
                yield Select(
                    [],
                    prompt="All stores",
                    id="store-select",
                    allow_blank=True,
                    compact=True,
                )

                yield Label("Product ID(s)")
                yield Input(
                    placeholder="306.043.67, 10606640",
                    id="product-input",
                )

                yield Button("Check Stock", id="check-stock-btn", variant="success")
                yield Button("Clear", id="clear-btn")

            # ── Main area ──────────────────────────────────────────────
            with Container(id="main-area"):
                yield Static(
                    "Select a country and store (optional),\n"
                    "then enter a product ID and press\n"
                    "[b]Check Stock[/b] to view availability.",
                    id="empty-state",
                )

        yield Footer()

    # ── Lifecycle ──────────────────────────────────────────────────────

    def on_mount(self) -> None:
        """Populate store dropdown for the initially selected country."""
        self._update_store_select(_COUNTRY_OPTIONS[0][1])

    # ── Actions ────────────────────────────────────────────────────────

    def action_check_stock(self) -> None:
        self.query_one("#check-stock-btn", Button).press()

    def action_clear(self) -> None:
        self.query_one("#clear-btn", Button).press()

    # ── Event handlers ─────────────────────────────────────────────────

    def on_select_changed(self, event: Select.Changed) -> None:
        """Repopulate the store dropdown whenever the country changes."""
        if event.select.id == "country-select" and event.value is not Select.NULL:
            self._update_store_select(str(event.value))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "check-stock-btn":
            self._do_check_stock()
        elif event.button.id == "clear-btn":
            self._do_clear()

    # ── Helpers ────────────────────────────────────────────────────────

    def _selected_country(self) -> str | None:
        sel = self.query_one("#country-select", Select)
        if sel.value is Select.NULL:
            return None
        return str(sel.value)

    def _selected_store(self) -> str | None:
        """Return selected store bu_code, or None for all stores."""
        sel = self.query_one("#store-select", Select)
        if sel.value is Select.NULL:
            return None
        return str(sel.value)

    def _product_ids(self) -> list[str]:
        raw = self.query_one("#product-input", Input).value.strip()
        if not raw:
            return []
        # Normalize: strip dots (e.g. 091.761.65 → 09176165)
        ids = []
        for token in raw.split(","):
            normalized = token.strip().replace(".", "")
            if normalized:
                ids.append(normalized)
        return ids

    def _update_store_select(self, country_code: str) -> None:
        """Repopulate the store Select with stores for the given country."""
        stores = api.get_stores(country_code)
        options = [
            (s.name, s.bu_code)
            for s in sorted(stores, key=lambda s: s.name)
        ]
        self.query_one("#store-select", Select).set_options(options)

    def _show_loading(self) -> None:
        """Replace main area content with a loading indicator."""
        main = self.query_one("#main-area")
        main.remove_children()
        main.mount(LoadingIndicator())

    def _show_empty(self, message: str) -> None:
        """Show a centred informational message in the main area."""
        main = self.query_one("#main-area")
        existing = main.query("#empty-state")
        if existing:
            # Reuse the widget to avoid DuplicateIds — just remove siblings
            for child in list(main.children):
                if child.id != "empty-state":
                    child.remove()
            existing.first(Static).update(message)
        else:
            main.remove_children()
            main.mount(Static(message, id="empty-state"))

    def _show_error(self, message: str) -> None:
        """Show a centred error message in the main area."""
        main = self.query_one("#main-area")
        existing = main.query("#error-state")
        if existing:
            for child in list(main.children):
                if child.id != "error-state":
                    child.remove()
            existing.first(Static).update(f"⚠️  {message}")
        else:
            main.remove_children()
            main.mount(Static(f"⚠️  {message}", id="error-state"))

    def _do_clear(self) -> None:
        self.query_one("#product-input", Input).value = ""
        self._show_empty(
            "Select a country and store (optional),\n"
            "then enter a product ID and press\n"
            "[b]Check Stock[/b] to view availability."
        )
        self.notify("Cleared.", timeout=2)

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
        bu_code = self._selected_store()
        # Capture the human-readable store name for display in no-results message
        store_name: str | None = None
        if bu_code:
            stores = api.get_stores(country)
            store_name = next((s.name for s in stores if s.bu_code == bu_code), None)
        self._show_loading()
        self._fetch_stock(country, product_ids, bu_code, store_name)

    @work(thread=True)
    def _fetch_stock(
            self,
            country_code: str,
            product_ids: list[str],
            bu_code: str | None = None,
            store_name: str | None = None,
    ) -> None:
        try:
            results = api.check_availability(country_code, product_ids, bu_code)
            self.call_from_thread(
                self._render_stock, results, country_code, product_ids, store_name
            )
        except Exception as exc:  # noqa: BLE001
            self.call_from_thread(
                self._show_error,
                f"Failed to fetch stock data: {exc}",
            )

    def _render_stock(
            self,
            results: list[api.StockInfo],
            country_code: str,
            product_ids: list[str],
            store_name: str | None,
    ) -> None:
        main = self.query_one("#main-area")
        main.remove_children()

        if not results:
            country_name = api.get_country_name(country_code)
            ids_str = ", ".join(product_ids)
            store_part = f" in [b]{store_name}[/b]" if store_name else ""
            self._show_empty(
                f"No availability data found for product(s) [b]{ids_str}[/b]"
                f"{store_part} in [b]{country_name}[/b]."
            )
            return

        table = DataTable(id="results-table", zebra_stripes=True, cursor_type="row")
        main.mount(table)
        table.add_columns(
            "Product ID",
            "Country",
            "Store",
            "Stock",
            "Availability",
            "Updated",
        )
        for r in results:
            avail_label, avail_color = _PROBABILITY_DISPLAY.get(r.probability, _PROBABILITY_FALLBACK)

            table.add_row(
                r.product_id,
                f"{r.country_code.upper()} – {r.country}",
                r.store_name,
                str(r.stock) if r.probability not in _ZERO_STOCK_KEYS else "0",
                Text(avail_label, style=avail_color),
                r.updated_at,
            )
