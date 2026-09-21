"""Persistent slider ranges and About information; no scene operations."""
from . import __version__
from .qt import QtCore, QtWidgets
from .controls import NumberSpinBox
from .ranges import GROUPS


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, studio):
        super(SettingsDialog, self).__init__(studio)
        self.setWindowTitle("Height Map Studio - Settings")
        self.setObjectName("HeightMapStudioSettings")
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        layout = QtWidgets.QVBoxLayout(self)
        help_text = QtWidgets.QLabel("Slider maximums apply immediately. Manual values remain independent.")
        layout.addWidget(help_text)
        grid = QtWidgets.QGridLayout()
        self.maximums = {}
        for index, (title, entries) in enumerate(GROUPS):
            group = QtWidgets.QGroupBox(title)
            form = QtWidgets.QFormLayout(group)
            for key, label, minimum, default, maximum in entries:
                field = NumberSpinBox()
                field.setDecimals(2)
                field.setRange(minimum + 0.01, maximum)
                field.setSingleStep(1)
                field.setKeyboardTracking(False)
                field.setFixedSize(120, 26)
                field.setValue(studio.parameters[key].slider.maximum() / 100.0)
                field.setToolTip("Allowed maximum: greater than %g, up to %g. Manual input is not limited by this slider setting." % (minimum, maximum))
                field.valueChanged.connect(lambda value, name=key: studio.set_slider_maximum(name, value))
                try:
                    import qtmax
                    qtmax.DisableMaxAcceleratorsOnFocus(field, True)
                except ImportError:
                    pass
                self.maximums[key] = field
                form.addRow(label + " maximum", field)
            grid.addWidget(group, index // 2, index % 2)
        layout.addLayout(grid)
        limits = QtWidgets.QLabel("Processing limits: Blur 16 px; AO radius 128 px. Other maximums: 1,000,000.")
        limits.setObjectName("muted")
        layout.addWidget(limits)
        about = QtWidgets.QGroupBox("About")
        form = QtWidgets.QFormLayout(about)
        form.addRow("Developer", QtWidgets.QLabel("Lukianenko Vasyl"))
        form.addRow("Version", QtWidgets.QLabel(__version__))
        self.links = []
        for label, url in (("3DGROUND", "https://3dground.net"), ("MaxPkg", "https://maxpkg.dev")):
            link = QtWidgets.QLabel('<a style="color:#9cc7ff" href="%s">%s</a>' % (url, url))
            link.setTextFormat(QtCore.Qt.RichText)
            link.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
            link.setOpenExternalLinks(True)
            self.links.append(link)
            form.addRow(label, link)
        layout.addWidget(about)
        close_button = QtWidgets.QPushButton("Close")
        close_button.setAutoDefault(False)
        close_button.clicked.connect(self.close)
        footer = QtWidgets.QHBoxLayout()
        footer.addStretch()
        footer.addWidget(close_button)
        layout.addLayout(footer)
