"""
Ordered, reorderable processing pipeline for a loaded CT volume, built on
top of triply.CT_scans's individual filter functions (threshold,
dilate, erode, crop, connected-component, hole/island finding). Kept in
its own component (rather than inline in app/pages/3_CT_Analysis.py) so
that page stays focused on load/convert/preview; this file owns
everything about "let the user apply these functions, in whatever order
they want, with their own parameters".

DESIGN
------
- _STEP_REGISTRY maps a human-readable operation name to its CT_scans
  function, a small parameter spec (used to auto-generate the "add step"
  widgets), and a `call` adapter that normalizes that function's actual
  argument order/naming into a uniform `call(image, params_dict) -> image`
  shape - each CT_scans function has a slightly different signature
  (image first, image last, extra seed coordinates, ...), so the adapter
  is what lets the rest of this module treat every step identically.
- The pipeline itself is an ordered list of {"id", "type"} dicts in
  st.session_state[f"{key}_steps"] (same model as the Field generator page).
  `id` is 8 hex characters from uuid4, generated once when the step is
  added; `type` is a _STEP_REGISTRY key. The step's PARAMETER VALUES are
  NOT stored in that list: they live in the step's own widgets, keyed
  f"{key}_{id}_{param name}", so every step stays editable after it has
  been added, and moving or deleting a step never mixes up the values of
  the others. Reordering/removing a step doesn't touch any image data -
  "Run pipeline" replays every enabled step from the original loaded
  array, so the list can be freely edited before (re-)running it. One
  exception: when the only change since the last run is NEW steps added
  after the previously run ones, only the new steps are run, starting
  from the previous result. Only that last full result is kept in memory
  (CT volumes are large), plus the 2D mid z-slice after each step for
  the "Show result after step" preview.
- The whole section is drawn by a @st.fragment (_render_pipeline_section),
  so editing the pipeline reruns only this section, not the whole page.
- The pipeline's settings (step list + every step's values) are kept
  across page switches and can be saved to / loaded from a file, with
  app.components.page_state and the prefix f"{key}_" (see SAVE / LOAD in
  render_ct_pipeline).
- watershed_algorithm is deliberately not included here: it needs two
  extra mask inputs (sure_fg, sure_bg) beyond "the current image", which
  doesn't fit this one-image-in-one-image-out step model. Left for a
  future, separate step type that can reference other steps' outputs.
- apply_mask_on_image DOES fit the model despite also needing a second
  image: its mask isn't sourced from another step's output, just a
  separate .mhd file path typed in as a param (see the "Apply mask" step
  below and _load_mask_array), so the uniform call(image, params) -> image
  shape still holds.
- Turning the pipeline result into a 3D mesh lives in
  app/pages/3_CT_Analysis.py, not here - see the "Generate 3D mesh"
  section there, which calls triply.mesh_tools.mesh_from_matrix
  directly on this module's returned result.
- The step cards (_render_step) show "Crop"'s resulting shape
  by tracking a running (Z, Y, X) shape through the step list and
  recomputing it with _shape_after_crop, a small function that DUPLICATES
  CT_scans.crop_images's own direction/point arithmetic rather than
  running the real crop just to read `.shape` off the result. That's a
  real coupling: if crop_images's direction handling ever changes,
  _shape_after_crop needs the same change or the displayed size quietly
  goes wrong without the pipeline itself breaking.
"""
import json
import os
import uuid
from dataclasses import dataclass
from typing import Any, Optional, Tuple

import numpy as np
import plotly.graph_objects as go
import SimpleITK as sitk
import streamlit as st

from triply import CT_scans
from app.state import get_output_dir
from app.components.ct_viewer_launcher import (
    render_lightweight_toggle, launch_ct_viewer, launch_ct_viewer_for_selection,
)
from app.components.file_picker import browse_file
from app.components.page_state import restore_widget_state, mirror_widget_state, render_state_io

__all__ = ["render_ct_pipeline"]


# =====================================================================
# 0 - (reserved)
# 1 - _load_mask_array
# 2 - _shape_after_crop
# 2b - manual selection (viewer) helpers  (_selection_path, _load_selection, _voxels_inside,
#      _value_for_dtype, _apply_manual_selection, _describe_manual_selection)
# 2c - holes / islands helpers  (_set_detected_voxels)
# 3 - Param (dataclass)
# 4 - _STEP_REGISTRY
# 5 - _describe_params
# 6 - step list callbacks   (_add_step, _move_step, _forget_step_values, _delete_step, _clear_steps)
# 7 - _render_add_step
# 8 - _render_params  (+ _clear_selection, _render_viewer_selection)
# 9 - _render_step
# 10 - _StepError + _step_signature + _mid_z_slice + _run_pipeline
# 11 - _build_result_fig
# 12 - _render_result_preview
# 13 - _not_saved + _render_pipeline_section  (fragment)
# 14 - render_ct_pipeline
# =====================================================================

# =====================================================================
# 1) _load_mask_array
# =====================================================================
@st.cache_resource(show_spinner="Loading mask...", max_entries=1)
def _load_mask_array(path: str) -> np.ndarray:
    """
    ============================================================================
    1) _LOAD_MASK_ARRAY
    Reads a mask volume from disk for the "Apply mask" step.
    ============================================================================

    PARAMETERS
    ----------
    path : str
        Path to the mask .mhd file.

    RETURNS
    -------
    mask : np.ndarray
        The mask volume, read-only (write flag disabled).

    NOTES
    -----
    Cached by Streamlit and keyed on `path` (a cheap string) - same
    pattern as _load_mhd in app/pages/3_CT_Analysis.py, so re-running the
    pipeline several times with the same mask path (e.g. while tweaking
    an unrelated step's parameters) doesn't re-read the mask file from
    disk on every "Run pipeline" click.

    st.cache_resource, not st.cache_data: same reasoning as _load_mhd -
    cache_data would hand back a fresh pickled copy of the mask on every
    page rerun, not just when the mask path changes. cache_resource
    returns the same object by reference instead. The read-only flag
    below is the same safety net as _load_mhd's: the "Apply mask" step
    only ever reads this mask (apply_mask_on_image does np.where(mask >
    0, image, 0), never mutates it), but marking it read-only turns any
    future accidental in-place mutation into an immediate crash instead
    of silently corrupting the cached mask for the rest of the session.

    max_entries=1: same reasoning as _load_mhd's cache cap - this holds
    a full mask volume per entry, so switching mask files shouldn't keep
    every previous one resident.
    """

    mask = sitk.GetArrayFromImage(sitk.ReadImage(path))
    mask.setflags(write=False)
    return mask


def _existing_mask_path(path: str) -> str:
    """
    Returns `path` unchanged if it points to an existing file, otherwise
    raises a ValueError with a readable message. Used by the "Apply mask"
    step's "call" adapter, so an empty or wrong path is reported in the
    step's card as "no mask file at ..." instead of SimpleITK's long
    low-level read error.
    """
    if not path or not os.path.isfile(path):
        raise ValueError(f"No mask file at '{path}'. Select an existing .mhd file.")
    return path


# =====================================================================
# 2) _shape_after_crop
# =====================================================================
def _shape_after_crop(shape: tuple, params: dict) -> tuple:
    """
    ============================================================================
    2) _SHAPE_AFTER_CROP
    Calculate the (Z, Y, X) array shape that CT_scans.crop_images would
    produce, given the shape entering the crop and its ("direction", "point")
    params.
    ============================================================================

    PARAMETERS
    ----------
    shape : tuple
        The (Z, Y, X) shape entering the crop.
    params : dict
        Must contain "direction" (one of "up"/"down"/"left"/"right"/
        "front"/"back") and "point" (the cut coordinate).

    RETURNS
    -------
    shape : tuple
        The resulting (Z, Y, X) shape after the crop.
    """
    n, y, x = shape
    direction, point = params["direction"], params["point"]
    if direction == "up":
        y = point
    elif direction == "down":
        y = y - point
    elif direction == "left":
        x = point
    elif direction == "right":
        x = x - point
    elif direction == "front":
        n = point
    elif direction == "back":
        n = n - point
    return (n, y, x)


