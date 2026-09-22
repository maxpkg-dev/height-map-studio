"""Slider defaults and explicit processing limits, independent of preferences."""
import math

# Each entry is (key, label, minimum, default slider maximum, processing maximum).
GROUPS = (
    ("Normal", (("strength", "Strength", 0, 20, 1000000), ("blur", "Blur", 0, 16, 16), ("detail_size", "Detail size", 0, 64, 64))),
    ("Displacement", (("disp_contrast", "Contrast", 0, 4, 1000000), ("disp_level", "Level", -1, 1, 1000000), ("disp_blur", "Blur", 0, 16, 16))),
    ("AO", (("ao_strength", "Strength", 0, 10, 1000000), ("ao_radius", "Radius", 1, 128, 128), ("ao_threshold", "Threshold", 0, 1, 1))),
    ("Specular", (("spec_brightness", "Brightness", -1, 1, 1000000), ("spec_contrast", "Contrast", 0, 4, 1000000), ("spec_compress", "Compress", 0, 1, 1))))
FIELDS = {entry[0]: entry for title, entries in GROUPS for entry in entries}


def validate_maximum(key, value):
    value = float(value)
    unused, label, minimum, default, maximum = FIELDS[key]
    if not math.isfinite(value) or value <= minimum or value > maximum:
        raise ValueError("%s maximum must be greater than %g and no greater than %g." % (label, minimum, maximum))
    value = round(value, 2)
    if value <= minimum:
        raise ValueError("Maximum must leave at least one 0.01 slider step.")
    return value


def saved_maximum(store, key):
    default = FIELDS[key][3]
    try:
        return validate_maximum(key, store.value("slider_max/" + key, default))
    except (TypeError, ValueError, OverflowError):
        return float(default)
