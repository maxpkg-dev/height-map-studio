"""Isolated GPU and Qt checks for spatial detail removal and combined preview."""
import array
import itertools
import math
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from map_controls_checks import fixture
from heightmap_studio.qt import QtCore, QtGui, QtWidgets, gl_format, image_bytes
from heightmap_studio.model import DEFAULTS, MAPS, halo, tiles
from heightmap_studio.gl import Engine, RGBA32F
from heightmap_studio.imageio import padded_tile, load_image
from heightmap_studio.jobs import ExportJob
from heightmap_studio.ui import Studio


def run():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    with tempfile.TemporaryDirectory(prefix="hms_preview_") as folder:
        store = QtCore.QSettings(str(Path(folder) / "settings.ini"), QtCore.QSettings.IniFormat)
        window = Studio(geometry_settings=store)
        try:
            preview = window.preview
            assert window.seamless.isChecked() and window.settings["seamless"] and preview.settings["seamless"]
            before = dict(window.settings)
            # Find the export Set by its existing map-keyed controls.
            export_state = [(box, box.isChecked()) for box in window.findChildren(QtWidgets.QCheckBox)
                            if box not in preview.map_checks.values()]
            for flags in itertools.product((False, True), repeat=4):
                for kind, enabled in zip(MAPS, flags):
                    preview.map_checks[kind].setChecked(enabled)
                assert tuple(preview.enabled_maps[k] for k in MAPS) == flags
                assert window.settings == before
                assert all(box.isChecked() == checked for box, checked in export_state)
            window.tabs.setCurrentIndex(0)
            window.parameters["detail_size"].set_value(8)
            window.tabs.setCurrentIndex(1)
            window.reset.click()
            assert window.settings["detail_size"] == 8
            window.tabs.setCurrentIndex(0)
            window.reset.click()
            assert window.settings["detail_size"] == 0
            assert all(preview.enabled_maps.values())
            assert preview.preview_menu_button.isHidden()
            preview.set_3d(True)
            assert not preview.preview_menu_button.isHidden()
            assert preview.preview_menu_button.height() == 20
            menu = preview.preview_menu_button.menu()
            menu.popup(QtCore.QPoint(10, 10))
            app.processEvents()
            preview.map_checks["ao"].click()
            assert menu.isVisible(), "Preview menu closed after a checkbox click"
            preview.set_3d(False)
            assert preview.preview_menu_button.isHidden() and not menu.isVisible()
            preview.set_3d(True)
            assert not preview.map_checks["ao"].isChecked()
        finally:
            window.close()
    print("PASS: all 16 preview selections independent of export/settings; persistent menu; local Normal reset")

    surface = QtGui.QOffscreenSurface(); surface.setFormat(gl_format()); surface.create()
    context = QtGui.QOpenGLContext(); context.setFormat(gl_format())
    assert context.create() and context.makeCurrent(surface)
    engine = Engine()

    def normal(image, **changes):
        settings = dict(DEFAULTS, strength=20)
        settings.update(changes)
        engine.upload(image, settings["seamless"])
        result = engine.process(settings, "normal")
        return engine.read(result, 0, 0, image.width(), image.height())

    try:
        clean = fixture(193, 129, lambda x,y: 44000 if 40 <= x < 154 and 30 <= y < 100 else 16000)
        def detail(x,y):
            if 14 <= x < 17 and 16 <= y < 19: return 60000
            if 75 <= x < 78 and 62 <= y < 65: return 2000
            return 44000 if 40 <= x < 154 and 30 <= y < 100 else 16000
        noisy = fixture(193, 129, detail)
        original = normal(noisy)
        filtered = normal(noisy, detail_size=8)
        assert filtered != original
        assert normal(noisy, detail_size=0) == original
        assert filtered != normal(noisy, blur=4), "Feature removal must differ from Gaussian blur"
        # Both small features become flat, while the broad plateau remains.
        for x,y in ((15,17),(76,63),(100,70)):
            pixel=filtered[(y*193+x)*3:(y*193+x)*3+3]
            assert all(abs(a-b)<=2 for a,b in zip(pixel,(128,128,255))), (x,y,list(pixel))
        dx = normal(noisy, detail_size=8, directx=True)
        assert all(abs(filtered[i]+dx[i]-255)<=1 if i%3==1 else filtered[i]==dx[i] for i in range(len(dx)))
        ramp=fixture(129,65,lambda x,y:12000+x*250)
        a=normal(ramp,detail_size=16,seamless=False)
        b=normal(ramp,detail_size=16,invert=True,seamless=False)
        index=(32*129+64)*3
        assert a[index]<128 and b[index]>128
        engine.upload(noisy,True)
        engine.process(dict(DEFAULTS, detail_size=8), "normal")
        first=array.array("H");first.frombytes(engine.read(engine.textures["detail1"],0,0,193,129,1,16))
        engine.process(dict(DEFAULTS, detail_size=16), "normal", scale=(2.,2.))
        second=array.array("H");second.frombytes(engine.read(engine.textures["detail1"],0,0,193,129,1,16))
        assert sum(abs(a-b) for a,b in zip(first,second))/len(first)<100
        for kind in ("ao", "specular", "displacement"):
            a=engine.read(engine.process(dict(DEFAULTS),kind),0,0,193,129)
            b=engine.read(engine.process(dict(DEFAULTS,detail_size=32),kind),0,0,193,129)
            assert a==b
        # A wide flat source region must remain flat: this is not a blur.
        normal(clean,detail_size=16)
        heights=array.array("H");heights.frombytes(engine.read(engine.textures["detail1"],0,0,193,129,1,16))
        assert max(heights[y*193+x] for y in range(50,80) for x in range(65,125))-min(heights[y*193+x] for y in range(50,80) for x in range(65,125))<=1
        print("PASS: small peaks/grooves flatten, broad plateaus remain; neutral, conventions, inversion and scale")

        source=fixture(137,83,lambda x,y: 32768+int(16000*math.sin(x*.23)*math.cos(y*.31)))
        for size in (7.3,32,64):
            for seamless in (False,True):
                settings=dict(DEFAULTS,detail_size=size,blur=1.2,strength=20,seamless=seamless)
                full=normal(source,detail_size=size,blur=1.2,seamless=seamless)
                composed=bytearray(len(full)); border=halo(settings,"normal")
                for x,y,tw,th in tiles(137,83,64):
                    tile=padded_tile(source,x,y,tw,th,border,seamless)
                    engine.upload(tile)
                    bounds=(((border-x+.5)/tile.width(),(border-y+.5)/tile.height()),
                            ((border-x+137-.5)/tile.width(),(border-y+83-.5)/tile.height()))
                    result=engine.process(settings,"normal",wrap=False,bounds=bounds)
                    data=engine.read(result,border,border,tw,th)
                    for row in range(th):
                        offset=((y+row)*137+x)*3
                        composed[offset:offset+tw*3]=data[row*tw*3:(row+1)*tw*3]
                assert max(abs(a-b) for a,b in zip(full,composed))<=1,(size,seamless)
        print("PASS: fractional/max feature size plus Blur, rectangular tiles and clamped/seamless borders agree within 1 byte")
        context.doneCurrent()
        with tempfile.TemporaryDirectory(prefix="hms_detail_export_") as folder:
            for extension in ("png", "tif"):
                filename=str(Path(folder)/("normal."+extension))
                worker=ExportJob(source,settings,[("normal",filename,False)],surface)
                failures=[]
                worker.failed.connect(lambda error: failures.append(error),QtCore.Qt.DirectConnection)
                worker.start();assert worker.wait(30000)
                assert not failures,failures
                decoded,unused,depth=load_image(filename)
                rgb=decoded.convertToFormat(QtGui.QImage.Format_RGB888)
                raw=image_bytes(rgb)
                packed=b"".join(raw[y*rgb.bytesPerLine():y*rgb.bytesPerLine()+137*3] for y in range(83))
                assert max(abs(a-b) for a,b in zip(full,packed))<=1
        assert context.makeCurrent(surface)
        print("PASS: Normal PNG/TIFF worker exports match the spatially filtered GPU result")

        source=fixture(128,128,lambda x,y: 65535 if ((x//16+y//16)%2) else 12000)
        engine.upload(source)
        maps={kind:engine.process(dict(DEFAULTS,strength=20),kind) for kind in MAPS}
        frame=engine.texture("preview-test",RGBA32F)
        textures=dict(resultMap=maps["normal"],normalMap=maps["normal"],dispMap=maps["displacement"],aoMap=maps["ao"],specMap=maps["specular"])
        uniforms=dict(viewportSize=(128.,128.),imageSize=(128.,128.),pan=(0.,0.),zoom=1.,rotation=(-.25,-.3),lightAngle=-.6,view3d=1,shape=1,directx=False)
        def draw(flags,shape=1,view=1):
            uniforms.update(zip(("useNormal","useDisplacement","useAO","useSpecular"),flags))
            uniforms.update(shape=shape,view3d=view)
            engine._target(frame)
            engine.display(engine.framebuffer.value,128,128,textures,uniforms)
            return engine.read(frame,0,0,128,128)
        for shape in range(3):
            base=draw((False,False,False,False),shape)
            for index in range(4):
                flags=[False]*4;flags[index]=True
                assert draw(flags,shape)!=base,(shape,index)
            variants=[draw(flags,shape) for flags in itertools.product((False,True),repeat=4)]
            assert len(set(variants))==16,shape
            assert draw((False,False,False,False),shape,0)==draw((True,True,True,True),shape,0)
            if "--snapshots" in sys.argv:
                raw=draw((True,True,True,True),shape)
                image=QtGui.QImage(raw,128,128,128*3,QtGui.QImage.Format_RGB888).copy().mirrored()
                image.save(str(Path(__file__).resolve().parents[1]/"work"/("combined-preview-%d.png"%shape)))
        print("PASS: each effect changes every shape; 16 distinct combinations per shape; 2D independent")
        # Uniform displacement must change the sphere silhouette, even with Normal disabled.
        engine.upload(fixture(128,128,lambda x,y:65535))
        textures["dispMap"]=engine.process(dict(DEFAULTS, disp_contrast=1.0),"displacement")
        # Disabled samplers still need valid texture names after upload releases textures.
        textures.update(resultMap=textures["dispMap"],normalMap=textures["dispMap"],aoMap=textures["dispMap"],specMap=textures["dispMap"])
        frame=engine.texture("preview-test",RGBA32F)
        a=draw((False,False,False,False));b=draw((False,True,False,False))
        background=a[:3]
        pixels_a=sum(a[i:i+3]!=background for i in range(0,len(a),3))
        pixels_b=sum(b[i:i+3]!=background for i in range(0,len(b),3))
        assert pixels_b>pixels_a*1.08,(pixels_a,pixels_b)
        print("PASS: Displacement changes silhouette without Normal; GPU: "+engine.gl.description)
    finally:
        engine.close();context.doneCurrent();surface.destroy()


if __name__=="__main__":
    run()