# =====================================================================
# 2b) manual selection (viewer) helpers
# =====================================================================
# Used by the "Manual selection (viewer)" step. The voxels are clicked in
# the desktop viewer (CT_visualization_window.open_window), opened on the
# ORIGINAL loaded volume - not on the volume entering the step (a
# deliberate limitation: no steps have to be computed to open it). The
# viewer runs in its own process and saves the clicks to a .npz file,
# one file per step (see ct_viewer_launcher.launch_ct_viewer_for_selection).

_MANUAL_SELECTION_MODES = ("Set selected voxels to value", "Keep only selected voxels")
_SELECTIONS_DIRNAME = "ct_manual_selections"


def _selection_path(step_id: str) -> str:
    """
    The .npz file holding the voxels selected for one step:
    <output folder>/ct_manual_selections/<step id>.npz. Named after the
    step id, so a pipeline loaded from a saved settings file (which keeps
    the step ids) finds its selections again.
    """
    return str(get_output_dir() / _SELECTIONS_DIRNAME / f"{step_id}.npz")


@st.cache_data(show_spinner=False, max_entries=16)
def _load_selection(path: str, file_stamp: float) -> Tuple[np.ndarray, tuple]:
    """
    ============================================================================
    _LOAD_SELECTION
    Reads a selection file written by launch_ct_viewer_for_selection.
    ============================================================================

    PARAMETERS
    ----------
    path : str
        The .npz file.
    file_stamp : float
        File modification time - only part of the cache key, so a new
        selection saved over the old file is read again.

    RETURNS
    -------
    pixels : np.ndarray (int64), shape (N, 3)
        One row (x, y, slice) per selected voxel, as returned by open_window.
    clicked_shape : tuple
        (Z, Y, X) shape of the volume the voxels were clicked on.
    """
    with np.load(path) as data:
        pixels = np.asarray(data["pixels"], dtype=np.int64).reshape(-1, 3)
        clicked_shape = tuple(int(size) for size in data["shape"])
    return pixels, clicked_shape


