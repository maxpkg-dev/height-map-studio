# Height Map Studio 1.0.0 — Test Results

Date: September 21, 2026.

## Verified environment

- Running **3ds Max 2027.2**; all Max operations and interface checks used **Max Ultra MCP**.
- PySide6 6.8.3; OpenGL renderer: **SVGA3D; build: RELEASE; LLVM** (virtual graphics adapter).
- Module syntax was also checked with Python 3.7 bundled with Max 2022.
- **Max 2022–2026 have not been tested in a running application.** The PySide2 adapter is implemented,
  but syntax checks do not verify the interface or graphics driver in those versions.

## Results

| Check | Result |
|---|---|
| Launch through `Launch.ms` | Passed |
| Neutral normal on a flat height map | Passed |
| Gradient directions, OpenGL/DirectX, height inversion | Passed |
| AO: cavities are darker than exposed surfaces | Passed |
| All 65,536 levels after reading 16-bit PNG/TIFF | Exact match |
| All 65,536 levels after GPU displacement processing | Exact match |
| Tiled versus full-image processing, clamp/repeat | Normal/Displacement/Specular: exact; AO: ≤ 1/255 |
| Normal strength at reduced preview resolution | Matches full resolution within 1/255 |
| Background export of four maps in PNG and TIFF | Passed |
| Slate: empty/populated View, placement to the right | Passed |
| Slate: actual `raw` color space in OCIO | Passed |
| Drag and drop; latest source load wins | Passed |
| Cancellation preserves an existing file | Passed |
| Close and reopen | Passed |
| Corrupt files and images larger than 8K are rejected | Passed |
| GPU error remains visible after loading an image | Passed with a simulated GPU failure |
| Visual 2D preview and 3D sphere preview | Checked through MCP screenshots |
| Load 8192 × 8192 16-bit PNG with a 2048 × 2048 preview | Passed |
| Load 8K RGB16 and restore the Qt decoder allocation limit | Passed; RGB values preserved exactly |
| Export all four maps at 8192 × 8192 | Passed |
| Independently verify every value in 8K displacement | All 67,108,864 values match the source |

Slate tests used a temporary View that was removed afterward. No objects in the user's scene
were created, deleted, or modified, and the scene file was not saved.

## Performance

Synthetic 16-bit gradient, 2048 × 2048 preview, default settings, three measurements after warm-up,
including GPU completion. Median times:

| Map | Preview processing |
|---|---:|
| Normal | 2.9 ms |
| Displacement | 2.0 ms |
| AO | 3.6 ms |
| Specular | 2.0 ms |

These measurements cover GPU processing passes, **excluding source decoding, upload to the GPU,
shader compilation, and repainting the entire window**. Other textures, Blur settings,
and drivers can produce different results.

Exporting all four maps at **8192 × 8192 to PNG took 83.7 seconds** in this environment.
The GUI test timer remained responsive, firing 2,584 times during export.
Immediate feedback refers to the preview; full 8K export is not instantaneous.

Test scripts are in the project's `tests` folder; machine-readable reports are in `work`.
Legacy gamma-based workflows, separate physical GPUs, and custom OCIO configurations
were not tested in this session.

## English-only revision

Interface labels, tooltips, messages, documentation, and test fixture names use English.
Processing algorithms and output formats are unchanged.

Additional live Max 2027.2 checks after the interface update:

| Check | Result |
|---|---|
| English labels and tooltips, including hidden settings | Passed |
| First-run dimensions calculated from the actual layout | 333 × 644 window; 305 × 305 square preview at the tested DPI |
| Square map fills all four preview corners without borders | Passed |
| Spinner buttons stay within the outer input rectangle | Passed |
| Spinner up/down mouse clicks, focus, and disabled state | Passed |
| Combo popup and checkbox behavior | Passed |
| Custom, nonsquare window size and position restored after reopening | Passed |
| Off-screen window returned to available screen bounds | Passed |

These checks used separate test preferences; the user's saved window placement was preserved.
Square input and button borders were verified visually through Max Ultra MCP.

## Compact controls and JPEG revision

Completed live checks in Max 2027.2:

- Default sample loads through the normal asynchronous pipeline; explicit initial files win.
- Local Lucide SVGs render; 2D/3D buttons remain mutually exclusive and preserve settings.
- Numeric fields measure 68 by 22 logical pixels. Arrow clicks, keyboard, wheel and disabled behavior pass.
- Normal slider covers 0–20 while manual 100, 123.45 and focus-out 101.25 remain intact.
- Enter commits input without invoking the Open image button.
- 80 ms debounce coalesces successive parameter updates.
- Four JPEG maps decode at source dimensions with 8-bit data; cancellation preserves existing output.
- JPEG is the fresh default and format changes are stored.
- A minimum-width screenshot shows Add to Slate on its own row, Map Settings and compact spinners.

After reconnecting Max, selected Normal/AO export beside a Unicode-named source produced
exactly two JPEG files and two Raw Bitmap nodes in a temporary Slate View. The test View was
removed afterward. Rejecting overwrite left existing files unchanged.
The bundled demo resolved to the remembered external output folder.
Empty map selection disables Save. Unusual filesystem permission failures were not retested.

Final live layout measurements: format selector and Save are both 28 pixels high;
Advanced options occupy the horizontal row to the right of their button; Reset settings is
left-aligned inside Map Settings, 69 by 20 pixels with a 10-pixel font. Checkbox mark placement
and the compact interface were inspected in real Max captures.

