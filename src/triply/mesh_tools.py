# triply: design, meshing, simulation and CT analysis of TPMS structures
# Copyright (C) 2026, Empa, Laboratory for High Performance Ceramics (201), Corentin Foucher
# SPDX-License-Identifier: MIT

"""
============================================================================
MESH_TOOLS
Operations on triangle surface meshes (verts, faces): marching cubes,
voxelization, simplification, smoothing, repair, checks, export.
============================================================================

#=====================================================================================================================
0 - (reserved)
1 - keep_largest_connected_component
2 - simplify_mesh
3 - calculate_triangle_areas
4 - export_as_STL
5 - mesh_from_matrix
6 - check_mesh_validity
7 - fix_mesh                       (helper _is_mesh_fixed)
8 - smooth_mesh                    (helper _taubin_coefficients_from_strength)
9 - matrix_from_mesh
10 - _uniform_laplacian_roughness  (roughness metric used by auto_smooth_mesh)
11 - auto_smooth_mesh
12 - rotate_STL
#=====================================================================================================================
"""

import numpy as np
from collections import defaultdict
import trimesh # type: ignore
from .logger import logger # type: ignore
from stl import mesh as stl_mesh # type: ignore
from skimage import measure # type: ignore
#import pymeshfix # type: ignore4
#import pyvista as pv # type: ignore



# =====================================================================
# 1) keep_largest_connected_component
# =====================================================================
def keep_largest_connected_component(verts: np.ndarray, faces: np.ndarray):
    """
    ============================================================================
    1) KEEP_LARGEST_CONNECTED_COMPONENT
    Extracts and returns only the largest connected component in a triangular mesh.
    ============================================================================

    PARAMETERS
    ----------
    verts : (N, 3) ndarray
        Vertex coordinates.
    faces : (M, 3) ndarray
        Triangular face indices.

    RETURNS
    -------
    largest_vertices : (K, 3) ndarray
        Vertices belonging to the largest connected region.
    largest_faces : (L, 3) ndarray
        Faces belonging to the largest connected region.

    EXAMPLE
    -------
    >>> v2, f2 = keep_largest_connected_component(vertices, faces)
    >>> print(v2.shape, f2.shape)
    """
    logger.info("Extracting largest connected component…")

    # ------------------------------------------------------------------
    # Validate inputs
    # ------------------------------------------------------------------
    if verts is None or faces is None:
        logger.error("Input verts or faces is None.")
        raise TypeError("verts and faces must not be None.")

    if len(faces) == 0:
        logger.warning("Mesh has zero faces — nothing to extract.")
        raise ValueError("Mesh has zero faces.")


    logger.debug(f"Input mesh: {len(verts)} vertices, {len(faces)} faces")

    # ------------------------------------------------------------------
    # find largest component
    # ------------------------------------------------------------------
    try:
        mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
        components = mesh.split(only_watertight=False)
    except Exception as e:
        logger.error(f"Failed to split mesh into components: {e}", exc_info=True)
        raise RuntimeError("Failed to split mesh into components.") from e   #from e preserves the original tracebackfrom trimesh

    if len(components) == 0:
        logger.warning("No connected components found in mesh.")
        raise RuntimeError("No connected components found in mesh.")

    # ------------------------------------------------------------------
    # result
    # ------------------------------------------------------------------
    largest = max(components, key=lambda m: len(m.faces))
    logger.info(
        f"Selected largest component: {len(largest.vertices)} vertices, "
        f"{len(largest.faces)} faces"
    )

    return largest.vertices, largest.faces



