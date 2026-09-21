# -*- coding: utf-8 -*-
"""Main-thread-only Slate integration. No generated MAXScript strings."""
import os


def node_extent(node, axis, legacy):
    # Older Slate interfaces expose positions but not node dimensions.
    try:
        return float(getattr(node, axis))
    except AttributeError:
        return legacy
    except RuntimeError as exc:
        message = str(exc).lower()
        if "unknown property" in message or "has no attribute" in message:
            return legacy
        raise


def add_to_slate(files, progress=None):
    if not files:
        return []
    import pymxs
    rt = pymxs.runtime
    textures = []
    pipeline = getattr(rt, "ColorPipelineMgr", None)
    ocio = pipeline is not None and pipeline != rt.undefined and "ocio" in str(pipeline.Mode).lower()
    raw_space = str(pipeline.DataColorSpace) if ocio else None
    if ocio and not raw_space:
        raise RuntimeError("The OCIO configuration has no Data Color Space.")
    # Validate all files and their color interpretation before changing the View.
    for kind, filename in files:
        if not os.path.isfile(filename):
            raise RuntimeError("File not found: " + filename)
        bitmap = rt.openBitmap(filename, colorSpace=raw_space) if ocio else rt.openBitmap(filename, gamma=1.0)
        if bitmap == rt.undefined:
            raise RuntimeError("3ds Max could not read: " + filename)
        if ocio:
            if str(bitmap.colorSpace) != raw_space:
                raise RuntimeError("3ds Max did not apply Raw/Data Color Space: " + filename)
        elif abs(float(bitmap.inputGammaValue) - 1.0) > 0.0001:
            raise RuntimeError("3ds Max did not apply gamma 1.0: " + filename)
        texture = rt.Bitmaptexture()
        texture.bitmap = bitmap
        texture.name = os.path.splitext(os.path.basename(filename))[0]
        textures.append(texture)
    def call(stage, operation, *args, **kwargs):
        if progress is not None:
            progress(stage)
        try:
            return operation(*args, **kwargs)
        except (RuntimeError, AttributeError, TypeError) as exc:
            raise RuntimeError(stage + ": " + str(exc)) from exc

    call("Open Slate", rt.sme.Open)
    if call("Count Slate Views", rt.sme.GetNumViews) == 0:
        rt.sme.activeView = call("Create Generated Maps View", rt.sme.CreateView, "Generated Maps")
    index = int(rt.sme.activeView)
    if index < 1 or index > rt.sme.GetNumViews():
        index = 1
        rt.sme.activeView = index
    view = call("Get active Slate View", rt.sme.GetView, index)
    if view == rt.undefined:
        raise RuntimeError("Get active Slate View: the View is not ready. Open a Slate View and try again.")
    before_count = call("Count existing Slate nodes", view.GetNumNodes)
    right_edge = 0.0
    for index in range(1, before_count + 1):
        node = view.GetNode(index)
        right_edge = max(right_edge, float(node.position.x) + node_extent(node, "width", 400.0) + 120.0)
    nodes = []
    next_y = 0.0
    with pymxs.undo(True, "Height Map Studio: add maps"):
        for index, texture in enumerate(textures):
            node, unused_position = call("Create Bitmap node " + texture.name, view.CreateNode,
                                         texture, pymxs.byref(rt.Point2(right_edge, next_y)))
            if node == rt.undefined:
                raise RuntimeError("Could not add a Bitmap node to Slate.")
            nodes.append(node)
            node.position = rt.Point2(right_edge, next_y)
            next_y += node_extent(node, "height", 200.0) + 20.0
    # Both NodeView methods are documented from Max 2014 onward.
    # Pass material/map references, not Slate node interfaces.
    if call("Verify created Slate nodes", view.GetNumNodes) < before_count + len(textures):
        raise RuntimeError("Verify created Slate nodes: not all requested nodes are present.")
    call("Select new Slate nodes", view.SetSelectedNodes, rt.Array(*textures))
    call("Frame new Slate nodes", view.ZoomExtents, type=rt.Name("selected"))
    return nodes
