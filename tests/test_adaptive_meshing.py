"""
Tests for triply.adaptive_meshing, and for TPMSModel.generate_mesh_adaptive(),
which runs it on a TPMS model (including custom thickness / threshold given
as functions of position with set_point_function()).
"""
import numpy as np
import pytest

#this is just like the import in triply.mesh_tools, but we do it here so that pytest can skip all tests in this module if triply isn't importable
adaptive_meshing = pytest.importorskip("triply.adaptive_meshing")
trimesh = pytest.importorskip("trimesh")
from skimage import measure  # noqa: E402
from triply.TPMS_classes.tpms_gyroid import GyroidModel  # noqa: E402

"""
============================================================================
0 - helpers (gyroid band field, grid, adaptive pipeline, uniform reference mesh)
1 - TestCellsInit
2 - TestCellsMethods
3 - TestRefineCells
4 - TestMeshCells
5 - TestFullPipeline
6 - TestTPMSModelAdaptive
============================================================================
"""

# ============================================================================
# 0 - helpers
# ============================================================================
PERIOD = 100.0
THICKNESS = 0.5
BOX_SIZE = 100.0
NUMBER_OF_POINTS = 15          # coarse grid: 15 points per axis -> 14 cells of 100 / 14 per axis
BOX_MARGIN = 1e-6              # default box_margin of refine_cells / Cells.add_box


def gyroid(x, y, z):
    """Gyroid implicit field, one period over the box."""
    w = 2 * np.pi / PERIOD
    return (np.sin(w * x) * np.cos(w * y) + np.sin(w * y) * np.cos(w * z)
            + np.sin(w * z) * np.cos(w * x))


def gyroid_band(x, y, z):
    """Gyroid in band mode: positive (solid) inside the wall."""
    return THICKNESS - np.abs(gyroid(x, y, z))


def coarse_grid(number_of_points=NUMBER_OF_POINTS, origin=(0.0, 0.0, 0.0)):
    """Regular grid of the box [origin, origin + BOX_SIZE] along each axis, indexing="ij"."""
    axis_x = origin[0] + np.linspace(0, BOX_SIZE, number_of_points)
    axis_y = origin[1] + np.linspace(0, BOX_SIZE, number_of_points)
    axis_z = origin[2] + np.linspace(0, BOX_SIZE, number_of_points)
    return np.meshgrid(axis_x, axis_y, axis_z, indexing="ij")


def distance_to_box(x, y, z, origin=(0.0, 0.0, 0.0)):
    """Distance to the nearest face of the box [origin, origin + BOX_SIZE]: positive inside, negative outside."""
    distance_x_face = np.minimum(x - origin[0], BOX_SIZE + origin[0] - x)
    distance_y_face = np.minimum(y - origin[1], BOX_SIZE + origin[1] - y)
    distance_z_face = np.minimum(z - origin[2], BOX_SIZE + origin[2] - z)
    return np.minimum(np.minimum(distance_x_face, distance_y_face), distance_z_face)


def run_pipeline(field_function, number_of_subdivisions, origin=(0.0, 0.0, 0.0)):
    """create_cells -> refine_cells -> mesh_cells on the coarse grid. Returns the mesh and the final cells."""
    x, y, z = coarse_grid(origin=origin)
    cells = adaptive_meshing.create_cells(x, y, z, field_function)
    adaptive_meshing.refine_cells(cells, number_of_subdivisions)
    verts, faces = adaptive_meshing.mesh_cells(cells)
    return trimesh.Trimesh(verts, faces, process=False), cells


def uniform_closed_mesh(field_function, number_of_points):
    """
    Reference: marching cubes on the FULL uniform fine grid, with the field closed by the
    box exactly as refine_cells does it (min(field, distance to box - BOX_MARGIN)),
    then merged and cleaned like mesh_cells.
    """
    x, y, z = coarse_grid(number_of_points)
    spacing = x[1, 0, 0] - x[0, 0, 0]
    values = np.minimum(field_function(x, y, z), distance_to_box(x, y, z) - BOX_MARGIN)
    verts, faces, _, _ = measure.marching_cubes(values, level=0.0, spacing=(spacing,) * 3,
                                                allow_degenerate=True, method="lewiner")
    mesh = trimesh.Trimesh(verts, faces, process=False)
    mesh.merge_vertices()
    mesh.update_faces(mesh.nondegenerate_faces())
    return mesh