Native Qt parent and Win32 owner both matched the Max main window. A one-shot delayed activation
was added. Actual viewport drag-launch and Alt-Tab/minimize behavior remain unverified.

## Shape overlay revision

Plane/Sphere/Cube icon controls belong to the preview's upper-right corner, with Fit at bottom left.
The cube shader intersects rays against six box faces and constructs a right-handed normal
basis and full texture coordinates per face. Format order is JPEG / PNG / TIFF with stable
named preferences; its selector moved to the former external Fit position.

Live Max 2027.2 checks passed: shader compilation, all three shape frames, exclusive icon selection,
cube rotation and changing light, Fit restoring the view without modifying map settings,
overlay positions after resizing, and icons rendering from local SVG files. The cube was visually
inspected with three visible textured faces. Fit is a momentary 28 by 28 icon button, matching
the shape buttons. Shape controls disappear in 2D while Fit remains visible.

Python 3.7 syntax and ZIP integrity checks pass. Separate Max 2022–2026 runtime and other DPI scales
remain untested. A standalone PySide2 attempt could not load its Qt DLL dependencies outside Max;
the successful live GPU checks above were performed after the Max bridge reconnected.

## Slate selection and continuous rotation

Live Max 2027.2 checks passed:

- A newly added single Bitmap is selected and centered; a distant preexisting node is deselected and unmoved.
- A new two-map set is selected together and framed, excluding earlier nodes from the framing bounds.
- Native Slate captures confirmed single-node framing at 200% and two-node framing at 100%.
- Empty integration input changes nothing. Add to Slate disabled preserves the existing node count and selection.
- Test cleanup removes only its temporary View and restores the previous View/open state.

The integration uses `NodeView.SetSelectedNodes` with map references followed by
`NodeView.ZoomExtents(type: #selected)`. Both are documented in the Max 2022 reference as
available since Max 2014. This establishes API availability, not a Max 2022 runtime test.

Rotation testing delivered 240 mouse-move events per shape, with multiple turns on both axes
and direction reversal during one drag. Every step matched its expected unclamped angle;
sampled GPU frames rendered without errors. Plane tests covered front/back, full turns and
both sides of an edge-on orientation. Right dragging changed only the light, and Fit restored
the initial rotation/light. The plane now uses two-sided tangent frames and only rejects
an effectively parallel ray, rather than disappearing throughout a wider angular band.

The mode-specific bottom-left icon was verified live: 2D displays Fit, 3D displays the
Lucide circular reset arrow and Reset view tooltip. Both SVGs render as distinct nonempty
icons at the same 28 by 28 button size. Switching modes preserves image, map parameters,
rotation and zoom; the existing reset action remains unchanged.

Advanced now shares the compact action row with Reset settings inside Map Settings.
Live minimum-layout verification measured a 313 by 687 collapsed window with a 285-square
preview, expanding to 439 pixels wide to keep the options horizontal and unclipped.
Both action buttons and the Advanced dropdown measure 20 pixels high. Checkbox mouse input
and dropdown keyboard input passed. Expanded controls were visually inspected after applying
the separate compact checkmark offset (-1 x, -2 y relative to the larger checkbox style).
Export checkboxes keep their previous size, font and mark placement.

## Promotional row update

Verified in connected 3ds Max 2027 using Max Ultra MCP: 26-pixel row immediately
below the preview, persistent heart Donate button, complete support/promotion
rotation with matching URLs, one 30-second timer, and timer stop/resume on
hide/show. The existing window was upgraded in place without rebuilding the GPU
preview. No browser was opened. Settings was neither modified nor tested.
The existing saved-size preview measured 493 x 498; first-run square sizing uses
the unchanged layout-measurement routine, but was not rerun in this narrow check.
Full application close/reopen was not retested during this update.
The portable ZIP was rebuilt from current source, including the single Save UI,
Settings, configurable slider ranges, and the promotional row. Every ZIP entry
was compared byte-for-byte with its source, and Python 3.7 syntax was checked.

## Separate Slate button and Launch refresh

Verified in Max 2027 through Max Ultra MCP after running the actual project Launch.ms:
- Add to Slate is a separate non-checkable button at the bottom right.
- Empty selection and all-missing maps produce nonmodal messages.
- The successful-export handler records custom paths without adding Slate nodes.
- Checked Normal/AO maps were added while the Specular preview tab was active.
- Two new nodes formed a nonoverlapping vertical column; only those nodes were selected,
  ZoomExtents(selected) completed, and a preexisting node kept its position.
- Partial availability added Normal and explicitly reported missing AO.
- Paths survived a fresh QSettings reader; separate sources remained isolated; standard
  beside-source filenames were found. No map generation or export was triggered by Add.
- The test-owned Slate View was removed and the prior active View/open state restored.
- Changed source reloaded into one new window, preserving the current image and map values
  with Save enabled. A second unchanged Launch reused exactly one window and one promo timer.

The repository and loaded module paths matched the requested active main checkout.
The stale interface was caused by Python module/window reuse, not another worktree.
Settings and promotion source hashes were unchanged. No Settings tests, browser links,
scene resets, or modal file-dialog tests were run. The exporter itself was not rerun;
this check covered the changed completion handler and separate Slate action.
Earlier automatic-Add-to-Slate test records describe the superseded checkbox behavior.
