"""
Generate a TPMS structure: pick a built-in surface type or paste a custom
equation, set periods/thickness/resolution/mesh options, preview the
result, and export an STL.

STATUS: functional.
"""
# Repo root isn't on sys.path by default - add it before importing
# anything under `app.*`. See app/_bootstrap.py for why this is inlined
# per-file rather than a shared import.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dataclasses import dataclass
from typing import Optional, Union

import numpy as np
import streamlit as st

st.set_page_config(page_title="Generate TPMS", layout="wide")

# Heavy imports (mesh/vtk/plotly/sympy stack, pulled in transitively via
# triply.TPMS_classes) live behind a spinner so the page shows
# something immediately instead of appearing frozen on first load. Cached
# after the first import - see src/triply/__init__.py.
with st.spinner("Loading triply toolkit..."):
    from triply.TPMS_classes import (
        GyroidModel, SchwartzPModel, DiamondModel, IWPModel, NeoviusModel,
        FischerKochSModel, FRDModel, LidinoidModel, SplitPModel,
    )

    from app.state import init_state, get_output_dir
    from app.components.equation_input import render_equation_input
    from app.components.mesh_preview import render_mesh_preview
    from app.components.field_view import render_field_slice
    from app.components.file_picker import browse_file, browse_directory
    from app.components.import_TPMS_files import import_matrix_from_file
    from app.components.documentation import generate_TPMS_doc

init_state()

# ============================================================
# ============== define internal variables ===================
# ============================================================

# ---- Built-in TPMS types (label -> class) ------
BUILTIN_TYPES = {
    "Gyroid": GyroidModel,
    "Schwartz P": SchwartzPModel,
    "Diamond": DiamondModel,
    "I-WP": IWPModel,
    "Neovius": NeoviusModel,
    "Fischer-Koch S": FischerKochSModel,
    "F-RD": FRDModel,
    "Lidinoid": LidinoidModel,
    "Split-P": SplitPModel,
}


# ---- Field modes (label -> TPMSModel.compute_field(mode=...) argument) ----
from app.components.tpms_source_panel import (
    _adapt_resolution,
    render_field_mode,
    render_threshold,
    render_thickness,
    load_STL,
    generate_ui_tpms,
    pad_to_square,
    render_period_input,
)

#dataclasses is a decorator from Python's standard library that turns a plain class into a lightweight data container: 
# with just type-annotated attributes and default values, it generates __init__, __repr__, and __eq__ for you. 
@dataclass
class TPMSParams:
    """
    Bundles every generation setting the "Generate" button and
    generate_ui_tpms() need, including the per-source-only inputs
    (periods px/py/pz, type_name, custom_equation, ...) that only one
    "Surface" branch at a time fills in. All of it lives on this one
    object - and is mutated in place, never reassigned - because
    _make_user_define_parameters() is an @st.fragment: a fragment-only
    rerun only re-executes that function, so a plain local variable set
    there would never reach the rest of the script.
    """
    # ----- grid parameters -----
    size_x: float = 10.0
    size_y: float = 10.0
    size_z: float = 10.0
    resolution: int = 64
    x: np.ndarray = None
    y: np.ndarray = None
    z: np.ndarray = None
    # ----- implicit field definition -----
    implicit_field_source: str = "Built-in type"
    type_name: str = "Gyroid"
    px: Union[float, np.ndarray] = 5.0
    py: Union[float, np.ndarray] = 5.0
    pz: Union[float, np.ndarray] = 5.0
    custom_equation: str = None
    field: np.ndarray = None
    # ----- solid definition -----
    field_mode: str = "Threshold"
    threshold: Union[float, np.ndarray] = 0.0
    thickness: Union[float, np.ndarray] = 1.0
    # ----- baseplate -----
    baseplate_thickness: float = 0.0
    # ----- combine with geometry -----
    geometry: np.ndarray = None
    combination_type: str = None
    geometry_verts: np.ndarray = None
    geometry_faces: np.ndarray = None
    # ----- mesh parameters -----
    simplification_factor: float = 0.9
    max_faces: bool = False
    max_faces_count: int = 100000
    auto_smooth: bool = True
    smoothing_factor: float = 0.9


# ============================================================
# ============== define internal functions ===================
# ============================================================



# ============================================================
# ===================== Start Page ===========================
# ============================================================
st.title("Generate a TPMS structure")

generate_TPMS_doc()  # render the "How it works" explainer, cached so it doesn't re-run every rerun

col_params, col_preview = st.columns([1.4, 1])

# ==========================================================
# ============== user defined parameters ===================
# ==========================================================
params = TPMSParams()  # fresh instance every full rerun, filled with dataclass
                        # defaults. Each widget below overwrites its own field with
                        # its actual current value. This only works because every
                        # widget has an explicit, stable key= - without one, passing
                        # a changing `value=params.xxx` as the widget's default makes
                        # Streamlit treat it as a new widget each rerun and reset it
                        # to that default, discarding whatever the user had set.

