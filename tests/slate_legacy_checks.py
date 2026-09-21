"""Isolated API contract checks; does not run 3ds Max or modify a live scene."""
import contextlib
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bridge", str(root / "HeightMapStudio/heightmap_studio/maxbridge.py"))
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class View:
    def __init__(self):
        self.nodes = []
        self.selected = []
        self.framed = False

    def GetNumNodes(self):
        return len(self.nodes)

    def GetNode(self, index):
        return self.nodes[index - 1]

    def CreateNode(self, texture, position):
        assert position[0] == "byref"
        node = SimpleNamespace(position=position[1], reference=texture)
        self.nodes.append(node)
        return node, position[1]

    def SetSelectedNodes(self, refs):
        self.selected = refs

    def ZoomExtents(self, type):
        assert type == "selected"
        self.framed = True


class Slate:
    def __init__(self):
        self.activeView = 0
        self.views = []

    def Open(self):
        pass

    def GetNumViews(self):
        return len(self.views)

    def CreateView(self, name):
        self.views.append(View())
        return len(self.views)

    def GetView(self, index):
        return self.views[index - 1]


slate = Slate()
runtime = SimpleNamespace(undefined=None, sme=slate, Bitmaptexture=SimpleNamespace,
    openBitmap=lambda path, gamma: SimpleNamespace(inputGammaValue=gamma),
    Point2=lambda x, y: SimpleNamespace(x=x, y=y), Array=lambda *items: list(items), Name=lambda value: value)
sys.modules["pymxs"] = SimpleNamespace(runtime=runtime, byref=lambda value: ("byref", value),
    undo=lambda *args: contextlib.nullcontext())
with tempfile.TemporaryDirectory() as folder:
    bitmap = Path(folder) / "map.png"
    bitmap.write_bytes(b"test fixture; decoding is outside this contract test")
    nodes = bridge.add_to_slate([("normal", str(bitmap)), ("ao", str(bitmap))])
    view = slate.GetView(1)
    assert len(nodes) == 2 and view.framed and len(view.selected) == 2
    assert nodes[1].position.y - nodes[0].position.y == 220
    original = (nodes[0].position.x, nodes[0].position.y)
    bridge.add_to_slate([("normal", str(bitmap))])
    assert (nodes[0].position.x, nodes[0].position.y) == original
    assert view.nodes[-1].position.x == 520
    def fail(*args):
        raise RuntimeError("node creation unavailable")
    view.CreateNode = fail
    try:
        bridge.add_to_slate([("normal", str(bitmap))])
    except RuntimeError as exc:
        assert "Create Bitmap node" in str(exc) and "node creation unavailable" in str(exc)
    else:
        raise AssertionError("Missing stage-specific error")
print("PASS: absent modern color manager/dimensions, empty/existing Views, byref tuple, vertical placement, selection/framing and operation-specific failures")
