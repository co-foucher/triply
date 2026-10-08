from typing import Optional

import numpy as np
import streamlit as st
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from triply import viz

# Display label -> build_mesh_figure() boolean flag name. Only one of the
# four flags is ever True at a time (mirrors build_mesh_figure's own
# "last one wins / normal is the fallback" behavior when it's called
# directly with more than one flag set).
_COLORSCALE_FLAGS = {
    "Normal (surface direction)": "show_normal_colorscale",
    "Flat": "show_flat_colorscale",
    "Random": "show_random_colorscale",
    "Curvature": "show_curvature_colorscale",
}


"""
#=====================================================================================================================
0 - (reserved)
1 - _build_mesh_figure
2 - render_mesh_preview
3 - _compute_mesh_info
4 - _render_mesh_info
#=====================================================================================================================
"""


# =====================================================================
# 1) _build_mesh_figure
# =====================================================================
@st.cache_data(show_spinner="Building mesh preview...", max_entries=8)
def _build_mesh_figure(_faces, verts, selected_flag: str):
    """
    ============================================================================
    1) _BUILD_MESH_FIGURE
    Pure, cacheable half of render_mesh_preview: builds the Mesh3d figure
    for one specific color mode. Deliberately free of any st.* calls -
    only the returned figure is memoized, no widget/UI side effect rides
    along with the cache (widgets aren't supported inside cache_data-
    decorated functions - see the write-up in project memory / chat
    history for why the original all-in-one version didn't actually work).
    ============================================================================

    PARAMETERS
    ----------
    faces, verts : ndarray
        Mesh data (as produced by TPMSModel.generate_mesh()).
    selected_flag : str
        One of _COLORSCALE_FLAGS's values (e.g. "show_normal_colorscale"),
        naming which build_mesh_figure() boolean flag to set True.

    RETURNS
    -------
    fig : plotly.graph_objects.Figure
        The Mesh3d figure for the selected color mode.

    NOTES
    -----
    max_entries=8 rather than 1 because a handful of distinct (mesh, colorscale) 
    combos shouldn't evict each other on every call.
    """
    flags = {flag: (flag == selected_flag) for flag in _COLORSCALE_FLAGS.values()}
    return viz.build_mesh_figure(_faces, verts, **flags)


# =====================================================================
# 2) render_mesh_preview
# =====================================================================
def render_mesh_preview(faces,
                        verts,
                        key: str,
                        height: int = 600,
                        show_info_toggle: bool = True,
                        length_unit: str = "mesh units") -> None:
    """
    ============================================================================
    2) RENDER_MESH_PREVIEW
    Embeds a mesh preview (Mesh3d figure + coloring selector) inside a
    Streamlit page.
    ============================================================================

    PARAMETERS
    ----------
    faces, verts : ndarray or None
        Mesh data (as produced by TPMSModel.generate_mesh()). If either is
        None, shows a placeholder instead.
    key : str
        Unique suffix for widget keys (avoids collisions between
        pages/reruns).
    height : int, optional
        Plotly figure height in pixels (default 600).
    show_info_toggle : bool, optional
        If True (default), a "Show mesh information" toggle is drawn under
        the figure. Turning it on computes and displays vertex/face counts,
        bounding-box size, surface area, volume, watertightness, etc. (see
        _compute_mesh_info). The toggle is off by default, so nothing is
        computed unless the user asks for it.
    length_unit : str, optional
        Label appended to lengths, areas and volumes (default "mesh units").
        Purely cosmetic: no conversion is done, the numbers are in whatever
        unit the vertex coordinates are in (pass "mm" when you know the
        mesh is in millimetres).

    RETURNS
    -------
    None
    """
    if faces is None or verts is None:
        st.info("Generate a mesh first to see a preview.")
        return

    label = st.selectbox(
        "Mesh coloring",
        list(_COLORSCALE_FLAGS.keys()),
        key=f"{key}_colorscale",
        help=(
            "Passed straight through to viz.build_mesh_figure(). Curvature "
            "coloring does a per-vertex neighborhood search and is "
            "noticeably slower on large/unsimplified meshes."
        ),
    )
    selected_flag = _COLORSCALE_FLAGS[label]

    fig = _build_mesh_figure(faces, verts, selected_flag)
    fig.update_layout(height=height)
    st.plotly_chart(fig, width="stretch", key=f"{key}_meshfig")

    if show_info_toggle:
        show_info = st.toggle(
            "Show mesh information",
            value=False,
            key=f"{key}_show_info",
            help=(
                "Vertex/face counts, bounding-box size, surface area, "
                "volume, watertightness, connected bodies, Euler "
                "characteristic and genus. Computed only while this is on."
            ),
        )
        if show_info:
            info = _compute_mesh_info(faces, verts)
            _render_mesh_info(info, key=key, length_unit=length_unit)


