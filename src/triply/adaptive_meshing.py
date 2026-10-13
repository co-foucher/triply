import numpy as np
import trimesh  # type: ignore
from typing import Callable, Optional, Sequence, Tuple

from . import mesh_tools
from .logger import logger, set_log_level  # type: ignore


"""
#=====================================================================================================================
0 - (reserved)
1 - CORNER_OFFSETS, NEIGHBOR_OFFSETS (constants)
2 - Cells (class)
3 - create_cells
4 - refine_cells
5 - mesh_cells
#=====================================================================================================================

NOTE ON THIS MODULE
--------------------
Adaptive (refined near the surface) meshing of an implicit field, as developed
in notebooks/adaptive_resolution_multilevel_2.ipynb.

Everything is defined at CORNERS: the field is evaluated at the corners of the
grid, and a CELL is the cube between 8 neighbouring corners.

The field is given as a FUNCTION, field_function(x, y, z), that can be evaluated
at any set of points (arrays of any shape). Convention, as in the rest of triply:
    field > 0  : solid
    field < 0  : empty
    field = 0  : the surface
Fields that need the whole grid to be computed (e.g. the "distance" mode with a
distance transform, or fields imported from a .npy file) cannot be used here.

The cells of one refinement level are held by a Cells object. Three functions
make the whole pipeline:
    create_cells()  the coarse cells of a grid (x, y, z), and the field
    refine_cells()  repeats, at every level: compute the field at the corners
                    -> keep the cells crossing the surface and their likely
                    neighbours -> split the kept cells into 8 children
    mesh_cells()    marching cubes on every kept cell, pieces sewn together
The fine grid is never stored as a full 3D matrix: only the kept cells are.

The lattice is always closed at the faces of the box covered by the coarse
grid (Cells.box_size): refine_cells() applies the box at every level
(Cells.add_box), and a cell is kept if it crosses the surface before OR after
the box is applied (see refine_cells).

USE EXAMPLE
-----------
import numpy as np
import triply
from triply.utils import reload_all
reload_all()

axis = np.linspace(0, 100, 15)                         # the COARSE grid: 15 points per axis
x, y, z = np.meshgrid(axis, axis, axis, indexing="ij")
model = triply.tpms_gyroid.GyroidModel(x, y, z, 50.0, 50.0, 50.0, 0.2)

def field_function(x, y, z):
    return model.density_field_at(x, y, z, mode="band")

cells = triply.adaptive_meshing.create_cells(x, y, z, field_function)
triply.adaptive_meshing.refine_cells(cells, number_of_subdivisions=3)
verts, faces = triply.adaptive_meshing.mesh_cells(cells)

triply.viz.view_mesh(faces, verts)
"""


# =====================================================================
# 1) CORNER_OFFSETS, NEIGHBOR_OFFSETS
# =====================================================================
# The 8 corners of a cell, and the 8 children of a cell, as integer offsets 0 or 1 along each axis.
# Order: corner (a, b, c) is entry 4a + 2b + c, so 8 values reshape to a (2, 2, 2) block indexed [x, y, z].
CORNER_OFFSETS = np.array([[a, b, c] for a in (0, 1) for b in (0, 1) for c in (0, 1)])   # shape (8, 3)

# Steps from a cell location (i, j, k) to the locations of its neighbours
NEIGHBOR_OFFSETS = np.array([
    # 6 cells sharing a FACE: one step along one axis
    [1, 0, 0], [-1, 0, 0],
    [0, 1, 0], [0, -1, 0],
    [0, 0, 1], [0, 0, -1],
    # 12 cells sharing an EDGE: one step along two axes
    [1, 1, 0], [1, -1, 0], [-1, 1, 0], [-1, -1, 0],      # edges along z
    [1, 0, 1], [1, 0, -1], [-1, 0, 1], [-1, 0, -1],      # edges along y
    [0, 1, 1], [0, 1, -1], [0, -1, 1], [0, -1, -1],      # edges along x
])   # shape (18, 3)


