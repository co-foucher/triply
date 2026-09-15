
from typing import Optional, Union

import numpy as np
import streamlit as st

from triply.TPMS_classes.tpms_custom import CustomTPMSModel
from app.components.equation_input import evaluate_custom_inputs, EquationError
from app.components.file_picker import browse_file
from app.components.import_TPMS_files import import_matrix_from_file
from app.components.equation_input import render_equation_input

# ---- Field modes (label -> TPMSModel.compute_field(mode=...) argument) ----
FIELD_MODES = {
    "Distance": "distance",
    "Signed": "signed",
    "Signed (inverted)": "signed_inverse",
    "Band": "band",
}

FIELD_HELPS = {
    "Distance": "The density field is computed as the distance (defined by the thickness) to an iso-surface (defined by the threshold).",
    "Signed": "The density field is computed by implicit_field > threshold.",
    "Signed (inverted)": "The density field is computed by implicit_field < threshold.",
    "Band": "The density field is computed as density_field = (thickness - np.abs(implicit_field)) > threshold. This is a fast approximation of the distance field",
}

# Reverse of FIELD_MODES ("distance" -> "Distance"), for turning the internal
# mode string back into its display label - e.g. for the "ignored in mode X"
# caption in render_thickness(), which only receives field_mode.
FIELD_MODE_LABELS = {v: k for k, v in FIELD_MODES.items()}

# SKELETAL_MODES: threshold defines the solid region directly, no thickness used
# SHEET_MODES: threshold locates a surface that's then thickened
# Also imported by app/pages/1_Generate_TPMS.py for its generate-dispatch branching.
SKELETAL_MODES = ("signed", "signed_inverse")
SHEET_MODES = ("band", "distance")


"""
#=====================================================================================================================
0 - (reserved)
1 - _adapt_resolution
2 - render_field_mode
3 - load_STL
4 - render_threshold
5 - render_thickness
6 - generate_ui_tpms
7 - pad_to_square
8 - render_period_input
#=====================================================================================================================
"""


# =====================================================================
# 1) _adapt_resolution
# =====================================================================
def _adapt_resolution(field:np.ndarray, params) -> np.ndarray:
    """
    ============================================================================
    1) _ADAPT_RESOLUTION
    Resamples an imported field/geometry array to match the requested grid
    resolution, warning the user in the UI that this happened.
    ============================================================================

    PARAMETERS
    ----------
    field : np.ndarray
        Imported voxel array whose shape doesn't match params.resolution.
    params : TPMSParams
        Generation settings bundle; params.resolution gives the target size
        along each axis.

    RETURNS
    -------
    field : np.ndarray
        The array resampled to (params.resolution,) * 3.
    """
    st.warning(f"Imported field shape {field.shape} does not match the expected resolution ({params.resolution}, {params.resolution}, {params.resolution}). Field will be resampled to the requested resolution.")
    from triply import voxel_tools
    field = voxel_tools.interpolate_voxel_grid(field, params.resolution, params.resolution, params.resolution)
    return field


# =====================================================================
# 2) render_field_mode
# =====================================================================
def render_field_mode() -> str:
    """
    ============================================================================
    2) RENDER_FIELD_MODE
    Draws the "Field mode" selectbox and returns the selected mode.
    ============================================================================

    PARAMETERS
    ----------
    None

    RETURNS
    -------
    field_mode : str
        One of "distance", "signed", "signed_inverse", "band".
    """
    mode_label = st.selectbox(
        "Field Calculation Mode", list(FIELD_MODES.keys()), index=0,
        key="field_mode",
        help=FIELD_HELPS[st.session_state.get("field_mode", "Distance")],
    )
    return FIELD_MODES[mode_label]

# =====================================================================
# 3) load_STL
# =====================================================================
@st.cache_data(show_spinner=False)
def load_STL(stl_path: str) -> tuple[np.ndarray, np.ndarray]:
    """
    ============================================================================
    3) LOAD_STL
    Loads an STL file and returns its vertices and faces as numpy arrays.
    ============================================================================

    PARAMETERS
    ----------
    stl_path : str
        Path to the STL file.

    RETURNS
    -------
    verts : np.ndarray
        Array of shape (N, 3) containing the vertex coordinates.
    faces : np.ndarray
        Array of shape (M, 3) containing the indices of the vertices that
        form each triangular face.
    """
    from stl import mesh

    # Load the STL file
    your_mesh = mesh.Mesh.from_file(stl_path)

    # Get the vertices and faces
    verts = your_mesh.vectors.reshape(-1, 3)
    faces = np.arange(len(verts)).reshape(-1, 3)

    return verts, faces

