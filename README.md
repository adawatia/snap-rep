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
- **Workout insights**: Sets, reps, active days, and observed best weight or reps per exercise. Open the charts on demand to inspect weekly activity and exercise progress.
- **Body weight**: Timestamped weigh-ins, a target, and optional daily and seven-day trend charts.
- **Portable data**: Settings offers workout CSV, weight CSV, and JSON backup exports through the system file picker or an explicit Copy action.
- **Flet MCP Ready**: Configured with `flet-mcp` so AI coding agents can verify controls, search icons, and inspect Flet APIs in real time.
- **Quick start guide**: A three-step guide appears on a fresh install and can be replayed from Settings.
- **Offline exercise catalog**: 876 sourced exercises from [Free Exercise DB](https://github.com/yuhonas/free-exercise-db), with muscle and equipment search and movement instructions. The original SnapRep exercises and their saved targets are retained; overlapping catalog names are combined. New loaded exercises ask for a starting weight once when selected, with a 0 kg option.
- **Exercise filters**: Browse by muscle group, neck, cardio, mobility, or the source movement types including plyometrics, powerlifting, Olympic lifting, and strongman.

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

### Build a signed Android APK

Install a JDK, Flutter 3.44.8, and the Android SDK with build tools. Run
`uv sync` first. On this development machine, the installed toolchain is at:

```bash
export JAVA_HOME="$HOME/java/17.0.13+11"
export ANDROID_HOME="$HOME/Android/sdk"
export PATH="$JAVA_HOME/bin:$HOME/flutter/3.44.8/bin:$PATH"
./scripts/build_android_release.sh
```

Replace the toolchain paths on another computer. The script reads the local
`.secrets/android-upload.jks` and `.secrets/android-signing.env`, builds one APK
per ABI in `build/apk/`, and verifies every APK with `apksigner` and `aapt`.
It checks the signer against `scripts/android_upload_cert.sha256` and rejects
unexpected permissions. The generated APKs are for `arm64-v8a`,
`armeabi-v7a`, and `x86_64`; install the variant matching the device.

On another computer, securely copy the existing upload keystore and password
file into `.secrets/`. **Do not generate another key for the same release
identity.** Back up both files securely and keep them out of source control.
For a new app identity only, run `python3 scripts/create_android_upload_key.py`
once, then update `scripts/android_upload_cert.sha256` with the printed
fingerprint.

### Build an Android App Bundle

Use the same toolchain and local signing files, then build an AAB for Google
Play in `build/aab/`:

```bash
source .secrets/android-signing.env
FLET_ANDROID_SIGNING_KEY_STORE="$PWD/.secrets/android-upload.jks" \
FLET_ANDROID_SIGNING_KEY_ALIAS=snaprep \
uv run flet build aab --python-version 3.13
```

The old upload key was previously committed to Git and should be treated as
compromised. Its local copy is preserved at `.secrets/legacy-snaprep-release.jks`.
If this app already uses Play App Signing, request an **upload key reset** in
Play Console and register `.secrets/android-upload-cert.pem` before uploading a
bundle signed with the new key. A directly installed APK signed with the old
key cannot be updated in place by one signed with the new key; uninstalling it
will remove its local data unless you back up and restore it first.

The Android application ID is `com.datlabs.snap_rep`. Packaged builds request
only the normal platform `VIBRATE` permission for haptic feedback; Flet's default
`INTERNET` permission and the connectivity plugin's `ACCESS_NETWORK_STATE`
permission are removed. AndroidX also declares an internal receiver permission,
which does not prompt the user. File import/export uses Android's system file
picker, so SnapRep does not request storage, camera, or notification access.
These settings are in [`pyproject.toml`](./pyproject.toml) under
`[tool.flet.android]`.

### Save or restore your data

Open **Settings → Your data** to export either CSV or create a JSON backup.
Choose **Save to device / Drive** and select a location you can find later.
SnapRep does not create a new backup in its private app storage. You can also
copy the JSON or CSV explicitly. To restore, choose the saved JSON file in
**Settings → Restore data**. Older backups previously saved inside SnapRep remain
available from the Restore dialog on the same installation.

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
│   ├── views/             # Tracker, History, Exercises, Stats, Weight, Settings
│   ├── config.py          # App constants, defaults, categories
│   ├── models.py          # Exercise, SetRecord, and WeightEntry models
│   ├── state.py           # AppState reactive state management & business logic
│   ├── storage.py         # Local JSON persistence & atomic writes
│   ├── theme.py           # Athletic Material 3 Dark & Light themes
│   └── main.py            # Application entrypoint & navigation
├── tests/
│   └── test_app.py        # Pytest UI and data checks
├── pyproject.toml         # UV project config & Flet Android build settings
├── README.md
└── uv.lock
```