# =====================================================================
# 2) Cells
# =====================================================================
class Cells:
    """
    ============================================================================
    2) CELLS
    All the cells of one refinement level.
    ============================================================================

    The field is calculated at points. A cell is a rectangular box gathering
    8 points at its corners.
    Row n of first_corners, indices, positions and values describes the same
    cell: n is its CELL NUMBER.
        first_corners (number of cells, 3)     location (i, j, k) of every cell
        indices       (number of cells, 8, 3)  integer indices of the 8 corners
        positions     (number of cells, 8, 3)  corner positions = origin + indices * resolution
        values        (number of cells, 8)     field at the corners (None until compute_values() is called)
        resolution    (3,)                     distance between two neighbouring points at this level
        origin        (3,)                     position of index (0, 0, 0), the same at every level
        box_size      (3,)                     size of the box covered by the grid given to __init__, the same at every level

    A cell's CELL LOCATION is (i, j, k), the indices of its first corner
    (entry 0 of CORNER_OFFSETS): its 8 corners are (i + a, j + b, k + c), a, b, c = 0 or 1.

    subdivide(), select() and add_box() change the object in place and return it.
    """
    # ---- Constants shared by every Cells object (see section 1) ----
    CORNER_OFFSETS = CORNER_OFFSETS             # (8, 3)
    NEIGHBOR_OFFSETS = NEIGHBOR_OFFSETS         # (18, 3)

    # =====================================================================
    # 2a) __init__
    # =====================================================================
    def __init__(self, x: np.ndarray, y: np.ndarray, z: np.ndarray):
        """
        Puts a regular grid of points into the form of cells. Computes no field and selects no cell.

        PARAMETERS
        ----------
        x, y, z : (number of points along x, number of points along y, number of points along z) ndarray
            Position of every grid point, indexed [i, j, k] (from np.meshgrid(..., indexing="ij")).

        Every group of 8 neighbouring points makes one cell, so there are
        (number of points along x - 1) * (number of points along y - 1) * (number of points along z - 1) cells.
        Corner (i, j, k) is at position origin + (i, j, k) * resolution, origin being the position of point [0, 0, 0].
        """
        # ---- 1) Store the inputs, as numpy arrays of a fixed type ----
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        z = np.asarray(z, dtype=float)

        # ---- 2) Validate inputs (before reading x[1, 0, 0] below, which needs them) ----
        if x.ndim != 3 or min(x.shape) < 2:
            raise ValueError(f"x must be a 3D matrix with at least 2 points along each axis, got shape {x.shape}")
        if y.shape != x.shape or z.shape != x.shape:
            raise ValueError(f"x, y and z must have the same shape, got {x.shape}, {y.shape}, {z.shape}")

        # ---- 3) Compute Resolution, origin and number of points along each axis ----
        self.resolution = np.array([x[1, 0, 0] - x[0, 0, 0],
                                    y[0, 1, 0] - y[0, 0, 0],
                                    z[0, 0, 1] - z[0, 0, 0]])                # (3,)
        # origin: position of point [0, 0, 0]
        self.origin = np.array([x[0, 0, 0], y[0, 0, 0], z[0, 0, 0]])         # (3,)
        number_of_points_x, number_of_points_y, number_of_points_z = x.shape
        # Size of the box covered by the grid, from its first to its last point (fixed: select / subdivide keep it)
        self.box_size = np.array([x[-1, 0, 0] - x[0, 0, 0],
                                  y[0, -1, 0] - y[0, 0, 0],
                                  z[0, 0, -1] - z[0, 0, 0]])                 # (3,)

        # ---- 4) Location (i, j, k) of every cell = its corner 0 ----
        # The last point along each axis starts no cell (it has no point at index + 1), hence the "- 1".
        # HENCE: number of cells = (number of points along x - 1) * (number of points along y - 1) * (number of points along z - 1)
        cell_i, cell_j, cell_k = np.meshgrid(np.arange(number_of_points_x - 1),
                                             np.arange(number_of_points_y - 1),
                                             np.arange(number_of_points_z - 1), indexing="ij")  # each (number of cells along x, along y, along z)
        # One row per cell, same order as [[i, j, k] for i in ... for j in ... for k in ...]
        self.first_corners = np.stack([cell_i.ravel(), cell_j.ravel(), cell_k.ravel()], axis=1)   # (number of cells, 3)

        # ---- 5) The 8 corners of every cell ----
        # (number of cells, 1, 3) + (1, 8, 3) -> (number of cells, 8, 3), see broadcasting
        self.indices = self.first_corners[:, np.newaxis, :] + Cells.CORNER_OFFSETS[np.newaxis, :, :]
        # Corner positions: (1, 1, 3) + (number of cells, 8, 3) * (1, 1, 3) -> (number of cells, 8, 3)
        self.positions = (self.origin[np.newaxis, np.newaxis, :]
                          + self.indices[:, :, :] * self.resolution[np.newaxis, np.newaxis, :])

        # ---- 6) No field yet: compute_values() fills it ----
        self.values = None                                                  # will be (number of cells, 8)
        # The field as a function of position, used by compute_values() when it is given none (set by create_cells)
        self.field_function = None

        # ---- 7) For every cell location (i, j, k), its cell number ----
        # this is a convenient dictionary of the cells
        self._build_cell_number_at_location()

    # =====================================================================
    # 2b) __len__
    # =====================================================================
    def __len__(self) -> int:
        """Number of cells: lets you write len(cells)."""
        return self.first_corners.shape[0]

    # =====================================================================
    # 2c) _build_cell_number_at_location
    # =====================================================================
    def _build_cell_number_at_location(self) -> None:
        """
        Builds the dictionary cell location (i, j, k) -> cell number (its row in first_corners).
        Must be called again every time first_corners changes (__init__, subdivide, select).
        (The leading "_" means: used inside the class only.)
        """
        self.cell_number_at_location = {}
        for cell_number in range(self.first_corners.shape[0]):
            cell_location = tuple(self.first_corners[cell_number, :])
            self.cell_number_at_location[cell_location] = cell_number

    # =====================================================================
    # 2d) compute_values
    # =====================================================================
    def compute_values(self, 
                       field_function: Optional[Callable] = None) -> "Cells":
        """
        Computes the field at the 8 corners of every cell and stores it in self.values (number of cells, 8).
        field_function(x, y, z): positions (any shape) -> field values (same shape).
        None (default): uses self.field_function, the one stored by create_cells.
        Returns self.
        """
        if field_function is None:      #  try in case the user already defined self.field_function
            field_function = self.field_function
        if field_function is None:      # if not defined, the user must give it now
            raise ValueError("No field: give field_function, or create the cells with create_cells(x, y, z, field_function).")

        self.values = field_function(self.positions[:, :, 0], self.positions[:, :, 1], self.positions[:, :, 2])
        return self

    # =====================================================================
    # 2e) crosses_surface
    # =====================================================================
    def crosses_surface(self) -> "Cells":
        """
        Fills the mask is_crossing_surface (number of cells,): True for the cells with
        some corners solid (value > 0) but not all. Returns self.
        """
        corner_is_solid = self.values[:, :] > 0                                            # (number of cells, 8)
        self.is_crossing_surface = corner_is_solid.any(axis=1) & ~corner_is_solid.all(axis=1)   # (number of cells,)
        return self

    # =====================================================================
    # 2f) face_neighbours_of
    # =====================================================================
    def face_neighbours_of(self, mask: np.ndarray) -> "Cells":
        """
        Fills the mask is_face_neighbour (number of cells,): True for the cells sharing a FACE
        or an EDGE (see NEIGHBOR_OFFSETS) with a cell where input mask is True. Returns self.
        Only cells of this collection can be found: a neighbour outside the grid,
        or not kept at this level, is skipped.
        """
        self.is_face_neighbour = np.zeros(self.first_corners.shape[0], dtype=bool)   # (number of cells,)
        for i, j, k in self.first_corners[mask, :]:                       # location of each cell where mask is True
            for step_i, step_j, step_k in Cells.NEIGHBOR_OFFSETS:
                neighbour_location = (i + step_i, j + step_j, k + step_k)
                if neighbour_location in self.cell_number_at_location:
                    self.is_face_neighbour[self.cell_number_at_location[neighbour_location]] = True
        return self

    # =====================================================================
    # 2g) remove_unlikely_neighbours
    # =====================================================================
    def remove_unlikely_neighbours(self, factor: float = 0.25) -> "Cells":
        """
        Removes from the mask is_face_neighbour the neighbours whose corners all stay far from 0
        (the surface): they probably do not contain it. Changes nothing else. Returns self.

        Per neighbour cell:
            closest_to_0 = smallest |corner value|                          (how close its corners get to the surface)
            spread       = largest corner value - smallest corner value     (how much the field varies across the cell)
        A neighbour is removed if closest_to_0 >= factor * (largest spread among the neighbours).
        """
        # No neighbour at all (e.g. no cell crosses the surface): nothing to remove,
        # and np.max below would fail on an empty array
        if not np.any(self.is_face_neighbour):
            return self

        # only the neighbour cells are looked at
        neighbour_values = self.values[self.is_face_neighbour, :]                                     # (number of neighbours, 8)

        # max difference between the corners of each cell
        spread = np.max(neighbour_values[:, :], axis=1) - np.min(neighbour_values[:, :], axis=1)      # (number of neighbours,)
        max_spread = np.max(spread)                                                                  # (scalar)
        # minimum absolute value of each cell
        closest_to_0 = np.min(np.abs(neighbour_values[:, :]), axis=1)                                 # (number of neighbours,)
        # compare to create the mask
        surface_may_reach = closest_to_0 < factor * max_spread                                       # (number of neighbours,)

        logger.debug(f"Unlikely neighbours: {np.sum(~surface_may_reach)} of {len(surface_may_reach)} removed.")

        # set to False the neighbours the surface probably does not reach
        neighbour_cell_numbers = np.where(self.is_face_neighbour)[0]                                  # (number of neighbours,)
        self.is_face_neighbour[neighbour_cell_numbers[~surface_may_reach]] = False
        return self

    # =====================================================================
    # 2h) select
    # =====================================================================
    def select(self, mask: np.ndarray) -> "Cells":
        """
        Keeps only the cells where mask is True, in place, and removes the others.
        mask : (number of cells,) True / False

        Every per-cell array is cut with the same mask, so row n still describes the same cell in all of them.
        The masks is_crossing_surface / is_face_neighbour are NOT cut: recompute them before using them again.
        Returns self.
        """
        # ---- 1) Check the mask ----
        # An integer array would not be read as True / False but as a list of cell numbers: refuse it
        mask = np.asarray(mask)
        number_of_cells = self.first_corners.shape[0]
        if mask.dtype != bool or mask.shape != (number_of_cells,):
            raise ValueError(f"mask must be a True / False array of shape ({number_of_cells},), "
                             f"got dtype {mask.dtype} and shape {mask.shape}")

        # ---- 2) Cut every per-cell array with the same mask ----
        # Nothing is recomputed: a kept cell keeps its corners, positions and values, only the rows of the others go.
        self.first_corners = self.first_corners[mask, :]          # (number of kept cells, 3)
        self.indices = self.indices[mask, :, :]                   # (number of kept cells, 8, 3)
        self.positions = self.positions[mask, :, :]               # (number of kept cells, 8, 3)
        if self.values is not None:
            self.values = self.values[mask, :]                    # (number of kept cells, 8)

        # ---- 3) Rebuild the dictionary: the cell numbers have changed ----
        self._build_cell_number_at_location()
        return self

    # =====================================================================
    # 2i) subdivide
    # =====================================================================
    def subdivide(self) -> "Cells":
        """
        Makes this Cells one level finer, in place: every cell is replaced by its 8 children, of half the size.
        Child first corners: (2i + a, 2j + b, 2k + c), a, b, c = 0 or 1. Their values are not computed yet.
        The origin does not change: index (0, 0, 0) stays at the same position at every level.
        Returns self.
        """
        # ---- 1) New cell locations and resolution ----
        # (number of cells, 1, 3) * 2 + (1, 8, 3) -> (number of cells, 8, 3), then one row per child
        self.first_corners = (2 * self.first_corners[:, np.newaxis, :]
                              + Cells.CORNER_OFFSETS[np.newaxis, :, :]).reshape(-1, 3)   # (number of cells * 8, 3)
        self.resolution = self.resolution / 2                                            # (3,)

        # ---- 2) Everything that depends on the cell locations is rebuilt (same lines as in __init__) ----
        # (number of cells, 1, 3) + (1, 8, 3) -> (number of cells, 8, 3), see broadcasting
        self.indices = self.first_corners[:, np.newaxis, :] + Cells.CORNER_OFFSETS[np.newaxis, :, :]
        # Corner positions: (1, 1, 3) + (number of cells, 8, 3) * (1, 1, 3) -> (number of cells, 8, 3)
        self.positions = (self.origin[np.newaxis, np.newaxis, :]
                          + self.indices[:, :, :] * self.resolution[np.newaxis, np.newaxis, :])

        # The values belonged to the parent cells: compute_values() must be called again
        self.values = None

        # For every cell location (i, j, k), its cell number
        self._build_cell_number_at_location()

        # ---- 3) The masks belonged to the parent cells (wrong length now): remove them ----
        # so that using one before crosses_surface() / face_neighbours_of() fails clearly instead of silently
        for mask_name in ("is_crossing_surface", "is_face_neighbour"):
            if hasattr(self, mask_name):
                delattr(self, mask_name)

        return self

    # =====================================================================
    # 2j) add_box
    # =====================================================================
    def add_box(self, box_margin: float = 1e-6) -> "Cells":
        """
        Closes the lattice at the box faces: every corner value becomes
        min(value, distance from the corner to the nearest box face - box_margin).
        Inside the box the distance is positive, so the lattice is unchanged away from the faces;
        on a face it is -box_margin, so the corner becomes just empty and a cap closes the lattice there.
        Updates self.values (number of cells, 8). Returns self.

        Call it right after compute_values(), at every level: compute_values() brings back the field without the box.

        The box is the one covered by the grid given to __init__: [origin, origin + box_size]
        along each axis (self.origin, self.box_size). For a grid starting at 0, that is [0, box_size].

        PARAMETERS
        ----------
        box_margin : float, optional
            Margin to the box faces (default 1e-6).
        """
        # Corner positions measured from the box start (= self.origin), each (number of cells, 8)
        x = self.positions[:, :, 0] - self.origin[0]
        y = self.positions[:, :, 1] - self.origin[1]
        z = self.positions[:, :, 2] - self.origin[2]

        # Distance (mm) to the nearest box face: positive inside the box, negative outside
        distance_x_face = np.minimum(x, self.box_size[0] - x)
        distance_y_face = np.minimum(y, self.box_size[1] - y)
        distance_z_face = np.minimum(z, self.box_size[2] - z)
        distance = np.minimum(distance_x_face, distance_y_face)
        distance = np.minimum(distance, distance_z_face) - box_margin       # (number of cells, 8)

        self.values = np.minimum(self.values[:, :], distance)
        return self


