# triply: design, meshing, simulation and CT analysis of TPMS structures
# Copyright (C) 2026, Empa, Laboratory for High Performance Ceramics (201), Corentin Foucher
# SPDX-License-Identifier: MIT

"""
============================================================================
TPMS_CHARACTERISATION: Characterisation of TPMS structures

============================================================================

#=====================================================================================================================
0 - (reserved)
1 - mean_intercept_length_along_direction
2 - mean_intercept_length_vs_angle
3 - fit_mil_ellipsoid
    plot_mil_rose_3d
#=====================================================================================================================
"""

import time
import numpy as np
from .logger import logger # type: ignore
from scipy.ndimage import map_coordinates


# ==============================================================================
# HELPERS: directions <-> angles
# ==============================================================================
def _hemisphere_directions(n_directions: int) -> np.ndarray:
    """
    Returns (n_directions, 3) unit vectors spread nearly uniformly over the
    upper hemisphere (z >= 0), using a Fibonacci spiral.

    Only a hemisphere is needed because w and -w give the same test lines,
    hence the same MIL.

    Construction:
        z_k   = 1 - (k + 0.5) / n          uniform in (0, 1]
                                           -> equal area per point, since the
                                              area of a spherical zone is
                                              proportional to its height in z
        phi_k = k * golden_angle           golden_angle = pi * (3 - sqrt(5))
                                           -> successive points never line up
        r_k   = sqrt(1 - z_k^2)            radius of the circle at height z_k
        w_k   = (r_k cos phi_k, r_k sin phi_k, z_k)
    """
    index = np.arange(n_directions) + 0.5
    z_component = 1.0 - index / n_directions
    golden_angle = np.pi * (3.0 - np.sqrt(5.0))
    azimuth = golden_angle * np.arange(n_directions)
    radius = np.sqrt(1.0 - z_component**2)
    return np.stack([radius * np.cos(azimuth),
                     radius * np.sin(azimuth),
                     z_component], axis=1)

