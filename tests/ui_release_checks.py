"""Real-Max regression checks for demo loading, controls, and JPEG exports."""
import json
import os
import time
import traceback
from heightmap_studio import ui, geometry
from heightmap_studio.qt import QtCore, QtGui, QtWidgets
from heightmap_studio.imageio import load_image
from heightmap_studio.model import MAPS
try:
    from PySide6 import QtTest
except ImportError:
    from PySide2 import QtTest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ReleaseChecks(QtCore.QObject):
    def __init__(self):
        super(ReleaseChecks, self).__init__()
        self.root = ROOT
        self.report = {"status": "running", "passed": [], "errors": []}
        self.store = QtCore.QSettings(os.path.join(self.root, "work", "release_checks.ini"), QtCore.QSettings.IniFormat)
        self.store.clear()
        self.window = ui.Studio(geometry_settings=self.store)
        self.window.setWindowTitle("Height Map Studio - verification")
        self.window.show()
        self.deadline = time.monotonic() + 30
        self.later(self.demo)

    def write(self):
        with open(os.path.join(self.root, "work", "ui_release_checks.json"), "w") as stream:
            json.dump(self.report, stream, indent=2)

    def later(self, callback, milliseconds=200):
        def guarded():
            try:
                callback()
            except Exception:
                self.report["errors"].append(traceback.format_exc())
                self.report["status"] = "failed"
                self.write()
        QtCore.QTimer.singleShot(milliseconds, guarded)

    def demo(self):
        w = self.window
        if w.load_jobs or w.image is None:
            assert time.monotonic() < self.deadline
            return self.later(self.demo)
        assert os.path.basename(w.filename) == "Sample_height_16.png"
        assert not w.preview.error, w.preview.error
        assert abs(w.preview.width() - w.preview.height()) <= 1
        assert w.add_slate.isVisible() and w.rect().contains(w.add_slate.geometry())
        assert not w.add_slate.isChecked()
        assert w.format.currentData() == "JPEG"
        w.format.setCurrentIndex(w.format.findData("PNG"))
        assert self.store.value("export_format") == "PNG"
        self.report["passed"].append("JPEG default and remembered format choice")
        self.report["minimum_window"] = [w.width(), w.height()]
        self.report["hwnd"] = int(w.winId())
        self.report["passed"].append("default sample, square preview, visible Slate option")
        for button in w.mode.buttons:
            pixmap = button.icon().pixmap(32, 32)
            assert not pixmap.isNull()
            icon_image = pixmap.toImage()
            assert any(icon_image.pixelColor(x, y).alpha() > 0 for x in range(32) for y in range(32))
        settings = dict(w.settings)
        QtTest.QTest.mouseClick(w.mode.buttons[1], QtCore.Qt.LeftButton)
        assert w.preview.is_3d and w.shape.isVisible() and not w.source.isEnabled()
        assert w.shape.parentWidget() is w.preview
        assert w.preview.rect().contains(w.shape.geometry())
        assert w.preview.fit_button.isVisible()
        assert not w.preview.fit_button.geometry().intersects(w.shape.geometry())
        for index in range(3):
            QtTest.QTest.mouseClick(w.shape.buttons[index], QtCore.Qt.LeftButton)
            assert w.preview.shape == index and w.shape.currentIndex() == index
            frame = w.preview.grabFramebuffer()
            assert not frame.isNull() and not w.preview.error
        w.preview.rotation = [0.8, -0.4]
        w.preview.light_angle = 1.2
        w.preview.update()
        frame = w.preview.grabFramebuffer()
        assert not frame.isNull() and not w.preview.error
        QtTest.QTest.mouseClick(w.preview.fit_button, QtCore.Qt.LeftButton)
        assert w.preview.rotation == [0.25, -0.2]
        assert settings == w.settings
        self.report["passed"].append("three exclusive shape overlays and cube GPU frame; Fit preserves map settings")
        QtTest.QTest.mouseClick(w.mode.buttons[1], QtCore.Qt.LeftButton)
        assert w.mode.buttons[1].isChecked()
        QtTest.QTest.mouseClick(w.mode.buttons[0], QtCore.Qt.LeftButton)
        assert not w.preview.is_3d and not w.shape.isVisible() and w.source.isEnabled()
        assert w.preview.fit_button.isVisible()
        assert settings == w.settings
        self.report["passed"].append("SVG rendering and exclusive mode buttons preserve settings")
        spin = w.parameters["strength"].spin
        spin.setValue(4)
        option = QtWidgets.QStyleOptionSpinBox()
        spin.initStyleOption(option)
        up = spin.style().subControlRect(QtWidgets.QStyle.CC_SpinBox, option, QtWidgets.QStyle.SC_SpinBoxUp, spin)
        down = spin.style().subControlRect(QtWidgets.QStyle.CC_SpinBox, option, QtWidgets.QStyle.SC_SpinBoxDown, spin)
        assert spin.rect().contains(up) and spin.rect().contains(down) and not up.intersects(down)
        QtTest.QTest.mouseClick(spin, QtCore.Qt.LeftButton, pos=up.center())
        assert abs(spin.value() - 4.1) < 0.001
        QtTest.QTest.mouseClick(spin, QtCore.Qt.LeftButton, pos=down.center())
        assert spin.value() == 4
        spin.setFocus()
        QtTest.QTest.keyClick(spin, QtCore.Qt.Key_Up)
        assert abs(spin.value() - 4.1) < 0.001
        wheel = QtGui.QWheelEvent(QtCore.QPointF(spin.rect().center()), QtCore.QPointF(spin.mapToGlobal(spin.rect().center())), QtCore.QPoint(), QtCore.QPoint(0, 120), QtCore.Qt.NoButton, QtCore.Qt.NoModifier, QtCore.Qt.NoScrollPhase, False)
        QtWidgets.QApplication.sendEvent(spin, wheel)
        assert abs(spin.value() - 4.2) < 0.001
        spin.setEnabled(False)
        QtTest.QTest.mouseClick(spin, QtCore.Qt.LeftButton, pos=up.center())
        assert abs(spin.value() - 4.2) < 0.001
        spin.setEnabled(True)
        parameter = w.parameters["strength"]
        for requested, expected in ((0, 0), (0.05, 0.05), (2.37, 2.37), (20, 20), (100, 100)):
            parameter.set_value(requested)
            assert spin.value() == expected and w.settings["strength"] == expected
            assert parameter.slider.value() == min(2000, round(expected * 100))
            w.preview.refresh(w.settings)
            assert not w.preview.error
        for typed in ("100", "123.45"):
            spin.setFocus()
            spin.selectAll()
            QtTest.QTest.keyClicks(spin, typed)
            assert spin.lineEdit().text() == typed
            QtTest.QTest.keyClick(spin, QtCore.Qt.Key_Return)
            assert spin.value() == float(typed) and w.settings["strength"] == float(typed)
            assert parameter.slider.value() == 2000
        spin.selectAll()
        QtTest.QTest.keyClicks(spin, "101.25")
        w.open_button.setFocus()
        QtWidgets.QApplication.processEvents()
        assert spin.value() == 101.25 and w.settings["strength"] == 101.25
        parameter.slider.setValue(300)
        assert spin.value() == 3 and w.settings["strength"] == 3
        self.report["passed"].append("Normal slider 0..20; manual 100, decimals, Enter and focus-out preserve values")
        self.report["passed"].append("spinner arrows, keyboard, wheel, disabled input")
        assert w.timer.interval() == 80 and w.timer.isSingleShot()
        self.fires = 0
        w.timer.timeout.connect(self.timer_fired)
        w.parameter_changed("strength", 3)
        self.later(lambda: w.parameter_changed("strength", 4), 30)
        self.later(self.export, 200)

    def timer_fired(self):
        self.fires += 1

    def export(self):
        assert self.fires == 1, self.fires
        self.report["passed"].append("80 ms debounce coalesces updates")
        w = self.window
        w.format.setCurrentIndex(w.format.findData("JPEG"))
        self.destinations = [(kind, os.path.join(self.root, "work", "sample_" + kind + ".jpg"), True) for kind in MAPS]
        w.start_export(self.destinations, False)
        w.export_job.failed.connect(self.failed)
        w.export_job.completed.connect(self.exported)

    def failed(self, message):
        self.report["errors"].append(message)
        self.report["status"] = "failed"
        self.write()

    def exported(self, files, seconds):
        try:
            assert [p for k, p in files] == [p for k, p, replace in self.destinations]
            for kind, filename in files:
                reader = QtGui.QImageReader(filename)
                assert bytes(reader.format()).lower() in (b"jpeg", b"jpg")
                image, preview, depth = load_image(filename)
                assert image.size() == self.window.image.size() and depth == 8
            self.report["passed"].append("four JPEG maps decode at source resolution and 8-bit precision")
            self.later(self.cancel)
        except Exception:
            self.failed(traceback.format_exc())

    def cancel(self):
        self.guard = os.path.join(self.root, "work", "jpeg_cancel_guard.jpg")
        with open(self.guard, "wb") as stream:
            stream.write(b"preserve existing JPEG")
        self.window.start_export([("ao", self.guard, True)], False)
        self.window.export_job.cancelled.connect(lambda: self.later(self.race))
        self.window.export_job.failed.connect(self.failed)
        self.window.cancel_export()

    def race(self):
        with open(self.guard, "rb") as stream:
            assert stream.read() == b"preserve existing JPEG"
        self.report["passed"].append("JPEG cancellation preserves existing destination")
        self.racer = ui.Studio(geometry_settings=self.store)
        self.racer.show()
        self.explicit = self.destinations[0][1]
        self.racer.load(self.explicit)
        self.deadline = time.monotonic() + 30
        self.later(self.finish)

    def finish(self):
        if self.racer.load_jobs:
            assert time.monotonic() < self.deadline
            return self.later(self.finish)
        assert self.racer.filename == self.explicit
        self.racer.load_demo_if_empty()
        assert self.racer.filename == self.explicit and self.racer.generation == 1
        self.racer.close()
        self.report["passed"].append("explicit initial load wins over queued demo")
        self.later(self.auto_save)

    def auto_save(self):
        import shutil
        import uuid
        self.auto_folder = os.path.join(self.root, "work", "auto_" + uuid.uuid4().hex)
        os.makedirs(self.auto_folder)
        self.auto_source = os.path.join(self.auto_folder, "height_\u043a\u0430\u0440\u0442\u0430.png")
        shutil.copyfile(os.path.join(self.root, "HeightMapStudio", "Sample_height_16.png"), self.auto_source)
        w = self.window
        w.filename = self.auto_source
        w.format.setCurrentIndex(w.format.findData("JPEG"))
        assert w.auto_output.isChecked() and w.output_folder() == self.auto_folder
        for check in w.map_checks.values():
            check.setChecked(False)
        assert not w.save_button.isEnabled()
        w.map_checks["normal"].setChecked(True)
        w.map_checks["ao"].setChecked(True)
        from pymxs import runtime as rt
        self.previous_view = int(rt.sme.activeView)
        self.slate_open = bool(rt.sme.IsOpen())
        rt.sme.Open()
        self.test_view = rt.sme.CreateView("HMS_JPEG_EXPORT_TEST")
        rt.sme.activeView = self.test_view
        w.add_slate.setChecked(True)
        w.save()
        assert w.export_job is not None
        w.export_job.completed.connect(self.auto_saved)
        w.export_job.failed.connect(self.failed)

    def auto_saved(self, files, seconds):
        from pymxs import runtime as rt
        try:
            assert [kind for kind, filename in files] == ["normal", "ao"]
            for kind, filename in files:
                assert filename == os.path.splitext(self.auto_source)[0] + "_" + kind + ".jpg"
                assert os.path.isfile(filename)
            view = rt.sme.GetView(self.test_view)
            assert view.GetNumNodes() == 2
            for index in (1, 2):
                bitmap = view.GetNode(index).reference.bitmap
                assert str(bitmap.filename) in [filename for kind, filename in files]
                assert str(bitmap.colorSpace).lower() == "raw"
            self.report["passed"].append("beside-source selected JPEG set, Unicode names, exactly two Raw Slate nodes")
        except Exception:
            self.failed(traceback.format_exc())
        finally:
            rt.sme.DeleteView(self.test_view, False)
            if 0 < self.previous_view <= rt.sme.GetNumViews():
                rt.sme.activeView = self.previous_view
            if not self.slate_open:
                rt.sme.Close()
        self.later(self.overwrite)

    def overwrite(self):
        self.before = {p: open(p, "rb").read() for k, p, overwrite in [(k, os.path.splitext(self.auto_source)[0] + "_" + k + ".jpg", True) for k in ("normal", "ao")]}
        def reject_overwrite():
            dialog = QtWidgets.QApplication.activeModalWidget()
            assert isinstance(dialog, QtWidgets.QMessageBox)
            dialog.button(QtWidgets.QMessageBox.No).click()
        QtCore.QTimer.singleShot(100, reject_overwrite)
        self.window.save()
        assert self.window.export_job is None
        for filename, expected in self.before.items():
            with open(filename, "rb") as stream:
                assert stream.read() == expected
        self.report["passed"].append("beside-source overwrite confirmation rejects without changes")
        self.report["status"] = "complete"
        self.window.raise_()
        self.write()


_hms_release_checks = ReleaseChecks()
