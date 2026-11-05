"""Flet service exposing Android wallpaper color schemes."""

from typing import Optional
import flet as ft


@ft.control("SnaprepDynamicColor")
class SnaprepDynamicColor(ft.Service):
    on_schemes: Optional[ft.EventHandler[ft.ControlEvent]] = None

    async def refresh(self) -> None:
        await self._invoke_method("refresh")
