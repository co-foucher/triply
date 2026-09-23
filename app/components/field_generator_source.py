import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json
import os
import uuid
from dataclasses import dataclass
from typing import Any, Optional, Tuple

import numpy as np
import streamlit as st

from app.components.branding import PAGE_ICON

st.set_page_config(page_title="Field generator", page_icon=PAGE_ICON, layout="wide")

with st.spinner("Loading triply toolkit..."):
    import pandas as pd
    import plotly.graph_objects as go

    from app.components.equation_input import (
        render_equation_input, evaluate_custom_inputs, EquationError,
    )
    from app.components.file_picker import browse_file
    from app.components.tpms_source_panel import load_STL, pad_to_square

"""
#=====================================================================================================================
0 - (reserved)
1 - Param (dataclass) + STEP_TYPES / BLEND_OPS definitions
2 - make_grid
3 - _spacing
4 - _compute_layer          (generator steps, cached)
5 - _geometry_mask          (voxelize STL / .npy onto the grid, cached)
6 - _apply_modifier         (modifier steps)
7 - _blend
8 - run_pipeline
9 - step list callbacks     (add_step, _move_step, _delete_step, clear_steps)
10 - _render_params
11 - render_step
12 - check_intended_use
13 - render_doc
14 - widget-state mirror    (restore_widget_state, mirror_widget_state)
#=====================================================================================================================
"""

# TO DELETE AT SOME POINT
DEFAULT_GRID = {"size_x": 10.0, "size_y": 10.0, "size_z": 10.0, "resolution": 64}


# =====================================================================
# 1) Param dataclass 
# =====================================================================
@dataclass
class Param:
    """
    ============================================================================
    PARAM
    Declares one user-editable parameter of a step type (one entry of
    STEP_TYPES[...]["params"]).
    ============================================================================

    FIELDS
    ------
    name : str
        Key of the value in the step's params dict (p[name]) and suffix of
        its widget key: f"fg_{step_id}_{name}". Must be unique within the
        step. "equation" and "path" are reserved: render_step() already
        uses them for the Equation text and the file-picker path.
    label : str
        Widget label shown in the UI. 
        (For "vec3", " x" / " y" / " z" is appended to it for each of the three inputs.)
    kind : str, optional
        Which widget is drawn (default "float"):
          - "float"  -> st.number_input, value stored as float.
          - "select" -> st.selectbox over `options`.
          - "vec3"   -> three st.number_input in one row, stored under
                        f"fg_{step_id}_{name}_0/_1/_2"; the value in the
                        params dict is a list [vx, vy, vz].
    default : Any or callable, optional
        Initial value, written to session_state once (setdefault) the
        first time the widget is drawn.
    options : tuple of str, optional
        Choices for kind="select". Ignored otherwise.
    help : str, optional
        Tooltip shown next to the widget (for "vec3", on each of the
        three inputs).
    min_value : float, optional
        Lower bound of the number_input. Only applied for kind="float"
        (not to "vec3" components).
    show_if : (str, tuple of str), optional
        (other_name, allowed_values): draw this widget only when the
        param `other_name` of the same step currently has a value in
        `allowed_values`. Params are drawn in list order, so `other_name`
        must come earlier in the list (in practice, a "select"). 

    EXAMPLE
    -------
    >>> Param("radius", "Radius", default=1.0, min_value=1e-6,
    ...       show_if=("shape", ("Sphere", "Cylinder")))
    """
    name: str
    label: str
    kind: str = "float"
    default: Any = 0.0
    options: Optional[Tuple[str, ...]] = None
    help: Optional[str] = None
    min_value: Optional[float] = None
    show_if: Optional[Tuple[str, Tuple[str, ...]]] = None


# =====================================================================
# 2) step type definitions
# =====================================================================
# some small helper functions for default values of certain parameters
def _box_center(g):
    return [g["size_x"] / 2.0, g["size_y"] / 2.0, g["size_z"] / 2.0]


def _quarter_min_size(g):
    return round(min(g["size_x"], g["size_y"], g["size_z"]) / 4.0, 4)


def _half_min_size(g):
    return round(min(g["size_x"], g["size_y"], g["size_z"]) / 2.0, 4)


AXES = ("x", "y", "z")

