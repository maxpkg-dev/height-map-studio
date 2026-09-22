# -*- coding: utf-8 -*-
import time
import os
from .qt import QtCore, QtGui, QtWidgets, QOpenGLWidget, gl_format
from .model import DEFAULTS, MAPS
from .controls import CheckBox, MapMode


class Preview(QOpenGLWidget):
    failed = QtCore.Signal(str)
    measured = QtCore.Signal(float, str)

    def __init__(self, parent=None):
        super(Preview, self).__init__(parent)
        self.setFormat(gl_format())
        self.setMinimumSize(280, 180)
        self.setToolTip("Wheel: zoom · Left drag: pan / rotate · Right drag in 3D: light · Double-click: reset")
        self.engine = None
        self.error = ""
        self.image = None
        self.original_size = (1, 1)
        self.settings = dict(DEFAULTS)
        self.kind = "normal"
        self.show_source = False
        self.is_3d = False
        self.shape = 1  # Plane, sphere, cube; start with the sphere.
        self.shape_selector = MapMode(self, shapes=True)
        self.shape_selector.setCurrentIndex(self.shape)
        self.shape_selector.hide()
        self.enabled_maps = dict.fromkeys(MAPS, True)
        self.preview_menu_button = QtWidgets.QToolButton(self)
        self.preview_menu_button.setText("Preview")
        self.preview_menu_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.preview_menu_button.setToolTip("Combine maps in 3D; independent of the current tab and export Set")
        menu = QtWidgets.QMenu(self.preview_menu_button)
        panel = QtWidgets.QWidget(menu)
        choices = QtWidgets.QVBoxLayout(panel)
        choices.setContentsMargins(8, 6, 8, 6)
        choices.setSpacing(4)
        self.map_checks = {}
        for kind, label in zip(MAPS, ("Normal", "Displace", "AO", "Specular")):
            check = CheckBox(label, panel)
            check.setProperty("compactIndicator", True)
            check.setChecked(True)
            check.toggled.connect(lambda enabled, key=kind: self.set_map_enabled(key, enabled))
            choices.addWidget(check)
            self.map_checks[kind] = check
        action = QtWidgets.QWidgetAction(menu)
        action.setDefaultWidget(panel)
        menu.addAction(action)
        self.preview_menu_button.setMenu(menu)
        menu.setStyleSheet("QMenu { background: #20252e; border: 1px solid #455166; } QWidget { font-size: 10px; } QCheckBox { spacing: 4px; } QCheckBox::indicator { width: 12px; height: 12px; }")
        self.preview_menu_button.setStyleSheet("QToolButton { font-size: 10px; padding: 1px 4px; background: #303846; border: 1px solid #455166; } QToolButton:hover { border-color: #6a88b2; }")
        self.preview_menu_button.setFixedHeight(20)
        self.preview_menu_button.hide()
        self.fit_button = QtWidgets.QPushButton(self)
        self.fit_button.setAutoDefault(False)
        self.fit_button.setFixedSize(28, 28)
        self.fit_button.setStyleSheet("QPushButton { padding: 3px; }")
        self.fit_icon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), "assets", "maximize.svg"))
        self.reset_icon = QtGui.QIcon(os.path.join(os.path.dirname(__file__), "assets", "rotate-ccw.svg"))
        self.fit_button.setIcon(self.fit_icon)
        self.fit_button.setIconSize(QtCore.QSize(16, 16))
        self.fit_button.setToolTip("Fit")
        self.fit_button.setAccessibleName("Fit")
        self.fit_button.clicked.connect(self.reset_view)
        self.zoom = 1.0
        self.pan = [0.0, 0.0]
        self.rotation = [0.25, -0.2]
        self.light_angle = -0.6
        self.last_position = None
        self.upload_dirty = False
        self.maps_dirty = True
        self.cache = {}

    def initializeGL(self):
        try:
            from .gl import Engine
            self.engine = Engine()
            self.upload_dirty = self.image is not None
            self.maps_dirty = True
            self.cache.clear()
            self.context().aboutToBeDestroyed.connect(self.cleanup)
        except Exception as exc:
            self.report_error(exc)

    def report_error(self, error):
        self.error = str(error)
        QtCore.QTimer.singleShot(0, lambda: self.failed.emit(self.error))

    def set_image(self, image, original_size):
        self.image, self.original_size = image, original_size
        self.upload_dirty = self.maps_dirty = True
        if self.engine is not None:
            self.error = ""
        self.reset_view()

    def refresh(self, settings=None):
        if settings is not None:
            if self.settings["seamless"] != settings["seamless"]:
                self.upload_dirty = True
            self.settings = dict(settings)
        self.maps_dirty = True
        self.update()

    def paintGL(self):
        if not self.engine or self.image is None or self.error:
            painter = QtGui.QPainter(self)
            painter.fillRect(self.rect(), QtGui.QColor("#161b22"))
            painter.setPen(QtGui.QColor("#8c99ab"))
            message = "GPU unavailable\n" + self.error if self.error else "Drop a height map here\nPNG · TIFF 16 bit · JPG"
            painter.drawText(self.rect().adjusted(20, 20, -20, -20), QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap, message)
            painter.end()
            return
        try:
            engine = self.engine
            started = time.perf_counter()
            recompute = self.upload_dirty or self.maps_dirty
            if self.upload_dirty:
                engine.upload(self.image, self.settings["seamless"])
                self.upload_dirty = False
                self.cache.clear()
            if self.maps_dirty:
                self.cache.clear()
                self.maps_dirty = False
            scale = (self.original_size[0] / float(self.image.width()), self.original_size[1] / float(self.image.height()))
            required = tuple(kind for kind in MAPS if self.enabled_maps[kind]) if self.is_3d else (self.kind,)
            for kind in required:
                if kind not in self.cache:
                    self.cache[kind] = engine.process(self.settings, kind, scale)
                    recompute = True
            texture = engine.textures["source"] if self.show_source else self.cache.get(self.kind, engine.textures["source"])
            fallback = texture
            textures = dict(resultMap=texture,
                            normalMap=self.cache.get("normal", fallback),
                            aoMap=self.cache.get("ao", fallback),
                            specMap=self.cache.get("specular", fallback),
                            dispMap=self.cache.get("displacement", fallback))
            ratio = self.devicePixelRatioF()
            width, height = int(self.width() * ratio), int(self.height() * ratio)
            engine.display(self.defaultFramebufferObject(), width, height, textures, dict(
                viewportSize=(float(width), float(height)),
                imageSize=(float(self.image.width()), float(self.image.height())),
                pan=(self.pan[0] * ratio, self.pan[1] * ratio), zoom=float(self.zoom),
                rotation=tuple(self.rotation), lightAngle=float(self.light_angle),
                view3d=int(self.is_3d), shape=int(self.shape), directx=self.settings["directx"],
                useNormal=self.enabled_maps["normal"], useDisplacement=self.enabled_maps["displacement"],
                useAO=self.enabled_maps["ao"], useSpecular=self.enabled_maps["specular"]))
            if recompute:
                # Include GPU completion in measured latency, not only command submission.
                engine.gl.Finish()
                elapsed = (time.perf_counter() - started) * 1000
                self.measured.emit(elapsed, engine.gl.description)
        except Exception as exc:
            self.report_error(exc)

    def set_map_enabled(self, kind, enabled):
        self.enabled_maps[kind] = bool(enabled)
        self.update()

    def reset_view(self):
        self.zoom, self.pan = 1.0, [0.0, 0.0]
        self.rotation, self.light_angle = [0.25, -0.2], -0.6
        self.update()

    def set_3d(self, enabled):
        self.is_3d = bool(enabled)
        self.preview_menu_button.setVisible(self.is_3d)
        if not self.is_3d:
            self.preview_menu_button.menu().hide()
        self.fit_button.setIcon(self.reset_icon if self.is_3d else self.fit_icon)
        label = "Reset view" if self.is_3d else "Fit"
        self.fit_button.setToolTip(label)
        self.fit_button.setAccessibleName(label)
        self.update()

    def wheelEvent(self, event):
        self.zoom = min(20.0, max(0.1, self.zoom * (1.15 ** (event.angleDelta().y() / 120.0))))
        self.update()
        event.accept()

    def resizeEvent(self, event):
        super(Preview, self).resizeEvent(event)
        size = self.shape_selector.sizeHint()
        self.shape_selector.resize(size)
        self.shape_selector.move(max(0, self.width() - size.width() - 8), 8)
        self.shape_selector.raise_()
        self.preview_menu_button.adjustSize()
        self.preview_menu_button.move(8, 8)
        self.preview_menu_button.raise_()
        self.fit_button.move(8, max(0, self.height() - self.fit_button.height() - 8))
        self.fit_button.raise_()

    def mousePressEvent(self, event):
        self.last_position = event.pos()

    def mouseMoveEvent(self, event):
        if self.last_position is None:
            return
        delta = event.pos() - self.last_position
        self.last_position = event.pos()
        if self.is_3d:
            if event.buttons() & QtCore.Qt.RightButton:
                self.light_angle += delta.x() * 0.015
            elif event.buttons() & QtCore.Qt.LeftButton:
                self.rotation[0] += delta.x() * 0.01
                self.rotation[1] += delta.y() * 0.01
        elif event.buttons() & QtCore.Qt.LeftButton:
            self.pan[0] += delta.x()
            self.pan[1] -= delta.y()
        self.update()

    def mouseReleaseEvent(self, event):
        self.last_position = None

    def mouseDoubleClickEvent(self, event):
        self.reset_view()

    def cleanup(self):
        if self.engine is not None:
            self.makeCurrent()
            self.engine.close()
            self.engine = None
            self.doneCurrent()
