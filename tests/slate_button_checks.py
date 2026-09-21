"""Bounded checks in an owned Slate View; no dialogs or global replacements."""
import json
import shutil
import tempfile
from pathlib import Path
from pymxs import runtime as rt
from heightmap_studio import ui, saved_maps
from heightmap_studio.qt import QtCore, QtWidgets


def run():
    root = Path(__file__).resolve().parents[1]
    old_view, was_open = int(rt.sme.activeView), bool(rt.sme.IsOpen())
    view_index = None
    window = None
    results = []
    try:
        with tempfile.TemporaryDirectory(prefix="hms_slate_") as folder:
            folder = Path(folder)
            store = QtCore.QSettings(str(folder / "test.ini"), QtCore.QSettings.IniFormat)
            window = ui.Studio(geometry_settings=store)
            window.generation = 1
            window.filename = str(folder / "source.png")
            window.export_source = window.filename
            assert isinstance(window.add_slate, QtWidgets.QPushButton)
            window.tabs.setCurrentIndex(3)
            for check in window.map_checks.values():
                check.setChecked(False)
            window.add_selected_to_slate()
            assert window.status.text().startswith("Select maps")
            window.map_checks["normal"].setChecked(True)
            window.map_checks["ao"].setChecked(True)
            window.add_selected_to_slate()
            assert "Missing: Normal, AO" in window.status.text()
            results.append("empty selection and all missing: nonmodal status, no Slate mutation")
            normal = folder / "custom-normal.png"
            ao = folder / "custom-ao.png"
            for path in (normal, ao):
                shutil.copyfile(str(root / "HeightMapStudio/Sample_height_16.png"), str(path))
            rt.sme.Open()
            view_index = int(rt.sme.CreateView("HMS_BUTTON_OWNED_TEST"))
            rt.sme.activeView = view_index
            view = rt.sme.GetView(view_index)
            old = view.CreateNode(rt.Bitmaptexture(name="Existing test node"), rt.Point2(20, 30))
            old_position = (float(old.position.x), float(old.position.y))
            window.export_completed([("normal", str(normal)), ("ao", str(ao))], 0.1)
            assert view.GetNumNodes() == 1
            results.append("export completion remembers custom paths without adding nodes")
            window.auto_output.setChecked(False)
            window.add_selected_to_slate()
            assert window.status.text() == "Added: Normal, AO"
            selected = list(view.GetSelectedNodes())
            assert len(selected) == 2
            selected.sort(key=lambda n: n.position.y)
            assert selected[0].position.x == selected[1].position.x
            assert selected[1].position.y - selected[0].position.y >= selected[0].height + 79
            assert (float(old.position.x), float(old.position.y)) == old_position
            assert {str(n.reference.filename) for n in selected} == {str(normal), str(ao)}
            results.append("two checked maps added despite Specular tab; exact paths; vertical nonoverlapping nodes selected; old node unchanged")
            ao.unlink()
            window.add_selected_to_slate()
            assert window.status.text() == "Added: Normal | Missing: AO"
            assert view.GetNumNodes() == 4 and len(view.GetSelectedNodes()) == 1
            results.append("partial availability adds only existing checked files and names missing AO")
            store.sync()
            reopened_store = QtCore.QSettings(str(folder / "test.ini"), QtCore.QSettings.IniFormat)
            files, missing = saved_maps.resolve(reopened_store, window.filename, ["normal", "ao"], ".jpg", False)
            assert files == [("normal", str(normal))] and missing == ["ao"]
            other = str(folder / "other.png")
            beside = folder / "other_specular.png"
            shutil.copyfile(str(normal), str(beside))
            assert saved_maps.resolve(store, other, ["specular"], ".png", True) == ([("specular", str(beside))], [])
            assert saved_maps.resolve(store, other, ["normal"], ".png", False) == ([], ["normal"])
            results.append("persisted custom paths; separate source histories; beside-source discovery")
            assert window.export_job is None
    finally:
        if window is not None:
            window.close()
        if view_index is not None:
            rt.sme.DeleteView(view_index, False)
        if 0 < old_view <= rt.sme.GetNumViews():
            rt.sme.activeView = old_view
        if not was_open:
            rt.sme.Close()
    report = dict(status="passed", checks=results, cleanup="owned View removed; original Slate View/open state restored")
    (root / "work/slate_button_checks.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    rt.hmsDiagnostic = json.dumps(report)


run()