# =====================================================================
# 4) render_threshold
# =====================================================================
def render_threshold(field_mode: str, params) -> np.ndarray:
    """
    ============================================================================
    4) RENDER_THRESHOLD
    Draws the threshold/level widget appropriate for field_mode and returns
    its value.
    ============================================================================

    PARAMETERS
    ----------
    field_mode : str
        The value returned by render_field_mode(). Depending on the mode,
        the threshold widget is either a number_input or not drawn at all
        (band mode ignores threshold entirely).

    RETURNS
    -------
    threshold : float
        The level/threshold value.
    """
    if field_mode == "band":
            return 0.0  # Band ignores level/threshold entirely - no widget
    else:
        threshold_field_source = st.segmented_control( "Threshold", ["Constant", "Custom equation", "Import from file"], default="Constant", key="threshold_field_source",)
        if threshold_field_source == "Constant":
            value = st.number_input(
                "Field threshold",
                value=0.0, label_visibility="collapsed")
            return value
        elif threshold_field_source == "Custom equation":
            custom_threshold_equation = render_equation_input(label="Custom threshold", 
                                                            default_equation = "0.3 + 0.8 * x / max(abs(x))", 
                                                            key_prefix="threshold_eq",
                                                            size_x=params.size_x,
                                                            size_y=params.size_y)
            if custom_threshold_equation is None:
                st.error("Please enter a valid custom threshold equation.")
                return np.full_like(params.x, 0.0)
            else:
                custom_threshold = evaluate_custom_inputs(custom_threshold_equation, params.x, params.y, params.z)
                return np.array(custom_threshold)
        elif threshold_field_source == "Import from file":
            browse_file(
                    key=f"threshold_field_matrix_path",
                    title=f"Select a threshold matrix file",
                    filetypes=[("Numpy files", "*.npy"), ("All files", "*.*")],
                )
            # import the matrix from file
            threshold_matrix = import_matrix_from_file(
                file_path=st.session_state[f"threshold_field_matrix_path"])
            if threshold_matrix is not None:
                if threshold_matrix.shape != (params.resolution,) * 3:
                        threshold_matrix = _adapt_resolution(threshold_matrix, params)
                return threshold_matrix

    return 0.0
            

# =====================================================================
# 5) render_thickness
# =====================================================================
def render_thickness(
    field_mode: str,
    params,
) -> Optional[float]:
    """
    ============================================================================
    5) RENDER_THICKNESS
    Draws the "Thickness" widget,
    when the caller already has its own thickness source - shows a caption
    instead.
    ============================================================================

    PARAMETERS
    ----------
    field_mode : str
        The value returned by render_field_mode().

    RETURNS
    -------
    thickness : float or np.ndarray
    """

    if field_mode not in SHEET_MODES:
        mode_label = FIELD_MODE_LABELS.get(field_mode, field_mode)
        st.caption(
            f"Note: thichkness is not used in {mode_label}' mode."
        )
        return None  # thickness is ignored in skeletal modes

    if field_mode in SHEET_MODES:
        #thickness_field_source = st.radio("Field Thickness", ["Constant", "Custom equation", "Import from file"], horizontal=True, key="thickness_field_source")
        thickness_field_source = st.segmented_control( "Thickness", ["Constant", "Custom equation", "Import from file"], default="Constant", key="thickness_field_source",)
        if thickness_field_source == "Constant":
            return st.number_input("Thickness", value=0.6, min_value=0.05, key="tpms_thickness", label_visibility="collapsed")
        elif thickness_field_source == "Custom equation":
            custom_thickness_equation = render_equation_input(label="Custom thickness equation", 
                                                              default_equation = "0.3 + 0.8 * x / max(abs(x))", 
                                                              key_prefix="thickness_eq",
                                                              size_x=params.size_x, size_y=params.size_y)
            if custom_thickness_equation is None:
                st.error("Please enter a valid custom thickness equation.")
                return 1.0
            else:
                custom_thickness = evaluate_custom_inputs(custom_thickness_equation, params.x, params.y, params.z)
                return custom_thickness
        elif thickness_field_source == "Import from file":
            browse_file(
                    key=f"thickness_field_matrix_path",
                    title=f"Select a thickness matrix file",
                    filetypes=[("Numpy files", "*.npy"), ("All files", "*.*")],
                )
            # import the matrix from file
            thickness_matrix = import_matrix_from_file(
                file_path=st.session_state[f"thickness_field_matrix_path"])
            if thickness_matrix is not None:
                if thickness_matrix.shape != (params.resolution,) * 3:
                        thickness_matrix = _adapt_resolution(thickness_matrix, params)
                return thickness_matrix
    return 0.0


