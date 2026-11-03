"""Dialog component for creating, saving, and copying SnapRep backups."""

import asyncio
from datetime import datetime
import flet as ft
from state import AppState


async def show_backup_dialog(page: ft.Page, state: AppState) -> None:
    backup_file, json_str, backup_data, copied = await state.create_backup()

    sets_count = len(backup_data.get("history", []))
    exercises_count = len(backup_data.get("exercises", []))
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
    location_label = "Saved to Local Storage:" if is_mobile else "Saved to file:"
    location_value = f"App Storage ({backup_file.name})" if is_mobile else str(backup_file)

    copy_status_text = ft.Text(
        "Copied to clipboard!" if copied else "Ready to share or export",
        size=12,
        color=ft.Colors.PRIMARY,
        weight=ft.FontWeight.W_600,
    )

    async def on_save_to_device(e):
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
            saved_path = await state.file_picker.save_file(
                dialog_title="Save SnapRep Backup",
                file_name=backup_file.name,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"],
                src_bytes=json_str.encode("utf-8"),
            )
            if saved_path:
                page.show_dialog(
                    ft.SnackBar(
                        content=ft.Text("Backup saved successfully!"),
                        show_close_icon=True,
                    )
                )
                page.update()
        except Exception as ex:
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(f"Could not save file: {ex}"),
                    show_close_icon=True,
                )
            )
            page.update()

    async def on_copy_click(e):
        if state.clipboard:
            try:
                await state.clipboard.set(json_str)
                copy_status_text.value = "Copied to clipboard!"
                copy_status_text.color = ft.Colors.GREEN
                copy_status_text.update()
                await state.trigger_haptic("click")
            except Exception:
                pass

    dialog = ft.AlertDialog(
        title=ft.Row(
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=24),
                ft.Text("Backup Complete", weight=ft.FontWeight.BOLD),
            ],
        ),
        content=ft.Container(
            width=340,
            content=ft.Column(
                spacing=12,
                tight=True,
                controls=[
                    ft.Text(
                        f"Successfully archived your workout data ({timestamp_str}).",
                        size=13,
                    ),
                    # Summary badges
                    ft.Container(
                        padding=10,
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                        border_radius=10,
                        content=ft.Column(
                            spacing=6,
                            controls=[
                                ft.Row(
                                    spacing=6,
                                    controls=[
                                        ft.Icon(ft.Icons.FITNESS_CENTER, size=16, color=ft.Colors.PRIMARY),
                                        ft.Text(f"{sets_count} workout sets", size=12, weight=ft.FontWeight.BOLD),
                                    ],
                                ),
                                ft.Row(
                                    spacing=6,
                                    controls=[
                                        ft.Icon(ft.Icons.LIST_ALT, size=16, color=ft.Colors.SECONDARY),
                                        ft.Text(f"{exercises_count} exercises & custom movements", size=12, weight=ft.FontWeight.BOLD),
                                    ],
                                ),
                                ft.Row(
                                    spacing=6,
                                    controls=[
                                        ft.Icon(ft.Icons.SETTINGS, size=16, color=ft.Colors.OUTLINE),
                                        ft.Text("App settings & timer preferences", size=12),
                                    ],
                                ),
                            ],
                        ),
                    ),
                    # File path details
                    ft.Container(
                        padding=10,
                        bgcolor=ft.Colors.SURFACE_CONTAINER,
                        border_radius=8,
                        content=ft.Column(
                            spacing=4,
                            controls=[
                                ft.Text(location_label, size=11, color=ft.Colors.OUTLINE),
                                ft.Text(location_value, size=12, weight=ft.FontWeight.BOLD),
                            ],
                        ),
                    ),
                    # Copy status row
                    ft.Row(
                        spacing=6,
                        controls=[
                            ft.Icon(ft.Icons.COPY_ALL, size=16, color=ft.Colors.PRIMARY),
                            copy_status_text,
                        ],
                    ),
                    # Save to device button
                    ft.FilledButton(
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=6,
                            controls=[
                                ft.Icon(ft.Icons.FILE_DOWNLOAD, size=18),
                                ft.Text("Save to Storage / Drive", weight=ft.FontWeight.BOLD),
                            ],
                        ),
                        on_click=on_save_to_device,
                    ),
                    ft.OutlinedButton(
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=6,
                            controls=[
                                ft.Icon(ft.Icons.CONTENT_COPY, size=16),
                                ft.Text("Copy JSON to Clipboard"),
                            ],
                        ),
                        on_click=on_copy_click,
                    ),
                ],
            ),
        ),
        actions=[
            ft.TextButton("Close", on_click=lambda _: page.pop_dialog()),
        ],
    )

    page.show_dialog(dialog)
    page.update()
