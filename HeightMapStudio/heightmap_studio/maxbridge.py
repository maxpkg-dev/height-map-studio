# -*- coding: utf-8 -*-
"""Main-thread-only Slate integration. No generated MAXScript strings."""
import os


def add_to_slate(files):
    if not files:
        return []
    import pymxs
    rt = pymxs.runtime
    textures = []
    pipeline = getattr(rt, "ColorPipelineMgr", None)
    ocio = pipeline is not None and "ocio" in str(pipeline.Mode).lower()
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
    rt.sme.Open()
    if rt.sme.GetNumViews() == 0:
        rt.sme.activeView = rt.sme.CreateView("Generated Maps")
    index = int(rt.sme.activeView)
    if index < 1 or index > rt.sme.GetNumViews():
        index = 1
        rt.sme.activeView = index
    view = rt.sme.GetView(index)
    right_edge = 0.0
    for index in range(1, view.GetNumNodes() + 1):
        node = view.GetNode(index)
        right_edge = max(right_edge, float(node.position.x) + float(node.width) + 120.0)
    nodes = []
    next_y = 0.0
    with pymxs.undo(True, "Height Map Studio: add maps"):
        for index, texture in enumerate(textures):
            node = view.CreateNode(texture, rt.Point2(right_edge, next_y))
            if node == rt.undefined:
                raise RuntimeError("Could not add a Bitmap node to Slate.")
            nodes.append(node)
            next_y += float(node.height) + 20.0
    # Both NodeView methods are documented from Max 2014 onward.
    # Pass material/map references, not Slate node interfaces.
    view.SetSelectedNodes(rt.Array(*textures))
    view.ZoomExtents(type=rt.Name("selected"))
    return nodes
