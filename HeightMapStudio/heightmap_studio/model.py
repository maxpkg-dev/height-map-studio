"""Shared, serializable processing settings; radii are source-image pixels."""
import math

MAPS = ("normal", "displacement", "ao", "specular")
DEFAULTS = dict(strength=3.0, blur=0.0, detail_size=0.0, disp_contrast=1.0, disp_level=0.0, disp_blur=0.0,
                ao_strength=2.0, ao_radius=24.0, ao_threshold=0.0, spec_brightness=0.0,
                spec_contrast=1.0, spec_compress=0.0, directx=False, invert=False, seamless=True)


def halo(settings, kind):
    if kind == "normal":
        radius = settings["detail_size"] * 0.5 * math.tan(math.pi / 16.0)
        support = sum(math.ceil(abs(math.cos(k * math.pi / 8.0)) * radius * multiple) + 1
                      for multiple in (1, 2, 1) for k in range(8)) if radius else 0
        return int(math.ceil(settings["blur"] * 3.0)) + int(support) + 2
    if kind == "displacement":
        return int(math.ceil(settings["disp_blur"] * 3.0)) + 1
    if kind == "ao":
        return int(math.ceil(settings["ao_radius"])) + 2
    return 1


def tiles(width, height, size=1024):
    for y in range(0, height, size):
        for x in range(0, width, size):
            yield x, y, min(size, width - x), min(size, height - y)
