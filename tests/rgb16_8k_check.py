"""Exercise Qt's 8K RGB16 allocation guard, restoring its original limit."""
import array
import json
import os
import traceback
from heightmap_studio.qt import QtCore, QtGui
from heightmap_studio.imageio import encode_png
from heightmap_studio.jobs import LoadJob
WORK=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"work")


class Check(QtCore.QObject):
    def __init__(self):
        super(Check,self).__init__()
        self.report={"status":"running"}
        self.before=QtGui.QImageReader.allocationLimit()
        self.write()
        filename=os.path.join(WORK,"rgb16_8k.png")
        row=array.array("H",[12345,23456,34567]*8192).tobytes()
        encode_png(filename,(row for y in range(8192)),8192,8192,3,16,lambda:None)
        self.job=LoadJob(1,filename,self)
        self.job.failed.connect(self.failed)
        self.job.loaded.connect(self.loaded)
        self.job.start()

    def write(self):
        with open(os.path.join(WORK,"rgb16_8k_check.json"),"w") as stream:
            json.dump(self.report,stream,indent=2)

    def failed(self,generation,error):
        self.report={"status":"failed","error":error}
        self.write()

    def loaded(self,generation,filename,image,preview,depth):
        try:
            assert depth==16 and image.size()==QtCore.QSize(8192,8192)
            assert QtGui.QImageReader.allocationLimit()==self.before
            sample=image.pixelColor(4096,4096).rgba64()
            assert (sample.red(),sample.green(),sample.blue())==(12345,23456,34567)
            self.report={"status":"complete","depth":16,"size":8192,"allocation_limit_restored":self.before}
            self.write()
        except Exception:
            self.failed(generation,traceback.format_exc())


_hms_rgb16=Check()