def _voxels_inside(pixels: np.ndarray, shape: tuple) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Splits the (x, y, slice) rows of `pixels` into three index arrays
    (z_indices, y_indices, x_indices), keeping only the voxels inside a
    volume of (Z, Y, X) `shape`. Rows outside are dropped: the 3D brush
    can reach slices before the first / after the last one.
    """
    x_indices = pixels[:, 0]
    y_indices = pixels[:, 1]
    z_indices = pixels[:, 2]
    number_of_slices, number_of_rows, number_of_columns = shape
    inside = ((0 <= z_indices) & (z_indices < number_of_slices)
              & (0 <= y_indices) & (y_indices < number_of_rows)
              & (0 <= x_indices) & (x_indices < number_of_columns))
    return z_indices[inside], y_indices[inside], x_indices[inside]


def _value_for_dtype(value: float, dtype: np.dtype):
    """
    Converts the user's value to the volume's data type, or raises a
    ValueError if it can't be represented exactly: without this check,
    e.g. 300 written into an 8-bit volume would silently wrap around to 44,
    and 2.5 would silently become 2.
    """
    dtype = np.dtype(dtype)
    if np.issubdtype(dtype, np.bool_):
        if value not in (0, 1):
            raise ValueError(f"The volume holds booleans: the value must be 0 or 1, not {value:g}.")
    elif np.issubdtype(dtype, np.integer):
        limits = np.iinfo(dtype)
        if not float(value).is_integer():
            raise ValueError(f"The volume holds integers ({dtype}): the value must be a whole number, not {value:g}.")
        if not limits.min <= value <= limits.max:
            raise ValueError(f"The volume holds {dtype} values: the value must be between "
                             f"{limits.min} and {limits.max}, not {value:g}.")
    return dtype.type(value)


def _apply_manual_selection(image: np.ndarray, params: dict) -> np.ndarray:
    """
    ============================================================================
    _APPLY_MANUAL_SELECTION
    "call" adapter of the "Manual selection (viewer)" step.
    ============================================================================

    PARAMETERS
    ----------
    image : np.ndarray
        The (Z, Y, X) volume entering the step. Modified in place: it is
        the pipeline's own working copy (see the comment above
        _STEP_REGISTRY).
    params : dict
        "mode"      : one of _MANUAL_SELECTION_MODES
        "value"     : float, checked against image.dtype (_value_for_dtype)
        "selection" : {"path": str, "file_stamp": float} (made by _render_params;
                      file_stamp is 0.0 when no selection was saved yet)

    RETURNS
    -------
    image : np.ndarray
        - "Set selected voxels to value": selected voxels = value, the others unchanged.
        - "Keep only selected voxels":    selected voxels unchanged, the others = value.

    RAISES
    ------
    ValueError
        No selection yet, selection made on a volume of another shape
        (e.g. a Crop before this step), or a value that doesn't fit the
        data type. Shown in the step's card.
    """
    selection = params["selection"]
    if selection["file_stamp"] == 0.0:
        raise ValueError("No voxels selected yet - click 'Select voxels in viewer'.")
    pixels, clicked_shape = _load_selection(selection["path"], selection["file_stamp"])
    if clicked_shape != image.shape:
        raise ValueError(f"The voxels were selected on a volume of shape {clicked_shape} (Z, Y, X), "
                         f"but this step receives {image.shape}. A step before it changes the shape "
                         "(e.g. Crop): move this step before that one.")
    value = _value_for_dtype(params["value"], image.dtype)
    z_indices, y_indices, x_indices = _voxels_inside(pixels, image.shape)
    if not image.flags.writeable:      # never write into a read-only array (e.g. a cached one)
        image = np.array(image, copy=True)

    if params["mode"] == "Set selected voxels to value":
        image[z_indices, y_indices, x_indices] = value
    else:  # "Keep only selected voxels"
        selected = np.zeros(image.shape, dtype=bool)
        selected[z_indices, y_indices, x_indices] = True
        image[~selected] = value
    return image


def _describe_manual_selection(params: dict, shape: tuple) -> str:
    """
    "describe" adapter of the "Manual selection (viewer)" step: number of
    selected voxels, how many fall outside the volume, and a warning if
    the selection was made on a volume of another shape than `shape`
    (the shape entering this step).
    """
    selection = params["selection"]
    if selection["file_stamp"] == 0.0:
        return "no voxels selected yet"
    pixels, clicked_shape = _load_selection(selection["path"], selection["file_stamp"])
    number_inside = len(_voxels_inside(pixels, clicked_shape)[0])
    number_outside = len(pixels) - number_inside
    if params["mode"] == "Set selected voxels to value":
        text = f"{number_inside} selected voxels -> {params['value']:g}"
    else:
        text = f"keep {number_inside} selected voxels, all others -> {params['value']:g}"
    if number_outside:
        text += f" ({number_outside} outside the volume, ignored)"
    if clicked_shape != tuple(shape):
        text += f" - WARNING: selected on a {clicked_shape} volume, this step receives {tuple(shape)}"
    return text


# =====================================================================
# 2c) holes / islands helpers
# =====================================================================
# CT_scans.find_small_holes / find_islands return a NEW binary image holding
# only the detected holes / islands (255 = detected, 0 = everything else).
# Used directly as a pipeline step, that map replaced the scan itself. These
# adapters keep the volume entering the step and only set the detected
# voxels to a value chosen by the user (e.g. fill holes with 255, remove
# islands with 0).
#
# How the rank selects components (checked on a test volume with a block,
# 2 internal holes and 2 islands; components are ranked by size, rank 1 =
# the largest region, and every component of rank >= the given rank is
# detected):
#   rank | find_small_holes                      | find_islands
#   0    | the whole volume                      | the whole volume
#   1    | exterior background + all inner holes | main body + all islands
#   2    | all inner holes                       | all islands (not the main body)
#   3+   | only the smaller holes                | only the smaller islands
# A rank larger than the number of components makes both functions return
# None (after printing "error: hole size too big...").

def _set_detected_voxels(image: np.ndarray, detected: Optional[np.ndarray], value: float,
                         rank: int, what: str) -> np.ndarray:
    """
    ============================================================================
    _SET_DETECTED_VOXELS
    Sets every voxel of `image` where `detected` > 0 to `value`.
    ============================================================================

    PARAMETERS
    ----------
    image : np.ndarray
        The (Z, Y, X) volume entering the step. Modified in place: it is
        the pipeline's own working copy (see the comment above
        _STEP_REGISTRY).
    detected : np.ndarray or None
        What find_small_holes / find_islands returned for `image`
        (255 = detected voxel, 0 = not), or None if the rank was larger
        than the number of components.
    value : float
        The value given to the detected voxels; checked against
        image.dtype by _value_for_dtype.
    rank : int
        The rank that was asked for (only used in the error message).
    what : str
        "holes" or "islands" (only used in the error message).

    RETURNS
    -------
    image : np.ndarray
        The input volume, with the detected voxels set to `value`.

    RAISES
    ------
    ValueError
        Rank too large, or a value that doesn't fit the data type.
    """
    if detected is None:
        raise ValueError(f"Rank {rank} is larger than the number of regions found "
                         f"(the count is printed in the console): lower it. "
                         f"Rank 2 = all {what}.")
    value = _value_for_dtype(value, image.dtype)
    if not image.flags.writeable:      # never write into a read-only array (e.g. a cached one)
        image = np.array(image, copy=True)
    image[detected > 0] = value        # boolean mask with the full (Z, Y, X) shape of the volume
    return image


# =====================================================================
# 3) Param dataclass
# =====================================================================
# A copy of the Param dataclass of app/components/field_generator_source.py,
# kept separate on purpose (the two pipelines evolve independently), with
# the kinds the CT steps need: "int" and "path" instead of "vec3" and "text".
@dataclass
class Param:
    """
    ============================================================================
    PARAM
    Declares one user-editable parameter of a step type (one entry of
    _STEP_REGISTRY[...]["params"]).
    ============================================================================

    FIELDS
    ------
    name : str
        Key of the value in the step's params dict (params[name], read by
        the step's "call" and "describe" adapters) and suffix of its
        widget key: f"{key}_{step_id}_{name}". Must be unique within the
        step.
    label : str
        Widget label shown in the UI.
    kind : str, optional
        Which widget is drawn (default "float"):
          - "float"  -> st.number_input, value stored as float.
          - "int"    -> st.number_input with step=1, value stored as int.
          - "select" -> st.selectbox over `options`.
          - "path"   -> browse_file (text box + "Browse..." button), value
                        stored as str.
          - "viewer_selection" -> "Select voxels in viewer" / "Refresh" /
                        "Clear selection" buttons + a status line; the
                        value is {"path", "file_stamp"} of the step's
                        selection file (see _render_params). Not a widget
                        value: nothing is stored in session_state for it.
    default : Any, optional
        Initial value, written to session_state once (setdefault) the
        first time the widget is drawn.
    options : tuple of str, optional
        Choices for kind="select". Ignored otherwise.
    help : str, optional
        Tooltip shown next to the widget.
    min_value : float or int, optional
        Lower bound of the number_input. Only used for "float" and "int".

    EXAMPLE
    -------
    >>> Param("kernel", "Kernel radius", kind="int", default=1, min_value=1)
    """
    name: str
    label: str
    kind: str = "float"
    default: Any = 0.0
    options: Optional[Tuple[str, ...]] = None
    help: Optional[str] = None
    min_value: Optional[float] = None


# =====================================================================
# 4) _STEP_REGISTRY
# =====================================================================
# Each entry: 
#   "group"    (one of _STEP_GROUPS: the category the step is listed under in the add-step bar),
#   "help"     (shown in the step card and under the operation picker), 
#   "params"   (list of Param, used to build the step card's widgets), 
#   "call"     (adapter from the uniform (image, params_dict) shape to that CT_scans function's actual signature)
#   "describe" (adapter from (params_dict, shape) to a short, step-specific one-liner shown in the step card)
# 
# `shape` is the (Z, Y, X) shape entering that step; ( every step but "Crop" ignores it)
# "describe" is optional: a step without one still works, it just falls back to a generic key=value listing. 

# None of these "call" adapters copy the array before calling their
# CT_scans function. That used to be here as a defensive np.array(img,
# copy=True) in every entry, on the theory that a couple of the
# underlying functions (apply_threshold) mutate their input in place and
# would otherwise corrupt "the original array this module replays from
# on every run" - but that protection is already provided, once, by
# _run_pipeline's own `current = np.array(array, copy=True)` before the
# loop starts. `current` is never aliased anywhere else while the loop
# runs (each step's output simply replaces it for the next step), so a
# step mutating its input in place only ever touches that already-
# isolated copy, never the original `array`. Copying again here on top
# of that was pure duplication: on a large volume it meant every single
# step paid for a full extra copy of the whole volume before doing any
# actual work (worst for "Crop", which then immediately throws most of
# that duplicated data away) - measured at ~1x the volume size in wasted
# peak memory per step, on top of the SimpleITK round-trip most of these
# functions already do internally.
# Categories of the add-step bar, in the order they are shown.
_STEP_GROUPS = ("Segmentation", "Morphology", "Geometry", "Region cleanup", "Data type")

_STEP_REGISTRY = {
    "Threshold -> binary mask": {
        "group": "Segmentation",
        "help": "segment_from_threshold: pixels within [lower, upper] become 255 (foreground), everything else 0.",
        "params": [
            Param("lower_threshold", "Lower threshold", kind="float", default=0.0),
            Param("upper_threshold", "Upper threshold", kind="float", default=255.0),
        ],
        "call": lambda img, p: CT_scans.segment_from_threshold(
            img, p["lower_threshold"], p["upper_threshold"]),
        "describe": lambda p, shape: f"[{p['lower_threshold']:g}, {p['upper_threshold']:g}] -> 255",
    },
    "Threshold -> keep range": {
        "group": "Segmentation",
        "help": "apply_threshold: pixels outside [lower, upper] are clipped (relative to lower) - not a binary mask.",
        "params": [
            Param("lower_threshold", "Lower threshold", kind="float", default=0.0),
            Param("upper_threshold", "Upper threshold", kind="float", default=255.0),
        ],
        "call": lambda img, p: CT_scans.apply_threshold(
            img, p["lower_threshold"], p["upper_threshold"]),
        "describe": lambda p, shape: f"keep [{p['lower_threshold']:g}, {p['upper_threshold']:g}]",
    },
    "Dilate": {
        "group": "Morphology",
        "help": "dilate_filter: grayscale dilation (grows bright regions) with the given kernel radius.",
        "params": [
            Param("kernel", "Kernel radius", kind="int", default=1, min_value=1),
        ],
        "call": lambda img, p: CT_scans.dilate_filter(img, p["kernel"]),
        "describe": lambda p, shape: f"grow by radius {p['kernel']}",
    },
    "Erode": {
        "group": "Morphology",
        "help": "erode_filter: grayscale erosion (shrinks bright regions) with the given kernel radius.",
        "params": [
            Param("kernel", "Kernel radius", kind="int", default=1, min_value=1),
        ],
        "call": lambda img, p: CT_scans.erode_filter(img, p["kernel"]),
        "describe": lambda p, shape: f"shrink by radius {p['kernel']}",
    },
    "Crop": {
        "group": "Geometry",
        "help": "crop_images: keeps the side of the volume given by 'Keep side', cut at 'Cut coordinate'.",
        "params": [
            Param("direction", "Keep side", kind="select",
                  options=("up", "down", "left", "right", "front", "back"), default="up"),
            Param("point", "Cut coordinate", kind="int", default=0, min_value=0),
        ],
        "call": lambda img, p: CT_scans.crop_images(p["point"], p["direction"], img),
        "describe": lambda p, shape: f"keep {p['direction']} of {p['point']} -> {_shape_after_crop(shape, p)} (Z, Y, X)",
        #"describe": _describe_crop,
    },
    "Connected component (seed point)": {
        "group": "Region cleanup",
        "help": "connected_filter: keeps only the region connected to the given (x, y, z) seed point.",
        "params": [
            Param("x", "Seed X", kind="int", default=0, min_value=0),
            Param("y", "Seed Y", kind="int", default=0, min_value=0),
            Param("z", "Seed Z", kind="int", default=0, min_value=0),
        ],
        "call": lambda img, p: CT_scans.connected_filter(p["x"], p["y"], p["z"], img),
        "describe": lambda p, shape: f"seed ({p['x']}, {p['y']}, {p['z']})",
    },
    # Param names "max_hole_size" / "max_island_size" kept from the first
    # version (they are part of the widget keys, so pipelines saved before
    # keep their rank); only label, default and meaning were corrected.
    "Find small holes": {
        "group": "Region cleanup",
        "help": "find_small_holes: finds the holes (background regions, voxel value 0) of the volume, "
                "and sets the voxels of the detected holes to 'Value'. "
                "Detected regions are ranked by size, rank 1 = the largest, i.e. the "
                "exterior background. Only regions of rank >= 'Rank' are detected. ",
        "params": [
            Param("max_hole_size", "Rank", kind="int", default=2, min_value=1,
                  help="Detected regions are ranked by size.  Only regions of rank >= 'Rank' are detected."),
            Param("value", "Value", kind="float", default=255.0,
                  help="Value given to the detected voxels. Must fit the volume's data type."),
        ],
        "call": lambda img, p: _set_detected_voxels(
            img, CT_scans.find_small_holes(img, p["max_hole_size"]), p["value"], p["max_hole_size"], "inner holes"),
        "describe": lambda p, shape: f"holes of rank >= {p['max_hole_size']} -> {p['value']:g}",
    },
    "Find islands": {
        "group": "Region cleanup",
        "help": "find_islands: finds the islands (foreground regions, voxel value > 0) of the volume, "
                "and sets the voxels of the detected islands to 'Value'. "
                "Regions are ranked by size, rank 1 = the largest, i.e. the "
                "main body. Only regions of rank >= 'Rank' are detected.  ",
        "params": [
            Param("max_island_size", "Rank", kind="int", default=2, min_value=1,
                  help="Regions are ranked by size. Only regions of rank >= 'Rank' are detected. "),
            Param("value", "Value", kind="float", default=0.0,
                  help="Value given to the detected voxels. Must fit the volume's data type."),
        ],
        "call": lambda img, p: _set_detected_voxels(
            img, CT_scans.find_islands(img, p["max_island_size"]), p["value"], p["max_island_size"], "islands"),
        "describe": lambda p, shape: f"islands of rank >= {p['max_island_size']} -> {p['value']:g}",
    },
    "Apply mask": {
        "group": "Segmentation",
        "help": "apply_mask_on_image: pixels outside the mask (mask <= 0) are set to 0. "
                "The mask is loaded from a separate .mhd volume - it must have the same "
                "shape as the volume being processed.",
        "params": [
            Param("mask_path", "Mask .mhd path", kind="path", default=""),
        ],
        "call": lambda img, p: CT_scans.apply_mask_on_image(
            img, _load_mask_array(_existing_mask_path(p["mask_path"]))),
        "describe": lambda p, shape: f"mask: {p['mask_path'] or '(not set)'}",
    },
    "Manual selection (viewer)": {
        "group": "Segmentation",
        "help": "Allows to manually select voxels in the desktop CT viewer and set them to a value, or keep only the selected voxels."
                "CT viewer opens the ORIGINAL loaded volume (not on the result of the steps before this one). "
                "'Set selected voxels to value': the selected voxels get the value. "
                "'Keep only selected voxels': all the OTHER voxels get the value. ",
        "params": [
            Param("mode", "Mode", kind="select", options=_MANUAL_SELECTION_MODES,
                  default=_MANUAL_SELECTION_MODES[0]),
            Param("value", "Value", kind="float", default=0.0,
                  help="Set mode: value given to the selected voxels. "
                       "Keep-only mode: value given to all the other voxels. "
                       "Must fit the volume's data type (e.g. a whole number 0-255 for 8-bit)."),
            Param("selection", "Selected voxels", kind="viewer_selection", default=None),
        ],
        "call": _apply_manual_selection,
        "describe": _describe_manual_selection,
    },
    "Change data type": {
        "group": "Data type",
        "help": "convert_data_type: converts the volume to another data type, rescaling its values "
                "linearly so that its min -> 0 and its max -> the largest value of the new type "
                "(e.g. 255 for uint8). Float types are scaled to [0, 1] instead.",
        "params": [
            Param("data_type", "New data type", kind="select",
                  options=CT_scans.SUPPORTED_DATA_TYPES, default="uint8"),
        ],
        "call": lambda img, p: CT_scans.convert_data_type(img, p["data_type"]),
        "describe": lambda p, shape: (f"min..max -> [0, 1] as {p['data_type']}"
                                      if p["data_type"].startswith("float")
                                      else f"min..max -> [0, {np.iinfo(np.dtype(p['data_type'])).max}] "
                                           f"as {p['data_type']}"),
    },
}


# =====================================================================
# 5) _describe_params
# =====================================================================
def _describe_params(step_type: str, params: dict, shape: tuple) -> str:
    """
    ============================================================================
    5) _DESCRIBE_PARAMS
    Fetches the step-specific "describe" adapter from _STEP_REGISTRY and
    calls it with (params, shape) to get a short one-liner for the
    step's card.
    ============================================================================

    PARAMETERS
    ----------
    step_type : str
        The step's registry key (e.g. "Threshold -> binary mask").
    params : dict
        That step's current parameter values.
    shape : tuple
        The (Z, Y, X) shape entering this step.

    RETURNS
    -------
    description : str
        A short one-liner. Falls back to a generic key=value listing if
        the step has no "describe" adapter.
    """
    describe = _STEP_REGISTRY[step_type].get("describe")
    if describe is not None:
        return describe(params, shape)
    # fallback: no step-specific adapter, just list the key=value pairs
    return ", ".join(f"{name}={value}" for name, value in params.items())


# =====================================================================
# 6) step list callbacks
# =====================================================================
# Used as on_click callbacks: Streamlit runs them BEFORE the page reruns,
# so the step list is already up to date when the cards are drawn. That
# avoids the old "if st.button(...): change the list; st.rerun()" pattern,
# which ran the whole page twice for every click.
# `key` is the pipeline's session-state key prefix (see render_ct_pipeline),
# so the step list lives in st.session_state[f"{key}_steps"].

def _add_step(key: str) -> None:
    """on_click of "Add step": appends the step type picked in the selectbox."""
    step_type = st.session_state[f"{key}_op_select"]
    # unique ID for this step (8 hex characters from uuid4): seeds all its widget keys
    step_id = uuid.uuid4().hex[:8]
    st.session_state[f"{key}_steps"].append({"id": step_id, "type": step_type})


def _move_step(key: str, step_id: str, delta: int) -> None:
    """on_click of the up (delta=-1) / down (delta=+1) buttons of a step card."""
    steps = st.session_state[f"{key}_steps"]
    index = next(position for position, step in enumerate(steps) if step["id"] == step_id)
    new_index = index + delta
    if 0 <= new_index < len(steps):
        steps[index], steps[new_index] = steps[new_index], steps[index]


def _forget_step_values(key: str, step_id: str) -> None:
    """
    Deletes every session_state key of one step (f"{key}_{step_id}_...":
    its parameter values, on/off toggle, buttons). Without this, the
    values of a deleted step would stay in the page-switch mirror and in
    saved files forever (see SAVE / LOAD in render_ct_pipeline), since
    mirror_widget_state copies every key starting with the prefix.
    """
    step_prefix = f"{key}_{step_id}_"
    for state_key in list(st.session_state.keys()):
        if isinstance(state_key, str) and state_key.startswith(step_prefix):
            del st.session_state[state_key]
    # Also from the mirror itself: otherwise, on the next full page run,
    # restore_widget_state would put the deleted step's values straight
    # back (they are "missing" from session_state, exactly what it restores).
    mirror = st.session_state.get(f"{key}__mirror", {})   # key name made by page_state._mirror_key(f"{key}_")
    for state_key in list(mirror.keys()):
        if state_key.startswith(step_prefix):
            del mirror[state_key]


def _delete_step(key: str, step_id: str) -> None:
    """on_click of the delete button of a step card."""
    st.session_state[f"{key}_steps"] = [
        step for step in st.session_state[f"{key}_steps"] if step["id"] != step_id
    ]
    _forget_step_values(key, step_id)


def _clear_steps(key: str) -> None:
    """on_click of "Clear all": removes every step, and the error messages of the last run."""
    for step in st.session_state[f"{key}_steps"]:
        _forget_step_values(key, step["id"])
    st.session_state[f"{key}_steps"] = []
    st.session_state[f"{key}_step_errors"] = {}


# =====================================================================
# 7) _render_add_step
# =====================================================================
def _render_add_step(key: str, number_of_steps: int) -> None:
    """
    ============================================================================
    7) _RENDER_ADD_STEP
    Renders the add-step bar drawn under the step cards: a category
    picker, the step types of that category, an "Add step" button and a
    "Clear all" button. The new step is added with its default parameter
    values; they are then edited directly in the step's card.
    ============================================================================

    PARAMETERS
    ----------
    key : str
        Session-state key prefix for this pipeline's widgets.
    number_of_steps : int
        Current number of steps (disables "Clear all" when there are none).

    RETURNS
    -------
    None
    """
    column_picker, column_add, column_clear = st.columns([3, 1.2, 1], vertical_alignment="bottom")
    with column_picker:
        # seeded with setdefault, not default=: a value put back by
        # restore_widget_state / a loaded file plus default= makes Streamlit
        # show "created with a default value but also had its value set via
        # the Session State API"
        st.session_state.setdefault(f"{key}_new_step_group", _STEP_GROUPS[0])
        group = st.segmented_control(
            "New step category", _STEP_GROUPS,
            key=f"{key}_new_step_group",
            help="Segmentation: turn grey values into a mask. Morphology: grow or shrink regions. "
                 "Geometry: change the volume's extent. Region cleanup: keep or isolate connected regions. "
                 "Data type: convert the voxel values to another type.",
        )
        # segmented_control returns None when the user clicks the selected
        # category again (deselects it): then every step type is listed.
        step_types = [step_type for step_type, spec in _STEP_REGISTRY.items()
                      if group is None or spec["group"] == group]
        step_type = st.selectbox("New step", step_types, key=f"{key}_op_select",
                                 label_visibility="collapsed")
    column_add.button("Add step", key=f"{key}_add_btn", icon=":material/add:", type="primary",
                      on_click=_add_step, args=(key,))
    column_clear.button("Clear all", key=f"{key}_clear_btn",
                        on_click=_clear_steps, args=(key,), disabled=(number_of_steps == 0))
    st.caption(_STEP_REGISTRY[step_type]["help"])


def _clear_selection(selection_path: str) -> None:
    """on_click of "Clear selection": deletes the step's selection file."""
    if os.path.isfile(selection_path):
        os.remove(selection_path)


