# triply: design, meshing, simulation and CT analysis of TPMS structures
# Copyright (C) 2026, Empa, Laboratory for High Performance Ceramics (201), Corentin Foucher
# SPDX-License-Identifier: MIT

"""
Back-end functions of the Simulation page (app/pages/4_Simulation.py):
STL -> tetrahedral mesh (fTetWild) -> ABAQUS input file -> ABAQUS solve.

The three *_job functions are long-running. The page runs them in a
background thread with app.components.jobs.start_job(), which passes them a
`log` callable as first argument; whatever they log is shown live on the page
by app.components.jobs.render_job_status(). render_load_case_form() is a plain
Streamlit form for the static load case.
"""
import streamlit as st
import time
from pathlib import Path
from typing import Callable, List, Optional
from triply import TET_mesh_tools, abaqus_tools

from app.components.jobs import Job


"""
#=====================================================================================================================
0 - (reserved)
1 - mesh_job                     (fTetWild: STL -> tet mesh .inp)
2 - create_abaqus_job            (pybaqus script: tet mesh -> Job-<name>.inp)
3a - _clear_previous_job_files   (helper of run_abaqus_job)
3 - run_abaqus_job               (ABAQUS solve)
4 - render_load_case_form        (Streamlit form -> extra_args of create_simulation)
#=====================================================================================================================
"""


# =====================================================================
# 1) mesh_job
# =====================================================================
def mesh_job(log: Callable[[str], None],
                stl_dir: str,
                file_name: str,
                mesh_output_name: str,
                ftetwild_path: str,
                epsilon: float,
                edge_length: float,
                CPU_cores: int):
    """
    ============================================================================
    1) MESH_JOB
    Meshes an STL into a tetrahedral mesh with fTetWild
    (TET_mesh_tools.mesh_an_STL), reading <stl_dir>/<file_name>.stl and
    writing <stl_dir>/<mesh_output_name>.inp.
    Runs synchronously: the Simulation page runs it in a background thread
    through app.components.jobs.start_job(), which passes `log` and turns an
    exception into a job with status "error".
    ============================================================================

    PARAMETERS
    ----------
    log : callable
        Function to call with progress messages (e.g. `log("message")`).
        Passed automatically by start_job.
    stl_dir : str
        Directory containing the STL file to mesh; the mesh is written there too.
    file_name : str
        Name of the STL file (without extension) to mesh.
    mesh_output_name : str
        Name of the output mesh (without extension) - written as
        <stl_dir>/<mesh_output_name>.inp.
    ftetwild_path : str
        Path to the fTetWild executable.
    epsilon : float
        Envelope size, relative to the bounding-box diagonal (fTetWild --epsr).
    edge_length : float
        Target edge length, relative to the bounding-box diagonal
        (fTetWild --lr).
    CPU_cores : int
        Number of CPU cores to use for meshing (fTetWild --max-threads).

    RETURNS
    -------
    bool
        Always True: reaching the end means fTetWild finished without error.

    RAISES
    ------
    subprocess.CalledProcessError
        If fTetWild exits with an error (raised by mesh_an_STL).
    """
    log(f"Meshing {file_name}.stl with fTetWild (this can take a while)...")
    TET_mesh_tools.mesh_an_STL(
        input_path=stl_dir + "/",
        output_path=stl_dir + "/",
        file_name=file_name,
        output_name=mesh_output_name,
        FtetWild_path=ftetwild_path,
        epsilon=epsilon,
        edge_length=edge_length,
        CPU_cores=int(CPU_cores),
    )
    log(f"fTetWild meshing finished - {mesh_output_name}.inp written.")
    return True



