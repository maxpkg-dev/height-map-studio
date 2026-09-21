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
