"""Theme configuration and color palettes for SnapRep."""

import flet as ft

# Warm coral actions over layered deep navy surfaces.
COLOR_PRIMARY = "#FF907E"
COLOR_ON_PRIMARY = "#3D1915"
COLOR_PRIMARY_CONTAINER = "#65352F"
COLOR_ON_PRIMARY_CONTAINER = "#FFE0D8"

COLOR_SECONDARY = "#B5CFD8"
COLOR_ON_SECONDARY = "#173642"
COLOR_SECONDARY_CONTAINER = "#2C4B59"
COLOR_ON_SECONDARY_CONTAINER = "#D5EBF0"

COLOR_TERTIARY = "#F0BE78"
COLOR_ON_TERTIARY = "#49300D"
COLOR_TERTIARY_CONTAINER = "#634B2A"
COLOR_ON_TERTIARY_CONTAINER = "#FFE2B7"

COLOR_SURFACE_DARK = "#0D1B28"
COLOR_CONTAINER_DARK = "#172838"
COLOR_CONTAINER_HIGH_DARK = "#203446"
COLOR_CONTAINER_HIGHEST_DARK = "#2A4152"
COLOR_ON_SURFACE_DARK = "#F3F6F7"
COLOR_ON_SURFACE_VARIANT_DARK = "#C2D0D7"
COLOR_OUTLINE_DARK = "#A1B4BE"
COLOR_OUTLINE_VARIANT_DARK = "#496170"

# Warm off-white canvas with navy text and a deeper coral action color.
COLOR_PRIMARY_LIGHT = "#AA3934"
COLOR_ON_PRIMARY_LIGHT = "#FFFFFF"
COLOR_PRIMARY_CONTAINER_LIGHT = "#FCE4DC"
COLOR_ON_PRIMARY_CONTAINER_LIGHT = "#732B27"

COLOR_SECONDARY_LIGHT = "#375D6E"
COLOR_ON_SECONDARY_LIGHT = "#FFFFFF"
COLOR_SECONDARY_CONTAINER_LIGHT = "#DCEBF0"
COLOR_ON_SECONDARY_CONTAINER_LIGHT = "#244957"

COLOR_TERTIARY_LIGHT = "#8B541D"
COLOR_ON_TERTIARY_LIGHT = "#FFFFFF"
COLOR_TERTIARY_CONTAINER_LIGHT = "#F6E5CB"
COLOR_ON_TERTIARY_CONTAINER_LIGHT = "#603B14"
COLOR_SURFACE_LIGHT = "#F8F5F1"
COLOR_CONTAINER_LIGHT = "#FFFCF8"
COLOR_CONTAINER_HIGH_LIGHT = "#F4EEE8"
COLOR_CONTAINER_HIGHEST_LIGHT = "#EDE5DD"
COLOR_ON_SURFACE_LIGHT = "#192B38"
COLOR_ON_SURFACE_VARIANT_LIGHT = "#4B606B"
COLOR_OUTLINE_LIGHT = "#637783"
COLOR_OUTLINE_VARIANT_LIGHT = "#CEC8C2"


def get_dark_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=COLOR_PRIMARY,
            on_primary=COLOR_ON_PRIMARY,
            primary_container=COLOR_PRIMARY_CONTAINER,
            on_primary_container=COLOR_ON_PRIMARY_CONTAINER,
            secondary=COLOR_SECONDARY,
            on_secondary=COLOR_ON_SECONDARY,
            secondary_container=COLOR_SECONDARY_CONTAINER,
            on_secondary_container=COLOR_ON_SECONDARY_CONTAINER,
            tertiary=COLOR_TERTIARY,
            on_tertiary=COLOR_ON_TERTIARY,
            tertiary_container=COLOR_TERTIARY_CONTAINER,
            on_tertiary_container=COLOR_ON_TERTIARY_CONTAINER,
            surface=COLOR_SURFACE_DARK,
            on_surface=COLOR_ON_SURFACE_DARK,
            on_surface_variant=COLOR_ON_SURFACE_VARIANT_DARK,
            surface_container=COLOR_CONTAINER_DARK,
            surface_container_high=COLOR_CONTAINER_HIGH_DARK,
            surface_container_highest=COLOR_CONTAINER_HIGHEST_DARK,
            outline=COLOR_OUTLINE_DARK,
            outline_variant=COLOR_OUTLINE_VARIANT_DARK,
        ),
        card_bgcolor=COLOR_CONTAINER_DARK,
        scaffold_bgcolor=COLOR_SURFACE_DARK,
        scrollbar_theme=ft.ScrollbarTheme(
            thumb_color=COLOR_PRIMARY,
            thickness=4,
            radius=8,
            thumb_visibility=False,
            track_visibility=False,
            interactive=True,
        ),
    )


def get_light_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=COLOR_PRIMARY_LIGHT,
            on_primary=COLOR_ON_PRIMARY_LIGHT,
            primary_container=COLOR_PRIMARY_CONTAINER_LIGHT,
            on_primary_container=COLOR_ON_PRIMARY_CONTAINER_LIGHT,
            secondary=COLOR_SECONDARY_LIGHT,
            on_secondary=COLOR_ON_SECONDARY_LIGHT,
            secondary_container=COLOR_SECONDARY_CONTAINER_LIGHT,
            on_secondary_container=COLOR_ON_SECONDARY_CONTAINER_LIGHT,
            tertiary=COLOR_TERTIARY_LIGHT,
            on_tertiary=COLOR_ON_TERTIARY_LIGHT,
            tertiary_container=COLOR_TERTIARY_CONTAINER_LIGHT,
            on_tertiary_container=COLOR_ON_TERTIARY_CONTAINER_LIGHT,
            surface=COLOR_SURFACE_LIGHT,
            on_surface=COLOR_ON_SURFACE_LIGHT,
            on_surface_variant=COLOR_ON_SURFACE_VARIANT_LIGHT,
            surface_container=COLOR_CONTAINER_LIGHT,
            surface_container_high=COLOR_CONTAINER_HIGH_LIGHT,
            surface_container_highest=COLOR_CONTAINER_HIGHEST_LIGHT,
            outline=COLOR_OUTLINE_LIGHT,
            outline_variant=COLOR_OUTLINE_VARIANT_LIGHT,
        ),
        card_bgcolor=COLOR_CONTAINER_LIGHT,
        scaffold_bgcolor=COLOR_SURFACE_LIGHT,
        scrollbar_theme=ft.ScrollbarTheme(
            thumb_color=COLOR_PRIMARY_LIGHT,
            thickness=4,
            radius=8,
            thumb_visibility=False,
            track_visibility=False,
            interactive=True,
        ),
    )


def resolve_theme_mode(mode_name: str) -> ft.ThemeMode:
    clean = (mode_name or "").lower().strip()
    if clean == "light":
        return ft.ThemeMode.LIGHT
    elif clean == "dark":
        return ft.ThemeMode.DARK
    return ft.ThemeMode.SYSTEM
