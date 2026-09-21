"""Protect numeric text entry on Max versions without the qtmax focus helper."""
from .qt import QtCore, QtWidgets


class FocusGuard(QtCore.QObject):
    def __init__(self, widget, runtime):
        super(FocusGuard, self).__init__(widget)
        self.widget = widget
        self.runtime = runtime
        self.active = False
        self.previous = True
        self.window = None
        widget.installEventFilter(self)
        for child in widget.findChildren(QtWidgets.QLineEdit):
            child.installEventFilter(self)
        widget.destroyed.connect(self.release)

    def acquire(self):
        if self.active:
            return
        self.previous = bool(self.runtime.enableAccelerators)
        self.runtime.enableAccelerators = False
        self.active = True
        window = self.widget.window()
        if window is not self.window:
            if self.window is not None:
                self.window.removeEventFilter(self)
            self.window = window
            window.installEventFilter(self)

    def release(self, *unused):
        if self.active:
            self.runtime.enableAccelerators = self.previous
            self.active = False

    def eventFilter(self, watched, event):
        kind = event.type()
        if kind == QtCore.QEvent.FocusIn:
            if watched is not self.window or watched is self.widget:
                self.acquire()
        elif kind in (QtCore.QEvent.FocusOut, QtCore.QEvent.Hide,
                      QtCore.QEvent.Close, QtCore.QEvent.WindowDeactivate):
            self.release()
        return False


def protect_text_entry(widget):
    try:
        import qtmax
    except ImportError:
        return  # Standalone Qt use has no Max shortcuts to manage.
    helper = getattr(qtmax, "DisableMaxAcceleratorsOnFocus", None)
    if callable(helper):
        helper(widget, True)
        return
    from pymxs import runtime
    if not hasattr(widget, "_max_focus_guard"):
        widget._max_focus_guard = FocusGuard(widget, runtime)
