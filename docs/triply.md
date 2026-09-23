# triply: the library

triply is a Python library for TPMS (triply periodic minimal surface) structures. Its point-and-click app is [coroforge](coroforge.md).

[← back to the README](../README.md)

- [Installation](#installation)
- [Quick start](#quick-start)
- [Modules](#modules)
- [Notebooks and examples](#notebooks-and-examples)
- [Logging](#logging)
- [Tests](#tests)
- [Known bugs](#known-bugs)

## Installation
triply requires **Python 3.10**. Create an environment first:

```powershell
conda create -n triply python=3.10
conda activate triply
conda install git
```

Then pick one of these:

| You want | Command |
|---|---|
| The library only | `pip install git+https://github.com/co-foucher/triply.git` |
| The library + the coroforge app | `pip install "triply[gui] @ git+https://github.com/co-foucher/triply.git"` |
| To edit the code (changes take effect immediately) | from the downloaded repository folder: `pip install -e .` (or `pip install -e ".[gui]"` with the app) |

The `[gui]` extra only adds Streamlit and sympy, so library-only installs stay lighter.

## Quick start
Every TPMS type is a class with the same pipeline: **grid → implicit field → density field → mesh → STL**.

```python
import numpy as np
from triply.TPMS_classes import GyroidModel

# 1) Coordinate grid: 64 voxels per axis over a 1 x 1 x 1 box
x, y, z = np.meshgrid(np.linspace(0, 1, 64),
                      np.linspace(0, 1, 64),
                      np.linspace(0, 1, 64), indexing="ij")

# 2) Model: periods px/py/pz and wall thickness (scalars, or arrays shaped like x)
model = GyroidModel(x, y, z, px=1.0, py=1.0, pz=1.0, thickness=0.2)

# 3) Density field. Modes: "distance" (default), "distance_fast", "band",
#    "signed", "signed_inverse". `level` moves the surface off F = 0.
model.compute_field(mode="distance", level=0.0)

# 4) Mesh: marching cubes, then smooth, simplify and repair
model.generate_mesh()
model.smooth_mesh(smoothing_factor=0.5)
model.simplify_mesh(target_faces=10000)   # or a fraction, e.g. 0.8
model.fix_mesh()
print("valid mesh:", model.check_mesh_quality())

# 5) Export
model.export_stl("my_gyroid")          # writes my_gyroid.stl (the extension is added)
model.save_mesh_preview("my_gyroid")   # interactive my_gyroid.html
model.save("my_gyroid.npz")            # grid, parameters and field
```

The other surfaces work the same way; only the class changes: `SchwartzPModel`, `DiamondModel`, `IWPModel`, `NeoviusModel`, `FischerKochSModel`, `FRDModel`, `LidinoidModel`, `SplitPModel`. For your own implicit field, use `CustomTPMSModel(x, y, z, thickness, field=F)`, where `F` is an array shaped like `x`.

### All-in-one function
Each surface also has a one-call pipeline (`create_a_gyroid`, `create_a_diamond`, ...) that builds the model, meshes it, and saves the `.stl` and `.html`:

```python
import numpy as np
from triply.TPMS_classes import create_a_gyroid

x, y, z = np.meshgrid(np.linspace(0, 10, 128),
                      np.linspace(0, 10, 128),
                      np.linspace(0, 20, 256), indexing="ij")

create_a_gyroid(x, y, z, px=2.0, py=2.0, pz=2.0, t=1.0,
                save_path="my_gyroid",
                baseplate_thickness=2.0,
                step_size=2,
                simplification_factor=0.8)
```

It returns `False` (and exports no STL) if the final mesh fails the validity check.

## Modules
Everything is importable from `triply`. Submodules are loaded on first use, so `import triply` stays fast.

### TPMS generation: `triply.TPMS_classes`
<img width="1894" height="921" alt="TPMS generation workflow" src="https://github.com/user-attachments/assets/c65cae60-cd07-47e0-a794-d1a3a486b6e0" />

- **`tpms_base.py`**: the `TPMSModel` base class: field computation, meshing, export, previews, quality checks, baseplates. Every surface type is a thin subclass that only supplies its implicit equation.
- **`tpms_gyroid.py` … `tpms_splitp.py`**: the nine surfaces, each with its model class and `create_a_...()` function.
- **`tpms_custom.py`**: `CustomTPMSModel`, for a precomputed implicit field.

Periods and thickness can be scalars or per-voxel arrays, for graded structures.

### Surface meshes: `mesh_tools`, `io_ops`, `viz`
- **`mesh_tools.py`**:
  - `mesh_from_matrix()` (marching cubes) and its inverse, `matrix_from_mesh()` (voxelize a mesh into a filled grid)
  - `simplify_mesh()` with three backends: `"pyvista"` (default), `"trimesh"`, `"open3d"`
  - `smooth_mesh()` (Taubin smoothing) and `auto_smooth_mesh()`, which smooths in batches until a roughness metric stops improving
  - `fix_mesh()`, `check_mesh_validity()` (watertight, winding, self-intersections), `keep_largest_connected_component()`
  - `rotate_STL()`, `calculate_triangle_areas()`, `export_as_STL()`
  
  Low-level functions take and return `(verts, faces)`, in that order.
- **`io_ops.py`**: STL loading, and saving/loading the grid + parameters + field as `.npz`.
- **`viz.py`**: interactive Plotly mesh previews (colour by normals, flat, random or curvature), 2D slice views of 3D fields, triangle-area histograms.

### Printability: `voxel_tools`
- `detect_overhangs()`: flags voxels whose overhang angle exceeds a threshold (default 45°), tells safe two-sided bridges apart from true overhangs, and can add support voxels (`add_support_voxels=True`).
- `find_optimal_orientation()`: samples build directions over a sphere and returns the orientation with the fewest overhangs.
- `interpolate_voxel_grid()`: resamples a grid or field to another resolution (trilinear).

### Simulation: `TET_mesh_tools`, `abaqus_tools`
<img width="1533" height="857" alt="simulation workflow" src="https://github.com/user-attachments/assets/d9eeb841-5424-44ac-96ac-d32f1f1bc317" />

- **`TET_mesh_tools.py`**: tetrahedral meshing of an STL with [fTetWild](https://github.com/wildmeshing/fTetWild) (`mesh_an_STL()`), and mesh info.
- **`abaqus_tools.py`**: create ABAQUS jobs (frequency or static), run them, wait for completion, and extract a field at a node set. The scripts executed inside ABAQUS are in `pybaqus/`.

### CT scans: `CT_scans`, `CT_visualization_window`
- **`CT_scans.py`**: convert DICOM, TIFF or JPG slice stacks into one `.mhd` volume. It also provides reading, cropping, thresholding and segmentation (dilate/erode, connected regions, holes and islands, watershed), and masks.
- **`CT_visualization_window.py`**: interactive desktop viewer for CT volumes.

### Utilities
- **`logger.py`**: logging configuration (see [Logging](#logging)).
- **`config.py`**: shared constants and default tolerances.
- **`utils.py`**: helpers such as `reload_all()` for interactive development.

## Notebooks and examples
In `notebooks/`:
- **`Gyroids_STL.ipynb`**, **`Gyroids_STL_class.ipynb`**: generating TPMS structures
- **`overhang_test.ipynb`**: overhang detection and build-orientation search
- **`STL_to_TET.ipynb`**: STL to tetrahedral mesh with fTetWild
- **`full simulation workflow.ipynb`**: end-to-end simulation preparation
- **`CT_scan_processing.ipynb`**: CT scan to mesh, with interactive mesh colouring

In `examples/`: `create_ball_ct_scan.py` (a synthetic CT volume, `ball_ct_scan.mhd`) and `generate_frequency_sim.py`.

## Logging

```python
import triply
triply.set_log_level("DEBUG")  # or "INFO", "WARNING", "ERROR", "CRITICAL"
```

## Tests
From the repository folder:

```powershell
pytest
```

## Known bugs
- The STL coordinates don't exactly match the grid: marching cubes makes the structure about one voxel larger in every dimension.
