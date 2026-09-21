"""Small Qt 5/6 compatibility surface. Compatible with Python 3.7+."""
try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets
    QOpenGLWidget = QtWidgets.QOpenGLWidget


def image_bytes(image):
    ptr = image.constBits()
    count = image.bytesPerLine() * image.height()
    if hasattr(ptr, "setsize"):
        ptr.setsize(count)
    return bytes(ptr)[:count]


def gl_format():
    fmt = QtGui.QSurfaceFormat()
    fmt.setRenderableType(QtGui.QSurfaceFormat.OpenGL)
    fmt.setVersion(3, 3)
    fmt.setProfile(QtGui.QSurfaceFormat.CoreProfile)
    fmt.setDepthBufferSize(0)
    fmt.setStencilBufferSize(0)
    fmt.setSwapInterval(0)
    return fmt
