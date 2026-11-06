"""Dialog component for selecting, previewing, and restoring SnapRep backups."""

import json
from pathlib import Path
from typing import Any, Optional
import flet as ft
from state import AppState


async def show_restore_dialog(page: ft.Page, state: AppState) -> None:
    # Retain access to backups made by older app versions, without creating new private copies.
    local_backups = state.storage.get_local_backups()

    async def proceed_with_backup_content(raw_data: Any, source_name: str) -> None:
        try:
            if isinstance(raw_data, bytes):
                raw_data = raw_data.decode("utf-8")
            if isinstance(raw_data, str):
                parsed = json.loads(raw_data)
            elif isinstance(raw_data, (dict, list)):
                parsed = raw_data
            else:
                raise ValueError("Unsupported data type")
        except Exception as ex:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(f"Invalid backup file: {ex}"),
                    show_close_icon=True,
                )
            )
            page.update()
            return

        # Extract counts for preview
        if isinstance(parsed, dict):
            sections = {key: parsed.get(key, []) for key in ("history", "exercises", "weight_history")}
            if any(not isinstance(items, list) for items in sections.values()):
                page.show_dialog(ft.SnackBar(content=ft.Text("Invalid backup sections."), show_close_icon=True))
                page.update()
                return
            sets_count = len(sections["history"])
            exercises_count = len(sections["exercises"])
            weight_count = len(sections["weight_history"])
            created_at = str(parsed.get("created_at", "Unknown date"))
        elif isinstance(parsed, list):
            sets_count = len(parsed)
            exercises_count = 0
            weight_count = 0
            created_at = "Raw history list"
        else:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text("Backup JSON must be an object or array."),
                    show_close_icon=True,
                )
            )
            page.update()
            return

        if sets_count == 0 and exercises_count == 0 and weight_count == 0:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text("No workout sets, exercises, or weigh-ins found in backup."),
                    show_close_icon=True,
                )
            )
            page.update()
            return

        # Pop previous picker dialog
        page.pop_dialog()

        # Step 2: Show preview & Mode Selection Dialog
        restore_mode_radio = ft.RadioGroup(
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Radio(
                        value="merge",
                        label="Merge",
                    ),
                    ft.Text("Add records not already on this device.", size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Radio(
                        value="replace",
                        label="Replace",
                    ),
                    ft.Text("Overwrite sections present in this backup.", size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT),
                ],
            ),
            value="merge",
        )

        warning_text = ft.Text(
            "Merge mode safely combines records without deleting your current history.",
            size=11,
            color=ft.Colors.PRIMARY,
        )

        def on_mode_change(e):
            if restore_mode_radio.value == "replace":
                warning_text.value = "Replace overwrites only sections included in this backup."
                warning_text.color = ft.Colors.ERROR
            else:
                warning_text.value = "Merge mode safely combines records without deleting your current history."
                warning_text.color = ft.Colors.PRIMARY
            warning_text.update()

        restore_mode_radio.on_change = on_mode_change

        async def execute_restore(e):
            mode = restore_mode_radio.value or "merge"
            try:
                page.pop_dialog()
                restored_sets, restored_exercises, settings_done = await state.restore_backup(
                    parsed, mode=mode
                )
                msg = f"Restore complete: {restored_sets} sets, {restored_exercises} exercises ({mode})."
                page.show_dialog(
                    ft.SnackBar(
                        content=ft.Text(msg),
                        show_close_icon=True,
                    )
                )
                page.update()
            except Exception as err:
                page.show_dialog(
                    ft.SnackBar(
                        content=ft.Text(f"Restore failed: {err}"),
                        show_close_icon=True,
                    )
                )
                page.update()

        confirm_dialog = ft.AlertDialog(
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.RESTORE_OUTLINED, color=ft.Colors.PRIMARY, size=24),
                    ft.Text("Confirm Restore", weight=ft.FontWeight.BOLD),
                ],
            ),
            content=ft.Container(
                width=min(340, max(240, (getattr(page, "width", None) or 390) - 48)),
                content=ft.Column(
                    spacing=12,
                    tight=True,
                    controls=[
                        ft.Text(f"Source: {source_name}", size=12, weight=ft.FontWeight.BOLD,
                                max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Container(
                            padding=10,
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                            border_radius=8,
                            content=ft.Column(
                                spacing=4,
                                controls=[
                                    ft.Text(f"Backup Date: {created_at[:19]}", size=11, color=ft.Colors.OUTLINE),
                    ft.Text(f"{sets_count} workout sets", size=12, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{exercises_count} exercises", size=12, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{weight_count} weigh-ins", size=12, weight=ft.FontWeight.BOLD),
                                ],
                            ),
                        ),
                        ft.Text("Restore Mode:", size=12, weight=ft.FontWeight.BOLD),
                        restore_mode_radio,
                        warning_text,
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton(
                    "Restore",
                    icon=ft.Icons.CHECK,
                    on_click=execute_restore,
                ),
            ],
            scrollable=True,
        )

        page.show_dialog(confirm_dialog)
        page.update()

    # Step 1: Initial Action Dialog (Pick File, Choose Local Backup, or Paste Clipboard)
    async def on_pick_file_click(e):
        if not state.file_picker:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text("File picker service unavailable."),
                    show_close_icon=True,
                )
            )
            page.update()
            return

        try:
            files = await state.file_picker.pick_files(
                dialog_title="Select SnapRep Backup JSON",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"],
                with_data=True,
            )
            if not files:
                return

            picked = files[0]
            if picked.bytes:
                await proceed_with_backup_content(picked.bytes, picked.name)
            elif picked.path and Path(picked.path).exists():
                with open(picked.path, "r", encoding="utf-8") as f:
                    content = f.read()
                await proceed_with_backup_content(content, picked.name)
            else:
                page.show_dialog(
                    ft.SnackBar(
                        content=ft.Text("Could not read picked file content."),
                        show_close_icon=True,
                    )
                )
                page.update()
        except Exception as ex:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(f"File picker error: {ex}"),
                    show_close_icon=True,
                )
            )
            page.update()

    async def on_paste_clipboard_click(e):
        if not state.clipboard:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text("Clipboard service unavailable."),
                    show_close_icon=True,
                )
            )
            page.update()
            return

        try:
            clip_text = await state.clipboard.get()
            if not clip_text or not clip_text.strip():
                page.show_dialog(
                    ft.SnackBar(
                        content=ft.Text("Clipboard is empty."),
                        show_close_icon=True,
                    )
                )
                page.update()
                return

            await proceed_with_backup_content(clip_text.strip(), "Clipboard Data")
        except Exception as ex:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(f"Clipboard error: {ex}"),
                    show_close_icon=True,
                )
            )
            page.update()

    async def on_local_backup_click(backup_path: Path):
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                content = f.read()
            await proceed_with_backup_content(content, backup_path.name)
        except Exception as ex:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(f"Could not read local backup: {ex}"),
                    show_close_icon=True,
                )
            )
            page.update()

    # Build local backup options
    local_options = []
    if local_backups:
        local_options.append(ft.Text("Recent In-App Backups:", size=12, weight=ft.FontWeight.BOLD))
        for p in local_backups[:3]:
            async def handle_local_backup_click(e, backup_path=p):
                await on_local_backup_click(backup_path)

            btn = ft.OutlinedButton(
                content=ft.Row(
                    spacing=6,
                    controls=[
                        ft.Icon(ft.Icons.HISTORY, size=16),
                        ft.Text(p.name, size=11, max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                    ],
                ),
                on_click=handle_local_backup_click,
            )
            local_options.append(btn)

    initial_dialog = ft.AlertDialog(
        title=ft.Row(
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.RESTORE_OUTLINED, color=ft.Colors.PRIMARY, size=24),
                ft.Text("Restore Backup", weight=ft.FontWeight.BOLD),
            ],
        ),
        content=ft.Container(
            width=min(340, max(240, (getattr(page, "width", None) or 390) - 48)),
            content=ft.Column(
                spacing=12,
                tight=True,
                controls=[
                    ft.Text(
                        "Import workout history, exercises, settings, and weigh-ins.",
                        size=13,
                    ),
                    ft.FilledButton("Choose JSON file", icon=ft.Icons.FILE_OPEN_OUTLINED,
                                    on_click=on_pick_file_click),
                    ft.OutlinedButton("Paste JSON", icon=ft.Icons.CONTENT_PASTE,
                                      on_click=on_paste_clipboard_click),
                    *local_options,
                ],
            ),
        ),
        actions=[
            ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
        ],
        scrollable=True,
    )

    page.show_dialog(initial_dialog)
    page.update()