def _render_viewer_selection(key: str, step_id: str, volume_path: Optional[str]) -> dict:
    """
    ============================================================================
    _RENDER_VIEWER_SELECTION
    Draws the controls of a "viewer_selection" Param (see _render_params):
    "Select voxels in viewer", "Refresh", "Clear selection", and a status
    line.
    ============================================================================

    RETURNS
    -------
    selection : dict
        {"path": the step's selection file, "file_stamp": its modification
        time, or 0.0 if it doesn't exist (yet)}.

    NOTES
    -----
    The viewer runs in a separate process: the app is not told when its
    window is closed. The new file is picked up on the next rerun of this
    section - any interaction does it; "Refresh" is a button that does
    nothing else.
    """
    selection_path = _selection_path(step_id)
    has_selection = os.path.isfile(selection_path)
    file_stamp = os.path.getmtime(selection_path) if has_selection else 0.0

    column_select, column_refresh, column_clear = st.columns([2, 1, 1.3])
    if column_select.button("Select voxels in viewer", key=f"{key}_{step_id}_select_btn",
                            icon=":material/ads_click:", disabled=volume_path is None,
                            help="Opens the desktop viewer on the loaded volume. Turn the brush on, "
                                 "click the voxels, then CLOSE the window to save them."):
        launch_ct_viewer_for_selection(volume_path, selection_path)
        st.info("Viewer opening in a separate window. Select voxels with the brush, close the "
                "window, then click 'Refresh'. A new selection replaces the previous one.")
    column_refresh.button("Refresh", key=f"{key}_{step_id}_refresh_btn", icon=":material/refresh:",
                          help="Reads the selection saved when the viewer window was closed.")
    column_clear.button("Clear selection", key=f"{key}_{step_id}_clear_selection_btn",
                        on_click=_clear_selection, args=(selection_path,), disabled=not has_selection)
    if volume_path is None:
        st.caption("No .mhd file path was given to the pipeline: the viewer can't be opened.")
    return {"path": selection_path, "file_stamp": file_stamp}