# =====================================================================
# 6) generate_ui_tpms
# =====================================================================
def generate_ui_tpms(
    params,
    BUILTIN_TYPES: dict,
) -> None:
    """
    ============================================================================
    6) GENERATE_UI_TPMS
    Builds the TPMS model for the current gui inputs,
    computes its density field and mesh, and stores the result in
    st.session_state["current_model"]
    ============================================================================

    PARAMETERS
    ----------
    params : TPMSParams
        The generation settings bundle from 1_Generate_TPMS.py (grid size,
        resolution, field mode, threshold, baseplate thickness, mesh
        simplification/smoothing options). For "Built-in type", also
        supplies params.thickness.
    BUILTIN_TYPES : dict
        Maps a built-in type label (e.g. "Gyroid") to its TPMSModel
        subclass. Only used when source == "Built-in type".

    RETURNS
    -------
    None

    RAISES
    ------
    ValueError
        If params.field_mode is not one of the known SKELETAL_MODES/
        SHEET_MODES values.

    NOTES
    -----
    - EquationError raised by evaluate_custom_inputs() is caught internally
      and shown as a Streamlit error message rather than propagating.
    """
    x, y, z = np.meshgrid(
        np.linspace(0, params.size_x, params.resolution),
        np.linspace(0, params.size_y, params.resolution),
        np.linspace(0, params.size_z, params.resolution),
        indexing="ij",)

    try:
        with st.spinner("Computing field and generating mesh..."):
            # ----- Built-in type ------
            if params.implicit_field_source == "Built-in type":
                model = BUILTIN_TYPES[params.type_name](x, y, z, params.px, params.py, params.pz, params.thickness)

            # ----- Custom equation ------
            elif params.implicit_field_source == "Custom equation":
                params.field = evaluate_custom_inputs(params.custom_equation, x, y, z)
                model = CustomTPMSModel(x, y, z, params.thickness, field=params.field)

            # ----- Import from file ------
            elif params.implicit_field_source == "Import from file":
                model = CustomTPMSModel(x, y, z, params.thickness, field=params.field)

            # ---- compute density_field ------
            if params.field_mode in SKELETAL_MODES:   # "signed", "signed_inverse"
                model.compute_field(mode=params.field_mode, level=params.threshold)
            elif params.field_mode in SHEET_MODES:   # "band", "distance"
                model.compute_field(mode=params.field_mode, level=params.threshold)
            else:
                raise ValueError(f"Unknown field mode: {params.field_mode}")

            # ----- add baseplates ------
            if params.baseplate_thickness > 0:
                model.add_baseplates(thickness=params.baseplate_thickness)

            # ----- combine with imported geometry ------
            if params.geometry is not None:
                if params.geometry.shape != (params.resolution, params.resolution, params.resolution):
                    params.geometry = _adapt_resolution(params.geometry, params)
                    params.geometry = params.geometry > 0.5
                if params.combination_type == "Union":
                    model.density_field[params.geometry > 0] = 1  # union: set solid where geometry is solid
                    #model.density_field[geometry <= 0] = 0  # union: set solid where geometry is solid
                elif params.combination_type == "Intersection":
                    model.density_field[params.geometry == 0] = -1  # intersection: set non-solid where geometry is non-solid
                elif params.combination_type == "Substraction":
                    model.density_field[params.geometry > 0] = -1       # difference:  first, set solid where geometry is solid
                else:
                    st.error(f"Unknown combination type: {params.combination_type}")

            # ----- generate mesh ------
            st.session_state["current_field_range"] = (float(model.implicit_field.min()), float(model.implicit_field.max()))
            model.generate_mesh(iso_level=0)
            if params.auto_smooth:
                model.smooth_mesh(smoothing_factor=params.smoothing_factor)
            target_faces = params.max_faces_count if params.max_faces else params.simplification_factor
            model.simplify_mesh(target_faces=target_faces)
            model.fix_mesh()
            is_valid = model.check_mesh_quality()

        st.session_state["current_model"] = model

        if not is_valid:
            st.warning(
                "Generated mesh failed validity checks (not watertight / "
                "self-intersecting). Try a coarser grid, a different "
                "thickness, or a different field mode."
            )
        else:
            st.success(f"Mesh generated: {len(model.faces)} faces.")
    except EquationError as e:
        st.error(f"Equation error: {e}")



