"""Reload the English interface in Max while preserving the current session."""
import importlib
import json
import os
import re
from heightmap_studio import ui
from heightmap_studio import geometry
from heightmap_studio.qt import QtCore, QtWidgets
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def reopen():
    previous = ui._window
    snapshot = None
    if previous is not None:
        try:
            previous.isVisible()
        except RuntimeError:
            previous = None
    if previous is not None:
        if previous.load_jobs or previous.export_job:
            raise RuntimeError("Wait for the active image operation before reloading the interface.")
        snapshot = dict(
            image=previous.image, preview=previous.preview.image,
            filename=previous.filename, settings=dict(previous.settings),
            size=previous.size(), position=previous.pos(),
            kind=previous.tabs.currentIndex(), mode=previous.mode.currentIndex(),
            shape=previous.shape.currentIndex(), source=previous.source.isChecked(),
            advanced=previous.advanced_toggle.isChecked(),
            format=previous.format.currentData() or ("JPEG" if previous.format.currentText().startswith("JPEG") else previous.format.currentText()), slate=previous.add_slate.isChecked(),
            zoom=previous.preview.zoom, pan=list(previous.preview.pan),
            rotation=list(previous.preview.rotation), light=previous.preview.light_angle)
        # Seed placement from the already-open window when upgrading an older build.
        store = geometry.settings_store()
        store.setValue("geometry", previous.saveGeometry())
        store.sync()
        previous.close()
    for name in ("qt", "model", "ranges", "geometry", "imageio", "gl", "jobs", "maxbridge", "controls", "preview", "settings_dialog", "ui"):
        module = importlib.import_module("heightmap_studio." + name)
        importlib.reload(module)
    window = ui.show()
    if snapshot is not None:
        window.resize(snapshot["size"])
        window.move(snapshot["position"])
        window.settings = snapshot["settings"]
        for key, control in window.parameters.items():
            control.set_value(snapshot["settings"][key])
        window.convention.setCurrentIndex(int(snapshot["settings"]["directx"]))
        window.invert.setChecked(snapshot["settings"]["invert"])
        window.seamless.setChecked(snapshot["settings"]["seamless"])
        window.tabs.setCurrentIndex(snapshot["kind"])
        window.mode.setCurrentIndex(snapshot["mode"])
        window.shape.setCurrentIndex(snapshot["shape"])
        window.source.setChecked(snapshot["source"])
        window.advanced_toggle.setChecked(snapshot["advanced"])
        window.format.setCurrentIndex(window.format.findData(snapshot["format"]))
        window.add_slate.setChecked(snapshot["slate"])
        if snapshot["image"] is not None:
            from heightmap_studio.imageio import source_depth
            window.loaded(window.generation, snapshot["filename"], snapshot["image"],
                          snapshot["preview"], source_depth(snapshot["filename"]))
            window.preview.zoom = snapshot["zoom"]
            window.preview.pan = snapshot["pan"]
            window.preview.rotation = snapshot["rotation"]
            window.preview.light_angle = snapshot["light"]
    QtCore.QTimer.singleShot(250, lambda: inspect(window))


def inspect(window):
    labels = []
    for widget in window.findChildren(QtWidgets.QWidget):
        if isinstance(widget, (QtWidgets.QLabel, QtWidgets.QAbstractButton)):
            labels.append(widget.text())
        elif isinstance(widget, QtWidgets.QComboBox):
            labels.extend(widget.itemText(index) for index in range(widget.count()))
        if widget.toolTip():
            labels.append(widget.toolTip())
    assert not any(re.search(r"[\u0400-\u052f]", value) for value in labels)
    assert window.open_button.text() == "Open image…"
    assert window.save_button.text() == "Save" and not hasattr(window, "save_set_button")
    assert not window.preview.error, window.preview.error
    result = dict(english_labels=True, labels=labels, width=window.width(),
                  height=window.height(), gpu_error=window.preview.error,
                  preview_ms=window.last_measurement, hwnd=int(window.winId()))
    with open(os.path.join(ROOT, "work", "english_ui_check.json"), "w", encoding="utf8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)


reopen()
