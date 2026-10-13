"""
Tests for triply.adaptive_meshing.
"""
import numpy as np
import pytest

#this is just like the import in triply.mesh_tools, but we do it here so that pytest can skip all tests in this module if triply isn't importable
adaptive_meshing = pytest.importorskip("triply.adaptive_meshing")
trimesh = pytest.importorskip("trimesh")
from skimage import measure  # noqa: E402

"""
============================================================================
0 - helpers (gyroid band field, uniform reference mesh)
1 - TestDistanceInsideBox
2 - TestRefineCells
3 - TestMeshCells
4 - TestFullPipeline
============================================================================
"""

# ============================================================================
# 0 - helpers
# ============================================================================
PERIOD = 100.0
THICKNESS = 0.5
BOX_SIZE = (100.0, 100.0, 100.0)
FIELD_SLOPE_BOUND = 2 * np.sqrt(3) * 2 * np.pi / PERIOD     # gyroid in band mode
NEAR_SURFACE_FACTOR = 0.05


def gyroid_band(x, y, z):
    """Gyroid in band mode: positive (solid) inside the wall, open at the box faces."""
    w = 2 * np.pi / PERIOD
    gyroid = (np.sin(w * x) * np.cos(w * y) + np.sin(w * y) * np.cos(w * z)
              + np.sin(w * z) * np.cos(w * x))
    return THICKNESS - np.abs(gyroid)


def gyroid_band_closed(x, y, z):
    """Same gyroid, closed at the box faces: solid only inside the wall AND inside the box."""
    return np.minimum(gyroid_band(x, y, z), adaptive_meshing.distance_inside_box(x, y, z, BOX_SIZE))


def run_pipeline(field_function, resolution, number_of_subdivisions):
    """refine_cells then mesh_cells, as in the notebook."""
    _, cells_positions, cells_values, _ = adaptive_meshing.refine_cells(
        field_function, BOX_SIZE, (resolution,) * 3, number_of_subdivisions,
        NEAR_SURFACE_FACTOR, FIELD_SLOPE_BOUND)
    verts, faces = adaptive_meshing.mesh_cells(cells_positions, cells_values)
    return trimesh.Trimesh(verts, faces, process=False)


def uniform_mesh(field_function, number_of_points):
    """Reference: marching cubes on the full uniform grid over the box, merged and cleaned like mesh_cells."""
    axis = np.linspace(0, BOX_SIZE[0], number_of_points)
    spacing = axis[1] - axis[0]
    values = field_function(*np.meshgrid(axis, axis, axis, indexing="ij"))
    verts, faces, _, _ = measure.marching_cubes(values, level=0.0, spacing=(spacing,) * 3,
                                                allow_degenerate=True, method="lewiner")
    mesh = trimesh.Trimesh(verts, faces, process=False)
    mesh.merge_vertices()
    mesh.update_faces(mesh.nondegenerate_faces())
    return mesh


# ============================================================================
# 1 - TestDistanceInsideBox
# ============================================================================
class TestDistanceInsideBox:
    """
    Tests for adaptive_meshing.distance_inside_box().
    """

    def test_values(self):
        """Centre: half the box; on a face: just below 0 (the margin); outside: negative distance."""
        distance = adaptive_meshing.distance_inside_box(np.array([50.0, 0.0, -5.0]), np.array([50.0, 50.0, 50.0]),
                                                        np.array([50.0, 50.0, 50.0]), BOX_SIZE)
        np.testing.assert_allclose(distance, [50.0, 0.0, -5.0], atol=1e-9)
        assert distance[1] < 0     # the margin makes a point exactly on a face count as empty