# =====================================================================
# 8) _render_params
# =====================================================================
def _render_params(key: str, step_id: str, spec: dict, volume_path: Optional[str]) -> dict:
    """
    ============================================================================
    8) _RENDER_PARAMS
    Draws the widgets for every Param of one step (spec["params"], in list
    order) and returns their current values as a plain dict. Called once
    per step per rerun by _render_step(); the returned dict is the
    `params` passed to the step's "call" and "describe" adapters.
    ============================================================================

    PARAMETERS
    ----------
    key : str
        Session-state key prefix for this pipeline's widgets.
    step_id : str
        Step id (8 hex characters from uuid4). Every widget key of this
        step is f"{key}_{step_id}_{param.name}", so two steps of the same
        type never share a widget, and moving or deleting a step leaves
        the others' values untouched.
    spec : dict
        The step type's entry in _STEP_REGISTRY; only spec["params"] (a
        list of Param) is used here.
    volume_path : str or None
        Path of the loaded .mhd file, opened by the "viewer_selection"
        kind's button. None: that button is disabled.

    RETURNS
    -------
    values : dict
        {param.name: value}:
          - "float"  -> float
          - "int"    -> int
          - "select" -> str (one of param.options)
          - "path"   -> str
          - "viewer_selection" -> {"path": str, "file_stamp": float}
            (file_stamp = the selection file's modification time, 0.0 if
            there is no file yet; part of the step's signature, so a new
            selection marks the result out of date)
    """
    values = {}
    # The number / select widgets are drawn side by side, one column each.
    # "path" and "viewer_selection" params are drawn on their own full-width
    # row instead, because they make their own columns (text box / buttons).
    column_params = [param for param in spec["params"] if param.kind not in ("path", "viewer_selection")]
    columns = st.columns(len(column_params)) if column_params else []
    column_of_param = {param.name: column for param, column in zip(column_params, columns)}

    for param in spec["params"]:
        widget_key = f"{key}_{step_id}_{param.name}"

        if param.kind == "path":
            st.session_state.setdefault(widget_key, str(param.default))
            browse_file(key=widget_key, title=f"Select {param.label}",
                        filetypes=[("MHD files", "*.mhd"), ("All files", "*.*")])
            values[param.name] = st.session_state.get(widget_key, "")
            if not os.path.isfile(values[param.name]):
                st.caption("Select a file - running the pipeline fails at this step until one is set.")
            continue

        if param.kind == "viewer_selection":
            values[param.name] = _render_viewer_selection(key, step_id, volume_path)
            continue

        column = column_of_param[param.name]
        # seed the default once; afterwards the widget's own value is kept in session_state
        if param.kind == "select":
            st.session_state.setdefault(widget_key, param.default)
            values[param.name] = column.selectbox(
                param.label, param.options, key=widget_key, help=param.help)
        elif param.kind == "int":
            st.session_state.setdefault(widget_key, int(param.default))
            values[param.name] = int(column.number_input(
                param.label, min_value=param.min_value, step=1, key=widget_key, help=param.help))
        else:  # "float"
            st.session_state.setdefault(widget_key, float(param.default))
            values[param.name] = float(column.number_input(
                param.label, min_value=param.min_value, key=widget_key, help=param.help))
    return values