# ============================================================================
# 1 - TestCellsInit
# ============================================================================
class TestCellsInit:
    """
    Tests for adaptive_meshing.Cells.__init__(): a grid of points put in the form of cells.
    """

    def test_geometry(self):
        """Origin, resolution, box size and number of cells, on a grid that does not start at 0."""
        x, y, z = coarse_grid(number_of_points=5, origin=(10.0, -20.0, 30.0))
        cells = adaptive_meshing.Cells(x, y, z)
        np.testing.assert_allclose(cells.origin, [10.0, -20.0, 30.0])
        np.testing.assert_allclose(cells.resolution, [25.0, 25.0, 25.0])      # 100 / (5 - 1)
        np.testing.assert_allclose(cells.box_size, [100.0, 100.0, 100.0])
        assert len(cells) == 4 * 4 * 4                                         # cells = points - 1 per axis
        assert cells.values is None                                            # no field computed yet

    def test_positions_are_origin_plus_indices_times_resolution(self):
        """Row n of indices and positions is the same cell; its corners are the grid points."""
        x, y, z = coarse_grid(number_of_points=5, origin=(10.0, -20.0, 30.0))
        cells = adaptive_meshing.Cells(x, y, z)
        expected_positions = (cells.origin[np.newaxis, np.newaxis, :]
                              + cells.indices[:, :, :] * cells.resolution[np.newaxis, np.newaxis, :])
        np.testing.assert_allclose(cells.positions, expected_positions)
        # corner (i, j, k) of a cell is the grid point [i, j, k]
        corner_i = cells.indices[:, :, 0]
        corner_j = cells.indices[:, :, 1]
        corner_k = cells.indices[:, :, 2]
        np.testing.assert_allclose(cells.positions[:, :, 0], x[corner_i, corner_j, corner_k])
        np.testing.assert_allclose(cells.positions[:, :, 1], y[corner_i, corner_j, corner_k])
        np.testing.assert_allclose(cells.positions[:, :, 2], z[corner_i, corner_j, corner_k])

    def test_rejects_non_3d_grid(self):
        """x must be a 3D matrix with at least 2 points per axis."""
        axis = np.linspace(0, 1, 4)
        with pytest.raises(ValueError):
            adaptive_meshing.Cells(axis, axis, axis)

    def test_rejects_mismatched_shapes(self):
        """x, y and z must have the same shape."""
        x, y, z = coarse_grid(number_of_points=4)
        with pytest.raises(ValueError):
            adaptive_meshing.Cells(x, y, z[:, :, :-1])