@st.fragment
def _make_user_define_parameters(params: TPMSParams):
    # ------ grid parameters ------
    st.subheader("Grid parameters")
    params.resolution = st.slider(
        "Grid resolution (per axis)", 16, 500, params.resolution, step=8,
        key="tpms_resolution",
        help="Higher = finer surface but slower generation. Start low (~48-64) while iterating.",
    )
    d1, d2, d3 = st.columns(3)
    params.size_x = d1.number_input("Size X", value=params.size_x, min_value=0.01, key="tpms_size_x")

    params.size_y = d2.number_input("Size Y", value=params.size_y, min_value=0.01, key="tpms_size_y")
    params.size_z = d3.number_input("Size Z", value=params.size_z, min_value=0.01, key="tpms_size_z")
    params.x, params.y, params.z = np.meshgrid(
            np.linspace(0, params.size_x, params.resolution),
            np.linspace(0, params.size_y, params.resolution),
            np.linspace(0, params.size_z, params.resolution),
            indexing="ij",)
    st.divider()

    # ------ Implcit field definition ------
    st.subheader("Implicit field definition")
    params.implicit_field_source = st.radio("Source", ["Built-in type", "Custom equation", "Import from file"], horizontal=True, key="implicit_field_source")
    if params.implicit_field_source == "Built-in type":
        params.type_name = st.selectbox("TPMS type", list(BUILTIN_TYPES.keys()), key="tpms_type_name")
        c1, c2, c3 = st.columns(3)
        with c1:
            params.px = render_period_input(axis = 'X', params = params,)
        with c2:
            params.py = render_period_input(axis = 'Y', params = params,)
        with c3:
            params.pz = render_period_input(axis = 'Z', params = params,)

    elif params.implicit_field_source == "Custom equation":
        params.custom_equation = render_equation_input(label="Custom implicit surface", size_x=params.size_x, size_y=params.size_y, size_z=params.size_z, key_prefix="tpms_custom_equation")
    elif params.implicit_field_source == "Import from file":
        browse_file(key = "field_matrix_path",
            title="Select a matrix file",
            filetypes=[("Numpy files", "*.npy"), ("CSV files", "*.csv"), ("All files", "*.*")],)
        params.field = import_matrix_from_file(file_path = st.session_state["field_matrix_path"])
        if params.field is not None :
            params.field = _adapt_resolution(params.field, params)


    st.divider()
    # ------ density_field field definition ------
    st.subheader("Density Field Definition")
    params.field_mode = render_field_mode()
    params.threshold = render_threshold(params.field_mode, params=params)
    params.thickness = render_thickness(params.field_mode, params=params)

    st.divider()
    # ----- add baseplate ------
    col_1, col_2 = st.columns([1, 15], vertical_alignment="bottom")
    with col_1:
        add_baseplate = st.checkbox(" ", value=False, key="tpms_add_baseplate")
    with col_2:
        st.subheader("Baseplates")
    if add_baseplate:
        params.baseplate_thickness = st.number_input("Baseplate thickness (0 = none)", value=params.baseplate_thickness, min_value=0.0, key="tpms_baseplate_thickness")
    st.divider()

    # ----- Combine with geometry ------
    col_1, col_2 = st.columns([1, 15], vertical_alignment="bottom")
    with col_1:
        combine_with_geometry = st.checkbox(" ", value=False, key="tpms_combine_with_geometry")
    with col_2:
        st.subheader("Combine with existing geometry")
    if combine_with_geometry:
        browse_file(key = "combined_geometry_path",
            title="Select a matrix file",
            filetypes=[("STL files", "*.stl"), ("Numpy files", "*.npy"), ("All files", "*.*")],)
        if '.npy' in st.session_state["combined_geometry_path"]:
            params.geometry = import_matrix_from_file(file_path = st.session_state["combined_geometry_path"])
            params.geometry = pad_to_square(params.geometry)
            params.geometry_verts = None
            params.geometry_faces = None
        elif '.stl' in st.session_state["combined_geometry_path"]:
            from triply.mesh_tools import matrix_from_mesh
            params.geometry_verts, params.geometry_faces = load_STL(st.session_state["combined_geometry_path"])
            _,_,_, params.geometry = matrix_from_mesh(params.geometry_verts, params.geometry_faces, params.resolution)
            params.geometry = pad_to_square(params.geometry)
        else:
            st.error("Please select a valid .npy or .stl file for the geometry.")
            params.geometry_verts = None
            params.geometry_faces = None
        params.combination_type = st.selectbox("Combination type", ["Intersection", "Union", "Substraction"], key="tpms_combination_type")

    st.divider()
    # ----- mesh parameters ------
    #smoothing
    st.subheader("Mesh parameters")
    params.auto_smooth = st.checkbox("Auto-smooth mesh", value=params.auto_smooth,
            key="tpms_auto_smooth",
            help="If checked, the mesh is smoothed after simplification and again after fixing.")
    if params.auto_smooth:
        params.smoothing_factor = st.slider(
            "Smoothing factor", 0.0, 1.0, params.smoothing_factor, step=0.01,
            key="tpms_smoothing_factor",
            help="Passed to TPMSModel.smooth_mesh(smoothing_factor=...). Higher = more smoothing.")
    # simplification
    params.simplification_factor = st.slider(
        "Mesh simplification (fraction of faces kept)", 0.1, 1.0, params.simplification_factor,
        key="tpms_simplification_factor",
        help="Passed to TPMSModel.simplify_mesh(target_faces=...).",)
    params.max_faces = st.checkbox("Limit maximum faces", value=params.max_faces,
        key="tpms_max_faces",
        help="If checked, the mesh is simplified to a maximum number of faces.")
    if params.max_faces:
        params.max_faces_count = st.number_input(
            "Maximum faces", value=params.max_faces_count, min_value=1,
            key="tpms_max_faces_count",
            help="If 'Limit maximum faces' is checked, the mesh is simplified to this many faces.",)
    
    return params

