"""Select and frame generated nodes in a test-owned populated Slate View."""
import importlib
import json
import os
from pymxs import runtime as rt
from heightmap_studio import maxbridge


class SlateFocusChecks:
    def __init__(self):
        self.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.previous_view = int(rt.sme.activeView)
        self.was_open = bool(rt.sme.IsOpen())
        self.view_count = int(rt.sme.GetNumViews())
        self.report = {"passed": []}
        rt.sme.Open()
        self.index = rt.sme.CreateView("HMS_SELECTION_FRAME_TEST")
        rt.sme.activeView = self.index
        self.view = rt.sme.GetView(self.index)
        self.old_texture = rt.Bitmaptexture(name="Existing node - must remain untouched")
        self.old_node = self.view.CreateNode(self.old_texture, rt.Point2(-15000, -12000))
        self.old_position = (float(self.old_node.position.x), float(self.old_node.position.y))
        self.view.SetSelectedNodes(rt.Array(self.old_texture))
        self.view.ZoomExtents(type=rt.Name("selected"))
        self.files = [(kind, os.path.join(self.root, "work", "sample_" + kind + ".jpg")) for kind in ("normal", "ao", "specular")]

    def selected_refs(self):
        return [node.reference for node in self.view.GetSelectedNodes()]

    def validate(self, expected):
        refs = self.selected_refs()
        assert len(refs) == len(expected)
        assert all(node.reference in refs for node in expected)
        assert self.old_texture not in refs
        assert (float(self.old_node.position.x), float(self.old_node.position.y)) == self.old_position
        assert self.view.GetNodeByRef(self.old_texture) != rt.undefined

    def single(self):
        self.single_nodes = maxbridge.add_to_slate(self.files[:1])
        self.validate(self.single_nodes)
        assert self.view.GetNumNodes() == 2
        self.report["passed"].append("one new selected node; distant old node deselected and unmoved")

    def multiple(self):
        self.multi_nodes = maxbridge.add_to_slate(self.files[1:])
        self.validate(self.multi_nodes)
        assert self.single_nodes[0].reference not in self.selected_refs()
        assert self.view.GetNumNodes() == 4
        before = self.selected_refs()
        assert maxbridge.add_to_slate([]) == []
        assert self.selected_refs() == before
        self.report["passed"].append("all new set nodes selected; earlier nodes deselected and preserved; empty input has no effects")

    def cleanup(self):
        rt.sme.DeleteView(self.index, False)
        if 0 < self.previous_view <= rt.sme.GetNumViews():
            rt.sme.activeView = self.previous_view
        if not self.was_open:
            rt.sme.Close()
        assert int(rt.sme.GetNumViews()) == self.view_count
        self.report["passed"].append("only test-owned View removed; previous View/open state restored")
        with open(os.path.join(self.root, "work", "slate_focus_checks.json"), "w") as stream:
            json.dump(self.report, stream, indent=2)


importlib.reload(maxbridge)
_hms_slate_focus = SlateFocusChecks()
_hms_slate_focus.single()
