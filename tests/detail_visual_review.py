"""Compare square and round morphological flattening with ordinary Blur."""
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from map_controls_checks import fixture
from heightmap_studio.qt import QtCore,QtGui,QtWidgets,gl_format
from heightmap_studio.gl import Engine,RGBA32F
from heightmap_studio.model import DEFAULTS
from heightmap_studio.imageio import load_image


def render(output):
    app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    surface=QtGui.QOffscreenSurface();surface.setFormat(gl_format());surface.create()
    context=QtGui.QOpenGLContext();context.setFormat(gl_format())
    assert context.create() and context.makeCurrent(surface)
    engine=Engine()
    root=Path(__file__).resolve().parents[1]
    sample,unused,depth=load_image(str(root/'HeightMapStudio/Sample_height_16.png'))
    irregular=fixture(512,512,lambda x,y:32768+10000*math.sin(x*.029+math.cos(y*.019))*math.cos(y*.025)+7000*math.sin(x*.21+y*.08)*math.cos(y*.17-x*.03)+4000*math.sin(x*1.1+y*.7))
    try:
        for name,source in (("Sample",sample),("Irregular",irregular)):
            sheet=QtGui.QImage(1336,886,QtGui.QImage.Format_RGB32);sheet.fill(QtGui.QColor('#20252e'))
            painter=QtGui.QPainter(sheet)
            painter.setPen(QtGui.QColor('#ffffff'))
            painter.setFont(QtGui.QFont('Segoe UI',13))
            painter.drawText(16,26,name+' | Detail removal comparison')
            painter.setFont(QtGui.QFont('Segoe UI',9))
            painter.drawText(16,48,'Same source and Strength 10. Rows: processed height / normal map / Normal-only 3D preview.')
            for col,(label,size,blur,square) in enumerate((("Original",0,0,False),("Old square 32",32,0,True),("Round 32",32,0,False),("Round 64",64,0,False),("Blur 16",0,16,False))):
                engine.upload(source,True)
                normal=engine.process(dict(DEFAULTS,strength=10,detail_size=0 if square else size,blur=blur),'normal')
                height=engine.textures['detail1' if size and not square else 'blur1' if blur else 'height']
                if square:
                    edges=dict(boundsMin=(.5/512,.5/512),boundsMax=(1-.5/512,1-.5/512),clampBounds=False)
                    for index,(axis,mode,multiple) in enumerate((((1.,0.),1,1),((0.,1.),1,1),((1.,0.),2,2),((0.,1.),2,2),((1.,0.),1,1),((0.,1.),1,1))):
                        target=engine.texture('square%d'%(index%2),wrap=True);engine._target(target)
                        engine._draw('blur',{'heightMap':height},dict(edges,axis=axis,filterMode=mode,filterRadius=float(size*.5*multiple),texel=(1/512.,1/512.)))
                        height=target
                    normal=engine.texture('normal',RGBA32F,wrap=True);engine._target(normal)
                    engine._draw('map',{'heightMap':height},dict(edges,mode=0,strength=10.,directx=False,texel=(1/512.,1/512.),pixelScale=(1.,1.)))
                raw_height=engine.read(height,0,0,512,512,1,8)
                gray=QtGui.QImage(raw_height,512,512,512,QtGui.QImage.Format_Grayscale8).copy()
                painter.drawImage(QtCore.QRect(16+col*264,88,248,248),gray)
                raw=engine.read(normal,0,0,512,512)
                image=QtGui.QImage(raw,512,512,1536,QtGui.QImage.Format_RGB888).copy()
                image.save(str(output/('Normal-'+name+'-'+label.replace(' ','-')+'.png')))
                painter.drawText(16+col*264,76,label)
                painter.drawImage(QtCore.QRect(16+col*264,350,248,248),image)
                frame=engine.texture('review',RGBA32F)
                engine._target(frame)
                engine.display(engine.framebuffer.value,512,512,
                    dict(resultMap=normal,normalMap=normal,aoMap=normal,specMap=normal,dispMap=normal),
                    dict(viewportSize=(512.,512.),imageSize=(512.,512.),pan=(0.,0.),zoom=1.,rotation=(0.,0.),lightAngle=-.6,view3d=1,shape=0,directx=False,useNormal=True,useDisplacement=False,useAO=False,useSpecular=False))
                raw=engine.read(frame,0,0,512,512)
                shaded=QtGui.QImage(raw,512,512,1536,QtGui.QImage.Format_RGB888).copy().mirrored()
                painter.drawImage(QtCore.QRect(16+col*264,612,248,248),shaded)
            painter.end()
            filename=output/('Normal-Detail-'+name+'-Comparison.png')
            assert sheet.save(str(filename))
            print(filename)
    finally:
        engine.close();context.doneCurrent();surface.destroy()


if __name__=='__main__':
    render(sys.argv[1])