# ==============================================================================
# 1 - mean_intercept_length_along_direction
# ==============================================================================
def mean_intercept_length_along_direction(voxel_grid: np.ndarray,
                                          x: np.ndarray,
                                          y: np.ndarray,
                                          z: np.ndarray,
                                          direction: np.ndarray,
                                          n_lines: int = 2000,
                                          step_fraction: float = 0.5,
                                          seed: int | np.random.Generator | None = None) -> dict:
    """
    ============================================================================
    MEAN_INTERCEPT_LENGTH_ALONG_DIRECTION
    Computes the mean intercept length MIL(w) of a binary voxel grid along
    one test direction w.
    ============================================================================

    PRINCIPLE
    ---------
    Shoot n_lines parallel test lines along w through the volume, at random
    positions in the plane perpendicular to w. Walk along each line in steps
    of `step`, read solid/void at each sample, and count:
        L(w) = total line length inside the box
        I(w) = number of solid/void changes (interface crossings)
    Then
        MIL(w) = L(w) / I(w)

    MIL here is the mean length of ALL segments along a line (solid and void
    alternate). The mean SOLID intercept would be 2 * (BV/TV) * L / I.

    PARAMETERS
    ----------
    voxel_grid : (nx, ny, nz) ndarray
        3D voxel grid. Voxels > 0 are solid, all others are void
        (works with 0/1, bool and +1/-1).
    x : (nx,) ndarray
        Voxel-centre coordinates along x (3D meshgrid is cut to x[:, 0, 0]).
    y : (ny,) ndarray
        Same along y (3D meshgrid is cut to y[0, :, 0]).
    z : (nz,) ndarray
        Same along z (3D meshgrid is cut to z[0, 0, :]).
    direction : (3,) array-like
        Test direction w. Need not be unit length; it is normalised here.
    n_lines : int, optional
        Number of parallel test lines (default = 2000).
    step_fraction : float, optional
        Sampling step along a line, as a fraction of the smallest voxel
        spacing (default = 0.5).
    seed : int, np.random.Generator or None, optional
        Seed (or existing generator) for the random line positions
        (default = None).

    RETURNS
    -------
    mil : float
        MIL(w) in physical units (same units as x, y, z);
        nan if no interface was crossed.

    RAISES
    ------
    ValueError
        If n_lines <= 2.

    EXAMPLE
    -------
    >>> mil_z = mean_intercept_length_along_direction(voxel_grid, x, y, z,
    ...                                               direction=[0, 0, 1], seed=0)
    """

    # ------------------------------------------------------------------
    # Validate inputs
    # ------------------------------------------------------------------
    # Reduce 3D meshgrid coordinates to 1D axes
    if x.ndim == 3:
        x = x[:, 0, 0]
    if y.ndim == 3:
        y = y[0, :, 0]
    if z.ndim == 3:
        z = z[0, 0, :]

    if n_lines <= 2:
        raise ValueError("n_lines must be > 2")

    # normalize direction to unit vector
    direction = np.asarray(direction, dtype=float).reshape(3)
    direction = direction / np.linalg.norm(direction)

    # Binarise input solid: 1 = solid, 0 = void
    solid = (voxel_grid > 0).astype(np.int8)

    # ------------------------------------------------------------------
    # Prepare data for MIL computation
    # ------------------------------------------------------------------
    # grab voxel spacing (A4)
    spacing = np.array([x[1] - x[0], y[1] - y[0], z[1] - z[0]], dtype=float)

    # define working box: size, centre, half-diagonal 
    box_size = (np.array(solid.shape) - 1.0) * spacing     # size in each direction, in number of voxels * spacing
    box_centre = box_size / 2.0                            # position of box centre 
    half_diagonal = np.linalg.norm(box_size) / 2.0          # the norm of the vector divided by two gives the half-diagonal length of the box

    # Positions along each line where solid/void is checked: every `step`, from -R to +R
    step = step_fraction * spacing.min()
    line_parameter = np.arange(-half_diagonal, half_diagonal + step, step)  # vectror of distance values along the line, from -R to +R, in increments of `step`
    n_steps = line_parameter.size

    random_generator = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # find two directions perpendicular to the input direction, 
    # ------------------------------------------------------------------
    # they are used to define a plane in which the test lines are distributed
    if abs(direction[0]) < 0.9:
        helper = np.array([1.0, 0.0, 0.0])   # w is far from the x axis -> x axis is safe
    else:
        helper = np.array([0.0, 1.0, 0.0])   # w is close to the x axis -> use the y axis instead
    # you just need any vector that is not parallel to the input direction, to compute a perpendicular vector via cross product
    first_normal = np.cross(direction, helper)
    first_normal = first_normal / np.linalg.norm(first_normal)  # noramlize to unit vector
    # the second normal is calculated as the cross product of the input direction and the first normal
    second_normal = np.cross(direction, first_normal)

    # ------------------------------------------------------------------
    # feed the plane with random lines
    # ------------------------------------------------------------------
    offsets_1 = random_generator.uniform(-half_diagonal, half_diagonal, size=n_lines)    # a vector of random offsets in the plane, for each line (n_lines)
    offsets_2 = random_generator.uniform(-half_diagonal, half_diagonal, size=n_lines)    # a vector of random offsets in the plane, for each line (n_lines)
    line_origins = (box_centre
                + offsets_1[:, np.newaxis] * first_normal
                + offsets_2[:, np.newaxis] * second_normal)             # the origin of each line is the centre of the box, plus a random offset in the plane defined by the two normals
                                                                        # 2D array of shape (n_lines, 3) containing the origin of each line in 3D space

    # ------------------------------------------------------------------
    # list the points along each line, check if they are inside the box,
    # ------------------------------------------------------------------
    points = line_origins[:, np.newaxis, :] + line_parameter[:, np.newaxis] * direction # 3D array of shape (n_lines, n_steps, 3) containing the coordinates of each sample point along each line
    inside = np.all((points >= 0.0) & (points <= box_size), axis=2)    

    # ------------------------------------------------------------------
    # sample the solid/void values at those points, using nearest-neighbour interpolation (A3)
    # ------------------------------------------------------------------
    voxel_coordinates = points / spacing[np.newaxis, np.newaxis, :]
    values = map_coordinates(solid,
                             [voxel_coordinates[:, :, 0].ravel(),
                              voxel_coordinates[:, :, 1].ravel(),
                              voxel_coordinates[:, :, 2].ravel()],
                             order=0, mode="nearest").reshape(n_lines, n_steps)

    # ------------------------------------------------------------------
    # compute MIL: total length of lines inside the box, number of crossings, MIL = L/I
    # ------------------------------------------------------------------
    pair_inside = inside[:, :-1] & inside[:, 1:]
    total_length = np.count_nonzero(pair_inside) * step
    n_crossings = int(np.count_nonzero(pair_inside & (values[:, :-1] != values[:, 1:])))
    mil = total_length / n_crossings if n_crossings > 0 else np.nan

    # One line per direction: DEBUG only, because this is called once per direction
    logger.debug(f"w = ({direction[0]:+.3f}, {direction[1]:+.3f}, {direction[2]:+.3f}): "
                 f"L = {total_length:.4g}, I = {n_crossings}, MIL = {mil:.4g}")

    return mil



