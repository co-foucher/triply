# coroforge: the app

<img src="../app/assets/coroforge_logo.svg" alt="coroforge" width="560">

coroforge is the point-and-click app for [triply](triply.md). It runs as a small local server on your own computer, and you use it in your web browser. It has no logic of its own: every button calls a triply function, so the app and the library always give the same results.

[← back to the README](../README.md)

- [Opening the app](#opening-the-app)
- [How the app is organized](#how-the-app-is-organized)
- [The pages](#the-pages)
- [What some pages need besides Python](#what-some-pages-need-besides-python)
- [Troubleshooting](#troubleshooting)

## Opening the app

### Option 1: double-click `launcher.bat` (Windows, no Python or terminal needed)
1. Get the repository: on GitHub click **Code > Download ZIP** and extract it, or `git clone https://github.com/co-foucher/triply.git`.
2. Double-click **`launcher.bat`** in the repository folder.
3. A console window opens, titled *coroforge - keep this window open while you use the app*. It:
   - installs [uv](https://docs.astral.sh/uv/) for your user account if it's missing (no admin rights needed);
   - pre-answers Streamlit's one-time "Email:" question, so the first launch doesn't sit waiting for keyboard input;
   - runs `uv run --extra gui streamlit run app\Home.py`. This creates a `.venv` folder next to the launcher, with Python 3.10 and the exact package versions pinned in `uv.lock`, then starts the app.
4. The app opens in your browser at http://localhost:8501, on the **Home** page.

Good to know:
- The **first launch downloads about 450 MB and can take several minutes**. Later launches start in seconds. An internet connection is needed the first time, and again whenever `pyproject.toml` or `uv.lock` change.
- **Keep the console window open** while you use the app: closing it stops the app. Closing the browser tab doesn't.

### Option 2: from your own Python environment
Install triply with the `gui` extra (see [Installation](triply.md#installation)), then run from the repository folder:

```powershell
streamlit run app/Home.py
```

or, with uv, without creating an environment yourself:

```powershell
uv run --extra gui streamlit run app/Home.py
```

The app opens at http://localhost:8501. If Streamlit asks for an email on its very first run, just press Enter. Stop the app with `Ctrl+C` in the terminal.

## How the app is organized

### Pages chain together through files
Each page in the sidebar is one stage of the workflow. Pages don't pass data to each other directly: they write files to the **output folder**, and the next page asks you to select them. For example, an `.stl` exported on *Generate TPMS* is what *Prepare print* or *Simulation* opens.

The **Home** page draws this as a diagram and has one card per page, listing the files it reads (**in**) and writes (**out**):

<img src="../app/assets/home_pipeline_preview.png" alt="coroforge pages and the files they exchange" width="900">

Coloured boxes are pages, grey ones are the files they hand to each other. The dashed edge is *Generate TPMS* reading a mesh or field back in.

### "How this works" panels
Every page except the Library opens with a collapsed **How this works** panel that explains its pipeline step by step, with the equations behind each setting. Start there if a parameter isn't obvious.

### Sidebar (on every page)
- **Output folder**: where every page writes its files and reads them from. It defaults to `app/gui_outputs/` and is created if it doesn't exist. Changing it applies to the current browser session only.
- **Select Log Level**: how much of triply's logging is printed in the console window (DEBUG, INFO, WARNING, ERROR, CRITICAL; default INFO).

## The pages

### Generate TPMS
Builds a TPMS structure and exports it as an STL.
- **Implicit field**: one of nine built-in surfaces (Gyroid, Schwartz P, Diamond, I-WP, Neovius, Fischer-Koch S, F-RD, Lidinoid, Split-P), a custom equation in x, y, z, or a field imported from a `.npy` file. Periods can be constant, an equation, or imported.
- **Density field**: turns the implicit field into a solid with one of four modes: *Distance*, *Signed*, *Signed (inverted)* or *Band*. The threshold and the wall thickness can each be constant, an equation, or imported from a file.
- **Extras**: baseplates, and combining with an existing part (STL or `.npy`) by intersection, union or subtraction.
- **Mesh**: smoothing, simplification, and an optional face limit, with live previews of the field (2D slices) and the mesh (3D).
- **Out**: `.stl` (+ an `.html` preview), the implicit field `.npy`, and the thickness field `.npy`.

### Field generator
Builds a custom 3D field step by step, to use on *Generate TPMS* as an implicit field, threshold, thickness or period.
- **Layers** generate a field: constant, linear or radial gradient, signed distance to a sphere / box / cylinder, Gaussian blob, equation, distance to an STL or `.npy` mask, or an imported `.npy`. Each one is blended with the result so far (replace, add, subtract, multiply, min, max, smooth min/max), with a weight.
- **Modifiers** transform the result so far: remap to a range, clip, Gaussian smoothing, or a transfer function (negate, absolute value, power, smoothstep, step).
- Steps can be switched off, reordered and deleted. You can preview the result after any step and see a histogram. A check tells you whether the field suits the use you pick (e.g. a thickness must stay > 0).
- **Out**: `.npy`. On *Generate TPMS*, select it with **Import from file**, and **use the same Size X/Y/Z on both pages**: the file stores values only, not coordinates. The resolution may differ; the field is resampled.

### Prepare print
Voxelizes a mesh, labels its overhangs, bridges and needed supports, searches for the print orientation that needs the fewest of them, and exports the mesh rotated into it.
- **In** `.stl` · **Out** `.stl`, `.html`

### Simulation
Tet-meshes an STL with fTetWild, builds and runs an ABAQUS job (frequency or static stiffness), then extracts the displacement fields.
- **In** `.stl` · **Out** `.inp`, `.odb`, `.csv`

### CT Analysis
Stacks JPG / DICOM / TIFF slices into one volume, builds a segmentation pipeline over it, and extracts a mesh from the result.
- **In** image slices, or an existing `.mhd` · **Out** `.mhd`, `.stl`

### Library
Browses the output folder: previews each exported structure and downloads its mesh, its saved field files and its preview. It lists `.stl` files, so fields saved on the *Field generator* don't appear there.

## What some pages need besides Python
- **Simulation** needs [fTetWild](https://github.com/wildmeshing/fTetWild) (the path to its executable is set on the page; default `C:\Program Files\fTetWild\build\Release\FloatTetwild_bin.exe`) and a local **ABAQUS** installation whose `abaqus` command works in a terminal. Meshing and ABAQUS runs happen in the background; their status and log are shown on the page and refresh on their own.
- **CT Analysis** shows a slice preview in the browser. Its full interactive viewer opens as a separate desktop window.
- The **Browse...** buttons open your operating system's own file and folder dialogs. This works because the app runs on your own computer.

## Troubleshooting
If something goes wrong with `launcher.bat`, its window stays open with a message:
- *uv could not be installed*: the internet connection or a proxy blocked the download.
- *The app has stopped*: the reason is in the messages printed above it.
