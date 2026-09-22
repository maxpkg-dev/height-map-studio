# Test scripts

These scripts run inside 3ds Max and are not an unattended test suite. Read each
script before execution; use only test-owned files and Slate Views.

Current narrow regression: `slate_button_checks.py` covers separate Save/Add to
Slate behavior, saved paths, missing files, and vertical node layout.
`promotion_checks.py` covers the promotional strip without opening links.

Historical UI scripts (`single_save_checks.py`, `ui_release_checks.py`,
`english_ui_check.py`, `manual_save_checks.py`) target earlier UI revisions and
must be adapted before reuse. Earlier export harnesses pass the now-removed
automatic-Slate argument. They are retained as development evidence, not claimed
as passing current regression tests. Do not run all files as a batch.

Current standalone checks (run with the bundled Max 2022 Python 3.7):
- `displacement_blur_checks.py`: real Qt controls and GPU blur, independent maps,
  preview scaling, all 65536 levels at zero blur, and tiled export borders.
- `map_controls_checks.py`: tab-local Reset on every map, AO height-difference
  threshold, Specular compression after clipping, and worker PNG/TIFF exports
  across a tile boundary. Also runs with bundled Max 2027 Python or inside Max
  using isolated images, temporary settings and temporary output files.
- `accelerator_checks.py`: isolated focus-adapter lifecycle and capability behavior.
- `qt5_focus_checks.py`: real Qt5 widget events with a test accelerator-state object.
- `source_folder_checks.py`: real Qt5 context-menu dispatch without opening Explorer.
- `slate_legacy_checks.py`: isolated legacy Slate API contracts, not a live-Max test.
- `package_checks.py`: official tooling hashes, allowlist, icon and sample load guards.
