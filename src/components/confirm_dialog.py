"""Reusable confirmation dialog component."""

from typing import Awaitable, Callable, Optional
import flet as ft


def show_confirm_dialog(
    page: ft.Page,
    title: str,
    message: str,
    confirm_text: str = "Confirm",
    cancel_text: str = "Cancel",
    is_destructive: bool = False,
    on_confirm: Optional[Callable[[], Awaitable[None]]] = None,
) -> None:
    async def handle_confirm(e):
        page.pop_dialog()
        if on_confirm:
            await on_confirm()

    page.show_dialog(
        ft.AlertDialog(
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            content=ft.Text(message),
            actions=[
                ft.TextButton(cancel_text, on_click=lambda _: page.pop_dialog()),
                ft.TextButton(
                    confirm_text,
                    style=ft.ButtonStyle(
                        color=ft.Colors.ERROR if is_destructive else ft.Colors.PRIMARY,
                    ),
                    on_click=handle_confirm,
                ),
            ],
        )
    )
