# Height Map Studio

Turn one height image into **Normal**, **Displacement**, **Ambient Occlusion** and **Specular** maps inside 3ds Max. Fine-tune each map with simple controls and check the result in 2D or on a 3D sphere, plane or cube. AO and Specular are useful approximations derived from the height image.

1. Drag in a PNG, TIFF or JPG, or click **Open image**. A sample is ready when you first open the tool.
2. Adjust the map settings and switch between **2D / 3D** to preview the result.
3. Check the maps you want in **Set**, choose PNG, TIFF or JPEG, and click **Save**. Use PNG or TIFF for 16-bit displacement.
4. Click **Add to Slate** separately to add the selected saved maps as Bitmap nodes. Connect them to your material as needed.

**Save beside source** keeps exports next to your image. Turn it off to choose a destination. Right-click **Save** to open the source image folder.

**Installation:** for an MZP distribution, drag the `.mzp` into 3ds Max, confirm installation, and launch Height Map Studio from the **MaxPkg** category. For the portable ZIP, extract the whole folder and run `Launch.ms` through **Scripting > Run Script**.

Prefer browsing tools through a package manager? Visit [maxpkg.dev](https://maxpkg.dev) for MaxPkg and its available tools. This link does not imply that Height Map Studio is already listed there.