# ============================================================================
# 2 - TestCellsMethods
# ============================================================================
class TestCellsMethods:
    """
    Tests for the Cells methods used at every refinement level:
    compute_values, crosses_surface, face_neighbours_of, remove_unlikely_neighbours,
    select, subdivide, add_box.
    """

    def test_compute_values_without_field_raises(self):
        """Cells created directly (not by create_cells) have no field function."""
        cells = adaptive_meshing.Cells(*coarse_grid(number_of_points=3))
        with pytest.raises(ValueError):
            cells.compute_values()

    def test_compute_values_uses_stored_function(self):
        """create_cells stores the field; compute_values evaluates it at every corner."""
        x, y, z = coarse_grid(number_of_points=4)
        cells = adaptive_meshing.create_cells(x, y, z, gyroid_band)
        cells.compute_values()
        np.testing.assert_allclose(cells.values, gyroid_band(cells.positions[:, :, 0],
                                                             cells.positions[:, :, 1],
                                                             cells.positions[:, :, 2]))

    def test_crosses_surface(self):
        """Plane x = 50 between grid points: only the cells with corners on both sides cross it."""
        x, y, z = coarse_grid(number_of_points=5)                   # points at 0, 25, 50, 75, 100
        cells = adaptive_meshing.create_cells(x, y, z, lambda x, y, z: 60.0 - x)
        cells.compute_values().crosses_surface()
        # crossing cells: first corner at i = 2 (x from 50 to 75), all j, k
        expected = cells.first_corners[:, 0] == 2
        np.testing.assert_array_equal(cells.is_crossing_surface, expected)

    def test_face_neighbours_of_one_inner_cell(self):
        """An inner cell has 18 face/edge neighbours (NEIGHBOR_OFFSETS), not itself."""
        cells = adaptive_meshing.Cells(*coarse_grid(number_of_points=5))       # 4 x 4 x 4 cells
        mask = np.zeros(len(cells), dtype=bool)
        mask[cells.cell_number_at_location[(1, 1, 1)]] = True
        cells.face_neighbours_of(mask)
        assert cells.is_face_neighbour.sum() == len(adaptive_meshing.NEIGHBOR_OFFSETS) == 18
        assert not cells.is_face_neighbour[cells.cell_number_at_location[(1, 1, 1)]]

    def test_remove_unlikely_neighbours_without_neighbours(self):
        """No neighbour at all: nothing to remove, and no error."""
        x, y, z = coarse_grid(number_of_points=3)
        cells = adaptive_meshing.create_cells(x, y, z, gyroid_band)
        cells.compute_values()
        cells.face_neighbours_of(np.zeros(len(cells), dtype=bool))
        cells.remove_unlikely_neighbours()
        assert not cells.is_face_neighbour.any()

    def test_select_keeps_rows_aligned(self):
        """After select, row n of every array still describes the same cell, and the dictionary is rebuilt."""
        x, y, z = coarse_grid(number_of_points=4)
        cells = adaptive_meshing.create_cells(x, y, z, gyroid_band)
        cells.compute_values()
        keep = cells.first_corners[:, 2] == 1                      # cells with k = 1
        cells.select(keep)
        assert len(cells) == 3 * 3
        np.testing.assert_array_equal(cells.indices[:, 0, :], cells.first_corners[:, :])
        np.testing.assert_allclose(cells.values, gyroid_band(cells.positions[:, :, 0],
                                                             cells.positions[:, :, 1],
                                                             cells.positions[:, :, 2]))
        for cell_number in range(len(cells)):
            location = tuple(cells.first_corners[cell_number, :])
            assert cells.cell_number_at_location[location] == cell_number

    def test_select_rejects_integer_mask(self):
        """An integer array would be read as cell numbers, not as True / False: refused."""
        cells = adaptive_meshing.Cells(*coarse_grid(number_of_points=3))
        with pytest.raises(ValueError):
            cells.select(np.ones(len(cells), dtype=int))

    def test_subdivide(self):
        """8 children per cell, half the resolution, same origin, values and masks dropped."""
        x, y, z = coarse_grid(number_of_points=3, origin=(5.0, 5.0, 5.0))
        cells = adaptive_meshing.create_cells(x, y, z, gyroid_band)
        cells.compute_values().crosses_surface()
        number_of_parents = len(cells)
        parent_first_corner_position = cells.positions[0, 0, :].copy()
        cells.subdivide()

        assert len(cells) == 8 * number_of_parents
        np.testing.assert_allclose(cells.resolution, [25.0, 25.0, 25.0])      # 50 / 2
        np.testing.assert_allclose(cells.origin, [5.0, 5.0, 5.0])
        assert cells.values is None
        assert not hasattr(cells, "is_crossing_surface")
        # the first child of the first parent starts at the parent's first corner
        np.testing.assert_allclose(cells.positions[0, 0, :], parent_first_corner_position)
        # positions are still origin + indices * resolution
        np.testing.assert_allclose(cells.positions, cells.origin[np.newaxis, np.newaxis, :]
                                   + cells.indices[:, :, :] * cells.resolution[np.newaxis, np.newaxis, :])

    def test_add_box(self):
        """Corners on a box face become -box_margin; inside, min(value, distance to the box - margin)."""
        x, y, z = coarse_grid(number_of_points=5, origin=(10.0, 10.0, 10.0))
        cells = adaptive_meshing.create_cells(x, y, z, lambda x, y, z: np.full_like(x, 30.0))
        cells.compute_values().add_box(box_margin=BOX_MARGIN)
        expected = np.minimum(30.0, distance_to_box(cells.positions[:, :, 0], cells.positions[:, :, 1],
                                                    cells.positions[:, :, 2], origin=(10.0, 10.0, 10.0)) - BOX_MARGIN)
        np.testing.assert_allclose(cells.values, expected)
        on_a_face = np.isclose(distance_to_box(cells.positions[:, :, 0], cells.positions[:, :, 1],
                                               cells.positions[:, :, 2], origin=(10.0, 10.0, 10.0)), 0.0)
        np.testing.assert_allclose(cells.values[on_a_face], -BOX_MARGIN)


