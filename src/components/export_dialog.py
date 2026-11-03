"""Dialog component for displaying CSV export results."""

import flet as ft
from state import AppState


async def show_export_dialog(page: ft.Page, state: AppState) -> None:
    if not state.history:
        page.show_dialog(
            ft.SnackBar(
                content=ft.Text("No workout sets to export yet. Log a set first!"),
                show_close_icon=True,
            )
        )
        page.update()
        return

    export_file, csv_content, copied = await state.export_csv()

    preview_lines = csv_content.strip().splitlines()
    preview_text = "\n".join(preview_lines[:5])
    if len(preview_lines) > 5:
        preview_text += f"\n... and {len(preview_lines) - 5} more sets"

    is_mobile = page.platform in [ft.PagePlatform.ANDROID, ft.PagePlatform.IOS]
    location_label = "Saved to:" if is_mobile else "Saved to file:"
    location_value = f"App Storage ({export_file.name})" if is_mobile else str(export_file)

    page.show_dialog(
        ft.AlertDialog(
            title=ft.Row(
                spacing=8,
                controls=[
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN),
                    ft.Text("Export Complete", weight=ft.FontWeight.BOLD),
                ],
            ),
            content=ft.Container(
                width=340,
                content=ft.Column(
                    spacing=10,
                    tight=True,
                    controls=[
                        ft.Text(f"Successfully exported {len(state.history)} sets to CSV!"),
                        ft.Container(
                            padding=10,
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                            border_radius=8,
                            content=ft.Column(
                                spacing=4,
                                controls=[
                                    ft.Text(location_label, size=11, color=ft.Colors.OUTLINE),
                                    ft.Text(location_value, size=12, weight=ft.FontWeight.BOLD),
                                ],
                            ),
                        ),
                        ft.Row(
                            spacing=6,
                            controls=[
                                ft.Icon(ft.Icons.COPY_ALL, size=16, color=ft.Colors.PRIMARY),
                                ft.Text(
                                    "Copied to clipboard for Sheets / Excel!" if copied else "Ready to share",
                                    size=12,
                                    color=ft.Colors.PRIMARY,
                                    weight=ft.FontWeight.W_600,
                                ),
                            ],
                        ),
                        ft.Text("Preview:", size=11, color=ft.Colors.OUTLINE),
                        ft.Container(
                            padding=8,
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                            border_radius=6,
                            content=ft.Text(preview_text, size=11, font_family="monospace"),
                        ),
                    ],
                ),
            ),
            actions=[
                ft.Button("OK", on_click=lambda _: page.pop_dialog()),
            ],
        )
    )
    page.update()
