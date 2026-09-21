"""Remember successful exports per source, including custom filenames."""
import hashlib
import json
import os


def key(source):
    path = os.path.normcase(os.path.realpath(source))
    return "saved_maps/" + hashlib.sha256(path.encode("utf8")).hexdigest()


def remember(store, source, files):
    paths = read(store, source)
    paths.update({kind: os.path.abspath(filename) for kind, filename in files})
    store.setValue(key(source), json.dumps(paths))
    store.sync()


def read(store, source):
    try:
        paths = json.loads(str(store.value(key(source), "{}")))
        return {k: v for k, v in paths.items() if isinstance(v, str)} if isinstance(paths, dict) else {}
    except (ValueError, TypeError):
        return {}


def resolve(store, source, kinds, extension, beside_source):
    paths = read(store, source)
    stem = os.path.splitext(source)[0]
    available, missing = [], []
    for kind in kinds:
        filename = paths.get(kind)
        if filename is None and beside_source:
            filename = stem + "_" + kind + extension
        if filename and os.path.isfile(filename):
            available.append((kind, filename))
        else:
            missing.append(kind)
    return available, missing