# ============================================================================
# 3 - TestRefineCells
# ============================================================================
class TestRefineCells:
    """
    Tests for adaptive_meshing.refine_cells().
    """

    def test_final_resolution(self):
        """Final resolution = coarse resolution / 2**number_of_subdivisions."""
        _, cells = run_pipeline(gyroid_band, number_of_subdivisions=2)
        np.testing.assert_allclose(cells.resolution, [BOX_SIZE / (NUMBER_OF_POINTS - 1) / 4] * 3)

    def test_values_are_the_field_closed_by_the_box(self):
        """Kept cells: positions = origin + indices * resolution, values = min(field, distance to box - margin)."""
        origin = (-50.0, 0.0, 20.0)
        x, y, z = coarse_grid(origin=origin)
        cells = adaptive_meshing.create_cells(x, y, z, gyroid_band)
        adaptive_meshing.refine_cells(cells, number_of_subdivisions=1)

        np.testing.assert_allclose(cells.positions, cells.origin[np.newaxis, np.newaxis, :]
                                   + cells.indices[:, :, :] * cells.resolution[np.newaxis, np.newaxis, :])
        corner_x = cells.positions[:, :, 0]
        corner_y = cells.positions[:, :, 1]
        corner_z = cells.positions[:, :, 2]
        expected = np.minimum(gyroid_band(corner_x, corner_y, corner_z),
                              distance_to_box(corner_x, corner_y, corner_z, origin=origin) - BOX_MARGIN)
        np.testing.assert_allclose(cells.values, expected)

    def test_keeps_every_coarse_cell_crossing_the_lattice(self):
        """Without subdivision: every coarse cell whose 8 corners disagree on the lattice field is kept."""
        x, y, z = coarse_grid()
        number_of_cells = NUMBER_OF_POINTS - 1
        solid = gyroid_band(x, y, z) > 0
        corners = [solid[a:a + number_of_cells, b:b + number_of_cells, c:c + number_of_cells]
                   for a in (0, 1) for b in (0, 1) for c in (0, 1)]
        crossing = np.logical_or.reduce(corners) & ~np.logical_and.reduce(corners)    # (14, 14, 14)
        crossing_locations = {tuple(location) for location in np.argwhere(crossing)}

        cells = adaptive_meshing.create_cells(x, y, z, gyroid_band)
        adaptive_meshing.refine_cells(cells, number_of_subdivisions=0)
        kept_locations = set(cells.cell_number_at_location.keys())
        assert len(crossing_locations) > 0                        # the test is not empty
        assert crossing_locations <= kept_locations


# ============================================================================
# 4 - TestMeshCells
# ============================================================================
class TestMeshCells:
    """
    Tests for adaptive_meshing.mesh_cells().
    """

    def test_values_not_computed_raises(self):
        """mesh_cells needs the values: ValueError if compute_values / refine_cells was not called."""
        cells = adaptive_meshing.Cells(*coarse_grid(number_of_points=2))
        with pytest.raises(ValueError):
            adaptive_meshing.mesh_cells(cells)

    def test_no_surface_raises(self):
        """A field with no sign change gives no triangles: ValueError rather than an empty mesh."""
        x, y, z = coarse_grid(number_of_points=2)                   # a single cell
        cells = adaptive_meshing.create_cells(x, y, z, lambda x, y, z: np.ones_like(x))
        cells.compute_values()
        with pytest.raises(ValueError):
            adaptive_meshing.mesh_cells(cells)

    def test_single_cell_plane(self):
        """A plane x = 50 through one cell of the box [0, 100]^3 gives a flat square (2 triangles) at x = 50."""
        x, y, z = coarse_grid(number_of_points=2)                   # a single cell
        cells = adaptive_meshing.create_cells(x, y, z, lambda x, y, z: 50.0 - x)     # solid where x < 50
        cells.compute_values()
        verts, faces = adaptive_meshing.mesh_cells(cells)
        np.testing.assert_allclose(verts[:, 0], 50.0)
        assert len(faces) == 2


