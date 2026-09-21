# MaxPkg authoring project

The root packager and both standard hooks are original upstream files from
`maxpkg-dev/max-dev-tool` commit `1281d283b30d885382c12804ca12da3f092d888b`.
The official Adaptation prompt and Automation API were reviewed at that revision.

Run `maxpkg-packager.ms` in 3ds Max and click **Build MZP**. The saved configuration
targets the root `dist` folder. It uses Free classification, version 1.0.0, beta
channel, and minimum Max 2022. Max 2022 launch is user-verified; the wider test
history is in `HeightMapStudio/TEST_RESULTS.md`.

The entry is `HeightMapStudio/Launch.ms`, without compilation or path remapping.
All required Python modules, shaders, local icons and `Sample_height_16.png` are
included. A new empty window loads this package-relative sample. Existing user
images and newer explicit load requests take priority. Tests, caches, build output
and internal test reports are excluded from the package allowlist.

MaxPkg owns file deployment, macro/button creation and icon installation. There
was no legacy installer to replace. No custom hooks or duplicate startup actions
are needed. Existing QSettings remain in the user's profile and are intentionally
preserved across updates and uninstall. No source files are removed by packaging.

`maxpkg-icon.svg` is an original editable vector topographic-contour icon. It uses a square
64-unit canvas and was rendered locally for visual review; it is not AI raster art.
The packager includes it as `icons/icon.svg`.

The saved authoring INI uses local absolute source paths, as the official packager
does. If moving this checkout, update the Files List, icon and output paths in the
packager. Those authoring paths must not appear in the generated runtime manifest.
The package identity is stored only in the configuration and build metadata.

Current verification: official tooling hash equality, input-file completeness,
SVG validity, Python 3.7 syntax, isolated accelerator tests, real Qt 5.15.1 focus
events outside Max, and sample race guards. No MZP has been built in this stage:
After the user permitted a fresh connection check, max_list_instances still
returned Transport closed. No instance was selected and no build call ran.
Official API validation/build, archive inspection, installation, installed launch,
update preservation and uninstall remain unverified. No push or publication is
part of this local-only workflow.

The revised contour icon was rendered and visually checked at 32, 64 and 512 pixels.
Its bright contour rings replace the rejected pyramid-and-layers artwork.