# =====================================================================
# 9) _render_step
# =====================================================================
def _render_step(key: str, index: int, number_of_steps: int, step: dict, shape: tuple,
                 volume_path: Optional[str]) -> dict:
    """
    ============================================================================
    9) _RENDER_STEP
    Draws one step card (header with on/off toggle + move/delete buttons,
    the step's help text, its parameter widgets and its one-line
    description) and returns its config dict for _run_pipeline. The card
    also holds a placeholder for this step's error message, filled when
    the pipeline fails at this step.
    ============================================================================

    PARAMETERS
    ----------
    key : str
        Session-state key prefix for this pipeline's widgets.
    index : int
        Position of this step in the list (0-based).
    number_of_steps : int
        Total number of steps in the list (disables "down" on the last one).
    step : dict
        {"id": str, "type": str} - the step's unique ID and its
        _STEP_REGISTRY key.
    shape : tuple
        The (Z, Y, X) shape entering this step, only used by the
        description (see _shape_after_crop).
    volume_path : str or None
        Path of the loaded .mhd file, forwarded to _render_params.

    RETURNS
    -------
    config : dict
        {"id": str, "type": str, "index": int, "enabled": bool,
         "params": dict, "message_slot": st.empty()}
    """
    step_id, step_type = step["id"], step["type"]
    spec = _STEP_REGISTRY[step_type]

    with st.container(border=True):
        # ----- header: title, on/off, up, down, delete -----
        column_title, column_on, column_up, column_down, column_delete = st.columns(
            [6, 1.4, 0.8, 0.8, 0.8], vertical_alignment="center")
        column_title.markdown(f"**{index + 1}. {step_type}**")
        st.session_state.setdefault(f"{key}_{step_id}_enabled", True)
        enabled = column_on.toggle("On", key=f"{key}_{step_id}_enabled",
                                   help="Off: the step is skipped when the pipeline runs.")
        column_up.button("", icon=":material/arrow_upward:", key=f"{key}_{step_id}_up", help="Move up",
                         on_click=_move_step, args=(key, step_id, -1), disabled=(index == 0))
        column_down.button("", icon=":material/arrow_downward:", key=f"{key}_{step_id}_down", help="Move down",
                           on_click=_move_step, args=(key, step_id, +1),
                           disabled=(index == number_of_steps - 1))
        column_delete.button("", icon=":material/delete:", key=f"{key}_{step_id}_del", help="Delete step",
                             on_click=_delete_step, args=(key, step_id))
        st.caption(spec["help"])

        # ----- parameters, editable at any time -----
        params = _render_params(key, step_id, spec, volume_path)
        st.caption(f"**Notes:** {_describe_params(step_type, params, shape)}")

        # ----- error message of the last run, if it failed at this step -----
        message_slot = st.empty()
        last_error = st.session_state[f"{key}_step_errors"].get(step_id)
        if last_error is not None:
            message_slot.error(last_error)

    return {"id": step_id, "type": step_type, "index": index, "enabled": enabled,
            "params": params, "message_slot": message_slot}


# =====================================================================
# 10) _StepError + _step_signature + _run_pipeline
# =====================================================================
class _StepError(Exception):
    """Raised by _run_pipeline when one step fails; remembers which step (its id)."""

    def __init__(self, step_id: str, message: str):
        super().__init__(message)
        self.step_id = step_id


def _step_signature(config: dict) -> tuple:
    """
    Returns (step type, parameters as a sorted JSON string) for one step:
    two steps with the same signature produce the same output from the
    same input. Used to tell whether the result is out of date and
    whether a run can continue from the previous result (see
    render_ct_pipeline). The step id is deliberately NOT part of it: what
    matters is what the step does, not which card it is.
    """
    return (config["type"], json.dumps(config["params"], sort_keys=True))


def _mid_z_slice(volume: np.ndarray) -> np.ndarray:
    """
    Copy of the middle z-slice of a (Z, Y, X) volume. A copy, not a view,
    so it stays valid (and small: one (Y, X) image) after the volume is
    replaced or modified in place by a later step.
    """
    mid_z_index = volume.shape[0] // 2
    return np.array(volume[mid_z_index, :, :], copy=True)


def _run_pipeline(start_volume: np.ndarray, configs: list) -> Tuple[np.ndarray, list]:
    """
    ============================================================================
    10) _RUN_PIPELINE
    Replays the given steps, in order, starting from a copy of
    `start_volume`, and keeps the mid z-slice after each step.
    ============================================================================

    PARAMETERS
    ----------
    start_volume : np.ndarray
        The volume the first step receives: the original loaded volume
        for a full run, or the previous result when only new steps are
        run (see render_ct_pipeline). Never mutated - a copy is made
        before the loop starts, because some CT_scans functions
        (apply_threshold) modify their input in place.
    configs : list
        The ENABLED steps to run, one config dict each, as returned by
        _render_step: {"id", "type", "index", "params", ...}.

    RETURNS
    -------
    result : np.ndarray
        The volume after the last step.
    snapshots : list of (str, np.ndarray)
        One (label, mid z-slice) per step, label = "<card number>. <type>".
        Only the 2D mid slice is kept, not the 3D volume, so this stays
        small whatever the volume size (decision: keep only the last
        full output).

    RAISES
    ------
    _StepError
        If a step fails. Carries that step's id, so its error can be
        shown in its own card.
    """
    current = np.array(start_volume, copy=True)
    snapshots = []
    for config in configs:
        call = _STEP_REGISTRY[config["type"]]["call"]
        try:
            current = np.asarray(call(current, config["params"]))
        except Exception as error:
            raise _StepError(config["id"], f"{config['type']}: {error}") from error
        snapshots.append((f"{config['index'] + 1}. {config['type']}", _mid_z_slice(current)))
    return current, snapshots


# =====================================================================
# 11) _build_result_fig
# =====================================================================
@st.cache_data(show_spinner=False)
def _build_result_fig(mid_slice: np.ndarray, spacing: tuple = (1.0, 1.0, 1.0)) -> go.Figure:
    """
    ============================================================================
    11) _BUILD_RESULT_FIG
    Builds the mid z-slice Heatmap figure for a pipeline result.
    ============================================================================

    PARAMETERS
    ----------
    mid_slice : np.ndarray
        The 2D (Y, X) mid z-slice to plot.
    spacing : tuple, optional
        (sx, sy, sz) physical voxel spacing, used to keep the aspect
        ratio correct (default = (1.0, 1.0, 1.0)).

    RETURNS
    -------
    fig : plotly.graph_objects.Figure
        The Heatmap figure.

    NOTES
    -----
    Cached on `mid_slice` ITSELF - not on st.session_state[result_key]
    (the full 3D result _render_result_preview slices this out of).
    That distinction matters: `mid_slice` is bounded by the volume's
    (Y, X) footprint alone, the same size regardless of how many
    Z-slices or pipeline steps are involved, so hashing it directly on
    every rerun is cheap (unlike hashing the full `result`, which is
    exactly the large-array cost _load_histogram's docstring in
    app/pages/3_CT_Analysis.py warns against). Because the hash is of
    the actual data, there's no separate "did it change" signal to
    maintain by hand - no version counter to remember to bump, no
    session-state key beyond `result_key` itself. A rerun that slices
    out the same mid_slice content is a cache hit; a genuinely
    different slice (new pipeline run, or Up/Down changing which step
    feeds the preview) is a miss, exactly and automatically.
    """
    sx, sy, _sz = spacing
    fig = go.Figure(go.Heatmap(z=mid_slice, colorscale="Gray"))
    fig.update_layout(height=500, margin=dict(l=0, r=0, t=20, b=0))
    fig.update_yaxes(scaleanchor="x", scaleratio=sy / sx)
    fig.update_xaxes(constrain="domain")
    fig.update_yaxes(autorange="reversed")
    return fig


