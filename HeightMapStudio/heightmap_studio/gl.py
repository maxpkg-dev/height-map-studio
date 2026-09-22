"""Minimal Windows OpenGL 3.3 binding, independent of PySide binding versions.

Every object belongs to the current context. Call close before releasing it.
"""
import ctypes as C
import os
import math
from .qt import image_bytes

U, I, F, P = C.c_uint, C.c_int, C.c_float, C.c_void_p
TEXTURE, FLOAT, USHORT, UBYTE = 0x0DE1, 0x1406, 0x1403, 0x1401
RED, RGB, RGBA = 0x1903, 0x1907, 0x1908
R32F, RGBA32F, RGBA16 = 0x822E, 0x8814, 0x805B
FRAMEBUFFER, COLOR0 = 0x8D40, 0x8CE0


class GL:
    def __init__(self):
        self.dll = C.WinDLL("opengl32.dll")
        self.dll.wglGetProcAddress.restype = P
        self.dll.wglGetProcAddress.argtypes = [C.c_char_p]
        specifications = {
            "GetString": (C.c_char_p, U), "GetIntegerv": (None, U, P),
            "GetError": (U,), "Finish": (None,),
            "GenTextures": (None, I, P), "DeleteTextures": (None, I, P),
            "BindTexture": (None, U, U), "ActiveTexture": (None, U),
            "TexParameteri": (None, U, U, I), "PixelStorei": (None, U, I),
            "TexImage2D": (None, U, I, I, I, I, I, U, U, P),
            "GenFramebuffers": (None, I, P), "DeleteFramebuffers": (None, I, P),
            "BindFramebuffer": (None, U, U),
            "FramebufferTexture2D": (None, U, U, U, U, I),
            "CheckFramebufferStatus": (U, U),
            "GenVertexArrays": (None, I, P), "DeleteVertexArrays": (None, I, P),
            "BindVertexArray": (None, U), "CreateShader": (U, U),
            "ShaderSource": (None, U, I, P, P), "CompileShader": (None, U),
            "GetShaderiv": (None, U, U, P), "GetShaderInfoLog": (None, U, I, P, P),
            "DeleteShader": (None, U), "CreateProgram": (U,),
            "AttachShader": (None, U, U), "LinkProgram": (None, U),
            "GetProgramiv": (None, U, U, P), "GetProgramInfoLog": (None, U, I, P, P),
            "UseProgram": (None, U), "DeleteProgram": (None, U),
            "GetUniformLocation": (I, U, C.c_char_p),
            "Uniform1i": (None, I, I), "Uniform1f": (None, I, F),
            "Uniform2f": (None, I, F, F), "Uniform3f": (None, I, F, F, F),
            "Viewport": (None, I, I, I, I), "Disable": (None, U),
            "DrawArrays": (None, U, I, I), "ReadPixels": (None, I, I, I, I, U, U, P),
        }
        for short, signature in specifications.items():
            full = "gl" + short
            address = self.dll.wglGetProcAddress(full.encode("ascii"))
            if address in (None, 0, 1, 2, 3, C.c_void_p(-1).value):
                function = getattr(self.dll, full, None)
                if function is None:
                    raise RuntimeError("GPU: OpenGL 3.3 is required (%s is unavailable)." % full)
                address = C.cast(function, P).value
            setattr(self, short, C.WINFUNCTYPE(signature[0], *signature[1:])(address))
        version = self.GetString(0x1F02)
        if not version:
            raise RuntimeError("Could not create an OpenGL GPU context.")
        self.description = (self.GetString(0x1F01) or b"GPU").decode("utf8", "replace")

    def check(self, label):
        error = self.GetError()
        if error:
            raise RuntimeError("GPU %s: OpenGL error 0x%04x" % (label, error))


VERTEX = """#version 330 core
out vec2 uv;
void main() {
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    uv = p;
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
"""


