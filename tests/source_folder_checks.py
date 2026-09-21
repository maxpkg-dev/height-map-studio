"""Real Qt 5 context-menu dispatch; captures the file URL without opening Explorer."""
import ast
import ctypes
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace

ctypes.windll.kernel32.SetDllDirectoryW(r"C:\Program Files\Autodesk\3ds Max 2022")
from PySide2 import QtCore, QtGui, QtWidgets
root = Path(__file__).resolve().parents[1]
tree = ast.parse((root / "HeightMapStudio/heightmap_studio/ui.py").read_text(encoding="utf8"))
studio = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Studio")
method = next(n for n in studio.body if isinstance(n, ast.FunctionDef) and n.name == "open_source_folder")
unit = ast.parse(""); unit.body = [method]
urls = []
namespace = {"os": os, "QtCore": QtCore,
    "QtGui": SimpleNamespace(QDesktopServices=SimpleNamespace(openUrl=lambda url: urls.append(url) or True))}
exec(compile(unit, "source_folder", "exec"), namespace)
app = QtWidgets.QApplication([])
button = QtWidgets.QPushButton("Save")
button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
status = QtWidgets.QLabel()
state = SimpleNamespace(filename="", status=status, slate_status_active=False)
button.customContextMenuRequested.connect(lambda point: namespace["open_source_folder"](state, point))
saves = []
button.clicked.connect(lambda: saves.append(True))

def right_click():
    app.sendEvent(button, QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Mouse, QtCore.QPoint(3, 3)))

right_click()
assert "missing" in status.text() and not urls and not saves
with tempfile.TemporaryDirectory(prefix="hms folder ") as folder:
    source = Path(folder) / "height \u043a\u0430\u0440\u0442\u0430.png"
    source.write_bytes(b"fixture")
    state.filename = str(source)
    right_click()
    assert urls[-1].isLocalFile() and Path(urls[-1].toLocalFile()).resolve() == source.parent.resolve()
    assert not saves
    source.unlink()
    right_click()
    assert len(urls) == 1 and "missing" in status.text()
button.click()
assert saves == [True]
print("PASS: right-click dispatch, correct local source-folder URL, Unicode/spaces, missing/deleted input and unchanged left-click action; no Explorer launched")