# =====================================================================
# 12) _render_result_preview
# =====================================================================
def _render_result_preview(result: np.ndarray, snapshots: list, key: str, spacing: tuple) -> None:
    """
    ============================================================================
    12) _RENDER_RESULT_PREVIEW
    Renders the mid z-slice heatmap of the pipeline result - or of the
    volume after any earlier step, picked in "Show result after step" -
    plus the interactive-viewer launcher (always on the final result).
    ============================================================================

    PARAMETERS
    ----------
    result : np.ndarray
        The final result of the last successful run.
    snapshots : list of (str, np.ndarray)
        (label, mid z-slice) for the loaded volume and after each step of
        the last run (see _run_pipeline and render_ct_pipeline).
    key : str
        Session-state key prefix for this pipeline's widgets.
    spacing : tuple
        (sx, sy, sz) physical voxel spacing, forwarded to
        _build_result_fig.

    RETURNS
    -------
    None

    NOTES
    -----
    Each snapshot's mid slice was taken from that step's OWN output
    (_mid_z_slice), so its z-index is half of that output's own depth -
    after a crop along Z this is the middle of the cropped volume.
    """
    labels = [label for label, _ in snapshots]
    shown_label = st.selectbox("Show result after step", labels, index=len(labels) - 1,
                               key=f"{key}_show_step",
                               help="Mid z-slice of the volume after that step, from the last run.")
    mid_slice = dict(snapshots)[shown_label]
    fig = _build_result_fig(mid_slice, spacing=spacing)
    st.plotly_chart(fig, width="stretch", key=f"{key}_preview_fig")

    lightweight = render_lightweight_toggle(f"{key}_mask_viewer")
    if st.button("Open interactive CT viewer (final result)", key=f"{key}_viewer_btn"):
        temp_path = get_output_dir() / "mask_temp.mhd"
        out_image = sitk.GetImageFromArray(result)
        # Spacing/direction still apply after any of these filters;
        # origin may be slightly off post-crop, but that's a minor
        # detail for a first version - reuses the loaded image's
        # metadata rather than defaulting to identity spacing.
        sitk.WriteImage(out_image, temp_path)
        launch_ct_viewer(str(temp_path), lightweight)


# =====================================================================
# 13) _not_saved + _render_pipeline_section  (fragment)
# =====================================================================
def _not_saved(key: str) -> Tuple[tuple, tuple]:
    """
    Returns (exclude_keys, exclude_suffixes): the session_state keys of
    this pipeline that are NOT mirrored across page switches nor written
    to a saved settings file (see SAVE / LOAD in render_ct_pipeline).

    exclude_keys - results of a run, not settings:
        {key}_result, {key}_snapshots         numpy arrays: can't go in JSON, and are large
        {key}_last_run                        tied to the volume loaded in memory (its id())
        {key}_step_errors, {key}_run_message  messages of the last run
        {key}_show_step                       its options only exist after a run
    exclude_suffixes:
        _btn, _up, _down, _del   buttons: Streamlit refuses to have their value written
        _fig                     chart (the preview figure): holds selection state, not input
        _lightweight             the viewer checkbox (ct_viewer_launcher) is drawn with value=,
                                 which would show Streamlit's "default value but also set via
                                 the Session State API" warning once its value is put back
    """
    exclude_keys = tuple(f"{key}_{name}" for name in
                         ("result", "snapshots", "last_run", "step_errors", "run_message", "show_step"))
    exclude_suffixes = ("_btn", "_up", "_down", "_del", "_fig", "_lightweight")
    return exclude_keys, exclude_suffixes


@st.fragment
def _render_pipeline_section(array: np.ndarray, key: str, spacing: tuple,
                             volume_path: Optional[str]) -> None:
    """
    ============================================================================
    13) _RENDER_PIPELINE_SECTION
    Draws the whole pipeline section (step cards, add-step bar, Run
    button, preview) and runs the pipeline when "Run pipeline" is clicked.
    ============================================================================

    PARAMETERS
    ----------
    array : np.ndarray
        The loaded volume. Never mutated.
    key : str
        Session-state key prefix for this pipeline's widgets.
    spacing : tuple
        (sx, sy, sz) physical voxel spacing, for the preview.
    volume_path : str or None
        Path of the loaded .mhd file (for the "Manual selection (viewer)" step).

    RETURNS
    -------
    None
        The result is written to st.session_state[f"{key}_result"];
        render_ct_pipeline reads it from there.

    WHY A FRAGMENT
    --------------
    @st.fragment makes every widget inside this function rerun ONLY this
    function, not the whole page: editing a parameter, adding, moving,
    toggling or deleting a step no longer redraws the mid-plane figure,
    the histogram, the mesh section and its 3D preview.
    The catch: on such a fragment-only rerun the rest of the page is not
    re-executed, so it would not see a new result. That's why a run
    always ends with st.rerun(scope="app"): one full page rerun, so the
    mesh/export section below picks up the new (or cleared) result. The
    message of the run is kept in session_state ({key}_run_message) to
    be shown after that rerun.
    It also ends with mirror_widget_state (see SAVE / LOAD in
    render_ct_pipeline), for the same reason: a fragment-only rerun
    doesn't reach the end of the page.
    """
    steps_key = f"{key}_steps"
    errors_key = f"{key}_step_errors"
    result_key = f"{key}_result"
    snapshots_key = f"{key}_snapshots"
    last_run_key = f"{key}_last_run"
    message_key = f"{key}_run_message"

    # Two columns: left is the pipeline itself (step cards, then the
    # add-step bar under them); right is the Run button and the preview.
    col_overview, col_preview = st.columns([1, 1])

    with col_overview:
        st.markdown("**Pipeline overview**")
        steps = st.session_state[steps_key]
        if not steps:
            st.info("No steps yet - pick a category and a step below, then click 'Add step'.")

        # Draw every step card and collect its config. `current_shape` is the
        # (Z, Y, X) shape entering each step: it starts at the loaded volume's
        # shape and only an ENABLED "Crop" changes it (see _shape_after_crop).
        configs = []
        current_shape = array.shape
        for index, step in enumerate(steps):
            config = _render_step(key, index, len(steps), step, current_shape, volume_path)
            configs.append(config)
            # applied AFTER this card is drawn, so it is the shape the NEXT card receives
            if config["type"] == "Crop" and config["enabled"]:
                current_shape = _shape_after_crop(current_shape, config["params"])

        # ----- add-step bar, under the cards (same place as on the Field generator page) -----
        _render_add_step(key, len(steps))

    # ----- compare the current steps with the last run -----
    enabled_configs = [config for config in configs if config["enabled"]]
    current_signatures = [_step_signature(config) for config in enabled_configs]
    # identifies the loaded volume: _load_mhd (st.cache_resource) returns the
    # same array object for the same file, so id() changes when another file is loaded
    volume_identity = (id(array), array.shape)
    last_run = st.session_state[last_run_key]   # {"volume", "signatures"} of the last successful run, or None
    result = st.session_state[result_key]
    same_volume = last_run is not None and last_run["volume"] == volume_identity
    result_is_out_of_date = result is not None and not (
        same_volume and last_run["signatures"] == current_signatures)
    # Continue from the previous result only when the current enabled steps
    # START WITH exactly the steps of the last run (same volume) and add new
    # ones after them: the previous result is then exactly what the first
    # new step would receive. Any other change (edit, reorder, toggle,
    # delete, other volume) needs a full run from the loaded volume, since
    # only the last output is kept (no intermediate volumes).
    number_of_reused_steps = 0
    if (result is not None and same_volume
            and len(current_signatures) > len(last_run["signatures"])
            and current_signatures[:len(last_run["signatures"])] == last_run["signatures"]):
        number_of_reused_steps = len(last_run["signatures"])

    with col_preview:
        # The button alone goes in a horizontal container centred in the column;
        # the spinner and success/error messages below stay full-width.
        run_label = "Run pipeline (result out of date)" if result_is_out_of_date else "Run pipeline"
        with st.container(horizontal=True, horizontal_alignment="center"):
            run_clicked = st.button(run_label, key=f"{key}_run_btn", type="primary",
                                    disabled=not enabled_configs)
        if run_clicked:
            st.session_state[errors_key] = {}     # clear the error messages of the previous run
            try:
                if number_of_reused_steps > 0:
                    steps_to_run = enabled_configs[number_of_reused_steps:]
                    with st.spinner(f"Running {len(steps_to_run)} new step(s) on the previous result..."):
                        new_result, new_snapshots = _run_pipeline(result, steps_to_run)
                    snapshots = st.session_state[snapshots_key] + new_snapshots
                    message = (f"Pipeline applied: ran {len(steps_to_run)} new step(s), "
                               f"reused the previous result for the first {number_of_reused_steps}.")
                else:
                    with st.spinner(f"Running {len(enabled_configs)} step(s)..."):
                        new_result, new_snapshots = _run_pipeline(array, enabled_configs)
                    snapshots = [("0. Loaded volume", _mid_z_slice(array))] + new_snapshots
                    message = f"Pipeline applied ({len(enabled_configs)} step(s))."
                st.session_state[result_key] = new_result
                st.session_state[snapshots_key] = snapshots
                st.session_state[last_run_key] = {"volume": volume_identity,
                                                  "signatures": current_signatures}
                st.session_state[message_key] = ("success", message)
            except _StepError as error:
                st.session_state[result_key] = None
                st.session_state[snapshots_key] = []
                st.session_state[last_run_key] = None
                # remembered so the message stays in the step's card on the next reruns
                st.session_state[errors_key] = {error.step_id: str(error)}
                st.session_state[message_key] = ("error", "Pipeline failed - see the step marked in red.")
            # show the final result again after a run, not the step picked before it
            st.session_state.pop(f"{key}_show_step", None)
            # full page rerun, so the mesh/export section sees the new result (see WHY A FRAGMENT)
            st.rerun(scope="app")

        # message of the last run: shown once, on the rerun that follows it
        if message_key in st.session_state:
            level, text = st.session_state.pop(message_key)
            getattr(st, level)(text)    # st.success(text) or st.error(text)
        if result_is_out_of_date:
            st.warning("The steps (or the loaded volume) changed since the last run: "
                       "the preview and the mesh section below still use the last run's result.")
        st.divider()

        # Rendered every rerun (not gated on "just ran") so the preview
        # stays visible while you keep editing the pipeline in between runs.
        if result is not None:
            _render_result_preview(result, st.session_state[snapshots_key], key, spacing)

    # Last lines of the fragment: copy the pipeline's settings into the
    # page-switch mirror (see SAVE / LOAD in render_ct_pipeline). It must be
    # here, not only at the end of the page: a fragment-only rerun (any
    # edit of a step) never reaches the end of the page script.
    exclude_keys, exclude_suffixes = _not_saved(key)
    mirror_widget_state(f"{key}_", exclude_keys=exclude_keys, exclude_suffixes=exclude_suffixes)


