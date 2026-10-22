"""
CT scan conversion + a static preview.

STATUS: scaffold. Deliberately does NOT rebuild the existing interactive
slice-scrubbing viewer (triply.CT_visualization_window) in the
browser: that viewer's scroll-to-scrub / click-to-inspect interactions
don't translate well to Streamlit's rerun-per-widget-interaction model.
Instead this page handles conversion + a simple static slice preview, and
can launch the existing matplotlib/Qt viewer as a separate process for the
full interactive experience.
"""
import sys
from functools import partial
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from app.components.branding import PAGE_ICON

st.set_page_config(page_title="CT Analysis", page_icon=PAGE_ICON, layout="wide")

# Heavy imports (SimpleITK/vtk/mesh/plotly stack) live behind a spinner so
# the page shows something immediately instead of appearing frozen on
# first load. Cached after the first import - see
# src/triply/__init__.py.
with st.spinner("Loading triply toolkit..."):
    import numpy as np
    import plotly.graph_objects as go
    import SimpleITK as sitk

    from triply import CT_scans, mesh_tools, viz

    from app.state import init_state, get_output_dir
    from app.components.file_picker import browse_file, browse_directory
    from app.components.ct_pipeline import render_ct_pipeline
    from app.components.mesh_preview import render_mesh_preview
    from app.components.ct_viewer_launcher import render_lightweight_toggle, launch_ct_viewer, CT_histogram
    from app.components.documentation import CT_analysis_doc
    from app.components.tpms_source_panel import render_smoothing_preview
    from app.components.page_state import restore_widget_state, mirror_widget_state

init_state()

# Keep the selected files across page switches. Streamlit deletes a widget's
# value when the user opens another page, and the "Path to file" box below is
# a widget: without this, coming back shows no volume, so the pipeline,
# preview and mesh sections (all inside `if mhd_path:`) disappear too.
# restore/mirror match keys by PREFIX, so these two prefixes cover only
# "ct_mhd_path" / "ct_input_path" (+ the "_browse_error" message of their
# Browse button); the pipeline keeps its own settings (ct_pipeline.py).
CT_KEPT_PATH_PREFIXES = ("ct_mhd_path", "ct_input_path")
for kept_prefix in CT_KEPT_PATH_PREFIXES:
    restore_widget_state(kept_prefix)    # before any widget is drawn

st.title("CT Scan Analysis")

CT_analysis_doc()  # render the "How it works" explainer, cached so it doesn't re-run every rerun

# ===========================================
# =============== functions =================
# ===========================================

@st.cache_resource(show_spinner="Loading volume...", max_entries=1)
def _load_mhd(path: str):
    image = sitk.ReadImage(path)
    array = sitk.GetArrayFromImage(image)  # (z, y, x)
    array.setflags(write=False)
    return array, image.GetSpacing(), image.GetOrigin(), image.GetDirection()

@st.cache_data(show_spinner="Loading midplane figure...")
def _create_midplane_figure(mid_slice: np.ndarray):
    fig = go.Figure(go.Heatmap(z=mid_slice, colorscale="Gray"))
    fig.update_layout(height=500, margin=dict(l=0, r=0, t=20, b=0))
    fig.update_yaxes(autorange="reversed")
    return fig


@st.cache_data(show_spinner="Loading histogram...")
def _load_histogram(_array: np.ndarray, mhd_path: str, bins: int = 256):
    hist, bin_edges = np.histogram(_array.ravel(), bins=bins)
    return hist, bin_edges


# ----- exporters (same pattern as the "Export" section of 1_Generate_TPMS.py) -----
# Each exporter writes one file and returns (status, message), where status is
# the Streamlit function used to report it: "success", "warning" or "error".
# Plain functions keep the buttons one-liners and let "Export all" call them all.

def _export_processed_volume(processed, spacing, origin, direction, name):
    out_path = get_output_dir() / f"{name}_processed.mhd"
    out_image = sitk.GetImageFromArray(processed)
    out_image.SetSpacing(spacing)
    out_image.SetOrigin(origin)
    out_image.SetDirection(direction)
    sitk.WriteImage(out_image, str(out_path))
    return "success", f"Saved {out_path}"


