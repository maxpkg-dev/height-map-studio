# Height Map Studio

A compact Normal, Displacement, Ambient Occlusion, and Specular map generator for 3ds Max.
Runs locally without an internet connection, a separate Python installation, or additional Python packages.

## Launch

1. Extract the **entire** HeightMapStudio folder from the ZIP to a permanent location.
2. In 3ds Max, choose **Scripting → Run Script** and open `Launch.ms`.
3. Drop a single height map onto the window or click **Open image…**.
   The included `Sample_height_16.png` loads automatically in a new empty window.
   Explicit file requests and already-open images take priority over this demo.

Running the script again activates the existing window when source files are unchanged.
After an update, Launch closes the old window and reloads this folder's code, preserving
the current image and controls. If an image operation is running, finish it and launch again.
It does not install a startup script.

Window size and position are remembered between sessions. With no saved placement, the window
uses the minimum practical width and derives its height from the current layout so the preview
is square. Saved user dimensions take priority. Off-screen placement is brought back into the
available screen area. Placement is stored in per-user Qt settings under HeightMapStudio/Window.

## Controls

| Map | Main settings |
|---|---|
| Normal | Strength, Blur |
| Displacement | Contrast, Level, Blur |
| AO | Strength, Radius, Threshold |
| Specular | Brightness, Contrast, Compress |

Each map retains its settings when switching tabs. **Reset settings** restores only the active map's parameters, plus OpenGL orientation when Normal is active. Shared inversion and seamless edges remain unchanged.
The reset button is inside **Map Settings**.
Normal Strength's slider covers 0–20; manual entry accepts values up to 1,000,000.
Values above 20 stay intact while the slider rests at its upper end.
Blur and AO radii are measured in source-image pixels.
Normal and Displacement have independent Blur settings (0–16 px, default 0).
AO Threshold (0–1, default 0) subtracts from positive neighbor-to-center height differences before horizon weighting. It is independent of absolute input brightness.
Specular Compress (0–1, default 0) mixes the clipped brightness/contrast result toward 0.5. This also compresses values already clipped to black or white.
Slider updates use an 80 ms debounce: processing starts after the latest change settles.

The small **Advanced** button sits beside Reset settings inside **Map Settings**. It reveals
compact OpenGL (+Y) / DirectX (−Y), Invert height, and Seamless edges controls to its right.
Seamless edges wraps filtering across the image boundary. The source must already tile seamlessly;
this option does not repair mismatched edges. Defaults: white represents raised areas, OpenGL normals,
and filtering clamped to the image boundary.

**Preview controls:** wheel to zoom; left drag to pan in 2D or rotate in 3D;
right drag in 3D to rotate the light; double-click or **Fit** to reset the view.
Model rotation supports continuous turns on both axes. The plane is visible from either side;
at an exactly edge-on angle, its zero-thickness surface naturally has no visible area.
At Fit, square maps fill a square preview edge to edge. Rectangular maps keep their original
aspect ratio without stretching or cropping. Buttons and numeric inputs use square borders,
with clearly separated painted spinner arrows and native input behavior.
The adjacent **2D** and **3D** buttons switch modes without resetting map settings.
The 3D preview offers Plane, Sphere and Cube through icon buttons at the top right of the viewer.
These buttons are hidden in 2D. The Fit overlay at the bottom left works in both modes.
In 3D it displays a circular reset arrow with the tooltip **Reset view**; in 2D it keeps **Fit**.
Cube faces each display a complete map with their own tangent-space normal orientation.
The plane uses lightweight displacement parallax; the cube retains its geometric silhouette.
This is an approximate material preview, not geometric displacement or a Corona/V-Ray render.

AO estimates occlusion from neighboring heights. Specular is an artistic mask derived from height;
a height map alone cannot recover a material's physical reflectance.

## Files

- Input: PNG / standard TIFF at 8 or 16 bits, and 8-bit JPG; maximum **8192 × 8192**.
- Single-channel 16-bit height maps are processed without conversion to 8 bits.
- Color images are converted to luminance using weights 0.2126 / 0.7152 / 0.0722.
- Alpha is ignored. Heights are treated as numeric data without sRGB/gamma conversion.
- Float/HDR TIFF, EXR, BigTIFF, and multilayer processing are not supported.
- **Save** exports only maps checked beside the button, regardless of the active preview tab.
  Right-click **Save** to open the current source image's folder in Explorer.
  Fresh preferences select only Normal. Your subsequent choices are remembered.
  An empty selection disables Save.
- **Save beside source** uses the source folder automatically. Turn it off to choose an output
  destination manually: a filename for one map, or a folder for multiple maps.
  The bundled demo asks for an external output folder once and remembers it.
