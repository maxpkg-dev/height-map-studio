"""Exercise continuous mouse drags and back-facing plane frames in live Max."""
import json
import math
import os
from heightmap_studio import ui
from heightmap_studio.qt import QtCore, QtGui, QtWidgets

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check_rotation():
    settings = QtCore.QSettings(os.path.join(ROOT, "work", "rotation_test.ini"), QtCore.QSettings.IniFormat)
    window = ui.Studio(geometry_settings=settings)
    # Reuse the already-loaded image without changing the user's window.
    current = ui._window
    window.image, window.filename = current.image, current.filename
    window.generation = 1
    window.preview.set_image(current.preview.image, current.preview.original_size)
    window.show()
    window.mode.setCurrentIndex(1)
    preview = window.preview
    QtWidgets.QApplication.processEvents()
    report = {"passed": []}
    try:
        for shape in range(3):
            window.shape.setCurrentIndex(shape)
            preview.reset_view()
            expected = [0.25, -0.2]
            position = QtCore.QPointF(40, 40)
            press = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, position, QtCore.Qt.LeftButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
            QtWidgets.QApplication.sendEvent(preview, press)
            # Repeated turns followed by reversing direction within the same drag.
            for step in range(240):
                direction = 1 if step < 160 else -1
                position += QtCore.QPointF(12 * direction, 13 * direction)
                event = QtGui.QMouseEvent(QtCore.QEvent.MouseMove, position, QtCore.Qt.NoButton, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier)
                QtWidgets.QApplication.sendEvent(preview, event)
                expected[0] += 0.12 * direction
                expected[1] += 0.13 * direction
                assert all(abs(a-b) < 1e-9 for a, b in zip(preview.rotation, expected))
                if step % 20 == 0:
                    assert not preview.grabFramebuffer().isNull()
                    assert not preview.error, preview.error
            release = QtGui.QMouseEvent(QtCore.QEvent.MouseButtonRelease, position, QtCore.Qt.LeftButton, QtCore.Qt.NoButton, QtCore.Qt.NoModifier)
            QtWidgets.QApplication.sendEvent(preview, release)
            assert preview.last_position is None
        report["passed"].append("all three shapes: 240 drag steps each, multiple full turns, reversal, no angle clamp or discontinuity")
        window.shape.setCurrentIndex(0)
        preview.zoom = 1
        for pitch in (0, math.pi / 2 - 0.03, math.pi / 2 + 0.03, math.pi, 2 * math.pi, -math.pi):
            preview.rotation = [0, pitch]
            frame = preview.grabFramebuffer()
            assert not preview.error
            center = frame.pixelColor(frame.width() // 2, frame.height() // 2)
            assert max(center.red(), center.green(), center.blue()) > 50, (pitch, center.name())
        report["passed"].append("plane renders front, back, full turns and immediately either side of edge-on")
        saved_rotation = list(preview.rotation)
        position = QtCore.QPointF(40, 40)
        QtWidgets.QApplication.sendEvent(preview, QtGui.QMouseEvent(QtCore.QEvent.MouseButtonPress, position, QtCore.Qt.RightButton, QtCore.Qt.RightButton, QtCore.Qt.NoModifier))
        before_light = preview.light_angle
        QtWidgets.QApplication.sendEvent(preview, QtGui.QMouseEvent(QtCore.QEvent.MouseMove, position + QtCore.QPointF(50, 0), QtCore.Qt.NoButton, QtCore.Qt.RightButton, QtCore.Qt.NoModifier))
        assert preview.rotation == saved_rotation and abs(preview.light_angle-before_light-0.75) < 1e-9
        preview.reset_view()
        assert preview.rotation == [0.25, -0.2] and preview.light_angle == -0.6
        report["passed"].append("right drag affects only light; Fit restores initial rotation and light")
    finally:
        window.close()
    with open(os.path.join(ROOT, "work", "rotation_checks.json"), "w") as stream:
        json.dump(report, stream, indent=2)


check_rotation()
