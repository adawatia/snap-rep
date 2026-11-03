# SnapRep

> **Every rep recorded.**

SnapRep is a modern Material 3 Android workout & rep-tracking application built with **Flet (Flutter for Python)**, managed with **`uv`**, and integrated with **Flet MCP** for AI-assisted UI development.

---

## 🌟 Key Features

- **Designed for Android**: Material 3 UI with `SafeArea` support (respects status bars, camera notches, and gesture navigation bars).
- **Haptic Feedback**: Android vibration and tap feedback on rep increments, set logs, and timer completion (`ft.HapticFeedback`).
- **Interactive Rep Tracker**: Large touch targets for rapid rep adjustments (`+1`, `+5`, `-1`, reset), customizable default rep presets, and exercise selection.
- **Set & Weight Tracking**: Tracks set progression (e.g., Set 1, Set 2) and barbell/dumbbell weights in kg.
- **Built-in Rest Timer**: Quick rest intervals (`30s`, `60s`, `90s`) with automatic countdown, pause/stop controls, and haptic alerts.
- **Workout Logbook & History**: Instant session review with today's total reps, sets logged, and total volume (kg).
- **Analytics & PRs**: Breakdown of total reps per exercise and personal record (PR) tracking.
- **Flet MCP Ready**: Configured with `flet-mcp` so AI coding agents can verify controls, search icons, and inspect Flet APIs in real time.

---

## 🚀 Quick Start with `uv`

### 1. Prerequisites
Ensure you have [`uv`](https://docs.astral.sh/uv/) installed.

```bash
uv --version
```

### 2. Install Dependencies
Synchronize project virtual environment and dependencies:

```bash
uv sync
```

### 3. Run Locally (Desktop / Hot Reload)
Test and preview the UI with instant hot reload:

```bash
uv run flet run
```

Or preview in a web browser:
```bash
uv run flet run --web
```

---

## 📱 Running & Building for Android

### Run on Android Device or Emulator
Connect an Android device with USB debugging enabled, or start an Android Virtual Device (AVD), then run:

```bash
uv run flet run --android
```

Or run in full debug mode with the mobile Flutter engine:
```bash
uv run flet debug android
```

### Build Android Package (APK / AAB)

Build a release or debug APK:
```bash
uv run flet build apk
```

Build an Android App Bundle (for Google Play / distribution):
```bash
uv run flet build aab
```

Android settings such as package name (`com.snaprep`), permissions (`INTERNET`, `VIBRATE`), and adaptive icon backgrounds are configured in [`pyproject.toml`](./pyproject.toml) under `[tool.flet.android]`.

---

## 🤖 Flet MCP Integration

This project is configured with the **Flet MCP (Model Context Protocol)** server to assist AI pair programmers (Antigravity, Cursor, Claude Code, VSCode).

### MCP Server Configuration
The MCP server is defined in [`.cursor/mcp.json`](./.cursor/mcp.json) and [`.vscode/mcp.json`](./.vscode/mcp.json):

```json
{
  "mcpServers": {
    "flet": {
      "command": "uv",
      "args": ["run", "flet", "mcp"]
    }
  }
}
```

### Available MCP Capabilities
- `get_api(name)`: Look up exact properties, events, and methods for any Flet control.
- `find_icon(query)`: Search Material & Cupertino icons (e.g. `query="fitness"`).
- `list_controls()`: Browse controls and services by category.
- `get_enum(name)` & `search_enum_members(query)`: Validate enum values (e.g. `ThemeMode`, `KeyboardType`).

---

## 🧪 Testing

Run automated tests for data models, serialization, and storage:

```bash
uv run pytest
```

---

## 📁 Project Structure

```
snap-rep/
├── .cursor/
│   └── mcp.json           # MCP server config for Cursor
├── .vscode/
│   └── mcp.json           # MCP server config for VSCode
├── src/
│   ├── assets/
│   │   └── icon.png       # Android adaptive app icon
│   ├── components/        # Reusable modal dialogs (Add exercise, CSV export, Confirm)
│   ├── views/             # Modular screens (Tracker, History, Stats, Settings)
│   ├── config.py          # App constants, defaults, categories
│   ├── models.py          # Data models (Exercise, SetRecord)
│   ├── state.py           # AppState reactive state management & business logic
│   ├── storage.py         # Local JSON persistence & atomic writes
│   ├── theme.py           # Athletic Material 3 Dark & Light themes
│   └── main.py            # Application entrypoint & navigation
├── tests/
│   └── test_app.py        # Pytest test suite (11 unit tests)
├── pyproject.toml         # UV project config & Flet Android build settings
├── README.md
└── uv.lock
```
