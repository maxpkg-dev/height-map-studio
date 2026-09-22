"""Compact, opt-in links to support and other 3DGROUND tools."""
from .qt import QtCore, QtGui, QtWidgets

DONATION = ("Support Height Map Studio - Donate",
            "https://store.payproglobal.com/checkout?products[1][id]=137852")
PROMOTIONS = (
    ("Clean up scene data with Prune Scene", "https://maxpkg.dev/catalog/prune-scene"),
    ("Prepare assets for delivery with Model Packer", "https://maxpkg.dev/catalog/model-packer"),
    ("Explore Max Ultra MCP on maxpkg.dev", "https://maxpkg.dev/catalog/max-ultra-mcp"),
)

ORANGE = "#ff9f43"
ORANGE_HOVER = "#ffb25f"
ORANGE_PRESSED = "#e8892f"


def donate_button(parent):
    button = QtWidgets.QPushButton("\u2665 Donate", parent)
    button.setFixedSize(94, 26)
    button.setAutoDefault(False)
    button.setDefault(False)
    button.setCursor(QtCore.Qt.PointingHandCursor)
    button.setStyleSheet("QPushButton { background: %s; color: #20252e; "
                        "border: 1px solid %s; padding: 2px 6px; font-size: 11px; font-weight: 600; } "
                        "QPushButton:hover, QPushButton:focus { background: %s; border-color: %s; } "
                        "QPushButton:pressed { background: %s; }" %
                        (ORANGE, ORANGE_HOVER, ORANGE_HOVER, ORANGE_HOVER, ORANGE_PRESSED))
    button.setToolTip("Support Height Map Studio\n" + DONATION[1])
    button.clicked.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(DONATION[1])))
    return button


class PromotionLink(QtWidgets.QPushButton):
    def __init__(self, parent=None):
        super(PromotionLink, self).__init__(parent)
        self.setObjectName("promotionStrip")
        self.setFixedHeight(26)
        self.setMinimumWidth(0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Fixed)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFlat(True)
        link_font = self.font()
        link_font.setUnderline(True)
        self.setFont(link_font)
        self.setStyleSheet("QPushButton { background: transparent; color: %s; "
                           "border: none; padding: 2px 0; font-size: 11px; text-align: left; } "
                           "QPushButton:hover, QPushButton:focus, QPushButton:pressed { "
                           "background: transparent; border: none; color: %s; }" %
                           (ORANGE, ORANGE_HOVER))
        self.index = 0
        self.record = DONATION
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(30000)
        self.timer.timeout.connect(self.advance)
        self.clicked.connect(self.open_current)
        self.update_label()

    def update_label(self):
        title, url = self.record
        self.setText(self.fontMetrics().elidedText(title, QtCore.Qt.ElideRight, max(0, self.width() - 16)))
        self.setToolTip(title + "\n" + url)
        self.setAccessibleName(title)
        self.setAccessibleDescription("Open this link in your browser: " + url)

    def advance(self):
        if self.underMouse() or self.hasFocus() or self.isDown():
            return
        self.index = (self.index + 1) % (2 * len(PROMOTIONS))
        self.record = DONATION if self.index % 2 == 0 else PROMOTIONS[self.index // 2]
        self.update_label()

    def open_current(self):
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(self.record[1]))

    def resizeEvent(self, event):
        super(PromotionLink, self).resizeEvent(event)
        self.update_label()

    def showEvent(self, event):
        super(PromotionLink, self).showEvent(event)
        self.timer.start()

    def hideEvent(self, event):
        self.timer.stop()
        super(PromotionLink, self).hideEvent(event)


class PromotionStrip(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(PromotionStrip, self).__init__(parent)
        self.setFixedHeight(26)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.link = PromotionLink(self)
        self.timer = self.link.timer
        self.donate = donate_button(self)
        layout.addWidget(self.link, 1)
        layout.addWidget(self.donate)
