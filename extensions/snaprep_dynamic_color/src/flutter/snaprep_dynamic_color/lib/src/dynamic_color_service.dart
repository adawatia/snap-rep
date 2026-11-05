import 'package:dynamic_color/dynamic_color.dart';
import 'package:flet/flet.dart';
import 'package:flutter/material.dart';

class SnaprepDynamicColorService extends FletService {
  SnaprepDynamicColorService({required super.control});

  @override
  void init() {
    super.init();
    control.addInvokeMethodListener(_onInvokeMethod);
    _refresh();
  }

  Future<dynamic> _onInvokeMethod(String name, dynamic args) async {
    if (name == 'refresh') {
      await _refresh();
    }
    return null;
  }

  Future<void> _refresh() async {
    try {
      final palette = await DynamicColorPlugin.getCorePalette();
      if (palette == null) {
        control.triggerEvent('schemes', {'available': false});
        return;
      }
      control.triggerEvent('schemes', {
        'available': true,
        'light': _roles(palette.toColorScheme(brightness: Brightness.light)),
        'dark': _roles(palette.toColorScheme(brightness: Brightness.dark)),
      });
    } catch (_) {
      control.triggerEvent('schemes', {'available': false});
    }
  }

  Map<String, String> _roles(ColorScheme scheme) {
    String hex(Color color) => '#${color.toARGB32().toRadixString(16).substring(2).toUpperCase()}';
    return {
      'primary': hex(scheme.primary),
      'on_primary': hex(scheme.onPrimary),
      'primary_container': hex(scheme.primaryContainer),
      'on_primary_container': hex(scheme.onPrimaryContainer),
      'secondary': hex(scheme.secondary),
      'on_secondary': hex(scheme.onSecondary),
      'secondary_container': hex(scheme.secondaryContainer),
      'on_secondary_container': hex(scheme.onSecondaryContainer),
      'tertiary': hex(scheme.tertiary),
      'on_tertiary': hex(scheme.onTertiary),
      'tertiary_container': hex(scheme.tertiaryContainer),
      'on_tertiary_container': hex(scheme.onTertiaryContainer),
      'surface': hex(scheme.surface),
      'on_surface': hex(scheme.onSurface),
      'on_surface_variant': hex(scheme.onSurfaceVariant),
      'surface_container': hex(scheme.surfaceContainer),
      'surface_container_high': hex(scheme.surfaceContainerHigh),
      'surface_container_highest': hex(scheme.surfaceContainerHighest),
      'outline': hex(scheme.outline),
      'outline_variant': hex(scheme.outlineVariant),
    };
  }

  @override
  void dispose() {
    control.removeInvokeMethodListener(_onInvokeMethod);
    super.dispose();
  }
}
