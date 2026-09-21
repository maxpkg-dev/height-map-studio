"""Verify the single Save action, selection preferences, dialogs and Slate."""
import json
import os
import shutil
import traceback
import uuid
from pymxs import runtime as rt
from heightmap_studio import ui
from heightmap_studio.imageio import load_image
from heightmap_studio.qt import QtCore, QtGui, QtWidgets

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class SaveChecks(QtCore.QObject):
    def __init__(self):
        super(SaveChecks, self).__init__()
        self.root = ROOT
        self.folder = os.path.join(ROOT, "work", "single_save_" + uuid.uuid4().hex)
        os.makedirs(self.folder)
        self.filename = os.path.join(self.folder, "height_\u043a\u0430\u0440\u0442\u0430.png")
        shutil.copyfile(os.path.join(ROOT, "HeightMapStudio", "Sample_height_16.png"), self.filename)
        self.store = QtCore.QSettings(os.path.join(self.folder, "settings.ini"), QtCore.QSettings.IniFormat)
        self.window = ui.Studio(geometry_settings=self.store)
        self.window.setWindowTitle("Height Map Studio - Save verification")
        self.report = {"status": "running", "passed": [], "errors": []}
        self.previous_view = int(rt.sme.activeView)
        self.was_open = bool(rt.sme.IsOpen())
        rt.sme.Open()
        self.view_index = rt.sme.CreateView("HMS_SINGLE_SAVE_TEST")
        rt.sme.activeView = self.view_index
        self.view = rt.sme.GetView(self.view_index)
        self.old_map = rt.Bitmaptexture(name="Existing test map")
        self.old_node = self.view.CreateNode(self.old_map, rt.Point2(-10000, -10000))
        self.old_position = (float(self.old_node.position.x), float(self.old_node.position.y))
        self.window.load(self.filename)
        self.window.show()
        self.later(self.start)

    def later(self, function):
        def run():
            try:
                function()
            except Exception:
                self.fail(traceback.format_exc())
        QtCore.QTimer.singleShot(200, run)

    def fail(self, error):
        self.report["errors"].append(error)
        self.report["status"] = "failed"
        self.cleanup()

    def start(self):
        w = self.window
        if w.load_jobs:
            return self.later(self.start)
        assert w.image is not None and not w.preview.error
        assert [k for k, c in w.map_checks.items() if c.isChecked()] == ["normal"]
        assert not w.add_slate.isChecked()
        assert not hasattr(w, "save_set_button")
        assert w.save_button.width() == 200 and w.save_button.height() == 34
        assert abs(w.preview.width() - w.preview.height()) <= 1
        assert w.add_slate.geometry().y() == w.auto_output.geometry().y()
        assert w.add_slate.x() > w.auto_output.x()
        assert w.map_checks["normal"].mapTo(w, QtCore.QPoint()).x() > w.save_button.x() + w.save_button.width()
        self.report["minimum_window"] = [w.width(), w.height()]
        self.report["passed"].append("fresh Normal-only default; single 200x34 Save with map choices right and shared options below; square preview")
        w.tabs.setCurrentIndex(2)
        rt.sme.activeView = self.view_index
        w.add_slate.setChecked(True)
        w.save()
        assert [x[0] for x in w.export_job.destinations] == ["normal"]
        w.export_job.completed.connect(lambda files, seconds: self.later(self.single_done))
        w.export_job.failed.connect(self.fail)

    def single_done(self):
        output = os.path.splitext(self.filename)[0] + "_normal.jpg"
        assert not QtGui.QImageReader(output).read().isNull()
        selected = list(self.view.GetSelectedNodes())
        assert len(selected) == 1 and str(selected[0].reference.bitmap.filename) == output
        assert self.view.GetNumNodes() == 2
        self.report["passed"].append("Save exports selected Normal despite active AO tab; one selected/framed Slate Bitmap")
        w = self.window
        w.map_checks["normal"].setChecked(False)
        assert not w.save_button.isEnabled()
        w.map_checks["ao"].setChecked(True)
        w.map_checks["specular"].setChecked(True)
        restored = ui.Studio(geometry_settings=self.store)
        assert not restored.add_slate.isChecked()
        assert [k for k, c in restored.map_checks.items() if c.isChecked()] == ["ao", "specular"]
        restored.close()
        self.report["passed"].append("empty selection disables Save; explicit selection survives recreation")
        rt.sme.activeView = self.view_index
        w.add_slate.setChecked(True)
        w.save()
        assert [x[0] for x in w.export_job.destinations] == ["ao", "specular"]
        w.export_job.completed.connect(lambda files, seconds: self.later(self.multi_done))
        w.export_job.failed.connect(self.fail)

    def multi_done(self):
        selected = list(self.view.GetSelectedNodes())
        assert len(selected) == 2 and self.view.GetNumNodes() == 4, (len(selected), self.view.GetNumNodes(), int(rt.sme.activeView), self.view_index, self.window.export_add_slate)
        expected = [os.path.splitext(self.filename)[0] + "_" + kind + ".jpg" for kind in ("ao", "specular")]
        assert sorted(str(n.reference.bitmap.filename) for n in selected) == sorted(expected)
        assert (float(self.old_node.position.x), float(self.old_node.position.y)) == self.old_position
        self.report["passed"].append("same Save exports only two checked maps and selects/frames only new Slate nodes")
        self.window.auto_output.setChecked(False)
        self.dialog_seen = None
        QtCore.QTimer.singleShot(100, self.cancel_dialog)
        self.window.save()
        assert self.dialog_seen == QtWidgets.QFileDialog.Directory
        self.window.map_checks["specular"].setChecked(False)
        self.dialog_seen = None
        QtCore.QTimer.singleShot(100, self.cancel_dialog)
        self.window.save()
        assert self.dialog_seen == QtWidgets.QFileDialog.AnyFile
        assert self.window.export_job is None
        self.report["passed"].append("manual multi-map folder dialog and single-map filename dialog open; cancellation starts no export")
        self.report["status"] = "complete"
        self.cleanup()

    def cancel_dialog(self):
        dialog = QtWidgets.QApplication.activeModalWidget()
        if isinstance(dialog, QtWidgets.QFileDialog):
            self.dialog_seen = dialog.fileMode()
            dialog.reject()

    def cleanup(self):
        rt.sme.DeleteView(self.view_index, False)
        if 0 < self.previous_view <= rt.sme.GetNumViews():
            rt.sme.activeView = self.previous_view
        if not self.was_open:
            rt.sme.Close()
        with open(os.path.join(self.root, "work", "single_save_checks.json"), "w") as stream:
            json.dump(self.report, stream, indent=2)
        if self.report["status"] == "failed":
            self.window.close()


_hms_save_checks = SaveChecks()
