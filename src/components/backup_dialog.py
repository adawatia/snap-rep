"""Offer a portable backup through the device save picker or clipboard."""

import flet as ft

from state import AppState


async def show_backup_dialog(page: ft.Page, state: AppState) -> None:
    filename, json_str, backup_data, _ = await state.create_backup()
    sets_count = len(backup_data["history"])
    weight_count = len(backup_data["weight_history"])
    status = ft.Text("Choose a location to save your backup.", size=12,
                     color=ft.Colors.ON_SURFACE_VARIANT)

    async def save(_):
        if not state.file_picker:
            status.value = "File picker unavailable. Copy the JSON instead."
            status.color = ft.Colors.ERROR
            page.update()
            return
        try:
            destination = await state.file_picker.save_file(
                dialog_title="Save SnapRep backup", file_name=filename.name,
                file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["json"],
                src_bytes=json_str.encode("utf-8"),
            )
            if destination:
                status.value = "Backup saved to your chosen location."
                status.color = ft.Colors.PRIMARY
                page.update()
        except Exception:
            status.value = "Could not save the backup. Try again or copy it."
            status.color = ft.Colors.ERROR
            page.update()

    async def copy(_):
        if not state.clipboard:
            status.value = "Clipboard unavailable. Save the backup instead."
            status.color = ft.Colors.ERROR
        else:
            try:
                await state.clipboard.set(json_str)
                status.value = "Backup JSON copied. Paste it somewhere safe."
                status.color = ft.Colors.PRIMARY
            except Exception:
                status.value = "Could not copy the backup. Save it instead."
                status.color = ft.Colors.ERROR
        page.update()

    width = min(340, max(240, (getattr(page, "width", None) or 390) - 48))
    page.show_dialog(ft.AlertDialog(
        title=ft.Text("Back up data", size=20, weight=ft.FontWeight.BOLD),
        scrollable=True,
        content=ft.Container(width=width, content=ft.Column(
            tight=True, spacing=12,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Text(f"{sets_count} workout sets · {weight_count} weigh-ins · exercises and settings",
                        size=13),
                status,
                ft.FilledButton("Save to device / Drive", icon=ft.Icons.SAVE_ALT_OUTLINED,
                                on_click=save),
                ft.OutlinedButton("Copy JSON", icon=ft.Icons.CONTENT_COPY,
                                  on_click=copy),
            ],
        )),
        actions=[ft.TextButton("Close", on_click=lambda _: page.pop_dialog())],
    ))
    page.update()
