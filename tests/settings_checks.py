"""Non-modal Settings tests; never activate external links or file dialogs."""
import json
import os
from heightmap_studio import ui, __version__
from heightmap_studio.qt import QtCore, QtWidgets
from PySide6 import QtTest


def run_settings_checks():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    store = QtCore.QSettings(os.path.join(root, "work", "settings_dialog_checks.ini"), QtCore.QSettings.IniFormat)
    store.clear()
    current = ui._window
    before = (current.filename, dict(current.settings), current.mode.currentIndex())
    window = ui.Studio(current.parentWidget(), geometry_settings=store)
    restored = None
    report = {"passed": []}
    try:
        window.generation = 1
        window.show()
        window.show_settings()
        dialog = window.settings_dialog
        assert dialog.parentWidget() is window
        assert not dialog.isModal()
        window.show_settings()
        assert window.settings_dialog is dialog
        assert len(dialog.maximums) == 8
        labels = [x.text() for x in dialog.findChildren(QtWidgets.QLabel)]
        assert "Lukianenko Vasyl" in labels and __version__ in labels
        for label, url in zip(dialog.links, ("https://3dground.net", "https://maxpkg.dev")):
            assert url in label.text() and label.openExternalLinks()
        field = dialog.maximums["strength"]
        field.setFocus()
        field.selectAll()
        QtTest.QTest.keyClicks(field, "1000")
        QtTest.QTest.keyClick(field, QtCore.Qt.Key_Return)
        parameter = window.parameters["strength"]
        assert field.value() == 1000 and parameter.slider.maximum() == 100000
        parameter.set_value(1234.56)
        assert window.settings["strength"] == 1234.56 and parameter.spin.value() == 1234.56
        field.setValue(10)
        assert parameter.slider.maximum() == 1000 and parameter.slider.value() == 1000
        assert window.settings["strength"] == 1234.56 and parameter.spin.value() == 1234.56
        report["passed"].append("typed Strength slider maximum 1000; manual 1234.56 preserved when maximum shrinks to10")
        for key, value in (("disp_contrast", 1000), ("disp_level", 1000), ("ao_strength", 1000), ("spec_brightness", 1000), ("spec_contrast", 1000)):
            dialog.maximums[key].setValue(value)
            assert window.parameters[key].slider.maximum() == 100000
        assert window.parameters["disp_level"].slider.minimum() == -100
        assert window.parameters["spec_brightness"].slider.minimum() == -100
        assert dialog.maximums["blur"].maximum() == 16
        assert dialog.maximums["ao_radius"].maximum() == 128
        field.lineEdit().setText("nan")
        assert not field.hasAcceptableInput()
        field.interpretText()
        assert window.parameters["strength"].slider.maximum() == 1000
        report["passed"].append("all editable ranges apply; signed minima retained; blur16/radius128 limits; nonfinite text rejected")
        dialog.close()
        window.show_settings()
        assert window.settings_dialog is dialog and dialog.isVisible()
        restored = ui.Studio(geometry_settings=store)
        assert restored.parameters["strength"].slider.maximum() == 1000
        assert restored.parameters["ao_strength"].slider.maximum() == 100000
        assert not restored.add_slate.isChecked()
        assert restored.settings["disp_contrast"] == 0.15
        assert restored.parameters["disp_contrast"].spin.value() == 0.15
        set_groups = [group for group in restored.findChildren(QtWidgets.QGroupBox) if group.title() == "Set"]
        assert len(set_groups) == 1 and set_groups[0].height() == restored.save_button.height() + 8 == 42
        assert set_groups[0].parentWidget().height() == 50
        assert [check.text() for check in restored.map_checks.values()] == ["Normal", "Displace", "AO", "Specular"]
        assert window.settings_button.height() == window.open_button.height()
        assert window.settings_button.width() == window.open_button.width()
        report["passed"].append("Settings single-window close/reopen, persisted ranges, exact About/version/links and matching launch buttons")
        QtWidgets.QApplication.processEvents()
        dialog.grab().save(os.path.join(root, "work", "settings_dialog.png"))
        assert before == (current.filename, dict(current.settings), current.mode.currentIndex())
        report["passed"].append("user image, map settings and view mode preserved")
        with open(os.path.join(root, "work", "settings_checks.json"), "w") as stream:
            json.dump(report, stream, indent=2)
    finally:
        if restored is not None:
            restored.close()
        window.close()


run_settings_checks()