# kind: "generator" -> produces a layer blended with the previous result
#       "modifier"  -> transforms the previous result in place
# custom: steps whose inputs aren't plain Params (equation text / file path)
STEP_TYPES = {
    # ------------------------- generators -------------------------
    "Constant": dict(
        kind="generator",
        caption="f = c everywhere.",
        params=[Param("value", "Value c", default=1.0)],
    ),
    "Linear gradient": dict(
        kind="generator",
        caption="Goes from v0 to v1 along a direction, across the whole box.",
        params=[
            Param("direction", "Direction", "vec3", default=[1.0, 0.0, 0.0],
                  help="Does not need to be normalized."),
            Param("v0", "Value at start v0", default=0.0),
            Param("v1", "Value at end v1", default=1.0),
        ],
    ),
    "Radial gradient": dict(
        kind="generator",
        caption="Goes from v_in at the center to v_out at radius R (and beyond).",
        params=[
            Param("shape", "Shape", "select", default="Spherical",
                  options=("Spherical", "Cylindrical")),
            Param("axis", "Cylinder axis", "select", default="z", options=AXES,
                  show_if=("shape", ("Cylindrical",))),
            Param("center", "Center", "vec3", default=_box_center),
            Param("radius", "Radius R", default=_half_min_size, min_value=1e-6),
            Param("v_in", "Value at center v_in", default=1.0),
            Param("v_out", "Value at R v_out", default=0.0),
            Param("profile", "Profile", "select", default="Linear",
                  options=("Linear", "Smoothstep")),
        ],
    ),
    "Primitive (signed distance)": dict(
        kind="generator",
        caption="Exact signed distance to a sphere / box / cylinder, in physical units "
                "(negative inside, 0 on the surface, positive outside).",
        params=[
            Param("shape", "Shape", "select", default="Sphere",
                  options=("Sphere", "Box", "Cylinder")),
            Param("center", "Center", "vec3", default=_box_center),
            Param("radius", "Radius", default=_quarter_min_size, min_value=1e-6,
                  show_if=("shape", ("Sphere", "Cylinder"))),
            Param("box_size", "Edge length", "vec3", default=lambda g: [_half_min_size(g)] * 3,
                  show_if=("shape", ("Box",))),
            Param("axis", "Cylinder axis", "select", default="z", options=AXES,
                  show_if=("shape", ("Cylinder",))),
            Param("height", "Cylinder height", default=_half_min_size, min_value=1e-6,
                  show_if=("shape", ("Cylinder",))),
        ],
    ),
    "Gaussian blob": dict(
        kind="generator",
        caption="f = A exp(-|p - c|^2 / (2 sigma^2)).",
        params=[
            Param("center", "Center c", "vec3", default=_box_center),
            Param("sigma", "Sigma", default=_quarter_min_size, min_value=1e-6),
            Param("amplitude", "Amplitude A", default=1.0),
        ],
    ),
    "Equation": dict(
        kind="generator",
        caption="Any formula f(x, y, z) - same syntax as the custom equations on Generate TPMS.",
        params=[],
        custom="equation",
    ),
    "Import .stl": dict(
        kind="generator",
        caption="Signed distance to an STL mesh or a .npy voxel mask "
                "(negative inside, positive outside), in physical units.",
        params=[
            Param("placement", "Placement", "select", default="Fit to grid",
                  options=("Fit to grid", "Absolute coordinates"),
                  help="Fit to grid: same mapping as 'Combine with existing geometry' on "
                       "Generate TPMS. Absolute: the mesh keeps its own coordinates "
                       "(STL only)."),
            Param("output", "Output", "select", default="Signed distance",
                  options=("Signed distance", "Unsigned distance", "Mask (1 inside, 0 outside)")),
        ],
        custom="geometry",
    ),
    "Import .npy": dict(
        kind="generator",
        caption="A 3D array from disk, resampled to the grid if its shape differs.",
        params=[],
        custom="import",
    ),
    # ------------------------- modifiers -------------------------
    "Remap range": dict(
        kind="modifier",
        caption=(
            "Rescales the whole field linearly so that its minimum becomes v_min and its maximum becomes v_max:  \n"
            "In essence, it calculates g(a) = v_min + (v_max - v_min) (a - a_min) / (a_max - a_min),  \n"
            "where a is the result of the previous step "
        ),
        params=[
            Param("v_min", "New minimum v_min", default=0.0),
            Param("v_max", "New maximum v_max", default=1.0),
        ],
    ),
    "Clip": dict(
        kind="modifier",
        caption=(
            "Caps the field:  \n"
            "values below lo become v_below, values above hi become v_above, everything in "
            "between is left untouched. By default v_below = lo and v_above = hi (plain clip)."
        ),
        params=[
            Param("lo", "Lower bound lo", default=0.0),
            Param("hi", "Upper bound hi", default=1.0),
            Param("outside", "Values outside [lo, hi]", "select", default="Keep bounds",
                  options=("Keep bounds", "Custom values"),
                  help="Keep bounds: a < lo -> lo, a > hi -> hi. "
                       "Custom values: a < lo -> v_below, a > hi -> v_above."),
            Param("v_below", "Value below lo (v_below)", default=0.0,
                  show_if=("outside", ("Custom values",))),
            Param("v_above", "Value above hi (v_above)", default=1.0,
                  show_if=("outside", ("Custom values",))),
        ],
    ),
    "Gaussian smoothing": dict(
        kind="modifier",
        caption=(
            "Blurs the field: each voxel is replaced by a Gaussian-weighted average of its surroundings using a convolution kernel.  \n"
            r"$g = a \ast G_\sigma$  " "\n"
            "where a is the result of the previous step  \n"
            "And G_sigma is the 3D Gaussian kernel with standard deviation sigma.  \n"
            "Sigma is to be given in physical units, not in voxels."
        ),
        params=[Param("sigma", "Sigma", default=0.5, min_value=0.0)],
    ),
    "Transfer function": dict(
        kind="modifier",
        caption=(
            "Applies a function g to every voxel independently (no neighbours involved), a = result of "
            "the previous step:\n"
            "- **Negate**: g = -a. Swaps inside and outside of a signed distance, reverses a gradient.\n"
            "- **Absolute value**: g = |a|. Folds negative values up; turns a signed distance into an "
            "unsigned one (0 on the surface, growing on both sides).\n"
            "- **Power**: g = sign(a) |a|^gamma. Keeps the sign. For |a| < 1, gamma > 1 pulls values "
            "toward 0 and gamma < 1 pushes them toward +/-1; above 1 it is the reverse. The effect "
            "depends on the field's scale, so Remap to [0, 1] or [-1, 1] first for predictable results.\n"
            "- **Smoothstep**: t = clip((a - e0) / (e1 - e0), 0, 1), g = t^2 (3 - 2t). 0 below e0, 1 above "
            "e1, an S-curve in between with zero slope at both ends; output always in [0, 1]. With "
            "e0 > e1 the curve is reversed (1 below e1, 0 above e0).\n"
            "- **Step**: g = 1 where a >= e0, else 0. A hard binary mask: used directly as a thickness "
            "or period it gives a sharp, voxel-staircased jump - prefer Smoothstep for a transition."
        ),
        params=[
            Param("function", "Function", "select", default="Smoothstep",
                  options=("Negate", "Absolute value", "Power", "Smoothstep", "Step")),
            Param("gamma", "Exponent gamma", default=2.0, min_value=1e-6,
                  show_if=("function", ("Power",))),
            Param("e0", "Edge e0", default=0.0, show_if=("function", ("Smoothstep", "Step"))),
            Param("e1", "Edge e1", default=1.0, show_if=("function", ("Smoothstep",))),
        ],
    ),
}

