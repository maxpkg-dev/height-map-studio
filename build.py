"""Create the portable release ZIP from this project. Python 3.7+."""
import hashlib
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parent
source = root / "HeightMapStudio"
target = root / "dist" / "HeightMapStudio-1.0.0.zip"
target.parent.mkdir(exist_ok=True)
with ZipFile(str(target), "w", ZIP_DEFLATED) as archive:
    for filename in sorted(source.rglob("*")):
        if filename.is_file() and "__pycache__" not in filename.parts and filename.suffix != ".pyc":
            if filename.suffix in (".py", ".ms", ".md", ".frag"):
                content = filename.read_text(encoding="utf8")
                if re.search(r"[\u0400-\u052f]", content):
                    raise ValueError("English-only release: unexpected Cyrillic text in " + str(filename))
            if filename.suffix == ".py":
                compile(filename.read_text(encoding="utf8"), str(filename), "exec")
            archive.write(str(filename), str(filename.relative_to(root)))
with ZipFile(str(target)) as archive:
    assert archive.testzip() is None
    assert "HeightMapStudio/Launch.ms" in archive.namelist()
    print("Files:", len(archive.namelist()))
print(str(target))
print("SHA256", hashlib.sha256(target.read_bytes()).hexdigest())
