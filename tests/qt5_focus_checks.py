"""Real Qt 5 widget events outside Max; only the accelerator state is a test object."""
import ctypes
import sys
from pathlib import Path
from types import SimpleNamespace

ctypes.windll.kernel32.SetDllDirectoryW(r"C:\Program Files\Autodesk\3ds Max 2022")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "HeightMapStudio"))
from heightmap_studio.qt import QtCore, QtGui, QtWidgets
from heightmap_studio.accelerators import FocusGuard

app = QtWidgets.QApplication([])
window = QtWidgets.QDialog()
layout = QtWidgets.QVBoxLayout(window)
field = QtWidgets.QDoubleSpinBox()
layout.addWidget(field)
runtime = SimpleNamespace(enableAccelerators=True)
guard = FocusGuard(field, runtime)
field._guard = guard

def focus_in():
    app.sendEvent(field.lineEdit(), QtGui.QFocusEvent(QtCore.QEvent.FocusIn))
    assert not runtime.enableAccelerators

focus_in()
app.sendEvent(field.lineEdit(), QtGui.QFocusEvent(QtCore.QEvent.FocusOut))
assert runtime.enableAccelerators
focus_in()
app.sendEvent(window, QtGui.QCloseEvent())
assert runtime.enableAccelerators
focus_in()
app.sendEvent(window, QtCore.QEvent(QtCore.QEvent.WindowDeactivate))
assert runtime.enableAccelerators
focus_in()
field.deleteLater()
QtCore.QCoreApplication.sendPostedEvents(field, QtCore.QEvent.DeferredDelete)
assert runtime.enableAccelerators
window.close()
assert QtWidgets.QWidget.screen
assert QtGui.QImage.Format_Grayscale16 and QtGui.QImage.Format_RGBX64
print("PASS: Qt %s real field/child focus, blur, close, deactivation and destruction restoration; relevant image/screen APIs present" % QtCore.qVersion())