def _export_stl(mesh, name):
    if mesh is None:
        return "warning", "No mesh to export - click 'Generate mesh' first."
    verts, faces = mesh
    out_path = get_output_dir() / name
    mesh_tools.export_as_STL(verts, faces, str(out_path) + ".stl")
    viz.save_mesh_as_html(faces, verts, str(out_path), show_normal_colorscale=True)  # keep an .html alongside the .stl, picked up by the Library page
    return "success", f"Saved {out_path}.stl (+ preview .html)"



# ==================================================
# ============ convert images to mhd ===============
# ==================================================
# ------ toggle title ------
col_check, col_title = st.columns([1, 100], vertical_alignment="bottom")
with col_check:
    Convert_to_mhd = st.checkbox(".", value=False)
with col_title:
    st.subheader("Convert slices to a .mhd volume")

if Convert_to_mhd:
    input_format = st.radio("Input format", ["JPG", "DICOM", "TIFF"], horizontal=True)
    # ------ define path to mhd ------
    st.session_state.setdefault("ct_input_path", "")
    col_path, col_browse = st.columns([5, 1.5], vertical_alignment="bottom")
    with col_path:
        input_path = st.text_input(
            "Input folder (or glob pattern, e.g. 'data/*.jpg')",
            key="ct_input_path",
        )
    with col_browse:
        st.write("")  # spacer so the button lines up with the text box, not its label
        browse_directory("ct_input_path", title=f"Select {input_format} folder")
    
    memory_saver = st.checkbox(
        "Downscale to 8-bit (memory saver)", value=True,
        help="Normalizes and converts pixel values to uint8 to save memory. "
             "Uncheck to keep the original bit depth.",
    )

    # ------ define pixel spacing ------
    spacing = None
    if input_format in ("JPG", "TIFF"):
        st.caption("Voxel spacing (mm) - JPG/TIFF files have no embedded spacing metadata.")
        s1, s2, s3 = st.columns(3)
        sx = s1.number_input("Spacing X", value=0.2, min_value=0.0001, format="%.4f")
        sy = s2.number_input("Spacing Y", value=0.2, min_value=0.0001, format="%.4f")
        sz = s3.number_input("Spacing Z", value=0.2, min_value=0.0001, format="%.4f")
        spacing = (sx, sy, sz)
    else:
        st.caption("DICOM voxel spacing is read automatically from the file metadata.")
    
    # ------ convert ------
    out_name = st.text_input("Output name (no extension)", value="ct_volume")
    if st.button("Convert to MHD") and input_path:
        with st.spinner(f"Converting {input_format}..."):
            out_path = get_output_dir() / out_name
            if input_format == "JPG":
                CT_scans.convert_jpg_to_mhd(input_path, str(out_path), spacing=spacing, memory_saver=memory_saver)
            elif input_format == "TIFF":
                CT_scans.convert_tiff_to_mhd(input_path, str(out_path), spacing=spacing, memory_saver=memory_saver)
            else:  # DICOM
                CT_scans.convert_dicomm_to_mhd(input_path, str(out_path), memory_saver=memory_saver)
        st.success(f"Saved {out_path}.mhd")

st.divider()

# ===========================================
# ======== select mhd to work on ============
# ===========================================
st.subheader("Preview a .mhd volume (static mid-slice)")
browse_file(
    "ct_mhd_path",
    title="Select an MHD file",
    filetypes=[("MHD files", "*.mhd"), ("All files", "*.*")],
)
mhd_path = st.session_state["ct_mhd_path"]