# ============================================================================
# 5 - TestFullPipeline
# ============================================================================
class TestFullPipeline:
    """
    create_cells + refine_cells + mesh_cells.
    """

    @pytest.mark.parametrize("number_of_subdivisions", [0, 1, 2])
    def test_same_mesh_as_uniform_grid(self, number_of_subdivisions):
        """Same vertices, faces and area as marching cubes on the full uniform fine grid closed by the box.

        Fine grid: (NUMBER_OF_POINTS - 1) * 2**number_of_subdivisions + 1 points per axis.
        The area is compared to 1e-6 relative: the reference grid comes from np.linspace and the refined
        corners from origin + index * resolution, which differ in the last digits of each position."""
        refined, _ = run_pipeline(gyroid_band, number_of_subdivisions)
        reference = uniform_closed_mesh(gyroid_band, (NUMBER_OF_POINTS - 1) * 2 ** number_of_subdivisions + 1)

        assert len(refined.vertices) == len(reference.vertices)
        assert len(refined.faces) == len(reference.faces)
        assert refined.area == pytest.approx(reference.area, rel=1e-6)

    @pytest.mark.parametrize("origin", [(0.0, 0.0, 0.0), (-50.0, 10.0, 200.0)])
    def test_closed_by_the_box(self, origin):
        """Watertight, filling exactly the box covered by the coarse grid, wherever that box starts."""
        mesh, _ = run_pipeline(lambda x, y, z: gyroid_band(x - origin[0], y - origin[1], z - origin[2]),
                               number_of_subdivisions=2, origin=origin)
        assert mesh.is_watertight
        expected_bounds = [list(origin), [origin[0] + BOX_SIZE, origin[1] + BOX_SIZE, origin[2] + BOX_SIZE]]
        np.testing.assert_allclose(mesh.bounds, expected_bounds, atol=1e-5)