# ==============================================================================
# 2 - mean_intercept_length_vs_angle
# ==============================================================================

def mean_intercept_length_vs_angle(voxel_grid: np.ndarray,
                                   x: np.ndarray,
                                   y: np.ndarray,
                                   z: np.ndarray,
                                   n_directions: int = 200,
                                   n_lines: int = 1000,
                                   step_fraction: float = 0.5,
                                   seed: int | None = None) -> dict:
    """
    ============================================================================
    MEAN_INTERCEPT_LENGTH_VS_ANGLE
    Computes MIL(w) for n_directions directions w spread over a hemisphere,
    by calling mean_intercept_length_along_direction once per direction.
    ============================================================================

    ANGLES
    ------
    Each direction w = (wx, wy, wz) is also given as spherical angles:
        polar angle   theta = arccos(wz)        0 deg = along +z, 90 deg = in xy-plane
        azimuth angle phi   = atan2(wy, wx)     0 deg = +x, 90 deg = +y, in [0, 360)
    so that  w = (sin theta cos phi, sin theta sin phi, cos theta).

    PARAMETERS
    ----------
    voxel_grid, x, y, z, n_lines, step_fraction :
        Passed unchanged to mean_intercept_length_along_direction.
    n_directions : int, optional
        Number of test directions on the hemisphere (default = 200).
    seed : int or None, optional
        Seed of one random generator shared by all directions, so the whole
        run is reproducible from one number (default = None).

    RETURNS
    -------
    result : dict
        "directions"     (n_directions, 3) unit vectors w.
        "polar_angle"    (n_directions,) theta in degrees.
        "azimuth_angle"  (n_directions,) phi in degrees.
        "mil"            (n_directions,) MIL(w) in physical units
                         (nan where no interface was crossed).

    EXAMPLE
    -------
    >>> result = mean_intercept_length_vs_angle(voxel_grid, x, y, z, seed=0)
    >>> plt.scatter(result["polar_angle"], result["mil"])
    """

    # ------------------------------------------------------------------
    # Test directions and their angles
    # ------------------------------------------------------------------
    logger.info(f"Computing MIL in {n_directions} directions, {n_lines} lines each, "
                f"step = {step_fraction} x smallest voxel spacing, grid {voxel_grid.shape}")
    start_time = time.time()

    directions = _hemisphere_directions(n_directions)
    polar_angle = np.degrees(np.arccos(directions[:, 2]))                                    # theta, from +z
    azimuth_angle = np.degrees(np.arctan2(directions[:, 1], directions[:, 0])) % 360.0       # phi, from +x towards +y

    # ------------------------------------------------------------------
    # MIL for each direction
    # ------------------------------------------------------------------
    # One generator for all directions: each call draws new random lines from it
    random_generator = np.random.default_rng(seed)

    mil = np.zeros(n_directions)
    for direction_number in range(n_directions):
        mil[direction_number] = mean_intercept_length_along_direction(
            voxel_grid, x, y, z,
            direction=directions[direction_number],
            n_lines=n_lines,
            step_fraction=step_fraction,
            seed=random_generator)

        # Progress every 10 % of the directions
        if (direction_number + 1) % max(1, n_directions // 10) == 0:
            logger.debug(f"{direction_number + 1}/{n_directions} directions done "
                         f"({time.time() - start_time:.1f} s)")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    n_without_crossing = int(np.count_nonzero(~np.isfinite(mil)))
    if n_without_crossing == n_directions:
        logger.warning("No direction crossed any solid/void interface: all MIL are nan. "
                       "Is the grid all solid or all void (check the sign of the field)?")
    else:
        if n_without_crossing > 0:
            logger.warning(f"{n_without_crossing}/{n_directions} directions crossed no interface "
                           f"(MIL = nan, i.e. infinite in those directions).")
        logger.info(f"MIL computed in {time.time() - start_time:.1f} s: "
                    f"min = {np.nanmin(mil):.4g}, max = {np.nanmax(mil):.4g}, "
                    f"max/min = {np.nanmax(mil) / np.nanmin(mil):.3f}")

    return {"directions": directions,
            "polar_angle": polar_angle,
            "azimuth_angle": azimuth_angle,
            "mil": mil}


# ==============================================================================
# 3 - fit_mil_ellipsoid
# ==============================================================================
def fit_mil_ellipsoid(directions: np.ndarray,
                      mil: np.ndarray,
                      residual_warning: float = 0.05) -> dict:
    """
    ============================================================================
    FIT_MIL_ELLIPSOID
    Fits an ellipsoid to MIL against direction:  1 / MIL(w)^2 = w^T M w
    and returns the symmetric 3x3 matrix M that describes it.
    ============================================================================

    PRINCIPLE
    ---------
    Put a point at distance MIL(w) from the origin in each direction w:
        r(w) = MIL(w) * w
    If these points lie on an ellipsoid, it can be written r^T M r = 1,
    with M a symmetric 3x3 matrix. Substituting r = MIL * w:
        MIL^2 * w^T M w = 1   =>   w^T M w = 1 / MIL(w)^2
    Fitting the ellipsoid therefore means finding M from the measured
    pairs (w, MIL(w)).

    ASSUMPTION
    ----------
    B1  MIL(w) follows an ellipsoid. This is a model choice
        (Harrigan & Mann 1984), not a result: check "relative_rms_residual"
        and look at the fitted surface on the MIL rose (plot_mil_rose_3d).
        Cubic TPMS (equal periods) give MIL bumps along the axes or
        diagonals that an ellipsoid cannot follow: the fit is then a sphere.

    LINEAR SYSTEM
    -------------
    With w = (wx, wy, wz) and M symmetric (M12 = M21, M13 = M31, M23 = M32):
        w^T M w = M11 wx^2 + M22 wy^2 + M33 wz^2
                + 2 M12 wx wy + 2 M23 wy wz + 2 M13 wx wz
    (each off-diagonal term appears twice: M_ij wi wj and M_ji wj wi).
    This is linear in the 6 unknowns  [M11, M22, M33, M12, M23, M13].
    One equation per direction k:
        [wx^2, wy^2, wz^2, 2 wx wy, 2 wy wz, 2 wx wz] . unknowns = 1 / MIL_k^2
    With more than 6 directions the system is overdetermined and is solved
    by least squares (minimise the sum of squared equation errors).

    PARAMETERS
    ----------
    directions : (K, 3) ndarray
        Unit test directions w (e.g. result["directions"] from
        mean_intercept_length_vs_angle).
    mil : (K,) ndarray
        MIL along each direction (e.g. result["mil"]); nan entries are ignored.
    residual_warning : float, optional
        Log a warning when relative_rms_residual exceeds this value
        (default = 0.05, i.e. 5 %).

    RETURNS
    -------
    result : dict
        "mil_tensor"             (3, 3) M.
        "mil_fitted"             (K,) MIL predicted by the ellipsoid,
                                 1 / sqrt(w^T M w) (nan where w^T M w <= 0).
        "relative_rms_residual"  RMS of (mil_fitted - mil) / mil
                                 (0 = points exactly on an ellipsoid).
        "is_positive_definite"   True if all eigenvalues of M > 0, i.e. the
                                 fitted surface is a closed ellipsoid. False
                                 means MIL is (near) infinite in some direction,
                                 e.g. along flat plates.

    RAISES
    ------
    ValueError
        If fewer than 6 directions have a valid MIL.

    EXAMPLE
    -------
    >>> result = mean_intercept_length_vs_angle(voxel_grid, x, y, z, seed=0)
    >>> ellipsoid = fit_mil_ellipsoid(result["directions"], result["mil"])
    >>> plot_mil_rose_3d(result, ellipsoid=ellipsoid)
    """

    # ------------------------------------------------------------------
    # Keep only directions where MIL was measured (at least one crossing)
    # ------------------------------------------------------------------
    valid = np.isfinite(mil)
    n_valid = int(np.count_nonzero(valid))
    if n_valid < 6:
        raise ValueError("At least 6 valid directions are needed to fit the 6 components of M.")
    if n_valid < len(mil):
        logger.info(f"{len(mil) - n_valid} directions with MIL = nan left out of the fit.")

    w_x = directions[valid, 0]
    w_y = directions[valid, 1]
    w_z = directions[valid, 2]

    # ------------------------------------------------------------------
    # Build the linear system: one row per direction
    # ------------------------------------------------------------------
    # columns multiply, in order:       M11      M22      M33      M12            M23            M13
    design_matrix = np.stack([w_x**2,  w_y**2,  w_z**2,  2 * w_x * w_y,  2 * w_y * w_z,  2 * w_x * w_z], axis=1)
    right_hand_side = 1.0 / mil[valid]**2

    # ------------------------------------------------------------------
    # Least-squares solution, then assemble the symmetric matrix M
    # ------------------------------------------------------------------
    unknowns, _, _, _ = np.linalg.lstsq(design_matrix, right_hand_side, rcond=None)
    m11, m22, m33, m12, m23, m13 = unknowns
    mil_tensor = np.array([[m11, m12, m13],
                           [m12, m22, m23],
                           [m13, m23, m33]])

    # ------------------------------------------------------------------
    # Fit quality: MIL predicted by the ellipsoid vs measured MIL
    # ------------------------------------------------------------------
    # w^T M w for every direction, written out with the same 6 terms
    all_x = directions[:, 0]
    all_y = directions[:, 1]
    all_z = directions[:, 2]
    quadratic_form = (m11 * all_x**2 + m22 * all_y**2 + m33 * all_z**2
                      + 2 * m12 * all_x * all_y + 2 * m23 * all_y * all_z + 2 * m13 * all_x * all_z)

    # MIL_fitted = 1 / sqrt(w^T M w), only defined where w^T M w > 0
    mil_fitted = np.full(len(directions), np.nan)
    positive = quadratic_form > 0.0
    mil_fitted[positive] = 1.0 / np.sqrt(quadratic_form[positive])

    relative_error = (mil_fitted[valid] - mil[valid]) / mil[valid]
    relative_rms_residual = float(np.sqrt(np.nanmean(relative_error**2)))

    # Closed ellipsoid only if all eigenvalues of M are positive
    is_positive_definite = bool(np.all(np.linalg.eigvalsh(mil_tensor) > 0.0))

    # ------------------------------------------------------------------
    # Log the result
    # ------------------------------------------------------------------
    logger.info(f"Ellipsoid fitted on {n_valid} directions: "
                f"relative RMS residual = {100 * relative_rms_residual:.1f} %")
    logger.debug(f"M =\n{np.array2string(mil_tensor, precision=4)}")
    if relative_rms_residual > residual_warning:
        logger.warning(f"Relative RMS residual {100 * relative_rms_residual:.1f} % > "
                       f"{100 * residual_warning:.0f} %: MIL does not follow an ellipsoid well. "
                       f"Check the MIL rose before using M.")
    if not is_positive_definite:
        logger.warning("Fitted M is not positive definite: the surface is not a closed ellipsoid "
                       "(MIL near infinite in some direction, e.g. plates).")

    return {"mil_tensor": mil_tensor,
            "mil_fitted": mil_fitted,
            "relative_rms_residual": relative_rms_residual,
            "is_positive_definite": is_positive_definite}




# ==============================================================================
# 4 - fit_mil_ellipsoid
# ==============================================================================

def plot_mil_rose_3d(result: dict,
                     title: str = "MIL rose",
                     length_unit: str = "voxels",
                     show_rays: bool = True,
                     max_mil: float | None = None,
                     ellipsoid: dict | None = None) :
    """
    ============================================================================
    PLOT_MIL_ROSE_3D
    Interactive 3D plot of MIL against direction: for every test direction w
    a ray is drawn from the origin to the point MIL(w) * w, so the length of
    each ray equals the MIL in that direction. Rotate, zoom and hover in a
    Jupyter notebook (plotly).
    ============================================================================

    WHAT IS PLOTTED
    ---------------
    For each direction w (unit vector) with a finite MIL(w):
        tip(w) = MIL(w) * w            |tip| = MIL(w)
    and the mirror point -MIL(w) * w, because w and -w give the same test
    lines, hence the same MIL. The cloud of tips is the MIL surface:
        isotropic structure  -> sphere
        ellipsoid model OK   -> ellipsoid
        cubic TPMS           -> bumps along x, y, z or along the diagonals

    PARAMETERS
    ----------
    result : dict
        Output of mean_intercept_length_vs_angle ("directions",
        "polar_angle", "azimuth_angle", "mil").
    title : str, optional
        Figure title.
    length_unit : str, optional
        Unit of MIL, shown on the colour bar and in the hover text.
    show_rays : bool, optional
        Draw a thin line from the origin to each tip (default = True).
    max_mil : float or None, optional
        Directions with MIL above this value are left out (default = None:
        keep all). Useful for plates, where MIL -> infinity parallel to the
        plates and a few huge rays hide everything else.
    ellipsoid : dict or None, optional
        Output of fit_mil_ellipsoid. If given, the fitted surface
        r = MIL_fitted(w) * w is drawn as a transparent surface over the
        points, to judge the fit by eye (default = None).

    RETURNS
    -------
    figure : plotly Figure
        Shown automatically when it is the last line of a notebook cell,
        or with figure.show().

    EXAMPLE
    -------
    >>> result = mean_intercept_length_vs_angle(voxel_grid, x, y, z, seed=0)
    >>> plot_mil_rose_3d(result, title="Gyroid")
    """
    import plotly.graph_objects as go
    # ------------------------------------------------------------------
    # Keep directions with a finite MIL (and below max_mil if given)
    # ------------------------------------------------------------------
    mil = result["mil"]
    keep = np.isfinite(mil)
    if max_mil is not None:
        keep = keep & (mil <= max_mil)

    n_without_crossing = int(np.count_nonzero(~np.isfinite(mil)))
    if n_without_crossing > 0:
        logger.info(f"{n_without_crossing} directions with MIL = nan (no crossing) not plotted.")
    if max_mil is not None:
        n_above_max = int(np.count_nonzero(np.isfinite(mil) & (mil > max_mil)))
        logger.info(f"{n_above_max} directions with MIL > {max_mil} not plotted (max_mil).")
    logger.debug(f"Plotting MIL rose: {int(np.count_nonzero(keep))} directions "
                 f"({2 * int(np.count_nonzero(keep))} points with the mirrored -w).")

    directions = result["directions"][keep]
    mil = mil[keep]
    polar_angle = result["polar_angle"][keep]
    azimuth_angle = result["azimuth_angle"][keep]

    # ------------------------------------------------------------------
    # Tips of the rays: +MIL * w and -MIL * w
    # ------------------------------------------------------------------
    tips_x = mil * directions[:, 0]
    tips_y = mil * directions[:, 1]
    tips_z = mil * directions[:, 2]

    all_tips_x = np.concatenate([tips_x, -tips_x])
    all_tips_y = np.concatenate([tips_y, -tips_y])
    all_tips_z = np.concatenate([tips_z, -tips_z])
    all_mil = np.concatenate([mil, mil])

    # Angles of the mirrored direction -w: theta -> 180 - theta, phi -> phi + 180
    all_polar_angle = np.concatenate([polar_angle, 180.0 - polar_angle])
    all_azimuth_angle = np.concatenate([azimuth_angle, (azimuth_angle + 180.0) % 360.0])

    figure = go.Figure()

    # ------------------------------------------------------------------
    # Rays from the origin to each tip, all in one trace
    # ------------------------------------------------------------------
    if show_rays:
        # Each ray is: origin, tip, None (None breaks the line between rays)
        n_rays = all_tips_x.size
        rays_x = np.column_stack([np.zeros(n_rays), all_tips_x, np.full(n_rays, np.nan)]).ravel()
        rays_y = np.column_stack([np.zeros(n_rays), all_tips_y, np.full(n_rays, np.nan)]).ravel()
        rays_z = np.column_stack([np.zeros(n_rays), all_tips_z, np.full(n_rays, np.nan)]).ravel()
        figure.add_trace(go.Scatter3d(x=rays_x, y=rays_y, z=rays_z,
                                      mode="lines",
                                      line=dict(color="rgba(90, 90, 90, 0.45)", width=1.5),
                                      hoverinfo="skip",
                                      showlegend=False))

    # ------------------------------------------------------------------
    # Tips, coloured by MIL, with hover text
    # ------------------------------------------------------------------
    hover_text = [f"θ = {theta:.1f}°<br>φ = {phi:.1f}°<br>MIL = {value:.3g} {length_unit}"
                  for theta, phi, value in zip(all_polar_angle, all_azimuth_angle, all_mil)]
    figure.add_trace(go.Scatter3d(x=all_tips_x, y=all_tips_y, z=all_tips_z,
                                  mode="markers",
                                  marker=dict(size=4,
                                              color=all_mil,
                                              colorscale="Blues",
                                              line=dict(color="rgb(80, 80, 80)", width=0.5),
                                              colorbar=dict(title=f"MIL ({length_unit})")),
                                  text=hover_text,
                                  hoverinfo="text",
                                  showlegend=False))

    # ------------------------------------------------------------------
    # Fitted ellipsoid (optional): r(w) = MIL_fitted(w) * w on a theta/phi grid
    # ------------------------------------------------------------------
    if ellipsoid is not None:
        mil_tensor = ellipsoid["mil_tensor"]
        # Full sphere of directions: theta 0..180 deg, phi 0..360 deg
        theta_grid, phi_grid = np.meshgrid(np.linspace(0.0, np.pi, 61),
                                           np.linspace(0.0, 2.0 * np.pi, 121),
                                           indexing="ij")
        grid_x = np.sin(theta_grid) * np.cos(phi_grid)
        grid_y = np.sin(theta_grid) * np.sin(phi_grid)
        grid_z = np.cos(theta_grid)
        # w^T M w at every grid direction, written out with the 6 terms
        quadratic_form = (mil_tensor[0, 0] * grid_x**2 + mil_tensor[1, 1] * grid_y**2 + mil_tensor[2, 2] * grid_z**2
                          + 2 * mil_tensor[0, 1] * grid_x * grid_y
                          + 2 * mil_tensor[1, 2] * grid_y * grid_z
                          + 2 * mil_tensor[0, 2] * grid_x * grid_z)
        # MIL_fitted = 1 / sqrt(w^T M w); nan (hole in the surface) where w^T M w <= 0
        mil_on_grid = np.full(quadratic_form.shape, np.nan)
        positive = quadratic_form > 0.0
        mil_on_grid[positive] = 1.0 / np.sqrt(quadratic_form[positive])
        # Cut the surface where it goes beyond the largest plotted MIL (open surface for plates)
        mil_on_grid[mil_on_grid > 1.05 * np.max(all_mil)] = np.nan

        figure.add_trace(go.Surface(x=mil_on_grid * grid_x,
                                    y=mil_on_grid * grid_y,
                                    z=mil_on_grid * grid_z,
                                    surfacecolor=mil_on_grid,
                                    colorscale="Oranges",
                                    showscale=False,
                                    opacity=0.35,
                                    hoverinfo="skip",
                                    name="fitted ellipsoid"))
        logger.debug("Fitted ellipsoid added to the MIL rose.")

    # ------------------------------------------------------------------
    # Equal scale on x, y, z, otherwise a sphere would look like an ellipsoid
    # ------------------------------------------------------------------
    largest = 1.05 * np.max(np.abs(np.concatenate([all_tips_x, all_tips_y, all_tips_z])))
    axis_range = [-largest, largest]
    figure.update_layout(title=title,
                         template="plotly_white",
                         scene=dict(xaxis=dict(title="x", range=axis_range),
                                    yaxis=dict(title="y", range=axis_range),
                                    zaxis=dict(title="z", range=axis_range),
                                    aspectmode="cube"),
                         width=700, height=650,
                         margin=dict(l=0, r=0, t=40, b=0))
    return figure