"""Isolated fallback lifecycle tests; does not connect to or emulate a Max session."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


class Signal:
    def connect(self, callback):
        self.callback = callback


class Widget:
    def __init__(self, parent=None):
        self.parent = parent
        self.destroyed = Signal()
        self.filters = []

    def findChildren(self, kind):
        return []

    def installEventFilter(self, guard):
        if guard not in self.filters:
            self.filters.append(guard)

    def removeEventFilter(self, guard):
        self.filters.remove(guard)

    def window(self):
        return self.parent or self


events = types.SimpleNamespace(FocusIn=1, FocusOut=2, Hide=3, Close=4, WindowDeactivate=5)
qt = types.ModuleType("heightmap_studio.qt")
qt.QtCore = types.SimpleNamespace(QObject=Widget, QEvent=events)
qt.QtWidgets = types.SimpleNamespace(QLineEdit=Widget)
sys.modules["heightmap_studio.qt"] = qt
sys.modules["qtmax"] = types.ModuleType("qtmax")
runtime = types.SimpleNamespace(enableAccelerators=True)
sys.modules["pymxs"] = types.SimpleNamespace(runtime=runtime)
spec = importlib.util.spec_from_file_location("heightmap_studio.accelerators",
    str(Path(__file__).resolve().parents[1] / "HeightMapStudio/heightmap_studio/accelerators.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Checks(unittest.TestCase):
    def setUp(self):
        runtime.enableAccelerators = True
        if hasattr(sys.modules["qtmax"], "DisableMaxAcceleratorsOnFocus"):
            del sys.modules["qtmax"].DisableMaxAcceleratorsOnFocus

    def test_restore_every_exit(self):
        for kind in (events.FocusOut, events.Hide, events.Close, events.WindowDeactivate):
            field = Widget(Widget())
            module.protect_text_entry(field)
            guard = field._max_focus_guard
            guard.eventFilter(field, types.SimpleNamespace(type=lambda: events.FocusIn))
            self.assertFalse(runtime.enableAccelerators)
            guard.eventFilter(field, types.SimpleNamespace(type=lambda: kind))
            self.assertTrue(runtime.enableAccelerators)

    def test_destroy_and_duplicate_focus(self):
        field = Widget(Widget())
        module.protect_text_entry(field)
        first = field._max_focus_guard
        module.protect_text_entry(field)
        self.assertIs(first, field._max_focus_guard)
        first.acquire()
        first.acquire()
        field.destroyed.callback()
        self.assertTrue(runtime.enableAccelerators)

    def test_preserve_disabled_state(self):
        runtime.enableAccelerators = False
        guard = module.FocusGuard(Widget(), runtime)
        guard.acquire()
        guard.release()
        self.assertFalse(runtime.enableAccelerators)

    def test_native_helper_preferred(self):
        calls = []
        sys.modules["qtmax"].DisableMaxAcceleratorsOnFocus = lambda *args: calls.append(args)
        field = Widget()
        module.protect_text_entry(field)
        self.assertEqual(calls, [(field, True)])
        self.assertFalse(hasattr(field, "_max_focus_guard"))

    def test_native_errors_not_hidden(self):
        def failure(*args):
            raise RuntimeError("native failure")
        sys.modules["qtmax"].DisableMaxAcceleratorsOnFocus = failure
        with self.assertRaises(RuntimeError):
            module.protect_text_entry(Widget())


if __name__ == "__main__":
    unittest.main()