# =====================================================================
# 3) _compute_mesh_info
# =====================================================================
@st.cache_data(show_spinner="Computing mesh information...", max_entries=8)
def _compute_mesh_info(_faces, verts) -> dict:
    """
    ============================================================================
    3) _COMPUTE_MESH_INFO
    Pure, cacheable half of the "Show mesh information" toggle: computes
    geometric and topological quantities of a triangle mesh. No st.* calls
    (same split as _build_mesh_figure / render_mesh_preview).
    ============================================================================

    PARAMETERS
    ----------
    _faces : ndarray, shape (F, 3), int
        Triangle vertex indices. Leading underscore = not hashed by
        st.cache_data (same convention as _build_mesh_figure: the cache key
        is the vertex array only).
    verts : ndarray, shape (N, 3), float
        Vertex coordinates.

    RETURNS
    -------
    info : dict
        Plain Python ints/floats/bools (so st.cache_data can pickle it):
        counts, bounding box, area, volume, topology. See the code below
        for every key and the formula behind it.
    """
    faces = np.asarray(_faces, dtype=np.int64)  # Nx3 array of vertex indices (triangles)
    verts = np.asarray(verts, dtype=np.float64) # Mx3 array of vertex coordinates (x, y, z)

    # ------------------------------------------------------------------
    # Counts
    # ------------------------------------------------------------------
    number_of_vertices = int(verts.shape[0])
    number_of_faces = int(faces.shape[0])

    # Vertices actually used by at least one face. 
    referenced_vertex_ids = np.unique(faces)
    number_of_referenced_vertices = int(referenced_vertex_ids.size)

    # ------------------------------------------------------------------
    # Edges
    # ------------------------------------------------------------------
    # grab all 3 edges of each triangle.
    all_edges = np.concatenate([faces[:, [0, 1]],   # the first two vertices
                                faces[:, [1, 2]],   # the second and third vertices
                                faces[:, [2, 0]]],  # the third and first vertices
                                axis=0)     #axis=0 means concatenate vertically, so we get a (3F, 2) array of edges
    # sort each edge so that the smaller index comes first (makes it easier to find unique edges)
    all_edges = np.sort(all_edges, axis=1)  # here you sort on the second axis !
    # find unique edges and how many faces share each edge (faces_per_edge)
    unique_edges, faces_per_edge = np.unique(all_edges, axis=0, return_counts=True)

    number_of_edges = int(unique_edges.shape[0])
    number_of_boundary_edges = int(np.sum(faces_per_edge == 1))      # open border (hole)
    number_of_non_manifold_edges = int(np.sum(faces_per_edge > 2))   # >2 faces meet on one edge
    # Watertightness: every edge is shared by exactly 2 faces (no holes, no non-manifold edges)
    is_watertight = bool(number_of_faces > 0 and np.all(faces_per_edge == 2))   #np.all returns a bool, true if all edges are shared by exactly 2 faces, false otherwise

    # ------------------------------------------------------------------
    # Bounding box (axis-aligned)
    # ------------------------------------------------------------------
    surface_verts = verts[referenced_vertex_ids]
    bounding_box_min = surface_verts.min(axis=0)
    bounding_box_max = surface_verts.max(axis=0)
    bounding_box_size = bounding_box_max - bounding_box_min
    bounding_box_volume = float(np.prod(bounding_box_size))

    # ------------------------------------------------------------------
    # Surface area
    # ------------------------------------------------------------------
    v0 = verts[faces[:, 0]]
    v1 = verts[faces[:, 1]]
    v2 = verts[faces[:, 2]]
    cross_products = np.cross(v1 - v0, v2 - v0)
    surface_area = float(0.5 * np.linalg.norm(cross_products, axis=1).sum())

    # ------------------------------------------------------------------
    # Enclosed volume (divergence theorem)
    # Each triangle and the origin form a tetrahedron of signed volume
    #     V_t = 1/6 * v0 . (v1 x v2)
    # For a closed, consistently oriented surface the contributions outside
    # the solid cancel and  V = sum_t V_t  (independent of the origin).
    # ------------------------------------------------------------------
    if is_watertight:
        signed_volume = float(np.einsum("ij,ij->i", v0, np.cross(v1, v2)).sum() / 6.0)
        volume = abs(signed_volume)
        # Relative density (solid volume fraction of the bounding box):
        #     rho* = V / (L_x * L_y * L_z)
        relative_density = volume / bounding_box_volume if bounding_box_volume > 0 else None
    else:
        signed_volume = None
        volume = None
        relative_density = None

    return {
        "number_of_vertices": number_of_vertices,
        "number_of_referenced_vertices": number_of_referenced_vertices,
        "number_of_faces": number_of_faces,
        "number_of_edges": number_of_edges,
        "number_of_boundary_edges": number_of_boundary_edges,
        "number_of_non_manifold_edges": number_of_non_manifold_edges,
        "is_watertight": is_watertight,
        "bounding_box_min": [float(value) for value in bounding_box_min],
        "bounding_box_max": [float(value) for value in bounding_box_max],
        "bounding_box_size": [float(value) for value in bounding_box_size],
        "bounding_box_volume": bounding_box_volume,
        "surface_area": surface_area,
        "signed_volume": signed_volume,
        "volume": volume,
        "relative_density": relative_density,
    }