# ===========================================
# ============== preview mhd ================
# ===========================================
if mhd_path:
    if not Path(mhd_path).exists():
        st.error("File not found.")
    else:
        # ------ load mhd file ------
        array, spacing, origin, direction = _load_mhd(mhd_path)
        # ------ get mid-plane image ------
        st.write(f"Volume shape: {array.shape} (Z, Y, X)")
        sx, sy, _sz = spacing  # (x, y, z) mm/voxel
        mid_plane = array[array.shape[0] // 2]
        fig = _create_midplane_figure(mid_plane)
        fig.update_layout(height=500, margin=dict(l=0, r=0, t=20, b=0))
        fig.update_yaxes(scaleanchor="x", scaleratio=sy / sx)
        fig.update_xaxes(constrain="domain")
        st.plotly_chart(fig, width="stretch")

        # ------opening full viewer ------
        st.caption(
            "For interactive scrubbing, curvature coloring, and "
            "click-to-inspect greyvalues, use the full desktop viewer:"
        )
        lightweight = render_lightweight_toggle("ct_main_viewer")
        if st.button("Open interactive CT viewer (separate window)"):
            launch_ct_viewer(mhd_path, lightweight)
        
        st.divider()

        # ===========================================
        # ============== histogram  =================
        # ===========================================
        st.subheader("Histogram of greyvalues")
        if make_histogram := st.checkbox("Show greyvalue histogram"):
            bin_amount = st.slider("Number of bins", min_value=10, max_value=1024, value=256, step=10)
            hist, bin_edges = _load_histogram(array, mhd_path=mhd_path, bins=bin_amount)
            CT_histogram(hist, bin_edges)

        st.divider()

        # ===========================================================
        # === processing pipeline (build / export / mesh) - boxed  ===
        # ===========================================================
        with st.container(border=True):
            processed = render_ct_pipeline(array, key="ct_pipeline", spacing=spacing, volume_path=mhd_path)    #Renders the full pipeline builder (add step / reorder / remove / run) for a loaded CT volume, plus a 2D slice preview of the final result.

        # ============================================
        # ============= generate mesh ================
        # ============================================
        with st.container(border=True):
            if processed is not None:
                #
                st.subheader("Generate 3D mesh")
                mesh_spacing = spacing[::-1]
                st.caption(
                    f"Voxel spacing (dz, dy, dx) = "
                    f"({mesh_spacing[0]:.4g}, {mesh_spacing[1]:.4g}, {mesh_spacing[2]:.4g}) mm/voxel - "
                    "used directly by marching cubes, so anisotropic voxels aren't stretched or squashed."
                )

                st.session_state.setdefault("ct_mesh", None)
                lo, hi = float(processed.min()), float(processed.max())
                m1, m2 = st.columns(2)
                iso_level = m1.number_input(
                    "Iso level", value=(lo + hi) / 2.0, key="ct_mesh_iso_level",
                    help="Marching-cubes threshold - the surface is extracted where "
                         "the mask crosses this value (roughly the midpoint for a "
                         "0/255 binary mask).",
                )
                mc_step_size = m2.number_input(
                    "Step size", value=10, min_value=1, step=1, key="ct_mesh_step",
                    help="Marching-cubes step size - higher is faster but coarser.",
                )

                # ----- mesh parameters (same controls as 1_Generate_TPMS.py) ------
                st.divider()
                col_smoothing, col_simplification = st.columns(2)
                # smoothing
                with col_smoothing:
                    col_auto_smooth, col_smoothing_passes = st.columns([1, 4])
                    with col_auto_smooth:
                        auto_smooth = st.toggle(
                            "Auto-smooth mesh", value=True, key="ct_mesh_auto_smooth",
                            help="On: the number of smoothing passes is chosen automatically.")
                    with col_smoothing_passes:
                        number_of_smoothing_passes = st.slider(
                            "smoothing passes", min_value=1, max_value=100, value=10, step=1,
                            key="ct_mesh_number_of_smoothing_passes",
                            disabled=auto_smooth)
                    smoothing_factor = st.slider(
                        "Smoothing factor", 0.0, 1.0, 0.9, step=0.01,
                        key="ct_mesh_smoothing_factor",
                        help=("Removes the small, voxel-sized roughness left by meshing, "
                            "without shrinking the part.\n\n"
                            "- **0**: no smoothing.\n"
                            "- **0.25**: light, removes only the finest grain (2-3 voxels wide).\n"
                            "- **0.5**: medium, also softens bumps about 4 voxels wide.\n"
                            "- **1**: strongest, also rounds off details about 4-6 voxels wide.\n\n"
                            "Shapes wider than about 14 voxels (walls, pores, overall size) "
                            "are never changed, whatever the value. "
                            "If thin or sharp details look washed out, lower the value."),
                    )
                    # live chart: which feature widths this smoothing factor removes / keeps
                    render_smoothing_preview(smoothing_factor,
                                            number_of_passes=number_of_smoothing_passes,
                                            key="ct_mesh_smoothing_preview")
                with col_simplification:
                    # simplification
                    simplification_factor = st.slider(
                        "Mesh simplification (fraction of faces kept)", 0.1, 1.0, 0.9,
                        key="ct_mesh_simplification_factor",
                        help="Passed to mesh_tools.simplify_mesh(target=...).")
                    max_faces = st.checkbox(
                        "Limit maximum faces", value=False, key="ct_mesh_max_faces",
                        help="If checked, the mesh is simplified to a maximum number of faces.")
                    max_faces_count = 100000
                    if max_faces:
                        max_faces_count = st.number_input(
                            "Maximum faces", value=100000, min_value=1, key="ct_mesh_max_faces_count",
                            help="If 'Limit maximum faces' is checked, the mesh is simplified to this many faces.")

                if st.button("Generate mesh", key="ct_mesh_btn", type="primary"):
                    try:
                        with st.spinner("Extracting isosurface mesh..."):
                            a0 = np.arange(processed.shape[0]) * mesh_spacing[0]
                            a1 = np.arange(processed.shape[1]) * mesh_spacing[1]
                            a2 = np.arange(processed.shape[2]) * mesh_spacing[2]
                            verts, faces = mesh_tools.mesh_from_matrix(
                                processed.astype(float), float(iso_level), int(mc_step_size), a0, a1, a2,
                            )
                            number_of_raw_faces = len(faces)
                        # smoothing (same calls as TPMSModel.smooth_mesh)
                        with st.spinner("Smoothing mesh..."):
                            if auto_smooth:
                                verts, faces = mesh_tools.auto_smooth_mesh(
                                    verts=verts, faces=faces,
                                    smoothing_factor=smoothing_factor,
                                    max_iterations=100)
                            else:
                                verts, faces = mesh_tools.smooth_mesh(
                                    verts=verts, faces=faces,
                                    smoothing_factor=smoothing_factor,
                                    iterations=number_of_smoothing_passes)
                        # simplification: a value <= 1 is a fraction of faces kept,
                        # a value > 1 is an absolute face count (see mesh_tools.simplify_mesh)
                        target_faces = max_faces_count if max_faces else simplification_factor
                        if max_faces or simplification_factor != 1.0:
                            with st.spinner("Simplifying mesh..."):
                                verts, faces = mesh_tools.simplify_mesh(verts, faces, target=target_faces)
                        st.session_state["ct_mesh"] = (verts, faces)
                        st.success(f"Mesh generated: {number_of_raw_faces} faces from marching cubes, "
                                   f"{len(faces)} faces after smoothing and simplification.")
                    except Exception as e:
                        st.session_state["ct_mesh"] = None
                        st.error(f"Mesh generation failed: {e}")

                mesh = st.session_state["ct_mesh"]
                if mesh is not None:
                    verts, faces = mesh
                    st.markdown("**3D mesh preview**")
                    render_mesh_preview(faces, verts, key="ct_mesh")

                # ===========================================
                # ================= export ==================
                # ===========================================
                st.divider()
                st.subheader("Export")
                with st.container(border=True):
                    name = st.text_input("File name", value="ct_volume", key="ct_export_file_name",
                                         help=f"Files are written to {get_output_dir()}")
                    # bind each exporter to its data, so every exporter is then called as exporter(name)
                    export_processed_volume = partial(_export_processed_volume, processed, spacing, origin, direction)
                    export_stl = partial(_export_stl, mesh)

                    col_volume, col_stl, col_all = st.columns(3)
                    exporters = []  # what the clicked button asks for (at most one button is clicked per rerun)
                    if col_volume.button("Processed volume (.mhd)", icon=":material/view_in_ar:",
                                         width="stretch", key="ct_export_volume_btn"):
                        exporters = [export_processed_volume]
                    if col_stl.button("STL mesh", icon=":material/deployed_code:", width="stretch",
                                      key="ct_export_stl_btn", disabled=mesh is None,
                                      help=None if mesh is not None else "Click 'Generate mesh' first."):
                        exporters = [export_stl]
                    if col_all.button("Export all", type="primary", icon=":material/download:",
                                      width="stretch", key="ct_export_all_btn"):
                        exporters = [export_processed_volume, export_stl]
                    for exporter in exporters:
                        status, message = exporter(name)
                        getattr(st, status)(message)  # e.g. st.success(message)

# ===========================================
# ===== keep the selected files (see top) ===
# ===========================================
# At the very end of the script, so it copies the paths as they are after this run.
for kept_prefix in CT_KEPT_PATH_PREFIXES:
    mirror_widget_state(kept_prefix)
