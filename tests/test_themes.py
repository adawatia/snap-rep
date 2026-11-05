"""Theme choices and wallpaper color bridge behavior."""

from pathlib import Path

import pytest

from state import AppState
from storage import AppStorage
from theme import PALETTES, get_palette_themes


@pytest.mark.parametrize("palette", PALETTES)
def test_palette_has_legible_light_and_dark_roles(palette):
    light, dark = get_palette_themes(palette)
    for theme in (light, dark):
        scheme = theme.color_scheme
        assert scheme.primary.startswith("#")
        assert scheme.on_primary.startswith("#")
        assert scheme.surface.startswith("#")
        assert scheme.on_surface.startswith("#")
        assert theme.scaffold_bgcolor == scheme.surface
    assert light.color_scheme.surface != dark.color_scheme.surface


def test_material_you_dynamic_roles_override_static_fallback():
    override = {
        "light": {"primary": "#123456", "surface": "#FDFDFC"},
        "dark": {"primary": "#ABCDEF", "surface": "#111111"},
    }
    light, dark = get_palette_themes("material_you", override)
    assert light.color_scheme.primary == "#123456"
    assert dark.color_scheme.primary == "#ABCDEF"
    assert light.scaffold_bgcolor == "#FDFDFC"
    assert dark.scaffold_bgcolor == "#111111"


@pytest.mark.asyncio
async def test_palette_and_mode_survive_restart_and_restore(tmp_path: Path):
    storage = AppStorage(storage_dir=tmp_path)
    state = AppState(storage=storage)
    state.update_setting("theme_palette", "catppuccin")
    state.update_setting("theme_mode", "dark")
    backup = storage.create_backup()[2]
    reloaded = AppState(storage=AppStorage(storage_dir=tmp_path))
    assert reloaded.settings["theme_palette"] == "catppuccin"
    assert reloaded.settings["theme_mode"] == "dark"
    reloaded.update_setting("theme_palette", "gruvbox")
    await reloaded.restore_backup(backup, mode="replace")
    assert reloaded.settings["theme_palette"] == "catppuccin"
    assert reloaded.settings["theme_mode"] == "dark"
