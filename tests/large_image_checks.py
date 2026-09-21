# -*- coding: utf-8 -*-
"""8K I/O/export and 2K latency checks, launched through Max Ultra MCP."""
import array
import json
import os
import statistics
import time
import traceback
from heightmap_studio import ui
from heightmap_studio.qt import QtCore, QtGui
from heightmap_studio.jobs import LoadJob
from heightmap_studio.imageio import encode_png, load_image
from heightmap_studio.model import DEFAULTS, MAPS
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK=os.path.join(ROOT,"work")


class Checks(QtCore.QObject):
    def __init__(self):
        super(Checks,self).__init__()
        self.report={"tests":[],"errors":[],"status":"running"}
        self.window=ui.show()
        self.ticks=0
        self.timer=QtCore.QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.write()
        # A genuine 8192x8192, 16-bit image: smooth ramp over X.
        filename=os.path.join(WORK,"height_8192_16.png")
        row=array.array("H",(round(x*65535/8191) for x in range(8192))).tobytes()
        encode_png(filename,(row for y in range(8192)),8192,8192,1,16,lambda:None)
        self.job=LoadJob(100,filename,self)
        self.job.failed.connect(lambda generation,message:self.error(message))
        self.job.loaded.connect(self.loaded)
        self.job.start()

    def tick(self):
        self.ticks+=1

    def write(self):
        with open(os.path.join(WORK,"large_image_checks.json"),"w",encoding="utf8") as stream:
            json.dump(self.report,stream,ensure_ascii=False,indent=2)

    def error(self,message):
        self.report["errors"].append(message)
        self.report["status"]="failed"
        self.timer.stop()
        self.write()

    def loaded(self,generation,filename,image,preview,depth):
        try:
            assert image.size()==QtCore.QSize(8192,8192)
            assert preview.size()==QtCore.QSize(2048,2048)
            assert depth==16
            self.report["tests"].append({"name":"load_8k_16bit","ok":True,"preview":2048})
            self.window.loaded(self.window.generation,filename,image,preview,depth)
            self.window.settings=dict(DEFAULTS)
            self.window.preview.settings=dict(DEFAULTS)
            self.preview_image=preview
            QtCore.QTimer.singleShot(250,self.benchmark)
        except Exception:
            self.error(traceback.format_exc())

    def benchmark(self):
        from heightmap_studio.gl import Engine
        self.window.preview.makeCurrent()
        engine=None
        try:
            engine=Engine()
            engine.upload(self.preview_image)
            timings={}
            for kind in MAPS:
                samples=[]
                for unused in range(4):
                    start=time.perf_counter()
                    engine.process(dict(DEFAULTS),kind,scale=(4.0,4.0))
                    engine.gl.Finish()
                    samples.append((time.perf_counter()-start)*1000)
                timings[kind]={"median_ms":statistics.median(samples[1:]),"samples_ms":samples[1:]}
            self.report["tests"].append({"name":"2k_latency","gpu":engine.gl.description,"timings":timings})
            self.write()
        except Exception:
            self.error(traceback.format_exc())
            return
        finally:
            if engine:
                engine.close()
            self.window.preview.doneCurrent()
        self.export_ticks=self.ticks
        self.window.start_export([(kind,os.path.join(WORK,"8k_"+kind+".png"),True) for kind in MAPS],False)
        self.window.export_job.failed.connect(self.error)
        self.window.export_job.completed.connect(self.export_done)

    def export_done(self,files,seconds):
        try:
            assert self.ticks-self.export_ticks>10,"UI timer did not run during export"
            details=[]
            for kind,filename in files:
                # Read just PNG IHDR to verify dimensions/precision without allocating another 8K image.
                import struct
                with open(filename,"rb") as stream:
                    header=stream.read(26)
                width,height,depth=struct.unpack(">IIB",header[16:25])
                assert (width,height)==(8192,8192)
                assert depth==(16 if kind=="displacement" else 8)
                details.append({"kind":kind,"bytes":os.path.getsize(filename),"depth":depth})
            self.report["tests"].append({"name":"export_8k_all_maps","ok":True,"seconds":seconds,"ui_ticks":self.ticks-self.export_ticks,"files":details})
            self.report["status"]="complete"
            self.timer.stop()
            self.write()
            QtCore.QTimer.singleShot(300,lambda:self.window.load(os.path.join(WORK,"demo_height_16.png")))
        except Exception:
            self.error(traceback.format_exc())


_hms_large_checks=Checks()
