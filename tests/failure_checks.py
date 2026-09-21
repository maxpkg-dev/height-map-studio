# -*- coding: utf-8 -*-
"""Deterministic failure and preview scaling checks, run via MCP in Max."""
import array
import json
import os
import traceback
from heightmap_studio import ui, gl
from heightmap_studio.qt import QtCore, QtGui
from heightmap_studio.imageio import encode_png, load_image
from heightmap_studio.model import DEFAULTS
from heightmap_studio.preview import Preview
WORK=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"work")
report={"tests":[],"errors":[]}


def run(name,fn):
    try:
        fn()
        report["tests"].append({"name":name,"ok":True})
    except Exception:
        report["errors"].append({"name":name,"error":traceback.format_exc()})


def bad_input():
    filename=os.path.join(WORK,"oversize.png")
    encode_png(filename,[b"\0"*8193],8193,1,1,8,lambda:None)
    try:
        load_image(filename)
    except ValueError as exc:
        assert "8192" in str(exc)
    else:
        raise AssertionError("oversize accepted")
    filename=os.path.join(WORK,"corrupted.png")
    with open(filename,"wb") as stream:
        stream.write(b"Not an image")
    try:
        load_image(filename)
    except ValueError:
        pass
    else:
        raise AssertionError("corrupt image accepted")


def unavailable_gpu():
    original=gl.Engine
    def unavailable():
        raise RuntimeError("TEST: GPU unavailable")
    widget=Preview()
    try:
        gl.Engine=unavailable
        widget.initializeGL()
        assert "GPU unavailable" in widget.error
        image=QtGui.QImage(16,16,QtGui.QImage.Format_RGBX64)
        widget.set_image(image,(16,16))
        assert "GPU unavailable" in widget.error
        assert widget.engine is None
    finally:
        gl.Engine=original
        widget.deleteLater()


def preview_scale():
    window=ui.show()
    window.preview.makeCurrent()
    engine=gl.Engine()
    try:
        # Interior slope in source pixels must be independent of preview reduction.
        row=array.array("H")
        for x in range(1024):
            v=x*64
            row.extend((v,v,v,65535))
        image=QtGui.QImage(row.tobytes()*64,1024,64,8192,QtGui.QImage.Format_RGBA64).copy()
        engine.upload(image)
        settings=dict(DEFAULTS,strength=40.0)
        full=engine.read(engine.process(settings,"normal"),512,32,1,1)
        reduced=image.scaled(256,16,QtCore.Qt.IgnoreAspectRatio,QtCore.Qt.SmoothTransformation)
        engine.upload(reduced)
        preview=engine.read(engine.process(settings,"normal",scale=(4.0,4.0)),128,8,1,1)
        assert max(abs(a-b) for a,b in zip(full,preview))<=1,(list(full),list(preview))
    finally:
        engine.close()
        window.preview.doneCurrent()


run("reject_oversize_and_corrupt_input",bad_input)
run("gpu_error_visible_after_loading",unavailable_gpu)
run("normal_strength_matches_preview_scale",preview_scale)
with open(os.path.join(WORK,"failure_checks.json"),"w",encoding="utf8") as stream:
    json.dump(report,stream,ensure_ascii=False,indent=2)
