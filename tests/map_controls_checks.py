"""Real Qt/GPU checks, standalone or inside Max; no scene or user preference edits."""
import array
import ctypes
import os
from pathlib import Path
import sys
import tempfile

if "pymxs" not in sys.modules:
    max_root = Path(sys.executable).resolve().parents[1]
    ctypes.windll.kernel32.SetDllDirectoryW(str(max_root))
    if hasattr(os, "add_dll_directory"):
        dll_directory = os.add_dll_directory(str(max_root))
    sys.modules["qtmax"] = None
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "HeightMapStudio"))
from heightmap_studio.qt import QtCore, QtGui, QtWidgets, gl_format, image_bytes
from heightmap_studio.model import DEFAULTS, MAPS
from heightmap_studio.ranges import GROUPS
from heightmap_studio.gl import Engine
from heightmap_studio.ui import Studio
from heightmap_studio.jobs import ExportJob
from heightmap_studio.imageio import load_image


def fixture(width, height, fn):
    values = array.array("H")
    for y in range(height):
        for x in range(width):
            v = int(fn(x, y))
            values.extend((v, v, v, 65535))
    data = values.tobytes()
    return QtGui.QImage(data, width, height, width * 8,
                        QtGui.QImage.Format_RGBA64).copy()


def run():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    with tempfile.TemporaryDirectory(prefix="hms_controls_") as folder:
        store = QtCore.QSettings(str(Path(folder) / "settings.ini"), QtCore.QSettings.IniFormat)
        window = Studio(geometry_settings=store)
        try:
            for index in range(4):
                for title, fields in GROUPS:
                    for key, label, low, high, maximum in fields:
                        window.parameters[key].set_value(DEFAULTS[key] + .25)
                window.invert.setChecked(True)
                window.seamless.setChecked(True)
                window.convention.setCurrentIndex(1)
                before = dict(window.settings)
                window.tabs.setCurrentIndex(index)
                window.reset.click()
                selected = {field[0] for field in GROUPS[index][1]}
                for key, value in before.items():
                    expected = DEFAULTS[key] if key in selected else False if key == "directx" and index == 0 else value
                    assert window.settings[key] == expected, (index, key, window.settings[key], expected)
                assert window.tabs.currentIndex() == index
            for key, index in (("ao_threshold", 2), ("spec_compress", 3), ("disp_blur", 1)):
                window.tabs.setCurrentIndex(index)
                control = window.parameters[key]
                assert control.parentWidget() is window.pages.currentWidget()
                control.slider.setValue(50)
                assert window.settings[key] == .5 and window.timer.isActive()
                assert control.spin.maximum() == (16 if key == "disp_blur" else 1)
        finally:
            window.close()
        print("PASS: sliders update processing settings; Reset is local on all four tabs")

        surface = QtGui.QOffscreenSurface()
        surface.setFormat(gl_format())
        surface.create()
        context = QtGui.QOpenGLContext()
        context.setFormat(gl_format())
        assert context.create() and context.makeCurrent(surface)
        engine = Engine()

        def render(settings, kind, scale=(1.0, 1.0)):
            return engine.read(engine.process(settings, kind, scale=scale), 0, 0,
                               engine.width, engine.height, 1, 8)

        try:
            source = fixture(65, 65, lambda x, y: 32768 if 24 < x < 40 and 24 < y < 40 else 36045)
            engine.upload(source)
            base = render(dict(DEFAULTS), "ao")
            filtered = render(dict(DEFAULTS, ao_threshold=.051), "ao")
            assert min(base) < 255 and min(filtered) == 255, (min(base), max(base), min(filtered), max(filtered), engine.gl.description)
            partial = render(dict(DEFAULTS, ao_threshold=.025), "ao")
            assert all(a <= b <= c for a, b, c in zip(base, partial, filtered))
            shifted = fixture(65, 65, lambda x, y: 10000 if 24 < x < 40 and 24 < y < 40 else 13277)
            engine.upload(shifted)
            assert max(abs(a-b) for a, b in zip(partial, render(dict(DEFAULTS, ao_threshold=.025), "ao"))) <= 1
            engine.upload(fixture(65, 65, lambda x, y: 0 if 24 < x < 40 and 24 < y < 40 else 65535))
            assert min(render(dict(DEFAULTS, ao_threshold=.051), "ao")) < 255
            for kind in ("normal", "displacement", "specular"):
                assert render(dict(DEFAULTS), kind) == render(dict(DEFAULTS, ao_threshold=1), kind)
            print("PASS: AO suppresses shallow detail, retains deep cavities, ignores absolute brightness")

            engine.upload(fixture(257, 3, lambda x, y: x * 65535 // 256))
            base = render(dict(DEFAULTS), "specular")
            assert base[0] == 0 and base[256] == 255
            compressed = render(dict(DEFAULTS, spec_compress=.5), "specular")
            assert compressed[0] == 64 and compressed[256] == 191
            assert all(abs(b - (a * .5 + 63.75)) <= 1 for a, b in zip(base, compressed))
            assert set(render(dict(DEFAULTS, spec_compress=1, spec_brightness=.4, spec_contrast=4), "specular")) == {128}
            clipped = render(dict(DEFAULTS, spec_compress=.5, spec_brightness=.2, spec_contrast=4), "specular")
            assert min(clipped) == 64 and max(clipped) == 191
            for kind in ("normal", "displacement", "ao"):
                assert render(dict(DEFAULTS), kind) == render(dict(DEFAULTS, spec_compress=1), kind)
            print("PASS: Compress brings black/white to gray after clipping; other maps unchanged")

            # Cross the real 1024-pixel export tile boundary, then decode PNG and TIFF.
            source = fixture(1057, 73, lambda x, y: 10000 if (x // 17 + y // 13) % 2 else 50000)
            settings = dict(DEFAULTS, ao_threshold=.2, spec_compress=.4, disp_blur=3.2)
            expected = {}
            engine.upload(source)
            for kind in ("ao", "specular", "displacement"):
                depth = 16 if kind == "displacement" else 8
                raw = engine.read(engine.process(settings, kind), 0, 0, 1057, 73, 1, depth)
                values = array.array("H")
                if depth == 16:
                    values.frombytes(raw)
                else:
                    values.extend(v * 257 for v in raw)
                expected[kind] = values
            engine.close()
            engine = None
            context.doneCurrent()
            for extension in ("png", "tif"):
                destinations = [(kind, str(Path(folder) / (kind + "." + extension)), False) for kind in expected]
                export = ExportJob(source, settings, destinations, surface)
                failures, saved = [], []
                export.failed.connect(lambda message: failures.append(message), QtCore.Qt.DirectConnection)
                export.completed.connect(lambda files, seconds: saved.extend(files), QtCore.Qt.DirectConnection)
                export.start()
                assert export.wait(30000), "Export timed out"
                assert not failures and len(saved) == 3, failures
                for kind, filename in saved:
                    image, preview, depth = load_image(filename)
                    values = array.array("H")
                    values.frombytes(image_bytes(image))
                    difference = max(abs(a-b) for a, b in zip(values[0::4], expected[kind]))
                    assert difference <= (1 if kind == "displacement" else 257), (extension, kind, difference)
                    if kind == "displacement":
                        assert depth == 16
            print("PASS: worker export PNG/TIFF agrees with full GPU frame across tile boundary; Displacement stays 16-bit")
        finally:
            if engine is not None:
                engine.close()
            context.doneCurrent()
            surface.destroy()
    print("PASS: map controls regression complete")


if __name__ == "__main__":
    run()