# =====================================================================
# 2) simplify_mesh
# =====================================================================
def simplify_mesh(verts: np.ndarray, faces: np.ndarray, target: float = 100000, mode: str = "pyvista"):
    """
    ============================================================================
    2) SIMPLIFY_MESH
    Reduces the number of faces of a mesh to a target, with one of three
    backends: PyVista decimate_pro (default, one call), trimesh vertex
    clustering or Open3D quadric decimation (both halve the face count per
    step until the target is reached).
    ============================================================================

    PARAMETERS
    ----------
    verts : (N, 3) ndarray
        Vertex coordinates.
    faces : (M, 3) ndarray
        Triangular faces.
    target : float, optional
        If target <= 1.0: fraction of faces to keep (e.g. 0.5 keeps 50%,
        1.0 keeps all). If target > 1.0: number of faces to keep
        (default = 100000).
    mode : str, optional
        "pyvista" (default): PyVista decimate_pro with reduction
            (M - target_faces) / M; the final face count is approximate.
        "trimesh": trimesh vertex clustering, halving the face count per
            step. If a step fails, the error is logged and the mesh reached
            so far is returned.
        "open3d": Open3D quadric decimation, halving the face count per
            step. If a step fails, RuntimeError is raised.

    RETURNS
    -------
    verts_simplified : (S, 3) ndarray
        Simplified vertices.
    faces_simplified : (T, 3) ndarray
        Simplified faces.

    RAISES
    ------
    TypeError
        If verts or faces is None, or if the mesh has zero faces.
    ValueError
        If mode is not "pyvista", "trimesh" or "open3d".
    RuntimeError
        If an Open3D simplification step fails (mode="open3d").

    EXAMPLE
    -------
    >>> v2, f2 = simplify_mesh(verts, faces, target=50000)
    >>> print(len(f2))
    """
    if verts is None or faces is None:
        logger.error("simplify_mesh(): verts or faces is None.")
        raise TypeError("verts and faces must not be None.")

    original = len(faces)
    current = original

    if target <= 1.0:
        n_faces_target = int(original * target)
    elif target > 1.0:
        n_faces_target = int(target)

    logger.info(f"Simplifying mesh: {original} faces → target {n_faces_target}")

    if original == 0:
        logger.warning("Mesh has zero faces — skipping simplification.")
        raise TypeError("Mesh has zero faces.")
    
    # -------- pyvista mode ---------------
    if mode == "pyvista":
        import pyvista as pv # type: ignore
        """
        PyVista (VTK wrapper) - FASTer than trimesh and easier API than raw VTK
        """
        faces_pv = np.hstack([[3] + list(f) for f in faces])
        mesh = pv.PolyData(verts, faces_pv)
        
        # Decimate
        mesh_decimated = mesh.decimate_pro((original-n_faces_target)/original)

        logger.info(f"Mesh simplification complete → {len(mesh_decimated.faces) // 4} faces remain.")
        return np.array(mesh_decimated.points), np.array(mesh_decimated.faces.reshape(-1, 4)[:, 1:])

    # -------- trimesh mode (iterative halving) ---------------
    if mode == "trimesh":
        i = 0
        while current > n_faces_target:
            i += 1
            current = max(int(current * 0.5), n_faces_target)

            logger.debug(f"[Step {i}] Target face count: {current}")

            try:
                mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
                # estimate cell_size to reach roughly `current` faces
                ratio = (current / max(len(mesh.faces), 1)) ** 0.5
                cell_size = float(mesh.bounding_box.extents.max()) * ratio
                mesh = mesh.simplify_vertex_clustering(cell_size=cell_size)
                verts = np.asarray(mesh.vertices)
                faces = np.asarray(mesh.faces)

            except Exception as e:
                logger.error(f"Mesh simplification failed at step {i}: {e}", exc_info=True)
                break

        logger.info(f"Mesh simplification complete → {len(faces)} faces remain.")
        return verts, faces

    # -------- open3d mode (iterative halving) ---------------
    elif mode == "open3d":
        i = 0
        while current > n_faces_target:
            i += 1
            current = max(int(current * 0.5), n_faces_target)

            logger.debug(f"[Step {i}] Target face count: {current}")

            try:
                import open3d as o3d
                o3d_mesh = o3d.geometry.TriangleMesh()
                o3d_mesh.vertices = o3d.utility.Vector3dVector(verts)
                o3d_mesh.triangles = o3d.utility.Vector3iVector(faces)
                o3d_mesh = o3d_mesh.simplify_quadric_decimation(target_number_of_triangles=current)
                verts = np.asarray(o3d_mesh.vertices)
                faces = np.asarray(o3d_mesh.triangles)

            except Exception as e:
                logger.error(f"Mesh simplification failed at step {i}: {e}", exc_info=True)
                raise RuntimeError("Failed to simplify mesh.") from e

        logger.info(f"Mesh simplification complete → {len(faces)} faces remain.")
        return verts, faces

    else:
        logger.error(f"Invalid simplification mode: {mode}. Returning original mesh.")
        raise ValueError("Invalid simplification mode.")

