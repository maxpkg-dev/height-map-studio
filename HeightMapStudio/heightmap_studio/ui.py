# -*- coding: utf-8 -*-
import os
from .qt import QtCore, QtGui, QtWidgets, gl_format
from .model import DEFAULTS, MAPS
from .preview import Preview
from .promotion import PromotionStrip
from .jobs import LoadJob, ExportJob
from . import geometry
from . import saved_maps
from .accelerators import protect_text_entry
from .controls import CheckBox, MapMode, NumberSpinBox
from .ranges import GROUPS, FIELDS, saved_maximum, validate_maximum

_window = None

STYLE = """
QDialog { background: #20252e; color: #e6eaf0; }
QWidget { font-family: 'Segoe UI'; font-size: 12px; color: #e6eaf0; }
QLabel#title { font-size: 18px; font-weight: 600; }
QLabel#muted { color: #9aa8bb; }
QPushButton, QComboBox, QDoubleSpinBox { background: #303846; border: 1px solid #455166; border-radius: 0; padding: 5px 9px; }
QDoubleSpinBox QLineEdit { background: transparent; border: 0; border-radius: 0; padding: 0; }
QDoubleSpinBox { padding: 0px 15px 0px 3px; min-height: 18px; }
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { subcontrol-origin: border; width: 14px; height: 10px; background: #354153; border-left: 1px solid #455166; }
QDoubleSpinBox::up-button { subcontrol-position: top right; border-bottom: 1px solid #455166; }
QDoubleSpinBox::down-button { subcontrol-position: bottom right; }
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover { background: #496184; }
QDoubleSpinBox::up-button:pressed, QDoubleSpinBox::down-button:pressed { background: #386fc1; }
QDoubleSpinBox::up-arrow, QDoubleSpinBox::down-arrow { image: none; }
QComboBox#exportFormat { padding: 2px 7px; }
QComboBox:hover, QDoubleSpinBox:hover { border-color: #6a88b2; }
QPushButton:focus, QComboBox:focus, QDoubleSpinBox:focus { border-color: #a1c6ff; }
QPushButton:hover { background: #3a4658; border-color: #6a88b2; }
QPushButton:checked, QPushButton#primary { background: #386fc1; border-color: #578bdd; }
QPushButton:disabled, QComboBox:disabled, QDoubleSpinBox:disabled { color: #727f91; background: #292f39; border-color: #36404e; }
QTabBar::tab { background: #292f39; padding: 7px 14px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { background: #303a49; border-bottom: 2px solid #6da9ff; }
QSlider::groove:horizontal { background: #141922; height: 5px; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #578bdd; border-radius: 2px; }
QSlider::handle:horizontal { background: #b4d1ff; width: 12px; margin: -4px 0; border-radius: 6px; }
QCheckBox { spacing: 6px; }
QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #586981; background: #252d39; image: none; }
QCheckBox::indicator:checked { background: #386fc1; border-color: #578bdd; }
QCheckBox::indicator:hover { border-color: #a1c6ff; }
QCheckBox:focus { color: #b4d1ff; }
QCheckBox::indicator:disabled { background: #292f39; border-color: #36404e; }
QCheckBox:disabled { color: #727f91; }
QGroupBox { border: 1px solid #3c485a; margin-top: 8px; padding-top: 7px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; color: #9aa8bb; }
QProgressBar { background: #151a22; border: 0; border-radius: 0; text-align: center; }
QProgressBar::chunk { background: #386fc1; }
QToolTip { background: #303846; color: #e6eaf0; border: 1px solid #578bdd; }
"""


class StatusLabel(QtWidgets.QLabel):
    COLORS = {"success": "#58c777", "error": "#ff6b6b", "warning": "#ffb347"}

    def setText(self, text, severity="info"):
        self.setStyleSheet("color: %s;" % self.COLORS[severity] if severity in self.COLORS else "")
        super(StatusLabel, self).setText(text)