# =====================================================================
# 2) create_abaqus_job
# =====================================================================
def create_abaqus_job(log: Callable[[str], None],
                mesh_dir: str,
                mesh_name: str,
                output_name: str,
                script_dir: str,
                script_name: str,
                young_modulus: float,
                poisson_ratio: float,
                density: float,
                quadratic_tets: int = 0,
                extra_args: Optional[dict] = None):
    """
    ============================================================================
    2) CREATE_ABAQUS_JOB
    Creates an ABAQUS simulation input file (Job-<output_name>.inp) from an
    existing tetrahedral mesh, by running the selected pybaqus script headless
    (abaqus_tools.create_simulation). Logs the load case before, and a hint
    on where to look if it fails.
    ============================================================================

    PARAMETERS
    ----------
    log : Callable[[str], None]
        Function to call with progress messages. Passed automatically by
        app.components.jobs.start_job.
    mesh_dir : str
        Folder containing the tetrahedral mesh <mesh_name>.inp.
    mesh_name : str
        Name of the mesh file without the .inp extension.
    output_name : str
        Model/job name without the "Job-" prefix, e.g. "my_tpms-static". The
        script writes Job-<output_name>.inp and
        generate_sim_logger_<output_name>.txt.
    script_dir : str
        Folder holding the copied pybaqus script. ABAQUS runs there, so the
        simulation files and logs are written into it.
    script_name : str
        File name of the pybaqus script, WITH the .py extension, e.g.
        "generate_static_sim.py" or "generate_frequency_sim.py".
    young_modulus : float
        Young's modulus, in the unit system of the mesh (MPa for N-mm-t-s).
    poisson_ratio : float
        Poisson's ratio.
    density : float
        Density, in the same unit system (t/mm^3 for N-mm-t-s).
    quadratic_tets : int, optional
        0 (default): linear 4-node tets (C3D4); 1: quadratic 10-node tets (C3D10).
    extra_args : dict or None, optional
        Simulation-specific key=value arguments forwarded on the ABAQUS
        command line, e.g. from render_load_case_form() for the static case
        (axis, load, compression, tol_frac). Default = None.

    RETURNS
    -------
    bool
        The result of abaqus_tools.create_simulation: True if the script
        reported success, False otherwise (the reason is then usually in
        generate_sim_logger_<output_name>.txt).

    RAISES
    ------
    subprocess.CalledProcessError
        If the abaqus command itself exits with an error (from create_simulation).
    """
    log("Invoking ABAQUS (noGUI) to create the simulation input...")
    if extra_args:
        log("Load case: " + ", ".join(f"{k}={v}" for k, v in extra_args.items()))
    ok = abaqus_tools.create_simulation(
        input_path=mesh_dir,
        input_name=mesh_name,
        output_path=str(script_dir),
        output_name=output_name,
        script_name=script_name,
        young_modulus=young_modulus,
        poisson_ratio=poisson_ratio,
        density=density,
        quadratic_tets=quadratic_tets,
        extra_args=extra_args,
    )
    log(f"create_simulation() returned: {ok}")
    if not ok:
        log(
            "Check generate_sim_logger_"
            f"{output_name}.txt in the simulation folder for the reason - for the "
            "static case it is usually an empty face node set (raise the face "
            "tolerance) or a mesh that has no flat ends along the load axis."
        )
    return ok


# =====================================================================
# 3a) _clear_previous_job_files
# =====================================================================
def _clear_previous_job_files(run_dir: Path, file_name: str, log: Callable[[str], None]) -> bool:
    """
    ============================================================================
    3a) _CLEAR_PREVIOUS_JOB_FILES
    Deletes any leftover Job-<file_name>.* files (.odb, .sta, .msg, .lck,
    .log, ...) from a previous run in run_dir.
    WHY: when those files are already present, ABAQUS itself prompts
    "Old job files exist. Overwrite? (y/n):" on stdin before it will start.
    abaqus_tools.run_simulation() launches it via subprocess.run() with no
    stdin attached, so that prompt just hangs forever instead of failing or
    proceeding. Clearing old outputs before each run means there's nothing
    left for ABAQUS to ask about.
    ============================================================================

    PARAMETERS
    ----------
    run_dir : Path or str
        Folder where the ABAQUS job runs.
    file_name : str
        Job name without the "Job-" prefix.
    log : Callable[[str], None]
        Function to call with messages: which files were removed, and which
        could not be.

    RETURNS
    -------
    bool
        True if run_dir ended up clear of Job-<file_name>.* files. False if
        one or more couldn't be removed - typically the .odb, still locked
        by an earlier ABAQUS process (or a CAE/viewer session) that's still
        running against it.
    """
    run_dir = Path(run_dir)
    removed = []
    stuck = []
    for f in run_dir.glob(f"Job-{file_name}.*"):
        try:
            f.unlink()
            removed.append(f.name)
        except OSError as e:
            stuck.append(f.name)
            log(f"Could not remove old job file {f.name}: {e}")
    if removed:
        log(f"Removed leftover job files from a previous run: {', '.join(removed)}")
    if stuck:
        log(
            "The following files from a previous run are still locked and "
            f"could not be removed: {', '.join(stuck)}. This usually means an "
            "earlier ABAQUS process for this job is still running, or an "
            "ABAQUS CAE/viewer session still has the .odb open - close it "
            "and try again."
        )
    return not stuck



