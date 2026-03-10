# FINNBAR

**FINNBAR** - a TUI for browsing and checking real-time IKEA product availability across your local stores, without
leaving the terminal.

---

No more clicking through IKEA's website only to find your KALLAX is out of stock. **FINNBAR** (_finns bara_ — Swedish
for "is available") lets you search, filter, and check availability across multiple stores — all from the comfort of
your terminal.

## Features

- 🏪 **Browse stores** – list all IKEA stores for any supported country (40+ countries, 400+ stores)
- 📦 **Check stock** – look up real-time availability for one or more product IDs across all stores in a country
- ⌨️ **Keyboard-driven** – full keyboard navigation with shortcut bindings

## Screenshots

![FINNBAR stock search](docs/screenshot-stock.png)

## Installation

### Standalone binary

Pre-built binaries are available on the [Releases][releases] page.

#### Linux

1. Download `finnbar-linux-<version>` from the [Releases][releases] page
2. Make it executable:
   ```bash
   chmod +x finnbar-linux-<version>
   ```
3. Run it:
   ```bash
   ./finnbar-linux-<version>
   ```

#### macOS

1. Download `finnbar-macos-<version>` from the [Releases][releases] page
2. Make it executable:
   ```bash
   chmod +x finnbar-macos-<version>
   ```
3. Remove the quarantine attribute applied by Gatekeeper:
   ```bash
   xattr -d com.apple.quarantine finnbar-macos-<version>
   ```
4. Run it:
   ```bash
   ./finnbar-macos-<version>
   ```

#### Windows

1. Download `finnbar-windows-<version>.exe` from the [Releases][releases] page
2. Run it from PowerShell or Command Prompt:
   ```powershell
   .\finnbar-windows-<version>.exe
   ```

### pipx (requires Python 3.11+)

```bash
# Install the latest version
pipx install finnbar

# Launch the TUI
finnbar
```

## Usage

| Keyboard shortcut | Action                                    |
|-------------------|-------------------------------------------|
| `Ctrl+K`          | Check stock for the entered product ID(s) |
| `Ctrl+X`          | Clear results                             |
| `Ctrl+Q`          | Quit                                      |

### Checking stock

1. Select a **country** from the dropdown
2. Optionally select a **store** from the dropdown (or leave it as "All stores")
3. Enter one or more **product IDs** in the input field (comma-separated, e.g. `306.043.67, 10606640`)
4. Press **Check Stock** or `Ctrl+K`

[releases]: https://github.com/fabieu/FINNBAR/releases
