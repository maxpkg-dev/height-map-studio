# -*- coding: utf-8 -*-
"""Background I/O and tiled GPU export. No Max API calls in this module."""
import math
import os
import tempfile
import time
from .qt import QtCore, QtGui, gl_format
from .imageio import load_image, padded_tile, encode_png, encode_tiff, encode_jpeg
from .model import halo, tiles


class Cancelled(Exception):
    pass


class LoadJob(QtCore.QThread):
    loaded = QtCore.Signal(int, str, object, object, int)
    failed = QtCore.Signal(int, str)

    def __init__(self, generation, filename, parent=None):
        super(LoadJob, self).__init__(parent)
        self.generation, self.filename = generation, filename

    def run(self):
        try:
            image, preview, depth = load_image(self.filename)
            if not self.isInterruptionRequested():
                self.loaded.emit(self.generation, self.filename, image, preview, depth)
        except Exception as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(self.generation, str(exc))


class ExportJob(QtCore.QThread):
    progress = QtCore.Signal(int, str)
    completed = QtCore.Signal(object, float)
    failed = QtCore.Signal(str)
    cancelled = QtCore.Signal()

    def __init__(self, image, settings, destinations, surface, parent=None):
        super(ExportJob, self).__init__(parent)
        self.image = image
        self.settings = dict(settings)
        self.destinations = destinations  # (kind, absolute destination, overwrite authorized)
        self.surface = surface

    def check_cancelled(self):
        if self.isInterruptionRequested():
            raise Cancelled()

    def run(self):
        from .gl import Engine
        engine, context = None, None
        temporary = []
        saved_files = []
        started = time.perf_counter()
        try:
            context = QtGui.QOpenGLContext()
            context.setFormat(gl_format())
            if not context.create() or not context.makeCurrent(self.surface):
                raise RuntimeError("Could not create a GPU context for export.")
            engine = Engine()
            width, height = self.image.width(), self.image.height()
            block_count = int(math.ceil(width / 1024.0) * math.ceil(height / 1024.0))
            completed_blocks = 0
            total_blocks = block_count * len(self.destinations)
            staged = []
            for kind, destination, overwrite in self.destinations:
                self.check_cancelled()
                extension = os.path.splitext(destination)[1].lower()
                encoders = {".png": encode_png, ".tif": encode_tiff, ".tiff": encode_tiff,
                            ".jpg": encode_jpeg, ".jpeg": encode_jpeg}
                if extension not in encoders:
                    raise ValueError("Unsupported output format: " + extension)
                jpeg = extension in (".jpg", ".jpeg")
                channels, depth = (3, 8) if kind == "normal" else (1, 16 if kind == "displacement" and not jpeg else 8)
                pixel_bytes = channels * (depth // 8)
                row_bytes = width * pixel_bytes
                border = halo(self.settings, kind)
                # Disk-backed raw rows bound memory; encode only after all tiles are available.
                with tempfile.TemporaryFile(prefix="heightmap_raw_") as raw:
                    raw.truncate(row_bytes * height)
                    for x, y, tw, th in tiles(width, height):
                        self.check_cancelled()
                        tile = padded_tile(self.image, x, y, tw, th, border, self.settings["seamless"])
                        engine.upload(tile, False)
                        bounds = (((border - x + 0.5) / tile.width(), (border - y + 0.5) / tile.height()),
                                  ((border - x + width - 0.5) / tile.width(), (border - y + height - 0.5) / tile.height()))
                        output = engine.process(self.settings, kind, wrap=False, bounds=bounds)
                        data = engine.read(output, border, border, tw, th, channels, depth)
                        tile_row = tw * pixel_bytes
                        for row in range(th):
                            raw.seek((y + row) * row_bytes + x * pixel_bytes)
                            raw.write(data[row * tile_row:(row + 1) * tile_row])
                        completed_blocks += 1
                        self.progress.emit(int(completed_blocks * 90 / total_blocks), "Processing: " + kind)
                    self.check_cancelled()
                    raw.seek(0)
                    fd, staging = tempfile.mkstemp(prefix=".heightmap_", suffix=".tmp", dir=os.path.dirname(destination))
                    os.close(fd)
                    temporary.append(staging)
                    rows = (raw.read(row_bytes) for unused in range(height))
                    encoder = encoders[extension]
                    self.progress.emit(int(completed_blocks * 90 / total_blocks), "Writing: " + kind)
                    encoder(staging, rows, width, height, channels, depth, self.check_cancelled)
                    staged.append((kind, staging, destination, overwrite))
            self.check_cancelled()
            # Stage the entire set first. Cancellation never damages existing files.
            for kind, staging, destination, overwrite in staged:
                if overwrite:
                    os.replace(staging, destination)
                else:
                    os.rename(staging, destination)  # Windows: fail if a competing file appeared.
                temporary.remove(staging)
                saved_files.append((kind, destination))
            self.progress.emit(100, "Done")
            self.completed.emit(saved_files, time.perf_counter() - started)
        except Cancelled:
            self.cancelled.emit()
        except Exception as exc:
            suffix = "\nAlready saved: " + ", ".join(p for k, p in saved_files) if saved_files else ""
            self.failed.emit(str(exc) + suffix)
        finally:
            if engine is not None:
                engine.close()
            if context is not None:
                context.doneCurrent()
            for filename in temporary:
                try:
                    os.remove(filename)
                except OSError:
                    pass  # Only workflow-owned staging files; final output is never removed.
