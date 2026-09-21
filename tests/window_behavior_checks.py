"""Exercise real Qt controls and placement in Max using isolated test preferences."""
import json
import os
import traceback
from heightmap_studio import ui, geometry
from heightmap_studio.qt import QtCore, QtGui, QtWidgets
try:
    from PySide6.QtTest import QTest
except ImportError:
    from PySide2.QtTest import QTest


class WindowChecks(QtCore.QObject):
    def __init__(self, root):
        super(WindowChecks, self).__init__()
        self.root = root
        self.report = {"status": "running", "tests": [], "errors": []}
        self.store = QtCore.QSettings(os.path.join(root, "work", "window_test.ini"), QtCore.QSettings.IniFormat)
        self.store.clear()
        self.parent_window = ui._window.parentWidget()
        self.window = ui.Studio(self.parent_window, geometry_settings=self.store)
        self.window.show()
        self.window.activateWindow()
        self.write()
        QtCore.QTimer.singleShot(300, self.first_run)

    def write(self):
        with open(os.path.join(self.root, "work", "window_behavior_checks.json"), "w", encoding="utf8") as stream:
            json.dump(self.report, stream, indent=2)

    def failed(self):
        self.report["status"] = "failed"
        self.report["errors"].append(traceback.format_exc())
        self.write()
        self.window.close()

    def first_run(self):
        try:
            w = self.window
            assert w.geometry_source == "first_run", w.geometry_source
            assert abs(w.preview.width() - w.preview.height()) <= 1, (w.preview.width(), w.preview.height())
            self.report["tests"].append(dict(name="first_run_square_preview", width=w.width(), height=w.height(),
                                              preview_width=w.preview.width(), preview_height=w.preview.height()))
            image = QtGui.QImage(256, 256, QtGui.QImage.Format_RGBX64)
            image.fill(QtGui.QColor(128, 128, 128))
            w.image = image
            w.preview.set_image(image, (256, 256))
            QtCore.QTimer.singleShot(150, self.controls)
        except Exception:
            self.failed()

    def controls(self):
        try:
            w = self.window
            frame = w.preview.grabFramebuffer()
            for x, y in ((0, 0), (frame.width()-1, 0), (0, frame.height()-1), (frame.width()-1, frame.height()-1)):
                color = frame.pixelColor(x, y)
                assert abs(color.red()-128)<=1 and abs(color.green()-128)<=1 and color.blue()==255, color.getRgb()
            self.report["tests"].append(dict(name="square_map_fills_all_preview_corners", passed=True))
            spin = w.parameters["strength"].spin
            option = QtWidgets.QStyleOptionSpinBox()
            spin.initStyleOption(option)
            up = spin.style().subControlRect(QtWidgets.QStyle.CC_SpinBox, option, QtWidgets.QStyle.SC_SpinBoxUp, spin)
            down = spin.style().subControlRect(QtWidgets.QStyle.CC_SpinBox, option, QtWidgets.QStyle.SC_SpinBoxDown, spin)
            assert spin.rect().contains(up) and spin.rect().contains(down)
            before = spin.value()
            QTest.mouseClick(spin, QtCore.Qt.LeftButton, pos=up.center())
            assert spin.value() > before
            QTest.mouseClick(spin, QtCore.Qt.LeftButton, pos=down.center())
            assert abs(spin.value()-before)<0.001
            spin.setFocus()
            assert spin.hasFocus()
            spin.setEnabled(False)
            QTest.mouseClick(spin, QtCore.Qt.LeftButton, pos=up.center())
            assert abs(spin.value()-before)<0.001
            spin.setEnabled(True)
            w.mode.showPopup()
            assert w.mode.view().isVisible()
            w.mode.hidePopup()
            w.source.click()
            assert w.source.isChecked()
            w.source.click()
            self.report["tests"].append(dict(name="spinner_bounds_arrows_focus_disabled_combo_checkbox", passed=True))
            # Restore must honor an intentionally non-square user layout.
            w.resize(w.width()+100, w.height()-40)
            w.move(w.frameGeometry().left()+20, w.frameGeometry().top()+20)
            geometry.keep_visible(w)
            self.expected_size = w.size()
            self.expected_position = w.pos()
            w.close()
            QtCore.QTimer.singleShot(100, self.reopen)
        except Exception:
            self.failed()

    def reopen(self):
        try:
            self.window = ui.Studio(self.parent_window, geometry_settings=self.store)
            self.window.show()
            QtCore.QTimer.singleShot(200, self.restored)
        except Exception:
            self.failed()

    def restored(self):
        try:
            w = self.window
            assert w.geometry_source == "saved"
            assert w.size() == self.expected_size, (w.size(), self.expected_size)
            assert (w.pos()-self.expected_position).manhattanLength() <= 2, (w.pos(), self.expected_position)
            self.report["tests"].append(dict(name="user_size_position_restored", passed=True))
            w.move(-20000, -20000)
            geometry.keep_visible(w)
            assert any(screen.availableGeometry().contains(w.frameGeometry()) for screen in QtWidgets.QApplication.screens())
            self.report["tests"].append(dict(name="offscreen_window_returns_to_visible_screen", passed=True))
            self.report["status"] = "complete"
            self.write()
            w.close()
            ui._window.raise_()
        except Exception:
            self.failed()


_hms_window_checks = WindowChecks(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
