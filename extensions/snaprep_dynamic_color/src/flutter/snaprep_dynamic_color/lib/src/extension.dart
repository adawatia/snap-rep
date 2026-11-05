import 'package:flet/flet.dart';
import 'package:flutter/widgets.dart';
import 'dynamic_color_service.dart';

class Extension extends FletExtension {
  @override
  void ensureInitialized() {}

  @override
  Widget? createWidget(Key? key, Control control) => null;

  @override
  FletService? createService(Control control) {
    if (control.type == 'SnaprepDynamicColor') {
      return SnaprepDynamicColorService(control: control);
    }
    return null;
  }
}