GENERATOR_TYPES = [k for k, v in STEP_TYPES.items() if v["kind"] == "generator"]
MODIFIER_TYPES = [k for k, v in STEP_TYPES.items() if v["kind"] == "modifier"]

BLEND_OPS = ("Replace", "Add", "Subtract", "Multiply", "Min", "Max", "Smooth min", "Smooth max")
SMOOTH_BLENDS = ("Smooth min", "Smooth max")
BLEND_OPS_HELPER = {
    "Replace":  "op(a, b) = b  (a = result so far, b = this layer). With w < 1 this cross-fades from a to b.",
    "Add":      "op(a, b) = a + b",
    "Subtract": "op(a, b) = a - b",
    "Multiply": "op(a, b) = a * b",
    "Min":      "op(a, b) = min(a, b). On signed-distance layers (negative inside): union of the shapes.",
    "Max":      "op(a, b) = max(a, b). On signed-distance layers (negative inside): intersection of the shapes.",
    "Smooth min": (
        "op(a, b) = smin(a, b, k), polynomial smooth minimum: "
        "h = clip(0.5 + 0.5 (b - a) / k, 0, 1), smin = b (1 - h) + a h - k h (1 - h). "
        "Exactly min(a, b) where |a - b| >= k; rounded where |a - b| < k, "
        "at most k/4 below min(a, b) (at a = b). Larger k = wider, smoother fillet."
    ),
    "Smooth max": (
        "op(a, b) = smax(a, b, k) = -smin(-a, -b, k). "
        "Exactly max(a, b) where |a - b| >= k; rounded where |a - b| < k, "
        "at most k/4 above max(a, b) (at a = b). Larger k = wider, smoother fillet."
    ),
}

INTENDED_USES = ("Implicit field", "Threshold", "Thickness", "Period")




# =====================================================================
# 2) make_grid
# =====================================================================
@st.cache_resource(max_entries=4, show_spinner=False)
def make_grid(size_x: float, size_y: float, size_z: float, resolution: int):
    """
    ============================================================================
    2) _GRID
    Same coordinate grids as 1_Generate_TPMS.py (linspace(0, size, res) per
    axis, indexing="ij"), so a field built here lands on the exact same
    voxel centers there. Cached as a resource (shared, not copied) and
    returned read-only so nothing can mutate the shared copy by accident.
    ============================================================================

    RETURNS
    -------
    X, Y, Z : np.ndarray
        (res, res, res) coordinate arrays.
    """
    X, Y, Z = np.meshgrid(
        np.linspace(0, size_x, resolution),
        np.linspace(0, size_y, resolution),
        np.linspace(0, size_z, resolution),
        indexing="ij",
    )
    for a in (X, Y, Z):
        a.setflags(write=False)
    return X, Y, Z


# =====================================================================
# 3) _spacing
# =====================================================================
def _spacing(grid_key: tuple) -> Tuple[float, float, float]:
    """Voxel spacing (dx, dy, dz) = size / (res - 1) for linspace grids."""
    sx, sy, sz, res = grid_key
    n = max(res - 1, 1)
    return sx / n, sy / n, sz / n


