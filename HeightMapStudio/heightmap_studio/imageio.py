# -*- coding: utf-8 -*-
"""Qt decoding with precision guards; streaming lossless PNG/TIFF encoding."""
import array
import os
import struct
import threading
import zlib
from .qt import QtCore, QtGui

LIMIT = 8192
_DECODE_LOCK = threading.Lock()


def source_depth(filename):
    """Read stored precision before trusting an image plugin's converted pixels."""
    with open(filename, "rb") as stream:
        header = stream.read(26)
        if header[:8] == b"\x89PNG\r\n\x1a\n":
            return header[24]
        if header[:2] not in (b"II", b"MM"):
            return 8
        endian = "<" if header[:2] == b"II" else ">"
        if struct.unpack(endian + "H", header[2:4])[0] != 42:
            raise ValueError("BigTIFF is not supported. Use standard TIFF or PNG.")
        offset = struct.unpack(endian + "I", header[4:8])[0]
        stream.seek(offset)
        count = struct.unpack(endian + "H", stream.read(2))[0]
        bits, sample_format = 8, 1
        for unused in range(count):
            entry = stream.read(12)
            tag, dtype, length = struct.unpack(endian + "HHI", entry[:8])
            if tag not in (258, 339):
                continue
            if dtype != 3 or not 1 <= length <= 8:
                raise ValueError("Unsupported TIFF structure.")
            raw = entry[8:12]
            if length > 2:
                saved = stream.tell()
                stream.seek(struct.unpack(endian + "I", raw)[0])
                raw = stream.read(length * 2)
                stream.seek(saved)
            values = struct.unpack(endian + "H" * length, raw[:length * 2])
            if tag == 258:
                bits = max(values)
            else:
                sample_format = max(values)
        if sample_format != 1 or bits > 16:
            raise ValueError("Only 8/16-bit integer TIFF images are supported. Float/HDR TIFF is not supported.")
        return bits


def load_image(filename):
    if os.path.splitext(filename)[1].lower() not in (".png", ".tif", ".tiff", ".jpg", ".jpeg"):
        raise ValueError("Choose a PNG, TIFF, or JPG image.")
    depth = source_depth(filename)
    reader = QtGui.QImageReader(filename)
    reader.setAutoTransform(True)
    size = reader.size()
    if size.width() > LIMIT or size.height() > LIMIT:
        raise ValueError("Maximum image size: 8192 × 8192 px.")
    # Qt 6 defaults to 256 MiB per decoded image, below an 8K RGB16 image.
    # Raise only for this bounded decode and restore the application's setting.
    with _DECODE_LOCK:
        previous_limit = QtGui.QImageReader.allocationLimit() if hasattr(QtGui.QImageReader, "allocationLimit") else None
        needed_mb = (max(0, size.width()) * max(0, size.height()) * 8 + 1048575) // 1048576 + 16
        raised = previous_limit is not None and previous_limit > 0 and needed_mb > previous_limit
        if raised:
            QtGui.QImageReader.setAllocationLimit(needed_mb)
        try:
            image = reader.read()
        finally:
            if raised:
                QtGui.QImageReader.setAllocationLimit(previous_limit)
    if image.isNull():
        raise ValueError("Could not read image: " + reader.errorString())
    if max(image.width(), image.height()) > LIMIT:
        raise ValueError("Maximum image size: 8192 × 8192 px.")
    if depth == 16 and image.depth() < 48 and image.format() != QtGui.QImage.Format_Grayscale16:
        raise ValueError("The Qt decoder reduced 16-bit precision. Save the source as a 16-bit grayscale PNG.")
    # Height is data in RGB; ignore alpha consistently in full and tiled paths.
    image = image.convertToFormat(QtGui.QImage.Format_RGBX64)
    if image.isNull():
        raise MemoryError("Not enough memory to load the image.")
    preview = image.scaled(2048, 2048, QtCore.Qt.KeepAspectRatio,
                           QtCore.Qt.SmoothTransformation) if max(image.width(), image.height()) > 2048 else image
    return image, preview, depth


def _segments(start, length, total, wrap):
    dest = 0
    while dest < length:
        source = start + dest
        if wrap:
            source %= total
            count = min(length - dest, total - source)
            yield dest, count, source, count
        elif source < 0:
            count = min(length - dest, -source)
            yield dest, count, 0, 1
        elif source >= total:
            count = length - dest
            yield dest, count, total - 1, 1
        else:
            count = min(length - dest, total - source)
            yield dest, count, source, count
        dest += count


def padded_tile(image, x, y, width, height, border, wrap):
    result = QtGui.QImage(width + 2 * border, height + 2 * border, QtGui.QImage.Format_RGBA64)
    if result.isNull():
        raise MemoryError("Not enough memory to process the tile.")
    painter = QtGui.QPainter(result)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
    try:
        for dy, dh, sy, sh in _segments(y - border, result.height(), image.height(), wrap):
            for dx, dw, sx, sw in _segments(x - border, result.width(), image.width(), wrap):
                painter.drawImage(QtCore.QRect(dx, dy, dw, dh), image, QtCore.QRect(sx, sy, sw, sh))
    finally:
        painter.end()
    return result


