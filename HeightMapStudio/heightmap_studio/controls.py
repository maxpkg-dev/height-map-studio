"""Compact native-input controls and local Lucide view icons."""
import os
from .qt import QtCore, QtGui, QtWidgets


class CheckBox(QtWidgets.QCheckBox):
    def paintEvent(self, event):
        super(CheckBox, self).paintEvent(event)
        if self.isChecked():
            option = QtWidgets.QStyleOptionButton()
            self.initStyleOption(option)
            bounds = self.style().subElementRect(QtWidgets.QStyle.SE_CheckBoxIndicator, option, self)
            painter = QtGui.QPainter(self)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            painter.setPen(QtGui.QPen(QtGui.QColor("#ffffff" if self.isEnabled() else "#8894a5"), 1.6))
            compact = bool(self.property("compactIndicator"))
            x = bounds.left() + (0 if compact else 1)
            y = bounds.top() + (0 if compact else 2)
            painter.drawPolyline(QtGui.QPolygonF([QtCore.QPointF(x + 3, y + 7), QtCore.QPointF(x + 6, y + 10), QtCore.QPointF(x + 11, y + 4)]))
            painter.end()


class NumberSpinBox(QtWidgets.QDoubleSpinBox):
    """Keep Qt hit testing and input; paint crisp, theme-independent arrows."""

    def paintEvent(self, event):
        super(NumberSpinBox, self).paintEvent(event)
        option = QtWidgets.QStyleOptionSpinBox()
        self.initStyleOption(option)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        style = self.style()
        for up, subcontrol, flag in (
                (True, QtWidgets.QStyle.SC_SpinBoxUp, QtWidgets.QAbstractSpinBox.StepUpEnabled),
                (False, QtWidgets.QStyle.SC_SpinBoxDown, QtWidgets.QAbstractSpinBox.StepDownEnabled)):
            bounds = style.subControlRect(QtWidgets.QStyle.CC_SpinBox, option, subcontrol, self)
            center = bounds.center()
            enabled = self.isEnabled() and bool(self.stepEnabled() & flag)
            painter.setPen(QtGui.QPen(QtGui.QColor("#dce8fa" if enabled else "#657185"), 1.5))
            direction = -1 if up else 1
            points = QtGui.QPolygonF([
                QtCore.QPointF(center.x() - 3, center.y() - direction * 1.5),
                QtCore.QPointF(center.x(), center.y() + direction * 1.5),
                QtCore.QPointF(center.x() + 3, center.y() - direction * 1.5)])
            painter.drawPolyline(points)
        painter.end()


class MapMode(QtWidgets.QWidget):
    currentIndexChanged = QtCore.Signal(int)

    def __init__(self, parent=None, shapes=False):
        super(MapMode, self).__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        self.group = QtWidgets.QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = []
        entries = (("", "square.svg", "Plane"), ("", "globe.svg", "Sphere"), ("", "box.svg", "Cube")) if shapes else (("2D", "image.svg", "View map"), ("3D", "box.svg", "Preview material"))
        for index, (label, asset, tooltip) in enumerate(entries):
            button = QtWidgets.QPushButton(label)
            button.setCheckable(True)
            button.setIcon(QtGui.QIcon(os.path.join(os.path.dirname(__file__), "assets", asset)))
            button.setIconSize(QtCore.QSize(16, 16))
            button.setToolTip(tooltip)
            button.setAccessibleName(tooltip)
            button.setAutoDefault(False)
            if shapes:
                button.setFixedSize(28, 28)
                button.setStyleSheet("QPushButton { padding: 3px; }")
            button.toggled.connect(lambda checked, i=index: self.currentIndexChanged.emit(i) if checked else None)
            self.group.addButton(button, index)
            self.buttons.append(button)
            layout.addWidget(button)
        self.buttons[0].setChecked(True)

    def currentIndex(self):
        return self.group.checkedId()

    def setCurrentIndex(self, index):
        self.buttons[index].setChecked(True)
