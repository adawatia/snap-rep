"""Save workout or body-weight CSV outside the app's private storage."""

import flet as ft

from state import AppState


async def show_export_dialog(page: ft.Page, state: AppState, kind: str = "workout") -> None:
    if kind not in ("workout", "weight"):
        raise ValueError("Unknown export type")
    count = len(state.history if kind == "workout" else state.weight_history)
    if count == 0:
        page.show_dialog(ft.SnackBar(
            content=ft.Text("No workout sets to export yet." if kind == "workout" else "No weigh-ins to export yet."),
            show_close_icon=True,
        ))
        page.update()
        return
    export_file, content = (
        state.storage.export_history_to_csv() if kind == "workout"
        else state.storage.export_weight_to_csv()
    )
    status = ft.Text("Choose where to save the CSV.", size=12, color=ft.Colors.ON_SURFACE_VARIANT)

    async def save_to_device(_):
        if not state.file_picker:
            status.value = "File picker unavailable. You can copy the CSV instead."
            status.color = ft.Colors.ERROR
            page.update()
            return
        try:
            saved_path = await state.file_picker.save_file(
                dialog_title="Save SnapRep CSV", file_name=export_file.name,
                file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=["csv"],
                src_bytes=content.encode("utf-8"),
            )
            if saved_path:
                status.value = "CSV saved to your chosen location."
                status.color = ft.Colors.PRIMARY
                page.update()
        except Exception:
            status.value = "Could not save CSV. Try again or copy it."
            status.color = ft.Colors.ERROR
            page.update()

    async def copy_csv(_):
        if not state.clipboard:
            status.value = "Clipboard unavailable. Save the CSV instead."
            status.color = ft.Colors.ERROR
        else:
            try:
                await state.clipboard.set(content)
                status.value = "CSV copied to clipboard."
                status.color = ft.Colors.PRIMARY
            except Exception:
                status.value = "Could not copy CSV. Save it instead."
                status.color = ft.Colors.ERROR
        page.update()

    name = "Workout history" if kind == "workout" else "Body-weight history"
    width = min(340, max(240, (getattr(page, "width", None) or 390) - 48))
    page.show_dialog(ft.AlertDialog(
        title=ft.Text(f"Export {name}", size=20, weight=ft.FontWeight.BOLD),
        scrollable=True,
        content=ft.Container(width=width, content=ft.Column(
            tight=True, spacing=12, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Text(f"{count} {('set' if count == 1 else 'sets') if kind == 'workout' else ('weigh-in' if count == 1 else 'weigh-ins')} ready as CSV.", size=13),
                ft.Text("Workout CSV keeps the Volume_kg column: weight × reps per set, not maximum weight."
                        if kind == "workout" else "Includes each weigh-in's date, time, and weight in kg.",
                        size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                status,
                ft.FilledButton("Save to device / Drive", icon=ft.Icons.SAVE_ALT_OUTLINED, on_click=save_to_device),
                ft.OutlinedButton("Copy CSV", icon=ft.Icons.CONTENT_COPY, on_click=copy_csv),
            ],
        )),
        actions=[ft.TextButton("Close", on_click=lambda _: page.pop_dialog())],
    ))
    page.update()