# ============================================================================
# 2 - TestRefineCells
# ============================================================================
class TestRefineCells:
    """
    Tests for adaptive_meshing.refine_cells().
    """

    def test_shapes_and_alignment(self):
        """Row n of every output is the same cell: positions = indices * cell size, values = field at positions."""
        indices, positions, values, cell_size = adaptive_meshing.refine_cells(
            gyroid_band, BOX_SIZE, (9, 9, 9), 2, NEAR_SURFACE_FACTOR, FIELD_SLOPE_BOUND)
        assert indices.shape == positions.shape and indices.shape[1:] == (8, 3)
        assert values.shape == (len(indices), 8)
        np.testing.assert_allclose(positions, indices * cell_size)
        np.testing.assert_allclose(values, gyroid_band(positions[..., 0], positions[..., 1], positions[..., 2]))

    def test_final_cell_size(self):
        """Final cell size = box / (points - 1) / 2**number_of_subdivisions."""
        _, _, _, cell_size = adaptive_meshing.refine_cells(
            gyroid_band, BOX_SIZE, (9, 9, 9), 2, NEAR_SURFACE_FACTOR, FIELD_SLOPE_BOUND)
        np.testing.assert_allclose(cell_size, 100.0 / 8 / 4)

    def test_no_subdivision_matches_coarse_grid_test(self):
        """Without subdivision and without the near-surface margin: exactly the coarse cells whose 8 corners disagree."""
        number_of_points = 9
        axis = np.linspace(0, BOX_SIZE[0], number_of_points)
        solid = gyroid_band(*np.meshgrid(axis, axis, axis, indexing="ij")) > 0
        n = number_of_points - 1
        corners = [solid[a:a + n, b:b + n, c:c + n] for a in (0, 1) for b in (0, 1) for c in (0, 1)]
        expected = (np.logical_or.reduce(corners) & ~np.logical_and.reduce(corners)).sum()

        indices, _, _, _ = adaptive_meshing.refine_cells(
            gyroid_band, BOX_SIZE, (number_of_points,) * 3, 0, 0.0, FIELD_SLOPE_BOUND)
        assert len(indices) == expected


# ============================================================================
# 3 - TestMeshCells
# ============================================================================
class TestMeshCells:
    """
    Tests for adaptive_meshing.mesh_cells().
    """

    def test_no_surface_raises(self):
        """A field with no sign change gives no triangles: ValueError rather than an empty mesh."""
        positions = adaptive_meshing.CORNER_OFFSETS[np.newaxis].astype(float)
        with pytest.raises(ValueError):
            adaptive_meshing.mesh_cells(positions, np.ones((1, 8)))

    def test_single_cell_plane(self):
        """A plane x = 0.5 through one unit cell gives a flat square (2 triangles) at x = 0.5."""
        positions = adaptive_meshing.CORNER_OFFSETS[np.newaxis].astype(float)       # unit cell at the origin
        values = 0.5 - positions[..., 0]                                             # solid where x < 0.5
        verts, faces = adaptive_meshing.mesh_cells(positions, values)
        np.testing.assert_allclose(verts[:, 0], 0.5)
        assert len(faces) == 2


# ============================================================================
# 4 - TestFullPipeline
# ============================================================================
class TestFullPipeline:
    """
    refine_cells + mesh_cells, as in the notebook.
    """

    @pytest.mark.parametrize("number_of_subdivisions", [1, 2])
    def test_same_mesh_as_uniform_grid(self, number_of_subdivisions):
        """Open lattice: same vertices, faces and area as marching cubes on the full uniform fine grid.

        The area is compared to 1e-6 relative: the reference grid comes from np.linspace and the refined
        corners from index * cell size, which differ in the last digits of each position."""
        number_of_points = 15
        refined = run_pipeline(gyroid_band, number_of_points, number_of_subdivisions)
        reference = uniform_mesh(gyroid_band, (number_of_points - 1) * 2 ** number_of_subdivisions + 1)

        assert len(refined.vertices) == len(reference.vertices)
        assert len(refined.faces) == len(reference.faces)
        assert refined.area == pytest.approx(reference.area, rel=1e-6)

    def test_closed_by_the_box(self):
        """With the box distance in the field: watertight, filling exactly the box."""
        mesh = run_pipeline(gyroid_band_closed, 15, 2)
        assert mesh.is_watertight
        np.testing.assert_allclose(mesh.bounds, [[0, 0, 0], BOX_SIZE], atol=1e-6)