def _chunk(stream, label, payload):
    stream.write(struct.pack(">I", len(payload)))
    stream.write(label)
    stream.write(payload)
    stream.write(struct.pack(">I", zlib.crc32(label + payload) & 0xffffffff))


def encode_png(filename, rows, width, height, channels, depth, cancelled):
    with open(filename, "wb") as stream:
        stream.write(b"\x89PNG\r\n\x1a\n")
        _chunk(stream, b"IHDR", struct.pack(">IIBBBBB", width, height, depth,
                                             2 if channels == 3 else 0, 0, 0, 0))
        compressor = zlib.compressobj(3)
        for row in rows:
            cancelled()
            if depth == 16:
                words = array.array("H")
                words.frombytes(row)
                words.byteswap()  # Windows is little-endian; PNG stores big-endian samples.
                row = words.tobytes()
            block = compressor.compress(b"\0" + row)
            if block:
                _chunk(stream, b"IDAT", block)
        _chunk(stream, b"IDAT", compressor.flush())
        _chunk(stream, b"IEND", b"")


def encode_tiff(filename, rows, width, height, channels, depth, cancelled):
    # Baseline little-endian TIFF, one uncompressed strip; no lossy conversion.
    tags = [(256, 4, 1, width), (257, 4, 1, height), (258, 3, channels, depth),
            (259, 3, 1, 1), (262, 3, 1, 2 if channels == 3 else 1),
            (273, 4, 1, 0), (277, 3, 1, channels), (278, 4, 1, height),
            (279, 4, 1, width * height * channels * (depth // 8)), (284, 3, 1, 1)]
    extra_offset = 8 + 2 + len(tags) * 12 + 4
    data_offset = extra_offset + (6 if channels == 3 else 0)
    with open(filename, "wb") as stream:
        stream.write(b"II" + struct.pack("<HIH", 42, 8, len(tags)))
        for tag, dtype, count, value in tags:
            if tag == 273:
                value = data_offset
            if tag == 258 and channels == 3:
                value = extra_offset
            stream.write(struct.pack("<HHII", tag, dtype, count, value))
        stream.write(struct.pack("<I", 0))
        if channels == 3:
            stream.write(struct.pack("<HHH", depth, depth, depth))
        for row in rows:
            cancelled()
            stream.write(row)


def encode_jpeg(filename, rows, width, height, channels, depth, cancelled):
    """Qt's JPEG encoder needs one packed 8-bit image (at most 192 MiB)."""
    if depth != 8:
        raise ValueError("JPEG export requires 8-bit samples.")
    image = QtGui.QImage(width, height, QtGui.QImage.Format_RGB888 if channels == 3 else QtGui.QImage.Format_Grayscale8)
    if image.isNull():
        raise MemoryError("Not enough memory to encode JPEG.")
    pointer = image.bits()
    if hasattr(pointer, "setsize"):
        pointer.setsize(image.bytesPerLine() * height)
    pixels = memoryview(pointer).cast("B")
    row_bytes = width * channels
    for index, row in enumerate(rows):
        cancelled()
        offset = index * image.bytesPerLine()
        pixels[offset:offset + row_bytes] = row
    del pixels, pointer
    cancelled()
    writer = QtGui.QImageWriter(filename, b"jpeg")
    writer.setQuality(95)
    if not writer.write(image):
        raise RuntimeError("Could not encode JPEG: " + writer.errorString())
    cancelled()  # A cancellation during the codec call prevents final commit.


def encode_jpeg(filename, rows, width, height, channels, depth, cancelled):
    """Qt's JPEG encoder needs one packed 8-bit image (at most 192 MiB)."""
    if depth != 8:
        raise ValueError("JPEG export requires 8-bit samples.")
    image = QtGui.QImage(width, height, QtGui.QImage.Format_RGB888 if channels == 3 else QtGui.QImage.Format_Grayscale8)
    if image.isNull():
        raise MemoryError("Not enough memory to encode JPEG.")
    pointer = image.bits()
    if hasattr(pointer, "setsize"):
        pointer.setsize(image.bytesPerLine() * height)
    pixels = memoryview(pointer).cast("B")
    row_bytes = width * channels
    for index, row in enumerate(rows):
        cancelled()
        offset = index * image.bytesPerLine()
        pixels[offset:offset + row_bytes] = row
    del pixels, pointer
    cancelled()
    writer = QtGui.QImageWriter(filename, b"jpeg")
    writer.setQuality(95)
    if not writer.write(image):
        raise RuntimeError("Could not encode JPEG: " + writer.errorString())
    cancelled()  # A cancellation during the codec call prevents final commit.
