# -*- coding: utf-8 -*-
"""Asynchronous Max integration checks; launch through Max Ultra MCP.

All generated files stay in work/. Slate tests use and remove their own View.
"""
import array
import json
import os
import sys
import time
import traceback
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "HeightMapStudio"))
from heightmap_studio.qt import QtCore, QtGui, QtWidgets, image_bytes
from heightmap_studio.imageio import load_image, encode_png
from heightmap_studio.model import MAPS, DEFAULTS
from heightmap_studio import ui
WORK = os.path.join(ROOT, "work")


class Checks(QtCore.QObject):
    def __init__(self):
        super(Checks,self).__init__()
        self.report={"tests":[],"errors":[],"status":"running"}
        self.window=ui.show()
        self.started=time.perf_counter()
        self.paths=[]
        self.phase="export"
        self.write()
        image,preview,depth=load_image(os.path.join(WORK,"precision_16.png"))
        self.window.image=image
        self.window.filename=os.path.join(WORK,"precision_16.png")
        self.window.settings=dict(DEFAULTS)
        self.window.preview.set_image(preview,(256,256))
        destinations=[]
        for ext in ("png","tif"):
            for kind in MAPS:
                filename=os.path.join(WORK,"test_"+kind+"."+ext)
                self.paths.append((kind,filename))
                destinations.append((kind,filename,True))
        self.window.start_export(destinations,False)
        self.window.export_job.failed.connect(self.error)
        self.window.export_job.completed.connect(self.export_complete)

    def write(self):
        with open(os.path.join(WORK,"integration_checks.json"),"w",encoding="utf8") as stream:
            json.dump(self.report,stream,ensure_ascii=False,indent=2)

    def error(self,message):
        self.report["errors"].append({"phase":self.phase,"error":message})
        self.report["status"]="failed"
        self.write()

    def export_complete(self,files,seconds):
        try:
            for kind,filename in files:
                image,preview,depth=load_image(filename)
                assert image.size()==QtCore.QSize(256,256)
                if kind=="displacement":
                    pixels=array.array("H"); pixels.frombytes(image_bytes(image))
                    assert pixels[::4]==array.array("H",range(65536))
                    assert depth==16
            self.report["tests"].append({"name":"background_export_8_files","seconds":seconds,"ok":True})
            self.phase="slate"
            self.slate_test()
            QtCore.QTimer.singleShot(300,self.cancel_test)
        except Exception:
            self.error(traceback.format_exc())

    def slate_test(self):
        from pymxs import runtime as rt
        from heightmap_studio.maxbridge import add_to_slate
        previous=int(rt.sme.activeView)
        was_open=bool(rt.sme.IsOpen())
        rt.sme.Open()
        count_before=int(rt.sme.GetNumViews())
        index=rt.sme.CreateView("HMS_INTEGRATION_TEST")
        rt.sme.activeView=index
        try:
            nodes=add_to_slate(self.paths[:4])
            view=rt.sme.GetView(index)
            assert view.GetNumNodes()==4
            first_right=max(float(n.position.x)+float(n.width) for n in nodes)
            more=add_to_slate(self.paths[4:])
            assert view.GetNumNodes()==8
            assert min(float(n.position.x) for n in more)>first_right
            details=[]
            for node in nodes+more:
                b=node.reference.bitmap
                details.append({"path":str(b.filename),"gamma":float(b.inputGammaValue),"colorspace":str(b.colorSpace)})
            self.report["tests"].append({"name":"slate_empty_and_populated_view_raw","ok":True,"maps":details})
        finally:
            rt.sme.DeleteView(index,False)
            if previous>0 and previous<=rt.sme.GetNumViews():
                rt.sme.activeView=previous
            if not was_open:
                rt.sme.Close()
            assert int(rt.sme.GetNumViews())==count_before
        self.write()

    def cancel_test(self):
        try:
            self.phase="cancel"
            filename=os.path.join(WORK,"cancel_guard.png")
            with open(filename,"wb") as stream:
                stream.write(b"EXISTING_FILE_MUST_SURVIVE")
            self.window.start_export([("ao",filename,True)],False)
            self.window.export_job.cancelled.connect(lambda: self.cancelled(filename))
            self.window.export_job.failed.connect(self.error)
            self.window.cancel_export()
        except Exception:
            self.error(traceback.format_exc())

    def cancelled(self,filename):
        try:
            with open(filename,"rb") as stream:
                assert stream.read()==b"EXISTING_FILE_MUST_SURVIVE"
            self.report["tests"].append({"name":"cancellation_preserves_existing_file","ok":True})
            QtCore.QTimer.singleShot(300,self.drag_test)
        except Exception:
            self.error(traceback.format_exc())

    def drag_test(self):
        try:
            self.phase="drag_drop_and_load_race"
            self.window.load(os.path.join(WORK,"precision_16.png"))
            mime=QtCore.QMimeData()
            filename=os.path.join(WORK,"demo_height_16.png")
            mime.setUrls([QtCore.QUrl.fromLocalFile(filename)])
            drag=QtGui.QDragEnterEvent(QtCore.QPoint(20,20),QtCore.Qt.CopyAction,mime,QtCore.Qt.LeftButton,QtCore.Qt.NoModifier)
            QtWidgets.QApplication.sendEvent(self.window,drag)
            assert drag.isAccepted()
            drop=QtGui.QDropEvent(QtCore.QPointF(20,20),QtCore.Qt.CopyAction,mime,QtCore.Qt.LeftButton,QtCore.Qt.NoModifier)
            QtWidgets.QApplication.sendEvent(self.window,drop)
            assert drop.isAccepted()
            self.expected=filename
            self.deadline=time.monotonic()+20
            QtCore.QTimer.singleShot(200,self.load_check)
        except Exception:
            self.error(traceback.format_exc())

    def load_check(self):
        try:
            if self.window.load_jobs:
                assert time.monotonic()<self.deadline,"load timeout"
                QtCore.QTimer.singleShot(200,self.load_check)
                return
            assert self.window.filename==self.expected,self.window.filename
            assert not self.window.preview.error,self.window.preview.error
            self.report["tests"].append({"name":"drag_drop_and_latest_load_wins","ok":True})
            self.phase="reopen"
            self.window.close()
            QtCore.QTimer.singleShot(200,self.reopen)
        except Exception:
            self.error(traceback.format_exc())

    def reopen(self):
        try:
            self.window=ui.show()
            assert self.window.isVisible()
            self.window.load(os.path.join(WORK,"demo_height_16.png"))
            self.report["tests"].append({"name":"close_reopen","ok":True})
            self.report["status"]="complete"
            self.report["seconds"]=time.perf_counter()-self.started
            self.write()
        except Exception:
            self.error(traceback.format_exc())


_hms_checks=Checks()
