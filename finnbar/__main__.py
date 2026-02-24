"""Entry point for `python -m finnbar`."""

from finnbar.app import FinnbarApp


def main() -> None:
    """Run the FINNBAR TUI."""
    FinnbarApp().run()


if __name__ == "__main__":
    main()