# =====================================================================
# 3) calculate_triangle_areas
# =====================================================================
def calculate_triangle_areas(verts: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """
    ============================================================================
    3) CALCULATE_TRIANGLE_AREAS
    Computes area for every triangular face in a mesh.
    ============================================================================

    PARAMETERS
    ----------
    verts : (N, 3) ndarray
        Vertex positions.
    faces : (M, 3) ndarray
        Triangular connectivity.

    RETURNS
    -------
    areas : (M,) ndarray
        Area of each triangle.

    EXAMPLE
    -------
    >>> areas = triangle_areas(verts, faces)
    >>> print("Min area:", areas.min())
    """
    logger.info("Calculating triangle areas…")

    if verts is None or faces is None:
        logger.error("calculate_triangle_areas(): verts or faces is None.")
        raise TypeError("verts and faces must not be None.")

    if len(faces) == 0:
        logger.warning("calculate_triangle_areas(): no faces provided.")
        raise ValueError("Mesh has zero faces.")
    
    logger.debug(f"Computing areas for {len(faces)} faces.")

    try:
        V = verts.astype(np.float64, copy=False)
        v0 = V[faces[:, 0]]
        v1 = V[faces[:, 1]]
        v2 = V[faces[:, 2]]

        cross_prod = np.cross(v1 - v0, v2 - v0)
        areas = 0.5 * np.linalg.norm(cross_prod, axis=1)

        logger.info("Triangle area computation complete.")
        logger.debug(f"Area stats — min: {areas.min()}, max: {areas.max()}")

        return areas

    except Exception as e:
        logger.error(f"Error computing triangle areas: {e}", exc_info=True)
        raise RuntimeError("Failed to compute triangle areas.") from e



# =====================================================================
# 4) export_as_STL
# =====================================================================
def export_as_STL(verts: np.ndarray, faces: np.ndarray, path: str):
    """
    ============================================================================
    4) EXPORT_AS_STL
    Exports a triangle mesh defined by (verts, faces) to an STL file.
    ============================================================================

    PARAMETERS
    ----------
    verts : (N, 3) ndarray
        Vertex coordinates.
    faces : (M, 3) ndarray
        Triangle face connectivity.
    path : str
        Output STL file path.

    RETURNS
    -------
    None
    """
    logger.info(f"Exporting STL → {path}")

    v0 = verts[faces[:, 0]]
    v1 = verts[faces[:, 1]]
    v2 = verts[faces[:, 2]]

    # ------------------------------------------------------------------
    # Validate inputs
    # ------------------------------------------------------------------
    if verts is None or faces is None:
        logger.error("export_as_STL(): verts or faces is None.")
        raise TypeError("verts and faces must not be None.")

    if len(faces) == 0:
        logger.warning("export_as_STL(): No faces to export; STL will be empty.")
        raise ValueError("Mesh has zero faces.")

    # -------------------------
    # Build STL mesh (vectorized)
    # -------------------------
    try:
        stl_obj = stl_mesh.Mesh(np.zeros(faces.shape[0], dtype=stl_mesh.Mesh.dtype))
        stl_obj.vectors[:, 0, :] = v0
        stl_obj.vectors[:, 1, :] = v1
        stl_obj.vectors[:, 2, :] = v2
    except Exception as e:
        logger.error(f"STL mesh construction failed: {e}", exc_info=True)
        raise RuntimeError("Failed to construct STL mesh.") from e

    # ------------------------------------------------------------------
    # Save file
    # ------------------------------------------------------------------
    try:
        stl_obj.save(path)
        logger.info(f"STL successfully saved: {path}")
    except Exception as e:
        logger.error(f"Failed to save STL file '{path}': {e}", exc_info=True)
        raise RuntimeError(f"Failed to save STL file '{path}'.") from e





# =====================================================================
# 5) mesh_from_matrix
# =====================================================================
def mesh_from_matrix(
    matrix: np.ndarray,
    iso_level: float,
    algo_step_size: int,
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    pad_width: int = 5,
    pad_val: float = -1,
    ):
    """
    ============================================================================
    5) MESH_FROM_MATRIX
    Extracts an isosurface mesh (verts, faces) from a 3D scalar field using
    marching cubes (scikit-image, Lewiner method). The volume is first padded
    with a constant value so that surfaces touching the boundary get closed
    "caps". Vertices are returned in the physical coordinates of the
    un-padded grid.
    ============================================================================

    PARAMETERS
    ----------
    matrix : (nx, ny, nz) ndarray
        Scalar field values sampled on a regular grid. Converted to float.
    iso_level : float
        Isosurface level (marching cubes "level"). Must lie within the
        range of matrix values.
    algo_step_size : int
        Marching cubes step size (larger = faster, less detail), passed
        straight to skimage.measure.marching_cubes.
    x, y, z : (nx, ny, nz) ndarray, or 1D ndarray
        Coordinates of every voxel, as 3D grids indexed like matrix
        (np.meshgrid(..., indexing="ij")). 1D arrays of length nx, ny, nz
        are also accepted and converted to such grids (a warning is logged).
        Must be evenly spaced and increasing: the voxel spacing is taken as
        |x[1,0,0] - x[0,0,0]| (same for y, z) and the origin as
        (x[0,0,0], y[0,0,0], z[0,0,0]).
    pad_width : int, optional
        Number of voxel layers padded on each face of the volume
        (default = 5).
    pad_val : float, optional
        Constant value of the padding (default = -1). It must be on the
        empty side of iso_level for the caps to close: with the solid where
        matrix > iso_level (TPMS density fields), use a value below
        iso_level. None is not supported.

    RETURNS
    -------
    verts : (N, 3) ndarray
        Vertex coordinates in physical units, in the frame of x, y, z.
    faces : (M, 3) ndarray
        Triangle connectivity (indices into verts).

    RAISES
    ------
    ValueError
        If x, y, z are 1D but their lengths don't match matrix's shape.
    RuntimeError
        If padding, marching cubes (e.g. iso_level outside the data range)
        or the vertex translation fails.
    """
    logger.info("Extracting isosurface mesh from matrix.")

    #------------------------------------------------------------------
    # Validate inputs
    #------------------------------------------------------------------
    # officialy this function only accepts 3D matrices for x,y,z,
    # but I always forget, I this hidden feature allows to pass 1D arrays for x,y,z,
    # and it will convert them to 3D meshgrid automatically.
    if x.ndim != 3 or y.ndim != 3 or z.ndim != 3:
        if x.ndim == 1 and y.ndim == 1 and z.ndim == 1:
            if x.shape[0] == matrix.shape[0] and y.shape[0] == matrix.shape[1] and z.shape[0] == matrix.shape[2]:
                logger.warning("x, y, z are 1D arrays, but matching matrix dimensions. Converting to 3D meshgrid.")
                x, y, z = np.meshgrid(x, y, z, indexing='ij')
            else:
                logger.error("x, y, z must match the shape of matrix or be 1D arrays matching each dimension.")
                logger.debug(f"x.shape: {x.shape}, y.shape: {y.shape}, z.shape: {z.shape}, matrix.shape: {matrix.shape}")
                raise ValueError("x, y, z must match the shape of matrix or be 1D arrays matching each dimension.")
            
    # ------------------------------------------------------------------
    # Pad volume to help close boundary openings ("caps")
    # ------------------------------------------------------------------
    try:
        v_padded = np.pad(matrix.astype(float), pad_width=pad_width, mode="constant", constant_values=pad_val)
    except Exception as e:
        logger.error(f"np.pad failed: {e}", exc_info=True)
        raise RuntimeError("Failed to pad matrix.") from e

    # ------------------------------------------------------------------
    # Extract isosurface
    # ------------------------------------------------------------------
    spacing = (np.abs(x[1,0,0]-x[0,0,0]),
            np.abs(y[0,1,0]-y[0,0,0]),
            np.abs(z[0,0,1]-z[0,0,0]))

    x_origin = x[0,0,0]
    y_origin = y[0,0,0]
    z_origin = z[0,0,0]
    origin = (x_origin - pad_width * spacing[0], y_origin - pad_width * spacing[1], z_origin - pad_width * spacing[2])

    # ------------------------------------------------------------------
    # Marching cubes (scikit-image)
    # ------------------------------------------------------------------
    try:
        verts, faces, normals, values = measure.marching_cubes(
            v_padded,
            level=iso_level,
            spacing=spacing,
            step_size=int(algo_step_size),
            allow_degenerate=True,
            method='lewiner'
        )
    except Exception as e:
        logger.error(f"marching_cubes failed: {e}", exc_info=True)
        raise RuntimeError("Failed to extract isosurface mesh.") from e

    # ------------------------------------------------------------------
    # Translate vertices to the physical coordinate system of the unpadded grid
    # ------------------------------------------------------------------
    try:
        verts[:, 0] = verts[:,0] + origin[0]
        verts[:, 1] = verts[:,1] + origin[1]
        verts[:, 2] = verts[:,2] + origin[2]
    except Exception as e:
        logger.error(f"vertex translation failed: {e}", exc_info=True)
        raise RuntimeError("Failed to translate mesh vertices.") from e

    logger.info(f"Extracted mesh with {len(verts)} verts and {len(faces)} faces.")

    # ------------------------------------------------------------------
    # result
    # ------------------------------------------------------------------
    return verts, faces



# =====================================================================
# 6) check_mesh_validity
# =====================================================================
def check_mesh_validity(verts: np.ndarray, faces: np.ndarray) -> dict:
    """
    ============================================================================
    6) CHECK_MESH_VALIDITY
    Performs basic topological and geometric validity checks on a triangle mesh
    using trimesh.
    ============================================================================
    
    PARAMETERS
    ----------
    verts : (N, 3) ndarray
        Vertex coordinates.
    faces : (M, 3) ndarray
        Triangle face connectivity.

    RETURNS
    -------
    info : dict
        Dictionary with mesh validity indicators.
    """
    # ------------------------------------------------------------------
    # Build mesh
    # ------------------------------------------------------------------
    try:
        m = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    except Exception as e:
        logger.error(f"check_mesh_validity(): Mesh construction failed: {e}", exc_info=True)
        raise RuntimeError("Failed to construct mesh.") from e

    edge_counts = np.bincount(m.edges_unique_inverse)

    # ------------------------------------------------------------------
    # Collect validity metrics
    # ------------------------------------------------------------------
    info = {
        "watertight": m.is_watertight,
        "winding_consistent": m.is_winding_consistent,
        "is_volume": m.is_volume,
        "boundary_edges": int(np.sum(edge_counts == 1)),
        "nonmanifold_edges": int(np.sum(edge_counts > 2)),
        "self_intersecting": (
            m.is_self_intersecting
            if hasattr(m, "is_self_intersecting")
            else False  # not supported in this trimesh version
        ),
    }
    if m.is_volume and m.is_watertight and m.is_winding_consistent:
        logger.info(f"check_mesh_validity(): {info}")
    else:
        logger.warning(f"check_mesh_validity(): Mesh is not a valid volume. Details: {info}")
    return info


# =====================================================================
# 7) fix_mesh
# =====================================================================
def fix_mesh(verts: np.ndarray, faces: np.ndarray):
    """
    ============================================================================
    7) FIX_MESH
    Attempts to fix common mesh issues (non-manifold edges, inconsistent normals)
    ============================================================================
    
    PARAMETERS
    ----------
    verts : (N, 3) ndarray
        Vertex coordinates.
    faces : (M, 3) ndarray
        Triangle face connectivity.

    RETURNS
    -------
    verts : (N, 3) ndarray
        Smoothed vertex coordinates.
    faces : (M, 3) ndarray
        triangle face connectivity.
    """
    # build trimesh object without automatic processing
    m = trimesh.Trimesh(vertices=verts, faces=faces, process=False)

    logger.info("Attempting to fix with trimesh.")
    trimesh.repair.fix_normals(m)
    try:
        if hasattr(trimesh.repair, "fill_holes"):
            trimesh.repair.fill_holes(m)
    except Exception:
        pass

    verts = m.vertices
    faces = m.faces

    if _is_mesh_fixed(verts, faces):
        # mesh is already valid after normal fixing; return early
        logger.info("mesh is already valid after normal fixing.")
        return verts, faces

    # Finalize: report resulting mesh size and return the arrays
    logger.info(f"fix_mesh(): returning mesh with {len(faces)} faces and {len(verts)} verts")
    return verts, faces


def _is_mesh_fixed(verts: np.ndarray, faces: np.ndarray) -> bool:
    """
    ============================================================================
    _IS_MESH_FIXED
    Helper function to check if a mesh is valid (watertight, manifold, etc.).
    Used for internal testing purposes.
    ============================================================================

    PARAMETERS
    ----------
    verts : (N, 3) ndarray
        Vertex coordinates.
    faces : (M, 3) ndarray
        Triangle face connectivity.

    RETURNS
    -------
    is_fixed : bool
        True if the mesh is watertight, winding-consistent, free of
        non-manifold edges, and not self-intersecting.
    """
    info = check_mesh_validity(verts, faces)
    if info is None:
        return False
    return info["watertight"] and info["winding_consistent"] and info["nonmanifold_edges"] == 0 and not info["self_intersecting"]==0




# =====================================================================
# 8) smooth_mesh
# =====================================================================

def _taubin_coefficients_from_strength(strength: float,
                                      passband_frequency: float = 0.1,
                                      maximum_frequency: float = 2.0):
    """
    Map a smoothing strength in [0, 1] to Taubin's (lambda, mu).

    strength = fraction of the highest-frequency noise removed per iteration:
        f(maximum_frequency) = 1 - strength
    while the shape is preserved:
        f(passband_frequency) = 1
    with f(k) = (1 - lambda*k) * (1 - mu*k) the per-iteration gain of a mode of frequency k.
    strength = 1 gives Open3D's defaults (0.5, -0.526).
    """
    if not 0.0 <= strength <= 1.0:
        raise ValueError("strength must be between 0 and 1.")
    frequency_ratio = passband_frequency / maximum_frequency          # q
    # positive root of (1 - q) x^2 + strength*q*x - strength = 0, with x = lambda * maximum_frequency
    scaled_lambda = (-strength * frequency_ratio
                     + np.sqrt((strength * frequency_ratio) ** 2
                               + 4.0 * (1.0 - frequency_ratio) * strength)) / (2.0 * (1.0 - frequency_ratio))
    lambda_factor = scaled_lambda / maximum_frequency
    # passband condition 1/lambda + 1/mu = passband_frequency
    mu_factor = lambda_factor / (passband_frequency * lambda_factor - 1.0)
    return lambda_factor, mu_factor

def smooth_mesh(verts: np.ndarray, 
                faces: np.ndarray, 
                smoothing_factor:float=0.1, 
                iterations:int=1):
    """
    ============================================================================
    8) SMOOTH_MESH
    Performs Taubin smoothing on the mesh using Open3D's filter_smooth_taubin.
    Taubin smoothing is volume-preserving (avoids the mesh shrinkage of plain
    Laplacian smoothing) by alternating a positive and negative Laplacian step.
    ============================================================================
    
    PARAMETERS
    ----------
    verts : (N, 3) ndarray
        Vertex coordinates.
    faces : (M, 3) ndarray
        Triangle face connectivity.
    smoothing_factor : float, optional
        Smoothing strength s, between 0 and 1 (default = 0.1). It is the
        fraction of the highest-frequency noise removed per iteration
        (s = 0: no smoothing; s = 1: Open3D's default lambda = 0.5,
        mu = -0.526). It is not lambda itself: lambda and mu are both
        computed from s by _taubin_coefficients_from_strength, with the
        passband frequency 0.1 kept unchanged (shape preserved), so every
        value in [0, 1] stays stable and non-shrinking.
        Raises ValueError if s is outside [0, 1].
    iterations : int, optional
        Number of Taubin iterations (default = 1).

    RETURNS
    -------
    verts_smoothed : (N, 3) ndarray
        Smoothed vertex coordinates.
    faces : (M, 3) ndarray
        Unchanged triangle face connectivity.
    """
    lambda_factor, mu_factor = _taubin_coefficients_from_strength(strength = smoothing_factor,
                                      passband_frequency = 0.1,
                                      maximum_frequency = 2.0)
    import open3d as o3d
    o3d_mesh = o3d.geometry.TriangleMesh()
    o3d_mesh.vertices = o3d.utility.Vector3dVector(verts)
    o3d_mesh.triangles = o3d.utility.Vector3iVector(faces)
    o3d_mesh = o3d_mesh.filter_smooth_taubin(
        number_of_iterations=iterations,
        lambda_filter=lambda_factor,
        mu=mu_factor,
    )
    #https://graphics.stanford.edu/courses/cs468-01-fall/Papers/taubin-smoothing.pdf
    return np.asarray(o3d_mesh.vertices), np.asarray(o3d_mesh.triangles)


# =====================================================================
# 9) matrix_from_mesh
# =====================================================================
def matrix_from_mesh(verts: np.ndarray,
                     faces: np.ndarray,
                     resolution: int):
    """
    ============================================================================
    9) MATRIX_FROM_MESH
    Voxelizes a triangle mesh into a filled 3D binary matrix (the inverse of
    mesh_from_matrix's marching-cubes extraction).
    ============================================================================

    PARAMETERS
    ----------
    verts : (N, 3) ndarray
        Vertex coordinates.
    faces : (M, 3) ndarray
        Triangular face indices.
    resolution : int
        Number of voxels along the mesh's largest bounding-box dimension.
        Voxel pitch is derived from this and applied uniformly on all three
        axes (cubic voxels), so shorter dimensions get proportionally fewer
        voxels.

    RETURNS
    -------
    x, y, z : (nx,), (ny,), (nz,) ndarray
        Physical coordinates of each voxel along each axis, read back from
        the resulting VoxelGrid so they exactly match matrix.shape.
    matrix : (nx, ny, nz) ndarray (uint8)
        Filled (interior included, not just the surface shell) voxel grid:
        1 = solid, 0 = empty.

        uint8 rather than bool, deliberately. A bool grid serializes to JSON
        as true/false instead of 1.0/0.0, which Plotly.js will not colorize
        (see viz.twod_view_of_matrix), and it silently clips any downstream
        code that assigns labels above 1 - voxel_tools stores 2/3/4 for
        overhang/bridge/support and a bool grid collapses all of them to
        True. Keeping it numeric here saves every caller from widening it.

        NOTE for callers: because it is numeric, `coords[matrix]` is
        *integer* indexing along axis 0, not masking. Use
        `matrix.astype(bool)` when you want a mask.

    RAISES
    ------
    ValueError
        If resolution is not positive, or the mesh has zero extent in any
        dimension.

    NOTES
    -----

    EXAMPLE
    -------
    >>> x, y, z, matrix = matrix_from_mesh(verts, faces, resolution=64)
    >>> print(matrix.shape)
    """
    if resolution <= 0:
        logger.error("Resolution must be a positive number.")
        raise ValueError("Resolution must be a positive number.")

    max_coords = np.max(verts, axis=0)
    min_coords = np.min(verts, axis=0)
    spans = max_coords - min_coords
    if np.any(spans == 0):
        logger.error("Mesh has zero span in at least one dimension; cannot voxelize.")
        raise ValueError("Mesh has zero span in at least one dimension; cannot voxelize.")
    # the pitch is determined by the largest span divided by the resolution.
    largest_span = np.max(spans)
    pitch = largest_span / (resolution - 1)

    #using one pitch, keeps square voxels
    matrix = trimesh.voxel.creation.voxelize(trimesh.Trimesh(vertices=verts, faces=faces, process=False),
                                                             pitch=pitch,
                                                             method='subdivide').fill()

    # Read the grid geometry back from the VoxelGrid itself instead of
    # recomputing it from min_coords/max_coords: trimesh derives its own
    # origin/shape from the occupied-voxel bounding box (rounded vertex
    # positions), which can differ by a voxel from a naive np.arange over
    # the mesh's continuous bounds.
    origin = matrix.translation  # location of voxel [0, 0, 0]
    scale = matrix.scale         # per-axis voxel size (uniform, == pitch)
    shape = matrix.shape

    x = origin[0] + np.arange(shape[0]) * scale[0]
    y = origin[1] + np.arange(shape[1]) * scale[1]
    z = origin[2] + np.arange(shape[2]) * scale[2]

    return x, y, z, np.array(matrix.matrix).astype(np.uint8)


# =====================================================================
# 10) _uniform_laplacian_roughness (roughness metric used by auto_smooth_mesh)
# =====================================================================
def _uniform_laplacian_roughness(verts: np.ndarray, faces: np.ndarray) -> float:
    """
    ============================================================================
    10) _UNIFORM_LAPLACIAN_ROUGHNESS
    Scalar "how bumpy is this mesh" proxy used by auto_smooth_mesh to decide
    when smoothing has converged. 
    AI SLOPE
    ============================================================================

    Computes the uniform-weight Laplacian coordinate at every vertex:
        L(v_i) = v_i - mean(neighbors of v_i)
    and returns the mean of ||L(v_i)|| across all vertices. Lower = smoother
    (a perfectly planar/uniform neighborhood gives L(v_i) = 0).

    PARAMETERS
    ----------
    verts : (N, 3) ndarray
        Vertex coordinates.
    faces : (M, 3) ndarray
        Triangular face connectivity.

    RETURNS
    -------
    roughness : float
        Mean Laplacian-coordinate magnitude over all vertices.
    """
    import scipy.sparse as sp

    n = len(verts)
    edges = np.vstack([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges = np.vstack([edges, edges[:, ::-1]])  # symmetrize (undirected adjacency)

    rows, cols = edges[:, 0], edges[:, 1]
    data = np.ones(len(rows), dtype=np.float64)
    adjacency = sp.coo_matrix((data, (rows, cols)), shape=(n, n)).tocsr()

    degree = np.asarray(adjacency.sum(axis=1)).flatten()
    degree[degree == 0] = 1.0  # avoid div-by-zero for isolated vertices

    neighbor_mean = adjacency.dot(verts) / degree[:, None]
    laplacian = verts - neighbor_mean
    return float(np.mean(np.linalg.norm(laplacian, axis=1)))


# =====================================================================
# 11) auto_smooth_mesh
# =====================================================================
def auto_smooth_mesh(
    verts: np.ndarray,
    faces: np.ndarray,
    smoothing_factor: float = 0.9,
    batch_iterations: int = 2,
    max_iterations: int = 100,
    improvement_tol: float = 0.005,
    max_displacement: float = None):
    """
    ============================================================================
    11) AUTO_SMOOTH_MESH
    Runs smooth_mesh() (Taubin smoothing) in batches of batch_iterations
    iterations, and stops once the mesh roughness stops improving, instead of
    requiring a hand-picked `iterations` value.
    Roughness R = mean over vertices of ||v_i - mean(neighbours of v_i)||
    (see _uniform_laplacian_roughness). After each batch, the relative
    improvement (R_previous - R) / R_previous is checked.
    ============================================================================
    PARAMETERS
    ----------
    verts : (N, 3) ndarray
        Vertex coordinates.
    faces : (M, 3) ndarray
        Triangular face connectivity.
    smoothing_factor : float, optional
        Smoothing strength s, between 0 and 1 (default = 0.9), passed
        straight to smooth_mesh (see there for how lambda and mu are
        computed from it).
    batch_iterations : int, optional
        Number of Taubin iterations per batch, i.e. between two roughness
        checks (default = 2). Smaller -> finer-grained stopping decisions;
        larger -> fewer roughness evaluations.
    max_iterations : int, optional
        Maximum number of BATCHES (default = 100), so at most
        max_iterations * batch_iterations Taubin iterations in total.
    improvement_tol : float, optional
        Stop once the relative roughness improvement of a batch drops
        below this fraction (default = 0.005, i.e. < 0.5%).
    max_displacement : float, optional
        Upper limit on the mean distance between each vertex and its
        position in the input mesh. A batch that would exceed it is
        discarded and smoothing stops. Default = None (no limit).

    STOPPING CONDITIONS (checked after each batch, in this order)
    -------------------
    - mean displacement > max_displacement -> batch discarded, stop
    - roughness == 0                       -> batch kept, stop
    - roughness increased                  -> batch kept, stop
    - improvement < improvement_tol        -> batch kept, stop
    - max_iterations batches reached       -> stop (a warning is logged)

    RETURNS
    -------
    verts_smoothed : (N, 3) ndarray
        Smoothed vertex coordinates.
    faces : (M, 3) ndarray
        Triangle face connectivity (unchanged).

    RAISES
    ------
    TypeError
        If verts or faces is None.
    ValueError
        If faces is empty, or if batch_iterations <= 0.

    EXAMPLE
    -------
    >>> verts_smoothed, faces = auto_smooth_mesh(verts, faces, max_displacement=0.05)
    """
    #------------------------------------------------------------------
    # Validate inputs
    #------------------------------------------------------------------
    if verts is None or faces is None:
        logger.error("auto_smooth_mesh(): verts or faces is None.")
        raise TypeError("verts and faces must not be None.")

    if len(faces) == 0:
        logger.warning("auto_smooth_mesh(): mesh has zero faces — nothing to smooth.")
        raise ValueError("Mesh has zero faces.")

    if batch_iterations <= 0:
        logger.error("auto_smooth_mesh(): batch_iterations must be positive.")
        raise ValueError("batch_iterations must be a positive integer.")

    #------------------------------------------------------------------
    # Initialize state
    #------------------------------------------------------------------
    original_verts = np.asarray(verts, dtype=np.float64).copy()
    current_verts = original_verts
    current_faces = np.asarray(faces).copy()

    roughness_history = [_uniform_laplacian_roughness(current_verts, current_faces)]
    prev_roughness = roughness_history[0]

    logger.info(f"auto_smooth_mesh(): starting roughness = {prev_roughness:.6g}")

    total_iterations = 0

    #------------------------------------------------------------------
    # Main smoothing loop
    #------------------------------------------------------------------
    while total_iterations < max_iterations:
        total_iterations = total_iterations + 1
        candidate_verts, candidate_faces = smooth_mesh(
                current_verts, current_faces,
                smoothing_factor=smoothing_factor,
                iterations=batch_iterations)
        # ----- catch some errors -----
        if max_displacement is not None :
            mean_disp = float(np.mean(np.linalg.norm(candidate_verts - original_verts, axis=1)))
            if mean_disp > max_displacement:
                logger.info(f"auto_smooth_mesh(): stopping — mean displacement {mean_disp:.6g} > max_displacement={max_displacement:.6g}."                )
                break
        # ----- update current mesh -----
        current_verts, current_faces = candidate_verts, candidate_faces

        # ---- check roughness ------
        roughness = _uniform_laplacian_roughness(current_verts, current_faces)
        roughness_history.append(roughness)
        if roughness == 0:
            logger.info("auto_smooth_mesh(): mesh is perfectly smooth (roughness=0). Stopping.")
            break
        improvement = (prev_roughness - roughness) / prev_roughness
        logger.debug( f"auto_smooth_mesh(): iter {total_iterations} — roughness={roughness:.6g}, improvement={improvement:.4%}")
        prev_roughness = roughness

        if improvement < 0:
            logger.warning(f"auto_smooth_mesh(): roughness increased (improvement={improvement:.4%}). Stopping.")
            break
        elif improvement < improvement_tol :
            logger.info(f"auto_smooth_mesh(): converged after {total_iterations} iterations (improvement < {improvement_tol:.2%}).")
            break
    if total_iterations >= max_iterations:
        logger.warning(f"auto_smooth_mesh(): reached max_iterations={max_iterations} without converging.")

    return current_verts, current_faces



# =====================================================================
# 12) rotate_STL
# =====================================================================
def rotate_STL(verts: np.ndarray,
                rotation: np.ndarray,) :
    """
    ============================================================================
    12) ROTATE_STL
    Rotates the vertices of a mesh with a 3x3 rotation matrix, about the
    physical origin (0, 0, 0): each vertex v becomes R @ v. It rotates 
    the mesh like the reoriented voxel grid, but find_optimal_orientation
    rotates about the grid centre c while this function rotates about (0, 0, 0):
    to land in the frame of new_x/new_y/new_z, pass verts - c and use the result.
    ============================================================================

    PARAMETERS
    ----------
    verts : (N, 3) ndarray
        Vertex coordinates.
    rotation : (3, 3) array_like
        Rotation matrix R. Must be a proper rotation (det = +1): with
        det = -1 the mesh is mirrored and its normals point inward.
        Not checked.

    RETURNS
    -------
    verts_rotated : (N, 3) ndarray
        Rotated vertex coordinates. The faces are unchanged and not
        returned: keep using the original faces array.

    RAISES
    ------
    TypeError
        If verts is None.

    EXAMPLE
    -------
    >>> verts_rotated = rotate_STL(verts, rotation_matrix)
    """
    # ===== check inputs =====
    if verts is None:
        logger.error("rotate_STL(): verts is None.")
        raise TypeError("verts must not be None.")

    #===== compute position of verts after rotation =====
    rotation = np.asarray(rotation, dtype=float)
    verts_rot = verts @ rotation.T

    return verts_rot