# =====================================================================
# 7) pad_to_square
# =====================================================================

def pad_to_square(matrix, pad_value=0):
    """
    ============================================================================
    7) PAD_TO_SQUARE
    Pads a matrix with a constant value so every axis matches the largest
    axis, making the array square along each dimension.
    ============================================================================

    PARAMETERS
    ----------
    matrix : np.ndarray
        The array to pad.
    pad_value : scalar, optional
        The constant fill value used for padding (default = 0).

    RETURNS
    -------
    padded : np.ndarray
        The padded array, with each dimension equal to max(matrix.shape).
    """
    target = max(matrix.shape)
    pad_width = [(0, target - dim) for dim in matrix.shape]
    return np.pad(matrix, pad_width=pad_width, mode="constant", constant_values=pad_value)


# =====================================================================
# 8) render_period_input
# =====================================================================
def render_period_input(
    axis: str,
    params,
    default: float = 5.0,
) -> Optional[Union[float, np.ndarray]]:
    """
    ============================================================================
    8) RENDER_PERIOD_INPUT
    Draws the "Period <axis>" input for one grid axis: a segmented control
    to choose between a constant value and an imported per-voxel period
    field, plus the widget for whichever source is selected. Replaces three
    near-identical copies of this logic (one per axis) that used to live
    inline in 1_Generate_TPMS.py.
    ============================================================================

    PARAMETERS
    ----------
    axis : str
        Axis label, e.g. "X", "Y", "Z" - used in widget labels/keys and
        error messages.
    params : TPMSParams
        Generation settings bundle; params.resolution gives the target grid
        size, used to validate/resample an imported period field.
    default : float, optional
        Default value for the "Constant" number_input (default 5.0).
    
    RETURNS
    -------
    period : float, np.ndarray, or None
    """
    # ------ select source: constant vs imported matrix -----
    source = st.segmented_control(
        f"Period {axis}", ["Constant", "Custom", "Import"],
        default="Constant",
        key=f"period_{axis.lower()}_source",
    )

    # ------ if source == constant ------
    if source == "Constant":
        return st.number_input(
            f"Period {axis}", value=default, min_value=0.01,
            key=f"tpms_p{axis.lower()}",label_visibility="collapsed",
        )

    # ------ if source == custom ------
    if source == "Custom":
        custom_period_equation = render_equation_input(
            label=f"Custom Period {axis} equation",
            default_equation=f"2.0 + 4.0 * {axis.lower()} / max(abs({axis.lower()}))",
            key_prefix=f"period_{axis.lower()}_eq",
            size_x=params.size_x, size_y=params.size_y,
        )
        if custom_period_equation is None:
            st.error(f"Please enter a valid custom Period {axis} equation.")
            return 5.0
        else:
            custom_period = evaluate_custom_inputs(
                custom_period_equation, params.x, params.y, params.z
            )
            return np.array(custom_period)

    # ------ if source == import ------
    # Render the "Browse..." button and 
    browse_file(
        key=f"{axis.upper()}_period_matrix_path",
        title=f"Select a {axis.upper()}-period matrix file",
        filetypes=[("Numpy files", "*.npy"), ("All files", "*.*")],
        small_ui=True,
    )
    # import the matrix from file
    period_matrix = import_matrix_from_file(
        file_path=st.session_state[f"{axis.upper()}_period_matrix_path"]
    )
    # validate the imported matrix
    if period_matrix is None:
        st.error(f"Please select a valid {axis.upper()}-period matrix file.")
        return None  # import failed / no file picked yet - already reported
    elif period_matrix.ndim != 3:
        st.error(f"Please select a valid 3D array for Period {axis}.")
        return None
    elif period_matrix.shape != (params.resolution,) * 3:
        period_matrix = _adapt_resolution(period_matrix, params)
    return period_matrix