class Engine:
    def __init__(self):
        self.gl = GL()
        self.textures = {}
        self.programs = {}
        self.width = self.height = 0
        self.framebuffer, self.vao = U(), U()
        self.gl.GenFramebuffers(1, C.byref(self.framebuffer))
        self.gl.GenVertexArrays(1, C.byref(self.vao))
        self.gl.BindVertexArray(self.vao.value)
        folder = os.path.join(os.path.dirname(__file__), "shaders")
        try:
            for label in ("height", "blur", "map", "display"):
                with open(os.path.join(folder, label + ".frag"), encoding="utf8") as source:
                    self.programs[label] = self._program(source.read())
        except Exception:
            self.close()
            raise

    def _program(self, fragment):
        gl = self.gl
        shaders = []
        program = 0
        try:
            for kind, source in ((0x8B31, VERTEX), (0x8B30, fragment)):
                shader = gl.CreateShader(kind)
                shaders.append(shader)
                data = C.c_char_p(source.encode("utf8"))
                gl.ShaderSource(shader, 1, C.byref(data), None)
                gl.CompileShader(shader)
                status = I()
                gl.GetShaderiv(shader, 0x8B81, C.byref(status))
                if not status.value:
                    log = C.create_string_buffer(8192)
                    gl.GetShaderInfoLog(shader, len(log), None, log)
                    raise RuntimeError(log.value.decode("utf8", "replace"))
            program = gl.CreateProgram()
            for shader in shaders:
                gl.AttachShader(program, shader)
            gl.LinkProgram(program)
            status = I()
            gl.GetProgramiv(program, 0x8B82, C.byref(status))
            if not status.value:
                log = C.create_string_buffer(8192)
                gl.GetProgramInfoLog(program, len(log), None, log)
                raise RuntimeError(log.value.decode("utf8", "replace"))
            return program
        except Exception:
            if program:
                gl.DeleteProgram(program)
            raise
        finally:
            for shader in shaders:
                gl.DeleteShader(shader)

    def texture(self, label, internal=R32F, data=None, wrap=False):
        gl = self.gl
        if label not in self.textures:
            texture = U()
            gl.GenTextures(1, C.byref(texture))
            self.textures[label] = texture.value
        texture = self.textures[label]
        gl.BindTexture(TEXTURE, texture)
        gl.TexParameteri(TEXTURE, 0x2801, 0x2601)
        gl.TexParameteri(TEXTURE, 0x2800, 0x2601)
        for axis in (0x2802, 0x2803):
            gl.TexParameteri(TEXTURE, axis, 0x2901 if wrap else 0x812F)
        gl.PixelStorei(0x0CF5, 1)
        buffer = C.create_string_buffer(data) if data is not None else None
        gl.TexImage2D(TEXTURE, 0, internal, self.width, self.height, 0,
                      RGBA if internal != R32F else RED,
                      USHORT if data is not None else FLOAT, buffer)
        gl.check("texture allocation")
        return texture

    def upload(self, image, wrap=False):
        self.release_textures()
        self.width, self.height = image.width(), image.height()
        limit = I()
        self.gl.GetIntegerv(0x0D33, C.byref(limit))
        if max(self.width, self.height) > limit.value:
            raise RuntimeError("Tile size exceeds the GPU texture limit.")
        self.texture("source", RGBA16, image_bytes(image), wrap)

    def release_textures(self):
        for texture in self.textures.values():
            self.gl.DeleteTextures(1, C.byref(U(texture)))
        self.textures.clear()

    def _target(self, texture):
        gl = self.gl
        gl.BindFramebuffer(FRAMEBUFFER, self.framebuffer.value)
        gl.FramebufferTexture2D(FRAMEBUFFER, COLOR0, TEXTURE, texture, 0)
        if gl.CheckFramebufferStatus(FRAMEBUFFER) != 0x8CD5:
            raise RuntimeError("The GPU does not support float32 render targets.")

    def _draw(self, label, textures, uniforms, width=None, height=None):
        gl = self.gl
        gl.Viewport(0, 0, width or self.width, height or self.height)
        for flag in (0x0B71, 0x0BE2, 0x0B44, 0x0C11, 0x8DB9):
            gl.Disable(flag)
        program = self.programs[label]
        gl.UseProgram(program)
        gl.BindVertexArray(self.vao.value)
        for index, (name, texture) in enumerate(textures.items()):
            gl.ActiveTexture(0x84C0 + index)
            gl.BindTexture(TEXTURE, texture)
            gl.Uniform1i(gl.GetUniformLocation(program, name.encode()), index)
        for name, value in uniforms.items():
            location = gl.GetUniformLocation(program, name.encode())
            if isinstance(value, (bool, int)):
                gl.Uniform1i(location, int(value))
            elif isinstance(value, tuple):
                getattr(gl, "Uniform%df" % len(value))(location, *value)
            else:
                gl.Uniform1f(location, value)
        gl.DrawArrays(0x0004, 0, 3)
        gl.check(label)

    def process(self, settings, kind, scale=(1.0, 1.0), wrap=None, bounds=None):
        wrap = settings["seamless"] if wrap is None else wrap
        if bounds is None:
            bounds = ((0.5 / self.width, 0.5 / self.height),
                      (1.0 - 0.5 / self.width, 1.0 - 0.5 / self.height))
        edges = dict(boundsMin=bounds[0], boundsMax=bounds[1], clampBounds=not settings["seamless"])
        height = self.texture("height", wrap=wrap)
        self._target(height)
        self._draw("height", {"source": self.textures["source"]}, {"invertHeight": settings["invert"]})
        if kind == "normal" and settings["detail_size"] > 0.0:
            # Eight line directions form a nearly circular 16-sided footprint.
            # Opening then closing creates plateaus without square-kernel corners.
            radius = settings["detail_size"] * 0.5 * math.tan(math.pi / 16.0)
            index = 0
            for mode, multiple in ((1, 1.0), (2, 2.0), (1, 1.0)):
                for direction in range(8):
                    angle = direction * math.pi / 8.0
                    target = self.texture("detail%d" % (index % 2), wrap=wrap)
                    self._target(target)
                    self._draw("blur", {"heightMap": height}, dict(edges,
                        axis=(math.cos(angle) / scale[0], math.sin(angle) / scale[1]),
                        filterMode=mode, filterRadius=float(radius * multiple),
                        texel=(1.0 / self.width, 1.0 / self.height)))
                    height = target
                    index += 1
        blur = settings["blur"] if kind == "normal" else settings["disp_blur"] if kind == "displacement" else 0.0
        if blur > 0.0:
            for index, axis in enumerate(((1.0, 0.0), (0.0, 1.0))):
                target = self.texture("blur%d" % index, wrap=wrap)
                self._target(target)
                sigma = blur / scale[index]
                self._draw("blur", {"heightMap": height},
                           dict(edges, axis=axis, sigma=float(sigma), filterMode=0,
                                texel=(1.0 / self.width, 1.0 / self.height)))
                height = target
        output = self.texture(kind, RGBA32F, wrap=wrap)
        self._target(output)
        self._draw("map", {"heightMap": height}, dict(edges,
            mode=("normal", "displacement", "ao", "specular").index(kind),
            texel=(1.0 / self.width, 1.0 / self.height), pixelScale=scale,
            strength=float(settings["strength"]), directx=settings["directx"],
            contrast=float(settings["disp_contrast"] if kind == "displacement" else settings["spec_contrast"]),
            level=float(settings["disp_level"] if kind == "displacement" else settings["spec_brightness"]),
            radius=float(settings["ao_radius"]), aoStrength=float(settings["ao_strength"]),
            aoThreshold=float(settings["ao_threshold"]),
            specCompress=float(settings["spec_compress"])))
        return output

    def read(self, texture, x, y, width, height, channels=3, depth=8):
        self._target(texture)
        self.gl.PixelStorei(0x0D05, 1)
        buffer = C.create_string_buffer(width * height * channels * (depth // 8))
        self.gl.ReadPixels(x, y, width, height, RGB if channels == 3 else RED,
                           USHORT if depth == 16 else UBYTE, buffer)
        self.gl.check("readback")
        return buffer.raw

    def display(self, framebuffer, width, height, maps, uniforms):
        self.gl.BindFramebuffer(FRAMEBUFFER, framebuffer)
        self._draw("display", maps, uniforms, width, height)

    def close(self):
        self.release_textures()
        for program in self.programs.values():
            self.gl.DeleteProgram(program)
        self.programs.clear()
        self.gl.DeleteFramebuffers(1, C.byref(self.framebuffer))
        self.gl.DeleteVertexArrays(1, C.byref(self.vao))