# =====================================================================
# 3) create_cells
# =====================================================================
def create_cells(x: np.ndarray,
                 y: np.ndarray,
                 z: np.ndarray,
                 field_function: Callable) -> Cells:
    """
    ============================================================================
    3) CREATE_CELLS
    Creates the coarse cells from a coarse grid of points (x, y, z) and the
    field, given as a function of position. The field function is stored, but
    not computed yet.
    ============================================================================

    PARAMETERS
    ----------
    x, y, z : np.ndarray
        The COARSE grid: 3D arrays of identical shape, position of every point,
        indexed [i, j, k] (from np.meshgrid(..., indexing="ij")). Its shape gives
        the number of points along each axis (cells = points - 1).
    field_function : callable
        field_function(x, y, z) -> values, same shape as x. Positive = solid.
        For a TPMS model: lambda x, y, z: model.density_field_at(x, y, z, mode, level).

    RETURNS
    -------
    cells : Cells
        The coarse cells, with cells.field_function set (values not computed yet).
    """
    cells = Cells(x=x, y=y, z=z)
    cells.field_function = field_function
    return cells


# =====================================================================
# 4) refine_cells
# =====================================================================
def refine_cells(cells: Cells,
                 number_of_subdivisions: int,
                 box_margin: float = 1e-6,
                 unlikely_neighbour_factor: float = 0.25) -> Cells:
    """
    ============================================================================
    4) REFINE_CELLS
    Runs the algorithm to refine the cells near the surface, in place, number_of_subdivisions
    times. At every level: compute the field at the corners -> keep the cells
    crossing the surface and their likely neighbours -> split the kept cells.
    The field is the one stored on the cells (cells.field_function, set by
    create_cells).
    ============================================================================

    PARAMETERS
    ----------
    cells : Cells
        The coarse cells, with their field_function (e.g. from create_cells). Changed in place.
    number_of_subdivisions : int
        How many times the kept cells are halved.
        Final resolution = coarse resolution / 2**number_of_subdivisions.
    box_margin : float, optional
        See Cells.add_box (default 1e-6).
    unlikely_neighbour_factor : float, optional
        See Cells.remove_unlikely_neighbours (default 0.25).

    RETURNS
    -------
    cells : Cells
        The same object, now holding the kept cells of the finest level, with
        their values (box included).

    NOTES
    -----
    A cell is kept if it crosses the surface of the lattice
    BEFORE the box is applied, or AFTER. The box sets the corners on its faces
    to empty: a thin wall that only touched those corners would otherwise no
    longer be seen, its cell would be dropped and the mesh would get holes.
    The test after the box finds the cells of the caps on the box faces.
    """
    for level in range(number_of_subdivisions + 1):
        # ---- 1) The field at the corners of the current cells, and the cells crossing it ----
        cells.compute_values()                                              # with cells.field_function
        cells.crosses_surface()
        crosses_the_lattice = cells.is_crossing_surface.copy()          # (number of cells,) before the box hides anything

        # ---- 2) The box: the crossing test is done again, and a cell crossing either field is kept ----
        cells.add_box(box_margin=box_margin)
        cells.crosses_surface()                                         # sees the caps on the box faces
        cells.is_crossing_surface = cells.is_crossing_surface | crosses_the_lattice

        # ---- 3) Which cells to keep: crossing, or a likely neighbour of a crossing cell ----
        cells.face_neighbours_of(cells.is_crossing_surface)
        cells.remove_unlikely_neighbours(unlikely_neighbour_factor)
        keep = cells.is_crossing_surface | cells.is_face_neighbour          # (number of cells,)

        logger.debug(f"Level {level}: resolution {cells.resolution.max():.4g}, "
                     f"{np.sum(keep)} of {len(keep)} cells kept.")
        cells.select(keep)

        # ---- 4) Finest level reached: stop, these are the cells to mesh ----
        if level == number_of_subdivisions:
            break

        # ---- 5) Make it finer there ----
        cells.subdivide()

    logger.info(f"Refinement done: {len(cells)} cells of resolution {cells.resolution.max():.4g} kept "
                f"({number_of_subdivisions} subdivisions).")
    return cells