with col_params:
    params = _make_user_define_parameters(params=params)
    # ----- generate button ------
    generate = st.button(
        "Generate", type="primary",
        disabled=(params.implicit_field_source == "Custom equation" and params.custom_equation is None),)


if params.geometry_verts is not None and params.geometry_faces is not None:
    with col_preview:
        st.subheader("combined geometry preview")
        render_mesh_preview(params.geometry_faces, params.geometry_verts, key="c_geometry")


# ==========================================================
# ===================== generate TPMS ======================
# ==========================================================
if generate:
    generate_ui_tpms(
        params=params,
        BUILTIN_TYPES=BUILTIN_TYPES,
    )

model = st.session_state.get("current_model")


# ==========================================================
# =================== preview section ======================
# ==========================================================
with col_preview:
    st.subheader("IMPLICIT Field (2D slice)")
    if model is not None and model.implicit_field is not None:
        render_field_slice(
            model.implicit_field, model.x, model.y, model.z, key="impolicti_field_preview",
            value_range=st.session_state.get("current_field_range"),
        )
        if not isinstance(params.threshold, float) and not isinstance(params.threshold, tuple):
            st.subheader("Complex Threshold Field (2D slice)")
            render_field_slice(
                params.threshold, model.x, model.y, model.z, key="complex_threshold_field_preview",
            )
        if not isinstance(params.thickness, float) and not isinstance(params.thickness, tuple):
            st.subheader("Complex Thickness Field (2D slice)")
            render_field_slice(
                params.thickness, model.x, model.y, model.z, key="complex_thickness_field_preview",
        )
    else:
        st.info("Compute a field first to see the 2D slice view.")

    
    st.subheader("Mesh preview")
    if model is not None and model.faces is not None:
        render_mesh_preview(model.faces, model.verts, key="generate")
    else:
        st.info("Set parameters and click Generate.")



# ==========================================================
# ================ save outputs section ====================
# ==========================================================
with col_preview:
    if model is not None and model.faces is not None:
        name = st.text_input("File name", value="my_tpms")

        # ----- Export STL ------
        if st.button("Export STL"):
            out_path = get_output_dir() / name
            model.export_stl(str(out_path))
            model.save_mesh_preview(str(out_path))  # keep an .html alongside the .stl, picked up by the Library page
            st.success(f"Saved {out_path}.stl (+ preview .html)")

        # ----- Export TPMS field ------
        if st.button("Export TPMS implicit field (.npy)"):
            out_path = get_output_dir() / name
            if model.implicit_field is None: # check if  field exists
                st.warning("No TPMS field available to export. Please ensure that the model field exists before exporting.")
            np.save(str(out_path) + ".npy", model.implicit_field)
            st.success(f"Saved {out_path}.npy")

        # ----- Export TPMS thickness field ------
        if st.button("Export TPMS thickness field (.npy)"):
            out_path = get_output_dir() / (name + "_thickness")
            if model.thickness is None: # check if thickness field exists
                st.error("No thickness field available to export. Please ensure that the model has a thickness field before exporting.")
            elif isinstance(model.thickness, float): #check if thickness field is a float
                st.warning("Thickness field is a float, not an array...")
                np.save(str(out_path) + ".npy", np.array([model.thickness])) #save as a 1D array
                st.success(f"Saved {out_path}.npy")
            elif isinstance(model.thickness, np.ndarray) and model.thickness.ndim == 3: #check if thickness field is a 3D array
                np.save(str(out_path) + ".npy", model.thickness)
                st.success(f"Saved {out_path}.npy")
            else:
                st.error("Thickness field is not a valid 3D array. Please ensure that the model's thickness field is a valid 3D array before exporting.")
    else:
        st.info("Set parameters and click Generate.")
