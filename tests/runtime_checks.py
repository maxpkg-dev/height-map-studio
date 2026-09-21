# -*- coding: utf-8 -*-
"""Run inside Max via MCP/python.ExecuteFile. Does not alter scene objects."""
import array
import json
import math
import os
import sys
import time
import traceback
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE = os.path.join(ROOT, "HeightMapStudio")
if PACKAGE not in sys.path:
    sys.path.insert(0, PACKAGE)
from heightmap_studio.qt import QtGui, image_bytes
from heightmap_studio.imageio import encode_png, encode_tiff, load_image, padded_tile
from heightmap_studio.model import DEFAULTS, halo, tiles
from heightmap_studio import ui
WORK = os.path.join(ROOT, "work")
os.makedirs(WORK, exist_ok=True)
REPORT = {"tests": [], "errors": []}


def fixture(width, height, fn):
    raw = array.array("H")
    for y in range(height):
        for x in range(width):
            v = int(max(0, min(65535, fn(x, y))))
            raw.extend((v, v, v, 65535))
    return QtGui.QImage(raw.tobytes(), width, height, width * 8, QtGui.QImage.Format_RGBA64).copy()


def run(name, function):
    started = time.perf_counter()
    try:
        detail = function()
        REPORT["tests"].append({"name": name, "ok": True, "seconds": time.perf_counter()-started, "detail": detail})
    except Exception:
        REPORT["errors"].append({"name": name, "traceback": traceback.format_exc()})


def precision():
    values = array.array("H", range(65536))
    raw = values.tobytes()
    for extension, encode in (("png", encode_png), ("tif", encode_tiff)):
        filename = os.path.join(WORK, "precision_16." + extension)
        encode(filename, (raw[y*512:(y+1)*512] for y in range(256)), 256, 256, 1, 16, lambda: None)
        image, preview, depth = load_image(filename)
        pixels = array.array("H")
        pixels.frombytes(image_bytes(image))
        assert pixels[0::4] == values, "16-bit decode lost values: " + extension
        assert depth == 16
    return "PNG/TIFF: all 65536 levels round-trip exactly"


def gpu_checks():
    from heightmap_studio.gl import Engine
    window = ui.show()
    window.preview.makeCurrent()
    engine = Engine()
    try:
        REPORT["gpu"] = engine.gl.description
        image = fixture(65, 33, lambda x,y: 32768)
        engine.upload(image)
        settings = dict(DEFAULTS)
        for kind, expected in (("normal", (128,128,255)), ("ao", (255,255,255))):
            result = engine.process(settings, kind)
            pixels = engine.read(result, 0, 0, 65, 33)
            assert all(abs(pixels[i]-expected[i%3]) <= 1 for i in range(len(pixels))), kind
        ramp = fixture(65,33,lambda x,y: (x+y)*600)
        engine.upload(ramp)
        normal = engine.read(engine.process(settings,"normal"), 32,16,1,1)
        assert normal[0]<128 and normal[1]>128 and normal[2]>=250, list(normal)
        settings["directx"]=True
        flipped=engine.read(engine.process(settings,"normal"),32,16,1,1)
        assert normal[0]==flipped[0] and abs(normal[1]+flipped[1]-255)<=1
        settings["directx"]=False
        settings["invert"]=True
        inverse=engine.read(engine.process(settings,"normal"),32,16,1,1)
        assert inverse[0]>128 and inverse[1]<128
        settings=dict(DEFAULTS)
        cavity=fixture(65,65,lambda x,y: 0 if 24<x<40 and 24<y<40 else 65535)
        engine.upload(cavity)
        result=engine.process(settings,"ao")
        center=engine.read(result,32,32,1,1)[0]
        corner=engine.read(result,2,2,1,1)[0]
        assert center<corner and corner==255, (center,corner)
        return {"flat":"neutral normal and white AO", "ramp":list(normal), "directx":list(flipped), "cavity_ao":center}
    finally:
        engine.close()
        window.preview.doneCurrent()


def tile_checks():
    from heightmap_studio.gl import Engine
    window=ui.show()
    window.preview.makeCurrent()
    engine=Engine()
    differences={}
    try:
        w,h=1153,73
        image=fixture(w,h,lambda x,y: 32768+22000*math.sin(x*0.11)*math.cos(y*0.15))
        settings=dict(DEFAULTS,blur=3.2,ao_radius=25.0)
        for seamless in (False,True):
            settings["seamless"]=seamless
            for kind in ("normal","ao","displacement","specular"):
                engine.upload(image,seamless)
                full=engine.read(engine.process(settings,kind),0,0,w,h)
                composed=bytearray(w*h*3)
                border=halo(settings,kind)
                for x,y,tw,th in tiles(w,h,512):
                    tile=padded_tile(image,x,y,tw,th,border,seamless)
                    engine.upload(tile)
                    bounds=(((border-x+0.5)/tile.width(),(border-y+0.5)/tile.height()),
                            ((border-x+w-0.5)/tile.width(),(border-y+h-0.5)/tile.height()))
                    pixels=engine.read(engine.process(settings,kind,wrap=False,bounds=bounds),border,border,tw,th)
                    for row in range(th):
                        offset=((y+row)*w+x)*3
                        composed[offset:offset+tw*3]=pixels[row*tw*3:(row+1)*tw*3]
                diff=max(abs(a-b) for a,b in zip(full,composed))
                differences[kind+"_"+str(seamless)]=diff
                assert diff<=1, (kind,seamless,diff)
        image,_,_=load_image(os.path.join(WORK,"precision_16.png"))
        engine.upload(image)
        output=engine.read(engine.process(dict(DEFAULTS),"displacement"),0,0,256,256,1,16)
        values=array.array("H"); values.frombytes(output)
        assert values==array.array("H",range(65536)), "GPU displacement precision loss"
        return differences
    finally:
        engine.close()
        window.preview.doneCurrent()


def sample():
    image=fixture(512,512,lambda x,y: 15000+42000*max(0.0,1.0-(((x%128)-64)/48.0)**8-(((y%128)-64)/48.0)**8))
    filename=os.path.join(WORK,"demo_height_16.png")
    pixels=array.array("H"); pixels.frombytes(image_bytes(image))
    raw=pixels[0::4].tobytes()
    encode_png(filename,(raw[y*1024:(y+1)*1024] for y in range(512)),512,512,1,16,lambda:None)
    ui.show().load(filename)
    return filename


run("precision_png_tiff_16",precision)
run("normal_conventions_and_ao",gpu_checks)
run("tiled_vs_full_and_gpu_16bit",tile_checks)
run("create_demo",sample)
with open(os.path.join(WORK,"runtime_checks.json"),"w",encoding="utf8") as stream:
    json.dump(REPORT,stream,ensure_ascii=False,indent=2)
