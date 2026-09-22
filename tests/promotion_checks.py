"""Light Max UI check; no browser, Settings dialog, export, or GPU rebuild."""
import json
from pathlib import Path
from pymxs import runtime as rt
from heightmap_studio import ui
from heightmap_studio.promotion import PromotionStrip, DONATION, PROMOTIONS, ORANGE
from heightmap_studio.qt import QtCore

root = Path(__file__).resolve().parents[1]
window = ui._window
assert window is not None and not window.load_jobs and not window.export_job
strip = getattr(window, "promotion", None)
if strip is None:
    old_height = window.height()
    strip = PromotionStrip(window)
    window.promotion = strip
    window.layout().insertWidget(window.layout().indexOf(window.preview) + 1, strip)
    window.resize(window.width(), old_height + 34)
    strip.show()
window.layout().activate()
assert window.layout().indexOf(strip) == window.layout().indexOf(window.preview) + 1
assert strip.height() == 26 and strip.donate.isVisible()
assert strip.donate.text() == "\u2665 Donate"
assert strip.donate.size().width() == 94 and strip.donate.size().height() == 26
assert ORANGE in strip.donate.styleSheet() and ORANGE in strip.link.styleSheet()
assert strip.timer.isActive() and strip.timer.interval() == 30000
assert len(strip.findChildren(QtCore.QTimer)) == 1

# Exercise every timeout without opening a URL or disturbing the live row.
probe = PromotionStrip()
records = []
for unused in range(2 * len(PROMOTIONS)):
    records.append(probe.link.record)
    probe.timer.timeout.emit()
assert records[::2] == [DONATION] * len(PROMOTIONS)
assert records[1::2] == list(PROMOTIONS)
assert probe.link.record == DONATION
probe.deleteLater()
strip.hide()
assert not strip.timer.isActive()
strip.show()
assert strip.timer.isActive()
window.layout().activate()
result = dict(status="passed", timer_ms=strip.timer.interval(), strip_height=strip.height(),
              preview=[window.preview.width(), window.preview.height()],
              records=records, persistent_donate=True, browser_opened=False,
              settings_tested=False, live_upgrade_without_gpu_reload=True)
(root / "work" / "promotion_checks.json").write_text(json.dumps(result, indent=2), encoding="utf8")
rt.hmsDiagnostic = json.dumps(result)