class Parameter(QtWidgets.QWidget):
    changed = QtCore.Signal(str, float)

    def __init__(self, key, title, low, high, default, parent=None):
        super(Parameter, self).__init__(parent)
        self.key = key
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QtWidgets.QLabel(title)
        label.setFixedWidth(82)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(round(low * 100), round(high * 100))
        self.spin = NumberSpinBox()
        self.spin.setRange(low, FIELDS[key][4])
        self.spin.setDecimals(2)
        self.spin.setSingleStep(0.1 if high <= 16 or key == "strength" else 1)
        self.spin.setFixedWidth(68)
        self.spin.setFixedHeight(22)
        self.spin.setKeyboardTracking(False)
        protect_text_entry(self.spin)
        self.slider.setValue(round(default * 100))
        self.spin.setValue(default)
        layout.addWidget(label)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spin)
        self.slider.valueChanged.connect(lambda value: self.set_value(value / 100.0))
        self.spin.valueChanged.connect(self.set_value)

    def set_value(self, value):
        self.spin.blockSignals(True)
        self.slider.blockSignals(True)
        self.spin.setValue(value)
        value = self.spin.value()
        self.slider.setValue(round(value * 100))
        self.spin.blockSignals(False)
        self.slider.blockSignals(False)
        self.changed.emit(self.key, float(value))

    def set_slider_maximum(self, value):
        maximum = round(validate_maximum(self.key, value) * 100)
        previous = self.slider.blockSignals(True)
        self.slider.setMaximum(maximum)
        self.slider.setValue(round(self.spin.value() * 100))
        self.slider.blockSignals(previous)


