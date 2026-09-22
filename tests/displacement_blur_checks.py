"""Standalone Qt/GPU regression; run with bundled Max 2022 Python 3.7."""
import array
import ctypes
import math
from pathlib import Path
import sys
import tempfile

ctypes.windll.kernel32.SetDllDirectoryW(r"C:\Program Files\Autodesk\3ds Max 2022")
# Max's shortcut adapter requires a running host; this test uses standalone Qt.
sys.modules["qtmax"] = None
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "HeightMapStudio"))
from heightmap_studio.qt import QtCore, QtGui, QtWidgets, gl_format
from heightmap_studio.model import DEFAULTS, halo, tiles
from heightmap_studio.imageio import padded_tile
from heightmap_studio.gl import Engine
from heightmap_studio.ui import Studio

app = QtWidgets.QApplication([])
with tempfile.TemporaryDirectory() as folder:
    store = QtCore.QSettings(str(Path(folder) / "settings.ini"), QtCore.QSettings.IniFormat)
    window = Studio(geometry_settings=store)
    try:
        window.tabs.setCurrentIndex(1)
        control = window.parameters["disp_blur"]
        assert control.parentWidget() is window.pages.currentWidget()
        assert control.spin.value() == 0 and control.spin.maximum() == 16
        control.slider.setValue(325)
        assert window.settings["disp_blur"] == 3.25
        assert window.settings["blur"] == 0 and window.timer.isActive()
        window.tabs.setCurrentIndex(0)
        window.parameters["blur"].set_value(1.5)
        window.tabs.setCurrentIndex(1)
        assert control.spin.value() == 3.25
        window.reset_settings()
        assert window.settings["disp_blur"] == 0 and window.settings["blur"] == 1.5
    finally:
        window.close()
print("PASS: Displacement slider range/default, independent values, tab retention and reset")

surface = QtGui.QOffscreenSurface()
surface.setFormat(gl_format())
surface.create()
context = QtGui.QOpenGLContext()
context.setFormat(gl_format())
assert context.create() and context.makeCurrent(surface)
engine = Engine()


def fixture(width, height, value):
    raw = array.array("H")
    for y in range(height):
        for x in range(width):
            v = int(value(x, y))
            raw.extend((v, v, v, 65535))
    data = raw.tobytes()
    return QtGui.QImage(data, width, height, width * 8, QtGui.QImage.Format_RGBA64).copy()


def pixels(settings, kind="displacement", scale=(1.0, 1.0)):
    raw = engine.read(engine.process(settings, kind, scale=scale), 0, 0, engine.width, engine.height, 1, 16)
    result = array.array("H")
    result.frombytes(raw)
    return result


try:
    engine.upload(fixture(256, 256, lambda x, y: y * 256 + x))
    precision = pixels(dict(DEFAULTS))
    assert precision == array.array("H", range(65536)), (engine.gl.description, list(precision[:20]), max(abs(a-b) for a,b in zip(precision, range(65536))))
    engine.upload(fixture(65, 65, lambda x, y: 65535 if x == 32 and y == 32 else 0))
    sharp = pixels(dict(DEFAULTS))
    blurred = pixels(dict(DEFAULTS, disp_blur=3.2))
    assert 0 < blurred[32 * 65 + 32] < sharp[32 * 65 + 32]
    assert blurred[32 * 65 + 31] > 0
    assert pixels(dict(DEFAULTS, blur=8)) == sharp
    for kind in ("normal", "ao", "specular"):
        assert pixels(dict(DEFAULTS), kind) == pixels(dict(DEFAULTS, disp_blur=8), kind)
    assert pixels(dict(DEFAULTS, disp_blur=6.4), scale=(2.0, 2.0)) == blurred
    print("PASS: GPU blur effect, independent maps, preview scaling and all 65536 levels at Blur=0")

    width, height = 131, 73
    source = fixture(width, height, lambda x, y: 32768 + 22000 * math.sin(x * .31) * math.cos(y * .23))
    for blur in (3.2, 16.0):
        for seamless in (False, True):
            settings = dict(DEFAULTS, disp_blur=blur, seamless=seamless)
            engine.upload(source, seamless)
            full = pixels(settings)
            composed = array.array("H", [0]) * (width * height)
            border = halo(settings, "displacement")
            for x, y, tw, th in tiles(width, height, 64):
                tile = padded_tile(source, x, y, tw, th, border, seamless)
                engine.upload(tile)
                bounds = (((border - x + .5) / tile.width(), (border - y + .5) / tile.height()),
                          ((border - x + width - .5) / tile.width(), (border - y + height - .5) / tile.height()))
                texture = engine.process(settings, "displacement", wrap=False, bounds=bounds)
                data = array.array("H")
                data.frombytes(engine.read(texture, border, border, tw, th, 1, 16))
                for row in range(th):
                    offset = (y + row) * width + x
                    composed[offset:offset + tw] = data[row * tw:(row + 1) * tw]
            difference = max(abs(a - b) for a, b in zip(full, composed))
            assert difference <= 1, (blur, seamless, difference)
    print("PASS: 16-bit tiled/full agreement within 1 level at Blur=3.2/16, clamped and seamless edges")
    print("GPU: " + engine.gl.description)
finally:
    engine.close()
    context.doneCurrent()