# =====================================================================
# 4) _compute_layer
# =====================================================================
@st.cache_resource(max_entries=32, show_spinner=False)
def _compute_layer(step_type: str, params_json: str, grid_key: tuple,
                   file_stamp: float) -> Tuple[np.ndarray, str]:
    """
    ============================================================================
    4) _COMPUTE_LAYER
    Evaluates one generator step on the grid. Pure (no st.* calls) so it can
    be cached: moving a weight slider or adding a step later in the stack
    doesn't recompute the layers that didn't change. Raises ValueError /
    EquationError for bad inputs - exceptions are not cached.
    ============================================================================

    PARAMETERS
    ----------
    step_type : str
        A generator key of STEP_TYPES.
    params_json : str
        json.dumps(params, sort_keys=True) - a string so the cache key is
        cheap and deterministic.
    grid_key : tuple
        (size_x, size_y, size_z, resolution).
    file_stamp : float
        Modification time of the step's input file (0 if none), so an
        edited file on disk invalidates the cache.

    RETURNS
    -------
    layer : np.ndarray
        (res, res, res) float64, read-only.
    note : str
        Informational message for the UI ("" if none).
    """
    p = json.loads(params_json)
    X, Y, Z = make_grid(*grid_key)
    note = ""

    if step_type == "Constant":
        layer = np.full(X.shape, float(p["value"]))

    elif step_type == "Linear gradient":
        d = np.asarray(p["direction"], dtype=float)
        norm = np.linalg.norm(d)
        if norm == 0:
            raise ValueError("Direction vector must be non-zero.")
        n = d / norm
        s = X * n[0] + Y * n[1] + Z * n[2]
        s_min, s_max = s.min(), s.max()   # reached at two opposite corners of the box
        t = (s - s_min) / (s_max - s_min) if s_max > s_min else np.zeros_like(s)
        layer = p["v0"] + (p["v1"] - p["v0"]) * t

    elif step_type == "Radial gradient":
        c = p["center"]
        if p["shape"] == "Spherical":
            r = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2)
        else:
            (A, ca), (B, cb) = _other_axes(p["axis"], X, Y, Z, c)
            r = np.sqrt((A - ca) ** 2 + (B - cb) ** 2)
        t = np.clip(r / p["radius"], 0.0, 1.0)
        if p["profile"] == "Smoothstep":
            t = t * t * (3.0 - 2.0 * t)
        layer = p["v_in"] + (p["v_out"] - p["v_in"]) * t

    elif step_type == "Primitive (signed distance)":
        c = p["center"]
        if p["shape"] == "Sphere":
            layer = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2) - p["radius"]
        elif p["shape"] == "Box":
            h = np.asarray(p["box_size"], dtype=float) / 2.0
            qx, qy, qz = np.abs(X - c[0]) - h[0], np.abs(Y - c[1]) - h[1], np.abs(Z - c[2]) - h[2]
            outside = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2 + np.maximum(qz, 0) ** 2)
            inside = np.minimum(np.maximum(np.maximum(qx, qy), qz), 0.0)
            layer = outside + inside
        else:  # Cylinder
            (A, ca), (B, cb) = _other_axes(p["axis"], X, Y, Z, c)
            axial_coord, axial_center = {"x": (X, c[0]), "y": (Y, c[1]), "z": (Z, c[2])}[p["axis"]]
            d_r = np.sqrt((A - ca) ** 2 + (B - cb) ** 2) - p["radius"]
            d_a = np.abs(axial_coord - axial_center) - p["height"] / 2.0
            layer = (np.sqrt(np.maximum(d_r, 0) ** 2 + np.maximum(d_a, 0) ** 2)
                     + np.minimum(np.maximum(d_r, d_a), 0.0))

    elif step_type == "Gaussian blob":
        c = p["center"]
        r2 = (X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2
        layer = p["amplitude"] * np.exp(-r2 / (2.0 * p["sigma"] ** 2))

    elif step_type == "Equation":
        layer = np.asarray(evaluate_custom_inputs(p["equation"], X, Y, Z), dtype=float)
        if not np.all(np.isfinite(layer)):
            raise ValueError("Equation produced non-finite values (inf/nan) on the grid.")

    elif step_type == "Import .stl":
        mask, note = _geometry_mask(p["path"], file_stamp, p["placement"], grid_key)
        if p["output"].startswith("Mask"):
            layer = mask.astype(float)
        else:
            if not mask.any() or mask.all():
                raise ValueError("The geometry fills none or all of the grid - there is no "
                                 "surface inside the box to measure a distance to.")
            from scipy.ndimage import distance_transform_edt
            spacing = _spacing(grid_key)
            h = float(np.mean(spacing))
            # distance_transform_edt(a): for every non-zero voxel of a, distance to the
            # nearest zero voxel (physical units via `sampling`).
            d_out = distance_transform_edt(~mask, sampling=spacing)   # outside -> nearest inside voxel
            d_in = distance_transform_edt(mask, sampling=spacing)     # inside  -> nearest outside voxel
            # surface assumed half a voxel from the last inside / first outside voxel center
            sd = np.where(mask, -(d_in - h / 2.0), d_out - h / 2.0)
            layer = np.abs(sd) if p["output"] == "Unsigned distance" else sd

    elif step_type == "Import .npy":
        path = p["path"]
        if not path:
            raise ValueError("No file selected.")
        arr = np.load(path)
        if arr.ndim != 3:
            raise ValueError(f"Expected a 3D array, got shape {arr.shape}.")
        res = grid_key[3]
        if arr.shape != (res,) * 3:
            from triply import voxel_tools
            note = f"Resampled from {arr.shape} to {(res,) * 3} (trilinear)."
            arr = voxel_tools.interpolate_voxel_grid(arr.astype(float), res, res, res)
        layer = arr.astype(float)

    else:
        raise ValueError(f"Unknown generator step type: {step_type}")

    layer = np.ascontiguousarray(np.broadcast_to(layer, X.shape), dtype=float)
    layer.setflags(write=False)
    return layer, note


def _other_axes(axis: str, X, Y, Z, c):
    """For a cylinder/radial axis, returns the two perpendicular (coord, center) pairs."""
    pairs = {"x": ((Y, c[1]), (Z, c[2])), "y": ((X, c[0]), (Z, c[2])), "z": ((X, c[0]), (Y, c[1]))}
    return pairs[axis]


# =====================================================================
# 5) _geometry_mask
# =====================================================================
@st.cache_resource(max_entries=8, show_spinner="Voxelizing geometry...")
def _geometry_mask(path: str, file_stamp: float, placement: str,
                   grid_key: tuple) -> Tuple[np.ndarray, str]:
    """
    ============================================================================
    5) _GEOMETRY_MASK
    Turns an STL or a .npy voxel mask into a boolean (res, res, res) mask on
    this page's grid (True = inside the geometry).
    ============================================================================

    PARAMETERS
    ----------
    path : str
        .stl or .npy file.
    file_stamp : float
        File modification time, only used as part of the cache key.
    placement : str
        "Fit to grid": reproduces 1_Generate_TPMS.py's "Combine with
        existing geometry" mapping exactly (matrix_from_mesh at the grid
        resolution -> pad_to_square -> resample to res^3 -> > 0.5), so a
        distance field built here lines up with a combine done there.
        "Absolute coordinates" (STL only): voxelizes at the grid spacing
        and places each voxel by its physical coordinates; parts of the
        grid outside the mesh bounding box are "outside".

    RETURNS
    -------
    mask : np.ndarray (bool), note : str
    """
    if not path:
        raise ValueError("No file selected.")
    sx, sy, sz, res = grid_key
    ext = os.path.splitext(path)[1].lower()
    from triply import voxel_tools

    if ext == ".npy":
        if placement != "Fit to grid":
            raise ValueError("A .npy mask has no coordinates - use 'Fit to grid'.")
        m = np.load(path)
        if m.ndim != 3:
            raise ValueError(f"Expected a 3D array, got shape {m.shape}.")
        m = pad_to_square(m)
        if m.shape != (res,) * 3:
            m = voxel_tools.interpolate_voxel_grid(m.astype(float), res, res, res)
        return m > 0.5, ""

    if ext != ".stl":
        raise ValueError("Geometry must be a .stl or .npy file.")

    from triply.mesh_tools import matrix_from_mesh
    verts, faces = load_STL(path)

    if placement == "Fit to grid":
        _, _, _, m = matrix_from_mesh(verts, faces, res)
        m = pad_to_square(m)
        if m.shape != (res,) * 3:
            m = voxel_tools.interpolate_voxel_grid(m.astype(float), res, res, res)
        return m > 0.5, ""

    # --- absolute coordinates ---
    h = min(_spacing(grid_key))
    largest_span = float(np.max(verts.max(axis=0) - verts.min(axis=0)))
    vox_res = int(np.ceil(largest_span / h)) + 1        # pitch = span / (vox_res - 1) <= h
    xg, yg, zg, m = matrix_from_mesh(verts, faces, vox_res)
    m = m.astype(bool)
    idx = []
    for coords_1d, g in ((np.linspace(0, sx, res), xg),
                         (np.linspace(0, sy, res), yg),
                         (np.linspace(0, sz, res), zg)):
        pitch = (g[1] - g[0]) if len(g) > 1 else 1.0
        i = np.rint((coords_1d - g[0]) / pitch).astype(int)   # nearest voxel of the mesh grid
        valid = (i >= 0) & (i < len(g))
        idx.append((np.clip(i, 0, len(g) - 1), valid))
    (ix, vx), (iy, vy), (iz, vz) = idx
    mask = m[np.ix_(ix, iy, iz)] & vx[:, None, None] & vy[None, :, None] & vz[None, None, :]
    note = "" if mask.any() else "The mesh does not overlap the grid box at all in absolute coordinates."
    return mask, note


# =====================================================================
# 6) _apply_modifier
# =====================================================================
def _apply_modifier(step_type: str, p: dict, f: np.ndarray, grid_key: tuple) -> np.ndarray:
    """
    ============================================================================
    6) _APPLY_MODIFIER
    g(a) for a modifier step, a = result of the previous step (named `f` in the
    code below; see the doc expander for each formula).
    ============================================================================
    """
    if step_type == "Remap range":
        f_min, f_max = float(f.min()), float(f.max())
        if f_max == f_min:
            return np.full_like(f, p["v_min"])
        return p["v_min"] + (p["v_max"] - p["v_min"]) * (f - f_min) / (f_max - f_min)

    if step_type == "Clip":
        if p["lo"] > p["hi"]:
            raise ValueError("Lower bound is above upper bound.")
        if p["outside"] == "Keep bounds":
            return np.clip(f, p["lo"], p["hi"])
        # custom: f < lo -> v_below, f > hi -> v_above, lo <= f <= hi unchanged
        out = np.where(f < p["lo"], p["v_below"], f)
        return np.where(f > p["hi"], p["v_above"], out)

    if step_type == "Gaussian smoothing":
        if p["sigma"] <= 0:
            return f.copy()
        from scipy.ndimage import gaussian_filter
        sigma_vox = [p["sigma"] / d for d in _spacing(grid_key)]   # physical -> voxel units, per axis
        return gaussian_filter(f, sigma=sigma_vox, mode="nearest")

    if step_type == "Transfer function":
        fn = p["function"]
        if fn == "Negate":
            return -f
        if fn == "Absolute value":
            return np.abs(f)
        if fn == "Power":
            return np.sign(f) * np.abs(f) ** p["gamma"]
        if fn == "Smoothstep":
            if p["e1"] == p["e0"]:
                raise ValueError("Smoothstep needs e0 != e1.")
            t = np.clip((f - p["e0"]) / (p["e1"] - p["e0"]), 0.0, 1.0)
            return t * t * (3.0 - 2.0 * t)
        if fn == "Step":
            return (f >= p["e0"]).astype(float)

    raise ValueError(f"Unknown modifier step type: {step_type}")


# =====================================================================
# 7) _blend
# =====================================================================
def _blend(op: str, a: np.ndarray, b: np.ndarray, k: float) -> np.ndarray:
    """
    ============================================================================
    7) _BLEND
    op(a, b) with a = result so far, b = this step's layer. Smooth min/max
    use the polynomial smooth minimum (Quilez):
        h    = clip(0.5 + 0.5 (b - a) / k, 0, 1)
        smin = b (1 - h) + a h - k h (1 - h)
        smax(a, b) = -smin(-a, -b)
    which equals min(a, b) wherever |a - b| >= k and rounds the crease
    below that, the deviation being at most k/4 (at a = b).
    ============================================================================
    """
    if op == "Replace":
        return b
    if op == "Add":
        return a + b
    if op == "Subtract":
        return a - b
    if op == "Multiply":
        return a * b
    if op == "Min":
        return np.minimum(a, b)
    if op == "Max":
        return np.maximum(a, b)
    if op in SMOOTH_BLENDS:
        corr = np.maximum(k - np.abs(a - b), 0.0) ** 2 / (4.0 * k)
        return np.minimum(a, b) - corr if op == "Smooth min" else np.maximum(a, b) + corr
    raise ValueError(f"Unknown blend: {op}")


# =====================================================================
# 8) run_pipeline
# =====================================================================
def run_pipeline(configs: list, grid_key: tuple):
    """
    ============================================================================
    8) _RUN_PIPELINE
    acc_0 = 0 ; acc_i = (1 - w_i) acc_{i-1} + w_i op_i(acc_{i-1}, layer_i)
    Disabled steps and steps that failed are skipped (acc passes through
    unchanged) and reported.
    ============================================================================

    RETURNS
    -------
    final : np.ndarray (float64)
    snapshots : list of (label, np.ndarray float32)  - result after each applied step
    rows : list of dict                              - per-step stats for the table
    messages : dict step_id -> (level, text)         - errors/notes shown under each step
    """
    X, _, _ = make_grid(*grid_key)
    acc = np.zeros(X.shape, dtype=float)
    snapshots, rows, messages = [], [], {}

    for i, cfg in enumerate(configs):
        label = f"{i + 1}. {cfg['type']}"
        if not cfg["enabled"]:
            rows.append({"step": label, "status": "off"})
            continue
        if cfg.get("invalid"):
            rows.append({"step": label, "status": "invalid input"})
            continue
        w = cfg["weight"]
        try:
            if STEP_TYPES[cfg["type"]]["kind"] == "generator":
                layer, note = _compute_layer(
                    cfg["type"], json.dumps(cfg["params"], sort_keys=True),
                    grid_key, cfg["file_stamp"],
                )
                if note:
                    messages[cfg["id"]] = ("info", note)
                new = _blend(cfg["blend"], acc, layer, cfg["k"])
            else:
                new = _apply_modifier(cfg["type"], cfg["params"], acc, grid_key)
        except (ValueError, EquationError, OSError, RuntimeError) as e:
            messages[cfg["id"]] = ("error", str(e))
            rows.append({"step": label, "status": "error"})
            continue

        acc = (1.0 - w) * acc + w * new if w != 1.0 else np.asarray(new, dtype=float)
        snapshots.append((label, acc.astype(np.float32)))
        rows.append({"step": label, "status": "ok",
                     "min": float(acc.min()), "max": float(acc.max()), "mean": float(acc.mean())})

    return acc, snapshots, rows, messages


# =====================================================================
# 9) step list callbacks
# =====================================================================
def get_steps() -> list:
    return st.session_state.setdefault("fg_steps", [])


def add_step() -> None:
    """on_click of "Add step": appends the step picked in the selectbox."""
    step_type = st.session_state["fg_new_step_type"]
    sid = uuid.uuid4().hex[:8]
    is_first = len(get_steps()) == 0
    st.session_state[f"fg_{sid}_blend"] = "Replace" if is_first else "Add"
    get_steps().append({"id": sid, "type": step_type})


def _move_step(sid: str, delta: int) -> None:
    steps = get_steps()
    i = next(j for j, s in enumerate(steps) if s["id"] == sid)
    j = i + delta
    if 0 <= j < len(steps):
        steps[i], steps[j] = steps[j], steps[i]


def _delete_step(sid: str) -> None:
    st.session_state["fg_steps"] = [s for s in get_steps() if s["id"] != sid]


def clear_steps() -> None:
    st.session_state["fg_steps"] = []


# =====================================================================
# 10) _render_params
# =====================================================================
def _render_params(sid: str,
                   spec: dict,
                   grid: dict) -> dict:
    """
    ============================================================================
    10) _RENDER_PARAMS
    Draws the widgets for every Param of one step (spec["params"], in list
    order) and returns their current values as a plain dict. Called once
    per step per rerun by render_step(); the returned dict becomes
    cfg["params"], i.e. the `p` read by _compute_layer / _apply_modifier.
    ============================================================================

    PARAMETERS
    ----------
    sid : str
        Step id (8 hex chars from uuid4). Every widget key of this step is
        f"fg_{sid}_{param.name}" (plus "_0/_1/_2" for vec3), so two steps
        of the same type never share a widget, and moving or deleting a
        step leaves the others' values untouched.
    spec : dict
        The step type's entry in STEP_TYPES; only spec["params"] (a list of
        Param) is used here.
    grid : dict
        {"size_x", "size_y", "size_z", "resolution"} of the current grid,
        passed to callable Param defaults (e.g. a center at mid-box).

    RETURNS
    -------
    values : dict
        {param.name: value} for the params drawn on this rerun:
          - "float"  -> float
          - "select" -> str (one of param.options)
          - "vec3"   -> [vx, vy, vz] (list of 3 floats)
        Params hidden by show_if are ABSENT from the dict (not None).
    """
    values = {}
    # for each parameter in the step's spec, draw the appropriate widget and store its value
    for prm in spec["params"]:
        # some parameters are conditional on the value of another parameter (e.g. "gamma" only shows if "function" is "Power")
        if prm.show_if is not None:
            # prm.show_if is a tuple containing (other_param_name, allowed_values)
            other, allowed = prm.show_if
            # so if the other parameter's value is not in the allowed values, skip this parameter (don't draw it)
            if values.get(other) not in allowed:
                continue
        # grab the default value for this parameter, which can be a callable (function) or a static value
        default = prm.default(grid) if callable(prm.default) else prm.default
        # define a unique key for this widget based on the step ID and parameter name
        key = f"fg_{sid}_{prm.name}"

        if prm.kind == "select":
            st.session_state.setdefault(key, default)
            values[prm.name] = st.selectbox(prm.label, prm.options, key=key, help=prm.help)

        elif prm.kind == "vec3":
            cols = st.columns(3)
            vec = []
            for j, (col, ax) in enumerate(zip(cols, AXES)):
                k = f"{key}_{j}"
                st.session_state.setdefault(k, float(default[j]))
                vec.append(col.number_input(f"{prm.label} {ax}", key=k, help=prm.help))
            values[prm.name] = vec

        else:  # float
            st.session_state.setdefault(key, float(default))
            values[prm.name] = st.number_input(
                prm.label, key=key, help=prm.help, min_value=prm.min_value,
            )
    return values


# =====================================================================
# 11) render_step
# =====================================================================
def render_step(i: int, 
                n_steps: int, 
                step: dict, 
                grid: dict) -> dict:
    """
    ============================================================================
    11) _RENDER_STEP
    Draws one step card (header with on/off + move/delete, blend and weight,
    then the step's own inputs) and returns its config dict for
    run_pipeline. The card also holds a placeholder that the page fills
    with this step's error/note once the pipeline has run.
    ============================================================================
    PARAMETERS
    ----------
    i : int
        Index of this step in the list (0-based).
    n_steps : int
        Total number of steps in the list.
    step : dict
        {"id": str, "type": str} - the step's type and its unique ID (used to seed widget keys).
    grid : dict
        {"size_x": float, "size_y": float, "size_z": float, "resolution": int} - the current grid settings.
    RETURNS
    -------
    cfg : dict
        {"id": str, "type": str, "enabled": bool, "blend": str or None, "weight": float, "k": float, "params": dict, "file_stamp": float, "message_slot": st.empty(), "invalid": bool (optional)}   
        The configuration dictionary for the rendered step.
    """
    # extract the step's ID and type
    sid, step_type = step["id"], step["type"]
    # dictionary of the step type's spec (kind, caption, params, custom)
    spec = STEP_TYPES[step_type]
    # whether this step is a generator (layer) or a modifier
    is_gen = spec["kind"] == "generator"
    # dictionary of all the values that will be passed to run_pipeline for this step
    cfg = {"id": sid, "type": step_type, "file_stamp": 0.0, "k": 0.5, "blend": None}

    with st.container(border=True):     # makes a pretty rectangle around the step's widgets
        # ----- header -----
        c_title, c_on, c_up, c_down, c_del = st.columns([6, 1.4, 0.8, 0.8, 0.8],
                                                        vertical_alignment="center")
        # write a small note about whether this is a layer or a modifier 
        kind_label = "layer" if is_gen else "modifier"
        c_title.markdown(f"**{i + 1}. {step_type}** &nbsp; :gray[({kind_label})]")
        # on/off toggle: default True, key seeded by step ID
        st.session_state.setdefault(f"fg_{sid}_enabled", True)
        cfg["enabled"] = c_on.toggle("On", key=f"fg_{sid}_enabled")
        #----- move / delete buttons -----
        c_up.button("", icon=":material/arrow_upward:", key=f"fg_{sid}_up", help="Move up",
                    on_click=_move_step, args=(sid, -1), disabled=(i == 0))
        c_down.button("", icon=":material/arrow_downward:", key=f"fg_{sid}_down", help="Move down",
                      on_click=_move_step, args=(sid, +1), disabled=(i == n_steps - 1))
        c_del.button("", icon=":material/delete:", key=f"fg_{sid}_del", help="Delete step",
                     on_click=_delete_step, args=(sid,))
        st.caption(spec["caption"])

        # ----- blend / weight -----
        st.session_state.setdefault(f"fg_{sid}_weight", 1.0)
        # if it's a generator, show blend options; if it's a modifier, just show strength slider
        if is_gen:
            st.session_state.setdefault(f"fg_{sid}_blend", "Add")
            b1, b2, b3 = st.columns([2, 2, 1.2])
            # select the blending type (Replace, Add, Subtract, Multiply, Min, Max, Smooth min, Smooth max)
            cfg["blend"] = b1.selectbox("Blend method with previous result", 
                BLEND_OPS, 
                key=f"fg_{sid}_blend",
                help=BLEND_OPS_HELPER[st.session_state[f"fg_{sid}_blend"]],
            )
            # select the weight of this step in the blending (0 = ignore, 1 = full effect)
            cfg["weight"] = b2.slider(
                "Weight w", 0.0, 1.0, step=0.01, key=f"fg_{sid}_weight",
                help="result = (1 - w) * a + w * op(a, b).",
            )
            b2.caption('Define how "strongly" this step contributes to the final result. w = 1 applies the blend fully')

            # if the blend is a smooth min/max, show an additional input for the smoothing parameter k
            if cfg["blend"] in SMOOTH_BLENDS:
                st.session_state.setdefault(f"fg_{sid}_k", 0.5)
                cfg["k"] = b3.number_input("Smoothing k", min_value=1e-6, key=f"fg_{sid}_k",
                                           help="Width (in field units) over which the crease is rounded.")
                b3.caption("Blends only where |a - b| < k; elsewhere it is exactly min/max. "
                            "The largest deviation from the sharp min/max is k/4, where a = b.")
        # if it's a modifier, just show a strength slider (0 = ignore, 1 = full effect)
        else:
            cfg["weight"] = st.slider(
                "Strength w", 0.0, 1.0, step=0.01, key=f"fg_{sid}_weight",
                help="result = (1 - w) a + w g(a).",
            )

        # ----- step-specific inputs -----
        # now every step type has its own parameters, which are defined in the STEP_TYPES dictionary.
        params = {}
        # rappel : spec = STEP_TYPES[step_type]
        # not all step types have a "custom" field, but if they do, it can be "equation", "geometry", or "import"
        # those are basically the ones that require a file input or a custom equation input, which are handled specially here.
        custom = spec.get("custom")
        if custom == "equation":
            eq = render_equation_input(
                label="Layer", default_equation="x / max(x)", key_prefix=f"fg_{sid}_eq",
                size_x=grid["size_x"], size_y=grid["size_y"], size_z=grid["size_z"],
            )
            if eq is None:
                cfg["invalid"] = True
            params["equation"] = eq
        elif custom in ("geometry", "import"):
            filetypes = ([("STL files", "*.stl"), ("Numpy files", "*.npy"), ("All files", "*.*")]
                         if custom == "geometry" else [("Numpy files", "*.npy"), ("All files", "*.*")])
            st.session_state.setdefault(f"fg_{sid}_path", "")
            browse_file(key=f"fg_{sid}_path", title="Select a file", filetypes=filetypes)
            path = st.session_state.get(f"fg_{sid}_path", "")
            params["path"] = path
            if path and os.path.isfile(path):
                cfg["file_stamp"] = os.path.getmtime(path)
            else:
                cfg["invalid"] = True
                st.caption("Select a file to activate this step.")
        
        # now display the rest of the parameters for this step type, which are defined in spec["params"]
        params.update(_render_params(sid, spec, grid))
        cfg["params"] = params
        cfg["message_slot"] = st.empty()
    return cfg


# =====================================================================
# 12) check_intended_use
# =====================================================================
def check_intended_use(use: str, f: np.ndarray) -> None:
    """
    ============================================================================
    12) _CHECK_INTENDED_USE
    Sanity checks on the final field against what the chosen Generate TPMS
    input expects. Only necessary conditions - passing them does not mean
    the field is a good choice.
    ============================================================================
    """
    f_min, f_max = float(f.min()), float(f.max())
    if use == "Implicit field":
        if f_min >= 0 or f_max <= 0:
            st.warning(f"The field never changes sign (range [{f_min:.3g}, {f_max:.3g}]): with "
                       "threshold 0 there is no surface. Shift it or pick another threshold there.")
        else:
            st.success("The field changes sign, so the threshold-0 surface exists.")
    elif use == "Threshold":
        st.info(f"Range [{f_min:.3g}, {f_max:.3g}]. The threshold is compared to the implicit "
                "field's values (about [-1.5, 1.5] for a Gyroid, [-3, 3] for Schwartz P): values "
                "outside the implicit field's range give fully solid or fully empty regions.")
    elif use == "Thickness":
        if f_min <= 0:
            st.error(f"Minimum is {f_min:.3g}: thickness must be > 0 everywhere.")
        else:
            st.success(f"Range [{f_min:.3g}, {f_max:.3g}], > 0 everywhere.")
        st.caption("Units: physical length in Distance mode, implicit-field units in Band mode.")
    elif use == "Period":
        if f_min < 0.01:
            st.error(f"Minimum is {f_min:.3g}: period must be > 0 (the constant input's floor is 0.01).")
        else:
            st.success(f"Range [{f_min:.3g}, {f_max:.3g}], > 0 everywhere.")
        st.caption("See 'How this works' for why a steep period gradient distorts the cells.")


# =====================================================================
# 14) widget-state mirror (survives page switches)
# =====================================================================
# Streamlit deletes a widget's session_state key at the end of any run in
# which that widget isn't drawn - i.e. as soon as the user opens another
# page. fg_steps (plain state) would survive but every step's parameters
# would reset. So: copy all fg_ widget values into one plain dict at the
# end of each run, and put back any that went missing at the start of the
# next one (before the widgets are created, the only time that's allowed).
_MIRROR_KEY = "fg__mirror"
# buttons can't be written through session_state; fg_show_step's options
# change with the steps, so it's recomputed rather than restored.
# Charts (their keys hold selection state, not user input) are skipped too.
_NOT_MIRRORED_SUFFIXES = ("_up", "_down", "_del", "_browse_btn", "_preview", "_fieldfig")
_NOT_MIRRORED_KEYS = ("fg_steps", "fg_show_step", "fg_hist", _MIRROR_KEY)


def restore_widget_state() -> None:
    for k, v in st.session_state.get(_MIRROR_KEY, {}).items():
        if k not in st.session_state:
            st.session_state[k] = v


def mirror_widget_state() -> None:
    st.session_state[_MIRROR_KEY] = {
        k: st.session_state[k] for k in list(st.session_state.keys())
        if isinstance(k, str) and k.startswith("fg_")
        and k not in _NOT_MIRRORED_KEYS and not k.endswith(_NOT_MIRRORED_SUFFIXES)
    }