class Studio(QtWidgets.QDialog):
    def __init__(self, parent=None, geometry_settings=None):
        super(Studio, self).__init__(parent)
        self.setWindowTitle("Height Map Studio - 3DGROUND")
        self.setObjectName("HeightMapStudio")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowMinMaxButtonsHint)
        self.geometry_settings = geometry_settings if geometry_settings is not None else geometry.settings_store()
        self.geometry_ready = False
        self.geometry_source = "pending"
        self.setAcceptDrops(True)
        self.setStyleSheet(STYLE)
        self.settings = dict(DEFAULTS)
        self.image = None
        self.filename = ""
        self.generation = 0
        self.load_jobs = set()
        self.pending_load = None
        self.export_job = None
        self.surface = None
        self.closing = False
        self.last_directory = ""
        self.last_measurement = None
        self.slate_status_active = False
        self.settings_dialog = None
        self.shape_explicit = False
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(80)
        self.timer.timeout.connect(lambda: self.preview.refresh(self.settings))
        self._build()

    def showEvent(self, event):
        super(Studio, self).showEvent(event)
        if not self.geometry_ready:
            self.geometry_ready = True
            QtCore.QTimer.singleShot(0, self.restore_window_geometry)
            QtCore.QTimer.singleShot(0, self.load_demo_if_empty)

    def load_demo_if_empty(self):
        # An explicit load, including a failed one, always takes priority.
        if not self.closing and self.generation == 0 and self.image is None:
            sample = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Sample_height_16.png")
            if os.path.isfile(sample):
                self.load(sample)

    def restore_window_geometry(self):
        self.geometry_source = geometry.restore(self)

    def raise_after_launch(self):
        # Max can reactivate its viewport while finishing a dropped script.
        # A single queued activation runs after that launch, without a focus loop.
        if not self.closing and self.isVisible():
            if self.isMinimized():
                self.showNormal()
            self.raise_()
            self.activateWindow()

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)
        header = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Height Map Studio")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        self.open_button = QtWidgets.QPushButton("Open image…")
        self.open_button.clicked.connect(self.choose_file)
        header.addWidget(self.open_button)
        self.settings_button = QtWidgets.QPushButton("Settings")
        self.settings_button.setToolTip("Slider ranges and About")
        self.settings_button.clicked.connect(self.show_settings)
        header.addWidget(self.settings_button)
        layout.addLayout(header)
        self.settings_button.setFixedSize(self.open_button.sizeHint())
        self.file_label = QtWidgets.QLabel("Height map → texture maps · up to 8K")
        self.file_label.setMinimumWidth(0)
        self.file_label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        self.file_label.setObjectName("muted")
        layout.addWidget(self.file_label)
        self.tabs = QtWidgets.QTabBar()
        self.tabs.setExpanding(True)
        for title in ("Normal", "Displacement", "AO", "Specular"):
            self.tabs.addTab(title)
        self.tabs.currentChanged.connect(self.tab_changed)
        layout.addWidget(self.tabs)
        self.preview = Preview()
        self.preview.failed.connect(self.gpu_error)
        self.preview.measured.connect(self.measured)
        layout.addWidget(self.preview, 1)
        self.promotion = PromotionStrip(self)
        layout.addWidget(self.promotion)
        toolbar = QtWidgets.QHBoxLayout()
        self.mode = MapMode()
        self.mode.currentIndexChanged.connect(self.mode_changed)
        self.shape = self.preview.shape_selector
        self.shape.setVisible(False)
        self.shape.currentIndexChanged.connect(self.shape_changed)
        self.source = CheckBox("Source")
        self.source.toggled.connect(self.source_changed)
        toolbar.addWidget(self.mode)
        toolbar.addWidget(self.source)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        self.pages = QtWidgets.QStackedWidget()
        self.parameters = {}
        for title, fields in GROUPS:
            page = QtWidgets.QWidget()
            page_layout = QtWidgets.QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setSpacing(3)
            for key, label, low, high, maximum in fields:
                control = Parameter(key, label, low, saved_maximum(self.geometry_settings, key), self.settings[key])
                if key == "detail_size":
                    control.setToolTip("Flatten small bumps and grooves into plateaus with a near-circular footprint at this scale in source pixels. Zero disables it; Blur softens the remaining edges.")
                control.changed.connect(self.parameter_changed)
                self.parameters[key] = control
                page_layout.addWidget(control)
            self.pages.addWidget(page)
        map_settings = QtWidgets.QGroupBox("Map Settings")
        settings_layout = QtWidgets.QVBoxLayout(map_settings)
        settings_layout.setContentsMargins(8, 8, 8, 7)
        settings_layout.addWidget(self.pages)
        layout.addWidget(map_settings)
        advanced_row = QtWidgets.QHBoxLayout()
        self.advanced_toggle = QtWidgets.QPushButton("▸ Advanced")
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.toggled.connect(self.toggle_advanced)
        self.reset = QtWidgets.QPushButton("Reset settings")
        self.reset.setStyleSheet("QPushButton { font-size: 10px; padding: 1px 4px; }")
        self.reset.setFixedHeight(20)
        self.reset.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.reset.setToolTip("Restore only the current map's parameters; keep shared height and edge options")
        self.reset.clicked.connect(self.reset_settings)
        self.advanced_toggle.setStyleSheet(self.reset.styleSheet())
        self.advanced_toggle.setFixedHeight(20)
        self.advanced_toggle.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        advanced_row.setSpacing(5)
        advanced_row.addWidget(self.reset)
        advanced_row.addWidget(self.advanced_toggle)
        settings_layout.addLayout(advanced_row)
        self.advanced = QtWidgets.QWidget()
        self.advanced.setStyleSheet("QWidget { font-size: 10px; } QComboBox { padding: 1px 3px; } QCheckBox { spacing: 3px; } QCheckBox::indicator { width: 12px; height: 12px; }")
        advanced_layout = QtWidgets.QHBoxLayout(self.advanced)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.setSpacing(5)
        self.convention = QtWidgets.QComboBox()
        self.convention.setFixedHeight(20)
        self.convention.addItems(["OpenGL (+Y)", "DirectX (−Y)"])
        self.convention.currentIndexChanged.connect(lambda index: self.option_changed("directx", bool(index)))
        self.invert = CheckBox("Invert height")
        self.invert.setProperty("compactIndicator", True)
        self.invert.toggled.connect(lambda value: self.option_changed("invert", value))
        self.seamless = CheckBox("Seamless edges")
        self.seamless.setProperty("compactIndicator", True)
        self.seamless.setChecked(self.settings["seamless"])
        self.seamless.setToolTip("Wrap filtering across image edges. The source image must already tile seamlessly.")
        self.seamless.toggled.connect(lambda value: self.option_changed("seamless", value))
        advanced_layout.addWidget(self.convention)
        advanced_layout.addWidget(self.invert)
        advanced_layout.addWidget(self.seamless)
        self.advanced.setVisible(False)
        advanced_row.addWidget(self.advanced)
        advanced_row.addStretch()
        export_row = QtWidgets.QHBoxLayout()
        self.format = QtWidgets.QComboBox()
        self.format.setObjectName("exportFormat")
        for label, kind in (("JPEG (8-bit)", "JPEG"), ("PNG", "PNG"), ("TIFF", "TIFF")):
            self.format.addItem(label, kind)
        saved_format = self.geometry_settings.value("export_format", "JPEG")
        self.format.setCurrentIndex(max(0, self.format.findData(saved_format)))
        self.format.currentIndexChanged.connect(self.save_format_preference)
        self.format.setToolTip("PNG/TIFF: 16-bit displacement. JPEG: all maps are lossy 8-bit, quality 95.")
        self.add_slate = QtWidgets.QPushButton("Add to Slate")
        self.add_slate.setToolTip("Add existing saved maps checked in Set to the active Slate View. Does not save or generate maps.")
        self.add_slate.clicked.connect(self.add_selected_to_slate)
        self.save_button = QtWidgets.QPushButton("Save")
        self.save_button.setToolTip("Save selected maps")
        self.save_button.setObjectName("primary")
        self.save_button.setFixedSize(200, 34)
        self.save_button.clicked.connect(self.save)
        self.save_button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.save_button.customContextMenuRequested.connect(self.open_source_folder)
        toolbar.addWidget(self.format)
        export_row.addWidget(self.save_button)
        self.format.setFixedHeight(self.mode.buttons[0].sizeHint().height())
        output_row = QtWidgets.QHBoxLayout()
        self.auto_output = CheckBox("Save beside source")
        self.auto_output.setChecked(str(self.geometry_settings.value("auto_output", "true")).lower() == "true")
        self.auto_output.setToolTip("Save checked maps beside the source. Turn off to choose a filename for one map or a folder for several. Existing files require confirmation.")
        self.auto_output.toggled.connect(lambda checked: self.geometry_settings.setValue("auto_output", checked))
        output_row.addWidget(self.auto_output)
        output_row.addStretch()
        output_row.addWidget(self.add_slate)
        set_group = QtWidgets.QGroupBox("Set")
        # QGroupBox reserves eight pixels above its frame for the title. Give the
        # widget that extra height and lift it so the visible frame aligns with Save.
        set_group.setFixedHeight(42)
        set_row = QtWidgets.QHBoxLayout(set_group)
        set_row.setContentsMargins(8, 7, 8, 3)
        set_row.setSpacing(8)
        self.map_checks = {}
        for kind, label in zip(MAPS, ("Normal", "Displace", "AO", "Specular")):
            check = CheckBox(label)
            check.setChecked(str(self.geometry_settings.value("set_" + kind, "true" if kind == "normal" else "false")).lower() == "true")
            check.toggled.connect(lambda checked, k=kind: self.set_selection_changed(k, checked))
            self.map_checks[kind] = check
            set_row.addWidget(check)
        set_container = QtWidgets.QWidget()
        set_container.setFixedHeight(50)
        set_container_layout = QtWidgets.QVBoxLayout(set_container)
        set_container_layout.setContentsMargins(0, 0, 0, 8)
        set_container_layout.addWidget(set_group)
        export_row.addWidget(set_container)
        layout.addSpacing(10)
        layout.addLayout(export_row)
        layout.addLayout(output_row)
        progress_row = QtWidgets.QHBoxLayout()
        self.status = StatusLabel("Ready to load")
        self.status.setWordWrap(True)
        self.status.setMinimumWidth(0)
        self.status.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Preferred)
        self.status.setObjectName("muted")
        self.progress = QtWidgets.QProgressBar()
        self.progress.setVisible(False)
        self.cancel = QtWidgets.QPushButton("Cancel")
        self.cancel.setVisible(False)
        self.cancel.clicked.connect(self.cancel_export)
        progress_row.addWidget(self.status, 1)
        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.cancel)
        layout.addLayout(progress_row)
        self.set_export_enabled(False)

        # Enter commits numeric input; it must not activate Open or Save.
        for button in self.findChildren(QtWidgets.QPushButton):
            button.setAutoDefault(False)
            button.setDefault(False)

    def set_export_enabled(self, enabled):
        self.export_enabled = enabled
        selected = any(check.isChecked() for check in self.map_checks.values())
        self.save_button.setEnabled(enabled and selected)
        self.add_slate.setEnabled(not self.export_job)
        hint = "Save selected maps" if selected else "Select at least one map in the Set row"
        self.save_button.setToolTip(hint + "\nRight-click: open the source image folder")

    def set_selection_changed(self, kind, checked):
        self.geometry_settings.setValue("set_" + kind, checked)
        self.geometry_settings.sync()
        self.set_export_enabled(self.export_enabled)

    def save_format_preference(self, index):
        self.geometry_settings.setValue("export_format", self.format.itemData(index))
        self.geometry_settings.sync()

    def set_slider_maximum(self, key, value):
        value = validate_maximum(key, value)
        self.parameters[key].set_slider_maximum(value)
        self.geometry_settings.setValue("slider_max/" + key, value)
        self.geometry_settings.sync()

    def show_settings(self):
        if self.settings_dialog is None:
            from .settings_dialog import SettingsDialog
            self.settings_dialog = SettingsDialog(self)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def choose_file(self):
        filename, unused = QtWidgets.QFileDialog.getOpenFileName(self, "Height map", self.last_directory,
                                                               "Height maps (*.png *.tif *.tiff *.jpg *.jpeg)")
        if filename:
            self.load(filename)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and not self.export_job:
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].isLocalFile():
                event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile() and not self.export_job:
            self.load(urls[0].toLocalFile())
            event.acceptProposedAction()

    def load(self, filename):
        if self.export_job or self.closing:
            return
        self.slate_status_active = False
        self.generation += 1
        for job in self.load_jobs:
            job.requestInterruption()
        self.status.setText("Loading…")
        self.set_export_enabled(False)
        request = (self.generation, os.path.abspath(filename))
        if self.load_jobs:
            self.pending_load = request
            return
        self.launch_load(*request)

    def launch_load(self, generation, filename):
        job = LoadJob(generation, filename, self)
        self.load_jobs.add(job)
        job.loaded.connect(self.loaded)
        job.failed.connect(self.load_failed)
        job.finished.connect(lambda: self.load_finished(job))
        job.start()

    def loaded(self, generation, filename, image, preview, depth):
        if generation != self.generation or self.closing:
            return
        self.image, self.filename = image, filename
        self.last_directory = os.path.dirname(filename)
        self.file_label.setText("%s  ·  %d × %d  ·  %d bit" % (os.path.basename(filename), image.width(), image.height(), depth))
        self.file_label.setToolTip(filename)
        self.preview.set_image(preview, (image.width(), image.height()))
        self.set_export_enabled(self.preview.engine is not None)

    def load_failed(self, generation, error):
        if generation == self.generation:
            self.status.setText("Loading failed")
            self.set_export_enabled(self.image is not None and not self.preview.error)
            QtWidgets.QMessageBox.warning(self, "Height Map Studio", error)

    def load_finished(self, job):
        self.load_jobs.discard(job)
        job.deleteLater()
        if self.pending_load and not self.closing:
            request = self.pending_load
            self.pending_load = None
            self.launch_load(*request)
        self.finish_close_if_ready()

    def parameter_changed(self, key, value):
        self.settings[key] = value
        self.timer.start()

    def option_changed(self, key, value):
        self.settings[key] = value
        self.timer.start()

    def tab_changed(self, index):
        if hasattr(self, "pages"):
            self.pages.setCurrentIndex(index)
            self.preview.kind = MAPS[index]
            self.preview.update()

    def mode_changed(self, index):
        self.preview.set_3d(bool(index))
        self.shape.setVisible(bool(index))
        self.source.setEnabled(not index)
        self.preview.update()

    def shape_changed(self, index):
        self.shape_explicit = True
        self.preview.shape = index
        self.preview.update()

    def source_changed(self, checked):
        self.preview.show_source = checked
        self.preview.update()

    def toggle_advanced(self, checked):
        self.advanced.setVisible(checked)
        self.advanced_toggle.setText("▾ Advanced" if checked else "▸ Advanced")

    def reset_settings(self):
        index = self.tabs.currentIndex()
        for key, label, low, high, maximum in GROUPS[index][1]:
            self.parameters[key].set_value(DEFAULTS[key])
        if index == 0:
            self.convention.setCurrentIndex(0)

    def measured(self, milliseconds, device):
        self.last_measurement = milliseconds
        if not self.export_job and not self.slate_status_active:
            self.status.setText("Preview %d × %d · %.1f ms" % (self.preview.image.width(), self.preview.image.height(), milliseconds))
            self.status.setToolTip(device + "\nTiming includes GPU completion; export uses full resolution.")

    def gpu_error(self, error):
        self.set_export_enabled(False)
        self.status.setText("GPU error")
        self.status.setToolTip(error)

    def output_folder(self, choose_folder=False):
        source_folder = os.path.dirname(os.path.abspath(self.filename))
        package_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        inside_package = os.path.commonpath([source_folder, package_folder]).lower() == package_folder.lower() if os.path.splitdrive(source_folder)[0].lower() == os.path.splitdrive(package_folder)[0].lower() else False
        if self.auto_output.isChecked() and not choose_folder and not inside_package and os.access(source_folder, os.W_OK):
            return source_folder
        previous = str(self.geometry_settings.value("output_folder", ""))
        if previous and os.path.splitdrive(previous)[0].lower() == os.path.splitdrive(package_folder)[0].lower():
            if os.path.commonpath([os.path.abspath(previous), package_folder]).lower() == package_folder.lower():
                previous = ""
        if inside_package and self.auto_output.isChecked() and not choose_folder and previous and os.path.isdir(previous) and os.access(previous, os.W_OK):
            return previous
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Output folder", previous or self.last_directory)
        if folder:
            # Never export the bundled demonstration into an installed package.
            same_drive = os.path.splitdrive(folder)[0].lower() == os.path.splitdrive(package_folder)[0].lower()
            if inside_package and same_drive and os.path.commonpath([os.path.abspath(folder), package_folder]).lower() == package_folder.lower():
                QtWidgets.QMessageBox.warning(self, "Output folder", "Choose an output folder outside the installed Height Map Studio folder.")
                return ""
            self.geometry_settings.setValue("output_folder", folder)
            self.geometry_settings.sync()
        return folder

    def inside_package(self, filename):
        package = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        try:
            return os.path.normcase(os.path.commonpath([os.path.realpath(filename), package])) == os.path.normcase(package)
        except ValueError:
            return False  # Different Windows drives.

    def open_source_folder(self, unused_position=None):
        self.slate_status_active = True
        if not self.filename or not os.path.isfile(self.filename):
            self.status.setText("Source image is missing. Load an existing image to open its folder.")
        else:
            folder = os.path.dirname(os.path.abspath(self.filename))
            if QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(folder)):
                self.status.setText("Opened source folder: " + folder)
            else:
                self.status.setText("Could not open source folder: " + folder)
        self.status.setToolTip(self.status.text())

    def save(self):
        self.slate_status_active = False
        if self.image is None or self.export_job:
            return
        kinds = [kind for kind in MAPS if self.map_checks[kind].isChecked()]
        if not kinds:
            return
        extension = {"JPEG": ".jpg", "PNG": ".png", "TIFF": ".tif"}[self.format.currentData()]
        stem = os.path.splitext(os.path.basename(self.filename))[0]
        if not self.auto_output.isChecked() and len(kinds) == 1:
            previous = str(self.geometry_settings.value("output_folder", self.last_directory))
            suggested = os.path.join(previous, stem + "_" + kinds[0] + extension)
            filename, unused = QtWidgets.QFileDialog.getSaveFileName(self, "Save selected map", suggested,
                "%s image (*%s)" % (self.format.currentData(), extension), options=QtWidgets.QFileDialog.DontConfirmOverwrite)
            if not filename:
                return
            if not filename.lower().endswith(extension):
                filename += extension
            destinations = [(kinds[0], filename)]
        else:
            folder = self.output_folder()
            if not folder:
                return
            destinations = [(kind, os.path.join(folder, stem + "_" + kind + extension)) for kind in kinds]
        if any(self.inside_package(filename) for kind, filename in destinations):
            QtWidgets.QMessageBox.warning(self, "Output folder", "Choose an output outside the installed Height Map Studio folder.")
            return
        if any(os.path.normcase(os.path.realpath(filename)) == os.path.normcase(os.path.realpath(self.filename)) or
               (os.path.exists(filename) and os.path.exists(self.filename) and os.path.samefile(filename, self.filename)) for kind, filename in destinations):
            QtWidgets.QMessageBox.warning(self, "Output path", "An output path cannot replace the source image.")
            return
        self.geometry_settings.setValue("output_folder", os.path.dirname(destinations[0][1]))
        self.geometry_settings.sync()
        existing = [filename for kind, filename in destinations if os.path.exists(filename)]
        if existing:
            answer = QtWidgets.QMessageBox.question(self, "Replace existing files?", "Files already exist:\n" + "\n".join(os.path.basename(p) for p in existing),
                                                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            if answer != QtWidgets.QMessageBox.Yes:
                return
        self.start_export([(kind, filename, filename in existing) for kind, filename in destinations])

    def start_export(self, destinations):
        if self.export_job:
            return
        self.surface = QtGui.QOffscreenSurface()
        self.surface.setFormat(gl_format())
        self.surface.create()  # Surface creation/destruction stays on the GUI thread.
        if not self.surface.isValid():
            QtWidgets.QMessageBox.warning(self, "GPU", "Could not create an offscreen export surface.")
            self.surface = None
            return
        self.export_source = self.filename
        self.export_job = ExportJob(self.image, self.settings, destinations, self.surface, self)
        self.export_job.progress.connect(self.export_progress)
        self.export_job.completed.connect(self.export_completed)
        self.export_job.failed.connect(self.export_failed)
        self.export_job.cancelled.connect(lambda: self.status.setText("Export cancelled"))
        self.export_job.finished.connect(self.export_finished)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        self.cancel.setVisible(True)
        self.set_export_enabled(False)
        self.open_button.setEnabled(False)
        self.pages.setEnabled(False)
        self.advanced.setEnabled(False)
        self.reset.setEnabled(False)
        self.export_job.start()

    def export_progress(self, value, message):
        self.progress.setValue(value)
        self.status.setText(message)

    def export_completed(self, files, seconds):
        saved_maps.remember(self.geometry_settings, self.export_source, files)
        self.status.setText("Saved: %d · %.1f s" % (len(files), seconds))

    def add_selected_to_slate(self):
        if self.export_job:
            return
        self.slate_status_active = True
        kinds = [kind for kind in MAPS if self.map_checks[kind].isChecked()]
        labels = dict(zip(MAPS, ("Normal", "Displace", "AO", "Specular")))
        if not kinds:
            self.status.setText("Select maps in Set to add to Slate.", "error")
            self.status.setToolTip(self.status.text())
            return
        if not self.filename:
            self.status.setText("Load a source image before adding its saved maps.", "error")
            self.status.setToolTip(self.status.text())
            return
        extension = {"JPEG": ".jpg", "PNG": ".png", "TIFF": ".tif"}[self.format.currentData()]
        files, missing = saved_maps.resolve(self.geometry_settings, self.filename, kinds,
                                           extension, self.auto_output.isChecked())
        missing_text = "Missing: " + ", ".join(labels[k] for k in missing) if missing else ""
        if not files:
            self.status.setText(missing_text + ". Save these maps first.", "error")
            self.status.setToolTip(self.status.text())
            return
        try:
            from .maxbridge import add_to_slate
            created = add_to_slate(files, progress=lambda step: self.status.setText("Slate: " + step))
            if not created:
                raise RuntimeError("No nodes were added")
        except Exception as exc:
            detail = "Slate error: " + str(exc)
            self.status.setText(detail, "error")
            self.status.setToolTip(detail + "\nInspect Slate before retrying; some nodes may have been created."
                                   + ("\n" + missing_text if missing else ""))
            self.raise_()
            return
        message = "Added: " + ", ".join(labels[k] for k, filename in files)
        if missing_text:
            message += " | " + missing_text
        self.status.setText(message, "warning" if missing_text else "success")
        self.status.setToolTip(message + "\n" + "\n".join(filename for kind, filename in files))

    def export_failed(self, error):
        self.status.setText("Export failed")
        QtWidgets.QMessageBox.warning(self, "Export", error)

    def export_finished(self):
        self.export_job.deleteLater()
        self.export_job = None
        self.surface.destroy()
        self.surface = None
        self.progress.setVisible(False)
        self.cancel.setVisible(False)
        self.open_button.setEnabled(True)
        self.pages.setEnabled(True)
        self.advanced.setEnabled(True)
        self.reset.setEnabled(True)
        self.set_export_enabled(not self.preview.error and self.image is not None)
        self.finish_close_if_ready()

    def cancel_export(self):
        if self.export_job:
            self.export_job.requestInterruption()
            self.status.setText("Cancelling…")

    def finish_close_if_ready(self):
        if self.closing and not self.load_jobs and not self.export_job:
            self.close()

    def closeEvent(self, event):
        self.timer.stop()
        self.promotion.timer.stop()
        if not self.closing and self.geometry_ready:
            geometry.save(self)
        if self.load_jobs or self.export_job:
            self.closing = True
            self.pending_load = None
            for job in self.load_jobs:
                job.requestInterruption()
            self.cancel_export()
            self.hide()
            event.ignore()
            return
        self.preview.cleanup()
        event.accept()
        self.deleteLater()


def show(filename=None):
    global _window
    try:
        if _window is not None and not _window.closing:
            _window.show()
            _window.raise_()
            _window.activateWindow()
            QtCore.QTimer.singleShot(100, _window.raise_after_launch)
            if filename:
                _window.load(filename)
            return _window
    except RuntimeError:
        _window = None
    try:
        import qtmax
        parent = qtmax.GetQMaxMainWindow()
    except ImportError:
        parent = None
    _window = Studio(parent)
    if filename:
        _window.load(filename)
    _window.show()
    _window.raise_()
    QtCore.QTimer.singleShot(100, _window.raise_after_launch)
    return _window
