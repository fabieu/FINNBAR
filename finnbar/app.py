"""FINNBAR – Textual TUI for checking IKEA product availability."""

from __future__ import annotations

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
from finnbar.render import StockResult, build_stock_result

_COUNTRY_OPTIONS: list[tuple[str, str]] = [
    (f"{country_code.upper()} – {api.get_country_name(country_code)}", country_code)
    for country_code in api.get_country_codes()
]


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

    MAIN_AREA_ID = "main-area"
    EMPTY_STATE_ID = "empty-state"
    ERROR_STATE_ID = "error-state"

    CHECK_STOCK_BTN_ID = "check-stock-btn"
    CLEAR_BTN_ID = "clear-btn"

    COUNTRY_SELECT_ID = "country-select"
    STORE_SELECT_ID = "store-select"
    PRODUCT_INPUT_ID = "product-input"

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
                    id=self.COUNTRY_SELECT_ID,
                    allow_blank=False,
                    value=_COUNTRY_OPTIONS[0][1],
                    compact=True,
                )

                yield Label("Store")
                yield Select(
                    [],
                    prompt="All stores",
                    id=self.STORE_SELECT_ID,
                    allow_blank=True,
                    compact=True,
                )

                yield Label("Product ID(s)")
                yield Input(
                    placeholder="306.043.67, 10606640",
                    id=self.PRODUCT_INPUT_ID,
                )

                yield Button("Check Stock", id=self.CHECK_STOCK_BTN_ID, variant="success")
                yield Button("Clear", id=self.CLEAR_BTN_ID)

            # ── Main area ──────────────────────────────────────────────
            with Container(id=self.MAIN_AREA_ID):
                yield Static(
                    "Select a country and store (optional),\n"
                    "then enter a product ID and press\n"
                    "[b]Check Stock[/b] to view availability.",
                    id=self.EMPTY_STATE_ID,
                )

        yield Footer()

    # ── Lifecycle ──────────────────────────────────────────────────────

    def on_mount(self) -> None:
        """Populate store dropdown for the initially selected country."""
        self._update_store_select(_COUNTRY_OPTIONS[0][1])

    # ── Actions ────────────────────────────────────────────────────────

    def action_check_stock(self) -> None:
        self.query_one(f"#{self.CHECK_STOCK_BTN_ID}", Button).press()

    def action_clear(self) -> None:
        self.query_one(f"#{self.CLEAR_BTN_ID}", Button).press()

    # ── Event handlers ─────────────────────────────────────────────────

    def on_select_changed(self, event: Select.Changed) -> None:
        """Repopulate the store dropdown whenever the country changes."""
        if event.select.id == self.COUNTRY_SELECT_ID and event.value is not Select.NULL:
            self._update_store_select(str(event.value))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == self.CHECK_STOCK_BTN_ID:
            self._do_check_stock()
        elif event.button.id == self.CLEAR_BTN_ID:
            self._do_clear()

    # ── Helpers ────────────────────────────────────────────────────────

    def _selected_country(self) -> str | None:
        sel = self.query_one(f"#{self.COUNTRY_SELECT_ID}", Select)
        if sel.value is Select.NULL:
            return None
        return str(sel.value)

    def _selected_store(self) -> str | None:
        """Return selected store bu_code, or None for all stores."""
        sel = self.query_one(f"#{self.STORE_SELECT_ID}", Select)
        if sel.value is Select.NULL:
            return None
        return str(sel.value)

    def _product_ids(self) -> list[str]:
        raw = self.query_one(f"#{self.PRODUCT_INPUT_ID}", Input).value.strip()
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
        self.query_one(f"#{self.STORE_SELECT_ID}", Select).set_options(options)

    def _show_loading(self) -> None:
        """Replace main area content with a loading indicator."""
        main = self.query_one(f"#{self.MAIN_AREA_ID}")
        main.remove_children()
        main.mount(LoadingIndicator())

    def _show_empty(self, message: str) -> None:
        """Show a centred informational message in the main area."""
        main = self.query_one(f"#{self.MAIN_AREA_ID}")
        existing = main.query(f"#{self.EMPTY_STATE_ID}")
        if existing:
            # Reuse the widget to avoid DuplicateIds — just remove siblings
            for child in main.children:
                if child.id != self.EMPTY_STATE_ID:
                    child.remove()
            existing.first(Static).update(message)
        else:
            main.remove_children()
            main.mount(Static(message, id=self.EMPTY_STATE_ID))

    def _show_error(self, message: str) -> None:
        """Show a centred error message in the main area."""
        main = self.query_one(f"#{self.MAIN_AREA_ID}")
        existing = main.query(f"#{self.ERROR_STATE_ID}")
        if existing:
            for child in main.children:
                if child.id != self.ERROR_STATE_ID:
                    child.remove()
            existing.first(Static).update(f"⚠️  {message}")
        else:
            main.remove_children()
            main.mount(Static(f"⚠️  {message}", id=self.ERROR_STATE_ID))

    def _do_clear(self) -> None:
        self.query_one(f"#{self.PRODUCT_INPUT_ID}", Input).value = ""
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
        main = self.query_one(f"#{self.MAIN_AREA_ID}")
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
        table.add_columns(*StockResult.column_headers())
        for result in results:
            table.add_row(*build_stock_result(result).cells())

        main.mount(table)