# =====================================================================
# 5) mesh_cells
# =====================================================================
def mesh_cells(cells: Cells) -> Tuple[np.ndarray, np.ndarray]:
    """
    ============================================================================
    5) MESH_CELLS
    Runs marching cubes (mesh_tools.mesh_from_matrix) on every cell
    separately, then sews the pieces into one mesh by merging the vertices
    that neighbouring cells computed twice.
    ============================================================================

    PARAMETERS
    ----------
    cells : Cells
        Cells with their values computed (e.g. after refine_cells).
        The surface is where the field is 0.

    RETURNS
    -------
    verts : (number of vertices, 3) ndarray
        Vertex positions.
    faces : (number of faces, 3) ndarray
        Triangle vertex indices.
    """
    if cells.values is None:
        raise ValueError("cells.values is None: call compute_values() (or refine_cells()) before mesh_cells().")

    all_vertices = []
    all_faces = []
    number_of_vertices_so_far = 0
    number_of_cells_meshed = 0

    # mesh_from_matrix logs on every call: silence it during the loop
    set_log_level("CRITICAL")
    try:
        for cell_number in range(len(cells)):
            corner_positions = cells.positions[cell_number, :, :]   # (8, 3) positions of this cell's 8 corners, in the order of CORNER_OFFSETS
            corner_values = cells.values[cell_number, :]            # (8,)   field at those corners

            # No sign change at the corners: no surface in this cell (marching cubes would raise an error)
            if corner_values.min() > 0 or corner_values.max() < 0:
                continue

            # the cell's axis from the corner positions: corner (0, 0, 0) is entry 0, corner (1, 1, 1) is entry 7
            cell_x = np.array([corner_positions[0, 0], corner_positions[7, 0]])
            cell_y = np.array([corner_positions[0, 1], corner_positions[7, 1]])
            cell_z = np.array([corner_positions[0, 2], corner_positions[7, 2]])

            # The 8 values as a (2, 2, 2) block indexed [x, y, z]
            cell_block = corner_values.reshape(2, 2, 2)

            # pad_width=0: no caps around a single cell, otherwise the pieces could not be sewn together.
            # The vertices come back in physical coordinates (origin read from cell_x, cell_y, cell_z).
            try:
                vertices, faces = mesh_tools.mesh_from_matrix(
                    cell_block, iso_level=0.0, algo_step_size=1,
                    x=cell_x, y=cell_y, z=cell_z, pad_width=0)
            except RuntimeError:
                continue    # some corners exactly at 0 but no real crossing: nothing to mesh

            # Faces count this cell's vertices from 0: shift them to the global vertex list
            all_vertices.append(vertices)
            all_faces.append(faces + number_of_vertices_so_far)
            number_of_vertices_so_far += len(vertices)
            number_of_cells_meshed += 1
    finally:
        set_log_level("INFO")

    if not all_vertices:
        raise ValueError("No surface found in any cell: the field has no sign change.")

    # Sew the pieces: process=False keeps the duplicate vertices at creation, so the merge below is explicit
    refined_mesh = trimesh.Trimesh(vertices=np.vstack(all_vertices), faces=np.vstack(all_faces), process=False)
    number_of_vertices_before_merging = len(refined_mesh.vertices)
    refined_mesh.merge_vertices()
    refined_mesh.update_faces(refined_mesh.nondegenerate_faces())     # drop zero-area triangles

    logger.info(f"{number_of_cells_meshed} of {len(cells)} cells contain surface; "
                f"{number_of_vertices_before_merging} -> {len(refined_mesh.vertices)} vertices after merging, "
                f"{len(refined_mesh.faces)} faces.")
    return np.asarray(refined_mesh.vertices), np.asarray(refined_mesh.faces)