# ============================================================================
# 6 - TestTPMSModelAdaptive
# ============================================================================
class TestTPMSModelAdaptive:
    """
    TPMSModel.generate_mesh_adaptive(): the model's field evaluated between grid points,
    with thickness / level given as constants or as functions of position (set_point_function).
    """

    NUMBER_OF_SUBDIVISIONS = 2
    FINE_CELL_SIZE = BOX_SIZE / (NUMBER_OF_POINTS - 1) / 2 ** NUMBER_OF_SUBDIVISIONS     # 1.786

    @staticmethod
    def thickness_function(x, y, z):
        """Wall thickness growing along x: 0.3 at x = 0, 0.9 at x = 100."""
        return 0.3 + 0.6 * x / BOX_SIZE

    @staticmethod
    def level_function(x, y, z):
        """Threshold (level) growing along y: -0.15 at y = 0, +0.15 at y = 100."""
        return 0.3 * (y / BOX_SIZE - 0.5)

    def make_model(self, thickness=THICKNESS):
        x, y, z = coarse_grid()
        return GyroidModel(x, y, z, PERIOD, PERIOD, PERIOD, thickness)

    def test_constant_functions_give_the_same_mesh_as_constants(self):
        """thickness / level given as functions returning a constant: same mesh as the plain constants."""
        model_constant = self.make_model(thickness=THICKNESS)
        verts_constant, faces_constant = model_constant.generate_mesh_adaptive(
            self.NUMBER_OF_SUBDIVISIONS, mode="band", level=0.1)

        model_functions = self.make_model(thickness=THICKNESS)
        model_functions.set_point_function("thickness", lambda x, y, z: np.full_like(x, THICKNESS))
        model_functions.set_point_function("level", lambda x, y, z: np.full_like(x, 0.1))
        verts_functions, faces_functions = model_functions.generate_mesh_adaptive(
            self.NUMBER_OF_SUBDIVISIONS, mode="band", level=0.0)          # level argument ignored: the function wins

        np.testing.assert_allclose(verts_functions, verts_constant)
        np.testing.assert_array_equal(faces_functions, faces_constant)

    def test_grid_array_without_function_raises(self):
        """A thickness known only on the grid (array) cannot be evaluated between grid points."""
        x, y, z = coarse_grid()
        model = self.make_model(thickness=self.thickness_function(x, y, z))     # (15, 15, 15) array
        with pytest.raises(ValueError):
            model.generate_mesh_adaptive(self.NUMBER_OF_SUBDIVISIONS, mode="band")

    def test_grid_array_level_without_function_raises(self):
        """Same for a level known only on the grid."""
        x, y, z = coarse_grid()
        model = self.make_model()
        with pytest.raises(ValueError):
            model.generate_mesh_adaptive(self.NUMBER_OF_SUBDIVISIONS, mode="signed",
                                         level=self.level_function(x, y, z))

    def test_distance_mode_raises(self):
        """The "distance" mode needs the whole grid (distance transform): not available here."""
        with pytest.raises(ValueError):
            self.make_model().generate_mesh_adaptive(self.NUMBER_OF_SUBDIVISIONS, mode="distance")

    def test_vertices_lie_on_the_surface_of_the_level_function(self):
        """
        Signed mode with a level function: every vertex away from the box lies on
        density = gyroid - level(y) = 0, up to the linear interpolation error of marching cubes.

        BOUND (derived)
        ---------------
        A vertex is the zero of the linear interpolation L of the density f along one cell edge
        of length h. Along that edge, |f - L| <= h**2 / 8 * max|f''|, so |f(vertex)| <= h**2 / 8 * max|f''|.
        With w = 2 pi / PERIOD, along x: d2/dx2 gyroid = -w**2 (sin(wx)cos(wy) + sin(wz)cos(wx)),
        so |f''| <= 2 w**2 (same along y and z), and level(y) is linear in y (no second derivative).
        Hence |f(vertex)| <= h**2 * w**2 / 4  (about 0.0031 for h = 1.786).

        ASSUMPTION
        ----------
        The bound holds for edges where the box did not change the corner values. Vertices within
        one fine cell h of a box face are excluded: their edge can end on a face (value -BOX_MARGIN,
        the cap). From h inward the box value is h - BOX_MARGIN, larger than |f| <= 1.5 + 0.15, so
        min(f, box) = f at both ends of every remaining edge (checked below).
        """
        model = self.make_model()
        model.set_point_function("level", self.level_function)
        verts, faces = model.generate_mesh_adaptive(self.NUMBER_OF_SUBDIVISIONS, mode="signed")

        h = self.FINE_CELL_SIZE
        w = 2 * np.pi / PERIOD
        bound = h ** 2 * w ** 2 / 4
        assert np.abs(gyroid(*coarse_grid())).max() + 0.15 < h - BOX_MARGIN      # the assumption above

        away_from_box = distance_to_box(verts[:, 0], verts[:, 1], verts[:, 2]) > h
        density = model.density_field_at(verts[away_from_box, 0], verts[away_from_box, 1],
                                         verts[away_from_box, 2], mode="signed")
        assert away_from_box.sum() > 1000                         # most of the mesh is checked
        assert np.abs(density).max() <= bound

        # the level function really is used between grid points: with a constant level 0
        # instead, these vertices are far off the surface
        density_with_level_0 = gyroid(verts[away_from_box, 0], verts[away_from_box, 1], verts[away_from_box, 2])
        assert np.abs(density_with_level_0).max() > 10 * bound

    def test_thickness_and_level_functions_give_closed_mesh(self):
        """Band mode with both functions: watertight and filling the box."""
        model = self.make_model()
        model.set_point_function("thickness", self.thickness_function)
        model.set_point_function("level", self.level_function)
        verts, faces = model.generate_mesh_adaptive(self.NUMBER_OF_SUBDIVISIONS, mode="band")
        mesh = trimesh.Trimesh(verts, faces, process=False)
        assert mesh.is_watertight
        np.testing.assert_allclose(mesh.bounds, [[0, 0, 0], [BOX_SIZE] * 3], atol=1e-5)

    def test_baseplates_are_solid(self):
        """
        With baseplate_thickness t, the slabs z < t and z > BOX_SIZE - t are solid: no surface inside them.
        A vertex lies on an edge with one empty corner, so it can be at most one fine cell h inside a slab;
        away from the side faces (the caps), no vertex has h < distance to the nearest z end < t - h.
        """
        plate_thickness = 5.0
        h = self.FINE_CELL_SIZE

        def vertices_inside_the_slabs(verts):
            distance_to_x_and_y_faces = np.minimum(np.minimum(verts[:, 0], BOX_SIZE - verts[:, 0]),
                                                   np.minimum(verts[:, 1], BOX_SIZE - verts[:, 1]))
            distance_to_z_ends = np.minimum(verts[:, 2], BOX_SIZE - verts[:, 2])
            inside = (distance_to_x_and_y_faces > h) & (distance_to_z_ends > h) & (distance_to_z_ends < plate_thickness - h)
            return inside.sum()

        verts_without, _ = self.make_model().generate_mesh_adaptive(self.NUMBER_OF_SUBDIVISIONS, mode="band")
        assert vertices_inside_the_slabs(verts_without) > 0       # the lattice alone does reach there

        verts_with, faces_with = self.make_model().generate_mesh_adaptive(
            self.NUMBER_OF_SUBDIVISIONS, mode="band", baseplate_thickness=plate_thickness)
        assert vertices_inside_the_slabs(verts_with) == 0
        assert trimesh.Trimesh(verts_with, faces_with, process=False).is_watertight
