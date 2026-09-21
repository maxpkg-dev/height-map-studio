"""Exercise the real single-file picker and source-collision warning in Max."""
import hashlib
import os
from heightmap_studio.qt import QtCore, QtWidgets


def choose_output(filename):
    dialog = QtWidgets.QApplication.activeModalWidget()
    assert isinstance(dialog, QtWidgets.QFileDialog)
    dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
    dialog.setDirectory(os.path.dirname(filename))
    dialog.selectFile(os.path.basename(filename))
    assert os.path.normcase(dialog.selectedFiles()[0]) == os.path.normcase(filename)
    dialog.accept()


def close_source_warning():
    dialog = QtWidgets.QApplication.activeModalWidget()
    assert isinstance(dialog, QtWidgets.QMessageBox)
    assert "source image" in dialog.text()
    dialog.accept()


def test_manual_output():
    w = _hms_save_checks.window
    w.auto_output.setChecked(False)
    w.add_slate.setChecked(False)
    for kind, check in w.map_checks.items():
        check.setChecked(kind == "ao")
    w.format.setCurrentIndex(w.format.findData("JPEG"))
    target = os.path.join(_hms_save_checks.folder, "custom_filename.jpg")
    QtCore.QTimer.singleShot(100, lambda: choose_output(target))
    w.save()
    if w.export_job is not None:
        assert w.export_job.destinations == [("ao", target, False)]
    else:
        assert os.path.isfile(target)  # Nested dialog events may finish this small export.


def test_source_guard():
    w = _hms_save_checks.window
    assert w.export_job is None
    w.format.setCurrentIndex(w.format.findData("PNG"))
    with open(w.filename, "rb") as stream:
        before = hashlib.sha256(stream.read()).hexdigest()
    def choose_source():
        QtCore.QTimer.singleShot(100, close_source_warning)
        choose_output(w.filename)
    QtCore.QTimer.singleShot(100, choose_source)
    w.save()
    assert w.export_job is None
    with open(w.filename, "rb") as stream:
        assert hashlib.sha256(stream.read()).hexdigest() == before


# Deliberately not auto-run: native file-dialog automation was interrupted by a
# Max disconnect. Perform source-collision checks manually in an isolated session.