# =====================================================================
# 14) render_ct_pipeline
# =====================================================================
def render_ct_pipeline(array: np.ndarray, key: str = "ct_pipeline", spacing: tuple = (1.0, 1.0, 1.0),
                       volume_path: Optional[str] = None) -> Optional[np.ndarray]:
    """
    ============================================================================
    14) RENDER_CT_PIPELINE
    Renders the full pipeline builder (add step / edit / reorder / remove /
    turn on-off / run) for a loaded CT volume, plus a 2D slice preview of
    the result.
    ============================================================================

    PARAMETERS
    ----------
    array : np.ndarray
        The loaded volume to process, e.g. sitk.GetArrayFromImage(image).
        Never mutated - every run starts from a fresh copy.
    key : str, optional
        Session-state key prefix, so multiple pipelines can coexist on a
        page if ever needed.
    spacing : tuple, optional
        (sx, sy, sz) physical voxel spacing, forwarded to the preview.
    volume_path : str, optional
        Path of the .mhd file `array` was loaded from. Needed only by the
        "Manual selection (viewer)" step, which opens the viewer on that
        file (default None: that step's viewer button is disabled).

    RETURNS
    -------
    result : np.ndarray or None
        The processed volume from the last successful "Run pipeline"
        click, or None if the pipeline hasn't been run yet (e.g. the
        caller can use this to decide whether to show an "Export" button).

    NOTES
    -----
    Deliberately NOT a fragment itself: it only sets up session_state,
    calls the fragment _render_pipeline_section, and returns the result
    from session_state. A fragment's return value can't be relied on by
    the page, while this plain function's can, on every full page run.

    SESSION-STATE KEYS
    ------------------
    {key}_steps                      list of {"id", "type"}: order and type of the steps
    {key}_step_errors                dict step_id -> error message of the last failed run
    {key}_result                     final volume of the last successful run (or None) - the only full volume kept
    {key}_snapshots                  list of (label, mid z-slice) of the last run, for "Show result after step"
    {key}_last_run                   {"volume": (id, shape), "signatures": [...]} of the last successful run, or None
    {key}_run_message                (level, text) of the last run, shown once after it
    {key}_show_step                  "Show result after step" picker
    {key}_new_step_group             category picker of the add-step bar
    {key}_op_select                  step type picker of the add-step bar
    {key}_add_btn / _clear_btn       "Add step" / "Clear all" buttons
    {key}_run_btn                    "Run pipeline" button
    {key}_{id}_enabled               on/off toggle of a step
    {key}_{id}_up / _down / _del     move / delete buttons of a step
    {key}_{id}_{param name}          one widget per Param of the step
    {key}__mirror                    page-switch copy of the settings (page_state.mirror_widget_state)
    Saved to a file / mirrored: every key above except those listed by _not_saved().
    """
    # SAVE / LOAD: every setting of the pipeline is a session_state key
    # starting with f"{key}_" (the step list and each step's widgets), so
    # app.components.page_state handles it like a page prefix:
    #   - restore_widget_state: puts back the values Streamlit deleted while
    #     the user was on another page (or while no volume was loaded, since
    #     the pipeline isn't drawn then). Before any widget of the pipeline.
    #   - render_state_io: "Load and save session settings" expander, files
    #     in <output folder>/sessions_saves/, listed only here (the file
    #     records its prefix). Drawn OUTSIDE the fragment on purpose: its
    #     Load button then reruns the whole page, so the mesh section sees
    #     that loading cleared the result.
    #   - mirror_widget_state: at the end of the fragment (see there).
    # Only the pipeline is saved, not the rest of the CT page (mesh and
    # export settings): those widgets are drawn with value=, which would
    # trigger Streamlit's "set via the Session State API" warning on restore.
    settings_prefix = f"{key}_"
    exclude_keys, exclude_suffixes = _not_saved(key)
    restore_widget_state(settings_prefix)

    st.session_state.setdefault(f"{key}_steps", [])
    st.session_state.setdefault(f"{key}_step_errors", {})
    st.session_state.setdefault(f"{key}_result", None)
    st.session_state.setdefault(f"{key}_snapshots", [])
    st.session_state.setdefault(f"{key}_last_run", None)
    # A step list saved by the Phase-0 version of this file ({"label", "params"}
    # dicts, no "id") can still be in session_state after a hot reload: drop it.
    if any("id" not in step for step in st.session_state[f"{key}_steps"]):
        st.session_state[f"{key}_steps"] = []

    st.subheader("Processing pipeline")
    render_state_io(settings_prefix, exclude_keys=exclude_keys, exclude_suffixes=exclude_suffixes)
    _render_pipeline_section(array, key, spacing, volume_path)
    return st.session_state[f"{key}_result"]
