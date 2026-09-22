# Height Map Studio

Create **Normal, Displacement, Ambient Occlusion and Specular** maps from one height image, directly inside 3ds Max. Simple controls and an interactive preview help you prepare surface detail for your materials.

## Load and adjust

Drag a **PNG, TIFF or JPG** into the window, or click **Open image**. A bundled sample loads automatically in a new empty window, so you can try the controls immediately.

Choose a map tab and adjust its controls:

| Map | Controls | Use |
| --- | --- | --- |
| Normal | Strength, Blur, Detail size | Control relief strength, soften edges, or remove narrow features. |
| Displacement | Contrast, Level, Blur | Adjust the height range and offset; soften detail. |
| AO | Strength, Radius, Threshold | Approximate shading and suppress shallow height detail. |
| Specular | Brightness, Contrast, Compress | Create a height-based mask and bring its extremes toward gray. |

Normal and Displacement have independent **Blur** controls (0–16 source-image pixels). **AO Threshold** ignores height differences up to the chosen value (0–1); larger differences contribute only their excess. Zero preserves the original AO. **Specular Compress** blends the finished mask toward 50% gray, after Brightness and Contrast: 0 leaves it unchanged, 0.5 brings black/white to 25%/75%, and 1 makes the mask uniformly gray. These controls affect both preview and saved maps.

AO and Specular are approximations from the height image, not measurements of the original material. **Advanced** contains OpenGL/DirectX normal orientation, height inversion and wrapped edge filtering. **Seamless edges** is enabled by default and can be turned off manually. Wrapped filtering works best with an already seamless source.

**Normal Detail size** flattens small bumps and grooves into simpler plateaus (0–64 source pixels). Zero leaves the source unchanged. A nearly circular feature filter avoids the square structures of a rectangular filter while preserving flat regions; it does not work like Blur. Larger values remove wider features and can merge nearby regions. **Blur** optionally softens the remaining edges afterward.

## Preview and controls

Switch between **2D** and **3D** without losing your map settings. The 3D preview starts with a **Sphere**; choose **Plane** or **Cube** with the shape buttons.

The compact **Preview** menu at the upper left appears only in **3D** and independently enables **Normal, Displace, AO and Specular** in the material. Combine any selection, or turn everything off for a plain surface. For example, disable Specular while judging normals without changing the Specular map settings. White check marks show enabled effects. The menu stays open while checking options, closes in 2D and remembers your selection. These choices do not change the editing tab, the 2D map view or the export Set.

Displace intersects an approximate height surface on all three shapes, including changes to the silhouette; it is not a bump substitute. Preview depth is fixed at 0.12 model units across the full height range. Very fine relief, grazing angles and cube/sphere UV seams remain approximate, and this preview does not predict renderer-specific tessellation or displacement settings. Exported map values are unaffected.

- **Mouse wheel:** zoom in or out.
- **Left-drag:** pan in 2D or rotate the model in 3D.
- **Right-drag horizontally in 3D:** rotate the light around the model.
- **Source:** inspect the original image in 2D.
- **Fit** in 2D, **Reset view** in 3D, or double-click: restore the view, zoom and light position.

The preview helps judge surface detail; it is not a final renderer result. **Reset settings** restores only the active map's controls. On Normal it also restores OpenGL orientation; other maps, Invert height, Seamless edges and the view keep their settings. **Settings** lets you adjust slider maximums.

## Save your maps

Check **Normal, Displace, AO and/or Specular** in **Set**, choose the file format, then click the single **Save** button. The checked maps are saved regardless of which tab you are viewing.

With **Save beside source** enabled, one click saves the selected maps next to the original image without a destination dialog. Names use `_normal`, `_displacement`, `_ao` and `_specular` suffixes. Existing files require confirmation before replacement. The bundled sample asks for a separate output folder the first time.

Turn **Save beside source** off to choose a filename for one map or an output folder for several maps. **Right-click Save** to open the source image's folder in Explorer.

- **PNG / TIFF:** 8-bit Normal, AO and Specular; **16-bit Displacement**.
- **JPEG:** lossy **8-bit** output for every map, including Displacement.
- Images up to **8192 x 8192** are supported. Saved maps use the source resolution. PNG/TIFF height images can retain their 16-bit precision on input.

## Add to Slate

After saving, click the separate **Add to Slate** button. It adds existing saved textures for the types checked in **Set** to the Slate Material Editor, arranged vertically. New nodes are selected and framed; existing nodes stay in place.

Missing maps are named in the status line, while available selected maps can still be added. This button does not generate or save maps, and does not connect them to your material automatically.

## Installation

**MZP package:** drag the Height Map Studio `.mzp` into 3ds Max, confirm installation, and launch the tool from the **MaxPkg** category.

**Portable ZIP:** extract the entire folder, then choose **Scripting > Run Script** and open `Launch.ms`.

You can also browse and install 3ds Max tools with [MaxPkg](https://maxpkg.dev). Check its catalogue for available packages.