# =====================================================================
# 4) _render_mesh_info
# =====================================================================
def _render_mesh_info(info: dict, 
                      key: str, 
                      length_unit: str = "mesh units") -> None:
    """
    ============================================================================
    4) _RENDER_MESH_INFO
    Thin, uncached UI half: displays the dict returned by
    _compute_mesh_info() as metrics + a downloadable table.
    ============================================================================

    PARAMETERS
    ----------
    info : dict
        Output of _compute_mesh_info().
    key : str
        Same key as render_mesh_preview (used for the download button key).
    length_unit : str, optional
        Unit label only, no conversion (see render_mesh_preview).

    RETURNS
    -------
    None
    """
    def format_optional(value, number_format: str = "{:.4g}") -> str:
        # Volume, density and genus are None for open meshes.
        return "n/a (not watertight)" if value is None else number_format.format(value)

    size_x, size_y, size_z = info["bounding_box_size"]

    # --- Counts ---------------------------------------------------------
    count_columns = st.columns(3)
    count_columns[0].metric("Vertices", f"{info['number_of_vertices']:,}")
    count_columns[1].metric("Faces", f"{info['number_of_faces']:,}")
    count_columns[2].metric("Edges", f"{info['number_of_edges']:,}")

    # --- Size -----------------------------------------------------------
    size_columns = st.columns(3)
    size_columns[0].metric(f"Size X [{length_unit}]", f"{size_x:.4g}")
    size_columns[1].metric(f"Size Y [{length_unit}]", f"{size_y:.4g}")
    size_columns[2].metric(f"Size Z [{length_unit}]", f"{size_z:.4g}")

    # --- Area / volume --------------------------------------------------
    measure_columns = st.columns(3)
    measure_columns[0].metric(f"Surface area [{length_unit}²]", f"{info['surface_area']:.4g}")
    measure_columns[1].metric(f"Volume [{length_unit}³]", format_optional(info["volume"]))
    measure_columns[2].metric(
        "Relative density",
        format_optional(info["relative_density"], "{:.2%}"),
        help="Solid volume / bounding-box volume (Lx·Ly·Lz).",
    )

    # --- Topology / health ----------------------------------------------
    if info["is_watertight"]:
        st.success(
            f"Watertight: every edge is shared by exactly 2 faces. "
        )
        if info["signed_volume"] is not None and info["signed_volume"] < 0:
            st.warning("Signed volume is negative: face normals point inwards (flipped orientation).")
    else:
        st.warning(
            f"Not watertight: {info['number_of_boundary_edges']:,} boundary edge(s) "
            f"(holes) and {info['number_of_non_manifold_edges']:,} non-manifold edge(s). "
            f"Volume, relative density and genus are not computed."
        )

    if info["number_of_referenced_vertices"] != info["number_of_vertices"]:
        unused = info["number_of_vertices"] - info["number_of_referenced_vertices"]
        st.caption(f"{unused:,} vertex/vertices are not used by any face (ignored for size and topology).")

    # --- Full table + download -----------------------------------------
    with st.expander("All values"):
        table_rows = []
        for name, value in info.items():
            # Lists (bounding box min/max/size) are shown as "x, y, z".
            if isinstance(value, list):
                value = ", ".join(f"{component:.6g}" for component in value)
            table_rows.append({"quantity": name, "value": str(value)})
        st.dataframe(table_rows, hide_index=True, width="stretch")

        csv_text = "quantity,value\n" + "\n".join(
            f"{row['quantity']},\"{row['value']}\"" for row in table_rows
        )
        st.download_button(
            "Download as CSV",
            data=csv_text,
            file_name="mesh_info.csv",
            mime="text/csv",
        )
