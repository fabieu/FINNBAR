# FINNBAR

**FINNBAR** – a TUI for checking IKEA product availability in your local store, straight from your terminal.

Built with [Textual](https://github.com/Textualize/textual) and powered by the [ikea-availability-checker](https://github.com/Ephigenia/ikea-availability-checker) data.

## Features

- 🏪 **Browse stores** – list all IKEA stores for any supported country (40+ countries, 400+ stores)
- 📦 **Check stock** – look up real-time availability for one or more product IDs across all stores in a country
- ⌨️ **Keyboard-driven** – full keyboard navigation with shortcut bindings shown in the footer

## Requirements

- Python 3.10+
- [Poetry](https://python-poetry.org/) package manager

## Installation

```bash
# Clone the repository
git clone https://github.com/fabieu/FINNBAR.git
cd FINNBAR

# Install dependencies and the runnable script
poetry install
```

## Usage

```bash
# Launch the TUI
poetry run finnbar
```

| Keyboard shortcut | Action |
|---|---|
| `Ctrl+S` | Search stores for the selected country |
| `Ctrl+K` | Check stock for the entered product ID(s) |
| `Ctrl+X` | Clear results |
| `Ctrl+Q` | Quit |

### Checking stock

1. Select a **country** from the dropdown
2. Enter one or more **product IDs** in the input field (comma-separated, e.g. `40299687, S69022537`)
3. Press **Check Stock** or `Ctrl+K`

### Browsing stores

1. Select a **country** from the dropdown
2. Press **Search Stores** or `Ctrl+S`
