# Height Map Studio

Create **Normal, Displacement, Ambient Occlusion and Specular** maps from one height image, directly inside 3ds Max. Simple controls and an interactive preview help you prepare surface detail for your materials.

## Load and adjust

Drag a **PNG, TIFF or JPG** into the window, or click **Open image**. A bundled sample loads automatically in a new empty window, so you can try the controls immediately.

Choose a map tab and adjust its two main controls:

| Map | Controls | Use |
| --- | --- | --- |
| Normal | Strength, Blur | Control the apparent surface detail. |
| Displacement | Contrast, Level, Blur | Adjust the height range and offset, and smooth detail. |
| AO | Strength, Radius | Approximate shading around height features. |
| Specular | Brightness, Contrast | Create a height-based specular mask. |

AO and Specular are approximations from the height image, not measurements of the original material. **Advanced** contains OpenGL/DirectX normal orientation, height inversion and wrapped edge filtering. Wrapped filtering works best with an already seamless source.

## Preview and controls

Switch between **2D** and **3D** without losing your map settings. The 3D preview starts with a **Sphere**; choose **Plane** or **Cube** with the shape buttons.

- **Mouse wheel:** zoom in or out.
- **Left-drag:** pan in 2D or rotate the model in 3D.
- **Right-drag horizontally in 3D:** rotate the light around the model.
- **Source:** inspect the original image in 2D.
- **Fit** in 2D, **Reset view** in 3D, or double-click: restore the view, zoom and light position.

The preview helps judge surface detail; it is not a final renderer result. **Reset settings** restores map controls separately from the view. **Settings** lets you adjust slider maximums.

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