- Output: PNG or TIFF; Normal uses RGB 8-bit, AO/Specular use grayscale 8-bit,
  and Displacement uses grayscale **16-bit**. TIFF output is uncompressed.
- JPEG output uses quality 95 and **8-bit** samples for every map, including displacement.
  JPEG is the initial format; later format choices are remembered.
  The format selector sits beside the view controls, in JPEG / PNG / TIFF order.
  JPEG is lossy. Its encoder needs an additional packed image, up to 192 MiB at 8K;
  cancellation during the codec call is handled before any final file is replaced.
- Export resolution matches the source. Filenames receive the suffixes
  `_normal`, `_displacement`, `_ao`, or `_specular`.
- Replacing existing files requires confirmation. During processing or encoding,
  **Cancel** removes only temporary files. The final commit of the prepared files is brief;
  if a disk error occurs, the error message lists files that were already saved.

## Slate Material Editor

**Save** only saves files. The separate **Add to Slate** button at the bottom right adds
existing files for the map types checked in **Set**, regardless of the active preview tab.
It does not generate or save maps. Successful export paths are remembered per source image,
including custom filenames and folders. If no saved path is known and Save beside source is
enabled, the source folder is checked for the standard map name in the selected format.
Missing maps are named in the status bar; available selected maps can still be added.
New Bitmap nodes form a vertical column to the right of existing nodes, with space between
them. Maps are not connected to materials automatically.
A View is created if none exists.
Only the newly created nodes are selected, and the View frames that selection. Previous
nodes keep their positions. Saving alone leaves Slate unchanged.
OCIO workflows use the configured **Data Color Space**; gamma-based workflows use **gamma 1.0**.
Scene color-management settings are not changed.
If adding a map to Slate fails, the exported files remain available and a separate error is shown.

## Performance and compatibility

Preview resolution is limited to 2048 pixels on its longest side. Full-resolution export
uses 1024 × 1024 tiles with overlapping filter borders. Export processing and encoding run
in a worker thread, keeping the Max interface available. The status bar shows preview update time,
including GPU completion.

Requires Windows x64 and a driver supporting **OpenGL 3.3 core**, float32 framebuffers,
and 16-bit textures. GPU failures display diagnostics without silently switching processing methods.
An 8K source uses approximately 512 MiB of RAM in the working format; loading may require additional copies.

The code includes PySide2 adapters for Max 2022–2024 and PySide6 adapters for Max 2025–2027.
See `TEST_RESULTS.md` for the versions actually tested and known verification limits.

## Project layout

`Launch.ms` starts `launch.py`. The `heightmap_studio` package contains the interface,
GPU pipeline, background jobs, image codecs, and Slate integration.
GLSL shaders are in `heightmap_studio/shaders`. Resources are resolved relative to the script.
The source code is editable.

View buttons use local Lucide `image`, `box`, `square`, `globe`, `maximize` and `rotate-ccw` SVGs, recolored for the dark interface.
Source: https://github.com/lucide-icons/lucide. The full upstream license notice is
included in `heightmap_studio/assets/LUCIDE-LICENSE.txt`. No runtime downloads are used.

## Support and related tools

A compact row between the preview and the 2D/3D controls rotates support and
related 3DGROUND tool links every 30 seconds. Rotation pauses while the link is
hovered, focused, or pressed. The separate heart Donate button remains visible.
Links open the default browser only when activated. The timer stops when the
window is hidden or closed; no network requests are made by the rotating row.

## GitHub Release helpers

`release-github.bat` follows the Dropper BAT launcher. The PowerShell workflow is
based on Dropper's release script and the existing GC adaptation's identity and
pushed-commit guards, with Height Map Studio's Python version metadata and origin.

After building a fresh MZP with the official packager, commit the intended release
files and push `main` yourself. Run `release-github.bat --check-only` first (or
`powershell -NoProfile -File .\release-github.ps1 -CheckOnly`). This requires Git,
authenticated GitHub CLI, a clean working tree and HEAD already on origin/main.

The helper selects the numerically highest MZP version, rejects ambiguous versions,
checks manifests, package identity/version/channel, the exact origin, and existing
release/tag state. It refuses to replace an existing release or move a conflicting
tag. CheckOnly never creates a release or uploads an asset. Running the BAT without
arguments asks for confirmation before publication; it does not build, commit or
push. For unattended check-only use, set `HMS_RELEASE_NO_PAUSE=1` before running the BAT.

Edit the artist guide in root `README.md`; `build.py` copies it into the portable
payload's README. Rebuild the official MZP after changing any packaged file,
including documentation. The existing MZP passed static inspection before the
expanded artist-guide update and now needs rebuilding to include that update.
