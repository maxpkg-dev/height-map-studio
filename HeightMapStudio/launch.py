# -*- coding: utf-8 -*-
"""Entry point for 3ds Max's bundled Python; no pip installation needed."""
import os
import sys
import hashlib
import importlib
from pathlib import Path

def launch(root):
    root = os.path.realpath(root)
    digest = hashlib.sha256(root.encode("utf8"))
    for path in sorted(Path(root).rglob("*")):
        if path.suffix in (".py", ".frag", ".svg") and "__pycache__" not in path.parts:
            digest.update(str(path.relative_to(root)).encode("utf8"))
            digest.update(path.read_bytes())
    signature = digest.hexdigest()
    module = sys.modules.get("heightmap_studio.ui")
    previous = getattr(module, "_window", None)
    if previous is not None:
        try:
            previous.isVisible()
        except RuntimeError:
            previous = None
    if module is not None and getattr(module, "_launch_signature", None) == signature:
        return module.show()
    snapshot = None
    if previous is not None:
        if previous.load_jobs or previous.export_job:
            previous.status.setText("Finish the current image operation, then run Launch again to update.")
            previous.raise_()
            return previous
        snapshot = dict(image=previous.image, preview=previous.preview.image,
                        filename=previous.filename, label=previous.file_label.text(),
                        settings=dict(previous.settings), tab=previous.tabs.currentIndex(),
                        mode=previous.mode.currentIndex(), shape=previous.shape.currentIndex(),
                        shape_explicit=getattr(previous, "shape_explicit", previous.shape.currentIndex() != 0),
                        source=previous.source.isChecked(), advanced=previous.advanced_toggle.isChecked(),
                        zoom=previous.preview.zoom, pan=list(previous.preview.pan),
                        rotation=list(previous.preview.rotation), light=previous.preview.light_angle,
                        enabled_maps=dict(getattr(previous.preview, "enabled_maps", {})))
        from heightmap_studio.qt import QtCore
        previous.close()
        QtCore.QCoreApplication.sendPostedEvents(previous, QtCore.QEvent.DeferredDelete)
    for name in list(sys.modules):
        if name == "heightmap_studio" or name.startswith("heightmap_studio."):
            del sys.modules[name]
    sys.path[:] = [p for p in sys.path if os.path.normcase(os.path.realpath(p)) != os.path.normcase(root)]
    sys.path.insert(0, root)
    importlib.invalidate_caches()
    from heightmap_studio import ui
    window = ui.show()
    ui._launch_signature = signature
    if snapshot is not None:
        if snapshot["image"] is not None:
            window.generation = 1  # Keep an existing user image; empty windows still load the demo.
        for key, value in snapshot["settings"].items():
            if key in window.parameters:
                window.parameters[key].set_value(value)
        window.convention.setCurrentIndex(int(snapshot["settings"]["directx"]))
        window.invert.setChecked(snapshot["settings"]["invert"])
        window.seamless.setChecked(snapshot["settings"]["seamless"])
        window.tabs.setCurrentIndex(snapshot["tab"])
        window.mode.setCurrentIndex(snapshot["mode"])
        if snapshot["shape_explicit"]:
            window.shape.setCurrentIndex(snapshot["shape"])
            window.shape_explicit = True
        window.source.setChecked(snapshot["source"])
        window.advanced_toggle.setChecked(snapshot["advanced"])
        if snapshot["image"] is not None:
            window.image = snapshot["image"]
            window.filename = snapshot["filename"]
            window.last_directory = os.path.dirname(window.filename)
            window.file_label.setText(snapshot["label"])
            window.file_label.setToolTip(window.filename)
            window.preview.set_image(snapshot["preview"], (window.image.width(), window.image.height()))
            window.set_export_enabled(window.preview.engine is not None and not window.preview.error)
        window.preview.zoom = snapshot["zoom"]
        window.preview.pan = snapshot["pan"]
        window.preview.rotation = snapshot["rotation"]
        window.preview.light_angle = snapshot["light"]
        for kind, enabled in snapshot["enabled_maps"].items():
            window.preview.map_checks[kind].setChecked(enabled)
    return window


launch(os.path.dirname(os.path.abspath(__file__)))
