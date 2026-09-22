# MaxPkg authoring project

The root packager and both standard hooks are original upstream files from
`maxpkg-dev/max-dev-tool` commit `1281d283b30d885382c12804ca12da3f092d888b`.
The official Adaptation prompt and Automation API were reviewed at that revision.

Run `maxpkg-packager.ms` in 3ds Max and click **Build MZP**. The saved configuration
targets the root `dist` folder. It uses Free classification, version 1.1.1, beta
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

The current `maxpkg-icon.svg` is an editable normal-map tile design on a square
64-unit canvas, with Qt-rendered previews at 16, 24, 32, 64 and 512 pixels. The
previous released contour icon is preserved in
`docs/icon-backups/maxpkg-icon-topographic-1.1.0.svg`. The packager includes only
the current icon as `icons/icon.svg`. The new design remains pending review.

The saved authoring INI uses local absolute source paths, as the official packager
does. If moving this checkout, update the Files List, icon and output paths in the
packager. Those authoring paths must not appear in the generated runtime manifest.
The package identity is stored only in the configuration and build metadata.

Version 1.1.1 was built in Max 2027 through the official MaxPkgPackerApi after
successful reload and validation. Archive verification found 39 entries, all 31
runtime files byte-identical to source, original hooks and icon, correct beta/Max
2022 metadata, valid CRCs, and no authoring paths in the manifests/bootstrap.

The new controls passed real Qt/GPU checks using the bundled Max 2022 and Max
2027 Python runtimes. Isolated fixture tests also passed inside Max 2027 through
Max Ultra MCP: map-local Reset, AO Threshold, Specular Compress and background
PNG/TIFF exports across a tile boundary. Displacement retains 16-bit precision;
blurred tiled/full results agree within one 16-bit level. Source launch succeeded.
Installation, installed launch, update and uninstall were not repeated for this
release; archive verification is not an installation test.

The published 1.1.0 tag and package remain immutable; later work should use a
new semantic version rather than replacing an existing release.