# =====================================================================
# 3) run_abaqus_job
# =====================================================================
def run_abaqus_job(log: Callable[[str], None],
                file_name: str,
                sim_dir: str,
                cpus: int = 1,
                max_wait_time: int = 600):
    """
    ============================================================================
    3) RUN_ABAQUS_JOB
    Runs the ABAQUS solve for a simulation input already created by
    create_abaqus_job, then waits for it to complete:
        1) clears old Job-<file_name>.* files from <sim_dir>/run
           (_clear_previous_job_files), returns False if some are locked
        2) abaqus_tools.run_simulation: copies Job-<file_name>.inp from sim_dir
           to <sim_dir>/run, starts the solve there, waits for it to start
        3) abaqus_tools.wait_for_simulation_completed: waits for it to finish
    The solve runs in the "run" subfolder because run_simulation copies the
    .inp from input_path to output_path, and shutil.copyfile raises
    SameFileError if those are the same folder. The .odb and log files
    therefore end up in <sim_dir>/run.
    ============================================================================

    PARAMETERS
    ----------
    log : Callable[[str], None]
        Function to call with progress messages. Passed automatically by
        app.components.jobs.start_job.
    file_name : str
        Job name without the "Job-" prefix: the input is Job-<file_name>.inp.
    sim_dir : str
        Folder holding Job-<file_name>.inp (written by create_abaqus_job).
    cpus : int, optional
        Number of CPU cores to use for the ABAQUS solve. Default = 1.
    max_wait_time : int, optional
        Max seconds to wait, applied separately to the "job started" wait
        and to the "job completed" wait. Default = 600.

    RETURNS
    -------
    bool
        True if the job started AND completed successfully. False if old job
        files could not be removed, if the job did not start, or if it did
        not complete within max_wait_time.
    """
    sim_dir = Path(sim_dir)
    run_dir = sim_dir / "run"
    run_dir.mkdir(parents=True, exist_ok=True)

    # avoid ABAQUS's interactive "Old job files exist. Overwrite? (y/n):"
    # prompt, which would otherwise hang the background thread forever.
    cleared = _clear_previous_job_files(run_dir, file_name, log)
    if not cleared:
        log("Aborting - a previous job's files are still locked (see message above).")
        return False
    
    log(f"Starting ABAQUS job for {file_name}...")
    started = abaqus_tools.run_simulation(
        input_path=str(sim_dir),
        output_path=str(run_dir),
        file_name=file_name,
        cpus=cpus,
        max_wait_time=max_wait_time,
    )
    if not started:
        log("run_simulation() returned False - job did not start.")
        return False
    log("ABAQUS job started - waiting for it to complete...")

    completed = abaqus_tools.wait_for_simulation_completed(
        ODB_path=str(run_dir),
        file_name=file_name,
        max_wait_time=max_wait_time,
    )
    log(f"wait_for_simulation_completed() returned: {completed}")
    return completed


# =====================================================================
# 4) render_load_case_form
# =====================================================================
def render_load_case_form(key: str = "static") -> dict:
    """
    ============================================================================
    4) RENDER_LOAD_CASE_FORM
    Draws the inputs that define the uniaxial load case and returns them in
    the shape create_simulation(extra_args=...) expects.
    ============================================================================

    PARAMETERS
    ----------
    key : str, optional
        Unique suffix for the widget keys (default "static").

    RETURNS
    -------
    dict with keys
        "axis"        : "x" | "y" | "z"
        "load"        : float, total force over the loaded face
        "compression" : int, 1 = push, 0 = pull (int rather than bool so it
                        survives the trip through the Abaqus command line)
        "tol_frac"    : float, face slab thickness / axial extent

    NOTES
    -----
    The units are whatever the STL is in - the material properties entered
    above use the same convention, so with mm + MPa the load is in N.
    """
    axis = st.selectbox(
        "Load axis",
        ["z", "x", "y"],
        key=f"{key}_axis",
        help=(
            "The structure is gripped on its two extreme faces along this axis "
            "and loaded along it. Stiffness is measured in this direction."
        ),
    )
    c1, c2 = st.columns(2)
    load = c1.number_input(
        "Total load",
        value=100.0,
        format="%.4f",
        key=f"{key}_load",
        help=(
            "Total force spread over every node of the loaded face. Same unit "
            "system as the Young's modulus above (mm + MPa -> N)."
        ),
    )
    sense = c2.radio(
        "Direction",
        ["Compression", "Tension"],
        key=f"{key}_sense",
        horizontal=True,
        help="Compression pushes the top face into the structure; tension pulls it away.",
    )
    tol_pct = st.slider(
        "Face thickness (% of height)",
        min_value=0.1,
        max_value=10.0,
        value=1.0,
        step=0.1,
        key=f"{key}_tol",
        help=(
            "How thick a slab at each end counts as 'the face'. Too tight and "
            "the node set comes out empty and ABAQUS errors out; too loose and "
            "you end up clamping a real chunk of the structure. 1 % suits a "
            "flat-cut block; raise it if the ends are rough or wavy."
        ),
    )
    non_liner_geometry = st.toggle(
        "Non-linear geometry",
        help="Account for large deformations non-linearity.",
    )
    return {
        "axis": axis,
        "load": float(load),
        "compression": 1 if sense == "Compression" else 0,
        "tol_frac": tol_pct / 100.0,
        "non_linear_geometry": 1 if non_liner_geometry else 0,
    }