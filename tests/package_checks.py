"""Static official-packager inputs and isolated sample-load guard checks."""
import ast
import configparser
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
import uuid
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
config = configparser.ConfigParser(interpolation=None)
config_bytes = (root / "maxpkg-packager.ini").read_bytes()
config.read_string(config_bytes.decode("utf16" if config_bytes.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"))
settings = config["settings"]
assert settings["license"] == "Free"
uuid.UUID(settings["packageGuid"])
assert settings["entry"] == r"HeightMapStudio\Launch.ms"
assert settings["compileEntry"] == "false"
assert Path(settings["outputFolder"]).resolve() == (root / "dist").resolve()
files = config["files"]
relative = set()
for index in range(1, int(files["count"]) + 1):
    source = Path(files[str(index) + "_abs"])
    rel = files[str(index) + "_rel"]
    assert source.is_file() and source.resolve() == (root / rel).resolve()
    assert not any(part in ("tests", "work", "dist", "__pycache__") for part in source.parts)
    relative.add(rel)
assert r"HeightMapStudio\Sample_height_16.png" in relative
assert r"HeightMapStudio\heightmap_studio\accelerators.py" in relative
assert settings["entry"] in relative
expected = {str(p.relative_to(root)) for p in (root / "HeightMapStudio").rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc" and p.name != "TEST_RESULTS.md"}
assert relative == expected
hashes = {
    "maxpkg-packager.ms": "8be1c68508e2297f0cd5a89c9d51c3aefbd1670db5901249274c842d33bbd16b",
    "_install.ms": "237663e6ae926a54605f5b0b52f7c9368903445df21a642e001c2efd7d0c883d",
    "_uninstall.ms": "c1082a7b3467ef0dd627b5722d54cb726028e317640821f5542528064d05a9cb"}
for name, digest in hashes.items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
svg = ET.parse(str(root / "maxpkg-icon.svg")).getroot()
assert svg.attrib["viewBox"] == "0 0 64 64"
ui_path = root / "HeightMapStudio/heightmap_studio/ui.py"
tree = ast.parse(ui_path.read_text(encoding="utf8"))
studio = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Studio")
namespace = {"os": os, "__file__": str(ui_path)}
for name in ("load_demo_if_empty", "loaded"):
    method = next(n for n in studio.body if isinstance(n, ast.FunctionDef) and n.name == name)
    unit = ast.parse("")
    unit.body = [method]
    exec(compile(unit, str(ui_path), "exec"), namespace)
calls = []
window = SimpleNamespace(closing=False, generation=0, image=None, load=calls.append)
namespace["load_demo_if_empty"](window)
assert calls == [str(root / "HeightMapStudio/Sample_height_16.png")]
for generation, image, closing in ((1, None, False), (0, object(), False), (0, None, True)):
    window.generation, window.image, window.closing = generation, image, closing
    namespace["load_demo_if_empty"](window)
    assert len(calls) == 1
window.generation, window.image, window.closing = 2, "user image", False
namespace["loaded"](window, 1, "sample", "stale image", None, 16)
assert window.image == "user image"
print("PASS: official tooling hashes, configuration, complete runtime/sample allowlist, SVG, demo guards and stale-load rejection")
