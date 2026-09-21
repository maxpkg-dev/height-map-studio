"""Persist window placement and derive a square first-run preview from the layout."""
from .qt import QtCore, QtGui, QtWidgets


def settings_store():
    return QtCore.QSettings(QtCore.QSettings.IniFormat, QtCore.QSettings.UserScope,
                           "HeightMapStudio", "Window")


def keep_visible(window):
    screens = QtWidgets.QApplication.screens()
    if not screens:
        return
    frame = window.frameGeometry()
    def overlap(screen):
        intersection = frame.intersected(screen.availableGeometry())
        return max(0, intersection.width()) * max(0, intersection.height())
    screen = max(screens, key=overlap)
    if overlap(screen) == 0:
        screen = window.parentWidget().screen() if window.parentWidget() else QtGui.QGuiApplication.primaryScreen()
    available = screen.availableGeometry()
    decoration_w = max(0, frame.width() - window.width())
    decoration_h = max(0, frame.height() - window.height())
    window.resize(min(window.width(), max(1, available.width() - decoration_w)),
                  min(window.height(), max(1, available.height() - decoration_h)))
    frame = window.frameGeometry()
    x = max(available.left(), min(frame.left(), available.right() - frame.width() + 1))
    y = max(available.top(), min(frame.top(), available.bottom() - frame.height() + 1))
    window.move(x, y)


def fit_first_run(window):
    layout = window.layout()
    layout.activate()
    margins = layout.contentsMargins()
    width = max(layout.minimumSize().width(),
                window.advanced.sizeHint().width() + margins.left() + margins.right())
    window.resize(width, layout.sizeHint().height())
    # Measure after Qt has applied font metrics, DPI, margins, spacing and toolbar heights.
    for unused in range(3):
        layout.activate()
        delta = window.preview.width() - window.preview.height()
        if delta == 0:
            break
        window.resize(window.width(), window.height() + delta)
    screen = window.parentWidget().screen() if window.parentWidget() else QtGui.QGuiApplication.primaryScreen()
    if screen is not None:
        area = screen.availableGeometry()
        frame = window.frameGeometry()
        window.move(area.center().x() - frame.width() // 2,
                    area.center().y() - frame.height() // 2)
    keep_visible(window)


def restore(window):
    saved = window.geometry_settings.value("geometry")
    if isinstance(saved, QtCore.QByteArray) and not saved.isEmpty() and window.restoreGeometry(saved):
        keep_visible(window)
        return "saved"
    fit_first_run(window)
    return "first_run"


def save(window):
    window.geometry_settings.setValue("geometry", window.saveGeometry())
    window.geometry_settings.sync()
