import streamlit as st


"""
#=====================================================================================================================
1 - generate_TPMS_doc   -> pages/1_Generate_TPMS.py
2 - prepare_print_doc   -> pages/2_Prepare_Print.py
3 - simulation_doc      -> pages/2_Simulation.py
4 - CT_analysis_doc     -> pages/3_CT_Analysis.py
#=====================================================================================================================
Every function in here has the same shape: a collapsed st.expander holding
a short walkthrough of that page's pipeline (one column per step), then an
"Additional features" row for the knobs that sit outside the main path.
Purely educational - no state, no side effects - and cached so they don't
re-run on every widget interaction.
"""


# =====================================================================
# 1) generate_TPMS_doc
# =====================================================================
@st.cache_data(show_spinner=False)
def generate_TPMS_doc():
    """
    ============================================================================
    1) GENERATE_TPMS_DOC
    Full-width, purely educational explainer of the generation pipeline:
    implicit field -> density field -> marching cubes -> mesh. Folded into
    an expander (collapsed by default) so it stays out of the way once you
    know how it works. No state, no side effects - safe to call every rerun.
    ============================================================================
    """
    with st.expander(
        "How this works (implicit field -> density field -> marching cubes)",
        expanded=False,
    ):
        st.subheader("How TPMS generation works")
        st.markdown(
            "Every TPMS on this page is built the same way, in three steps. "
            "Each one maps to a section of the control panel below."
        )
        step1, step2, step3 = st.columns(3)

        with step1:
            st.markdown("**1. Implicit field**")
            st.markdown(
                "A formula `F(x, y, z)` is evaluated at every point of the 3D "
                "grid (set under *Grid parameters*). For the Gyroid, for "
                "example:"
            )
            st.latex(
                r"F = \sin\!\frac{2\pi x}{p_x}\cos\!\frac{2\pi y}{p_y}"
                r" + \sin\!\frac{2\pi y}{p_y}\cos\!\frac{2\pi z}{p_z}"
                r" + \sin\!\frac{2\pi z}{p_z}\cos\!\frac{2\pi x}{p_x}"
            )
            st.markdown(
                "This is the **implicit field**: a smooth, periodic wave "
                "filling the whole grid."
            )

        with step2:
            st.markdown("**2. Density field**")
            st.markdown(
                "The **Density Field** turns the implicit field into a solid shape. " \
                "There are three modes to turn the implicit field into a solid:"
            )
            st.markdown(
                "- **Signed / Signed inverse**: every point in space where the implicit field is above (or below) the given **threshold** is solid\n"
                "- **Distance**: Following the **threshold** in space defines an iso-surface. This mode measures the real physical distance to this surface to form a wall of uniform **thickness**\n"
                "- **Band**: keep a shell where `|F|` stays below a thickness. It acts as a fast approximation of the distance field when **threshold** = 0.0\n"
            )
            st.markdown(
                "Whichever mode is picked, the result is one number per "
                "voxel: positive = solid, negative = empty. That's the "
                "**density field**."
            )

        with step3:
            st.markdown("**3. Marching cubes -> mesh**")
            st.markdown(
                "The density field is still just numbers on a grid - not a "
                "shape a slicer or CAD tool can use. **Marching cubes** "
                "walks the grid one small cube at a "
                "time, checks which corners are solid and which are empty, "
                "and drops a little triangle patch wherever the density "
                "field crosses zero between them."
            )
            st.markdown(
                "Stitch every one of those triangle patches together and "
                "you get a watertight triangular **mesh** (vertices + "
                "faces) - shown in the *Mesh preview* and, after "
                "simplification/smoothing below, exported as your `.stl`."
            )

        st.caption(
            "Implicit field -> density field -> marching cubes. "
            "Everything below is just knobs on those three steps."
        )
        st.divider()
        st.subheader("Additional features")
        st.markdown(
            "Beyond the three-step pipeline above, this page has a few extra "
            "knobs for less common cases:"
        )
        feat1, feat2, feat3 = st.columns(3)

        with feat1:
            st.markdown("**Baseplates**")
            st.markdown(
                "*Baseplate thickness* adds solid flat slabs on top and/or "
                "bottom of the structure.\n"
                "They do not affect the implicit field, but are applied to the density field "
            )


        with feat2:
            st.markdown("**Combine**")
            st.markdown(
                "**Combine with existing geometry** intersects, "
                "unions or subtracts an external shape (an `.stl` mesh or "
                "a `.npy` matrix) with the density field, e.g. to gyroid-"
                "fill an existing part."
            )

        with feat3:
            st.markdown("**Mesh cleanup & export**")
            st.markdown(
                "*Mesh parameters* auto-smooth, simplify and optionally cap "
                "the face count of the mesh coming out of marching cubes, "
                "so it stays light enough for a slicer or CAD tool. The "
                "save section then exports the mesh as `.stl`, or the raw "
                "implicit/thickness fields as `.npy` for reuse elsewhere "
                "(including feeding them back in via *Import from file*)."
            )



# =====================================================================
# 2) prepare_print_doc
# =====================================================================
@st.cache_data(show_spinner=False)
def prepare_print_doc():
    """
    ============================================================================
    2) PREPARE_PRINT_DOC
    Full-width, purely educational explainer of the print-preparation
    pipeline: STL -> occupancy matrix -> overhang labels -> orientation
    search. Folded into an expander (collapsed by default) so it stays out
    of the way once you know how it works. No state, no side effects -
    safe to call every rerun.
    ============================================================================
    """
    with st.expander(
        "How this works (voxelize -> overhang labels -> orientation search)",
        expanded=False,
    ):
        st.subheader("How print preparation works")
        st.markdown(
            "This page answers one question: **which way up should this part "
            "be printed?** It gets there in three steps, each mapping to a "
            "section of the control panel below."
        )
        step1, step2, step3 = st.columns(3)

        with step1:
            st.markdown("**1. Voxelize the STL**")
            st.markdown(
                "An `.stl` is only a *surface* made of a bag of triangles with no "
                "notion of inside or outside. "
            )
            st.markdown(
                "So the mesh is first sampled onto a regular grid at the "
                "chosen *Grid resolution*, giving one value per voxel: solid "
                "inside the part, empty outside. "
            )
            st.markdown(
                "The result is a 3D occupancy matrix, which is used in the next step " \
                "to judge which voxels are overhangs and which are bridges."
            )
            st.caption(
                "Cost grows with the cube of the resolution, so start low "
                "(~64) while you find the right thresholds."
            )

        with step2:
            st.markdown("**2. Overhang labels**")
            st.markdown(
                "Each solid voxel is then judged on what sits underneath it, "
                "using two thresholds:"
            )
            st.markdown(
                "- **Overhang angle**: a surface tilted more than this, has too little " \
                "material below it to print on. -> Lower = stricter\n"\
                "Voxels that do not meet this angle are labelled overhangs\n"
                "- **Bridge length**: an unsupported span *narrower* than "
                "this is something the printer can bridge across, so it is "
                "labelled a bridge rather than an overhang\n"
            )
            st.markdown(
                "Lastly, for every voxel marked as an overhang, the algorithm looks down along z-axis."\
                "If no solid voxel is found below, this voxel could be supported. "\
                "Support voxels are dropped down from the overhang to the bottom of the grid."\
                )
            st.markdown(
                " The result is one label per voxel - **empty, "
                "solid, overhang, bridge, support**."
            )

        with step3:
            st.markdown("**3. Orientation search**")
            st.markdown(
                "Rotating the part changes which of its faces are overhangs, "
                "and there is no closed form for the best angle - so it is "
                "searched by brute force."
            )
            st.markdown(
                "**Complexity** is the number of candidate orientations "
                "sampled around the part. Each candidate is re-labelled with "
                "step 2 and scored on how much overhang it has "
                "; the cheapest one wins. Higher complexity = finer "
                "search, proportionally slower."
            )
            st.markdown(
                "The winning rotation is applied to the mesh vertices as "
                "well, so the *slice view* and the *solid preview* of the "
                "best orientation are showing the same thing."
            )

        st.caption(
            "Overall, this method can not predict what happens if you use complex supports in your slicer (aka. tree style supports). "\
            "However, it is able to detect un-printable regions **inside** the lattice (which no support would ever be able to cover), show them to you and propose a rotation that minimizes them."\
            "The exported mesh can then be used in your slicer to generate supports and print the part optimally."
        )
        st.divider()
        st.subheader("Additional features")
        st.markdown(
            "Beyond the three steps above, a few things are worth knowing "
            "before trusting the answer:"
        )
        feat1, feat2, feat3 = st.columns(3)

        with feat1:
            st.markdown("**Slice views**")
            st.markdown(
                "The 2D slice view is the only reliable way to inspect a "
                "lattice: in the 3D preview the outer shell hides every "
                "overhang inside the part. Pick the slice axis and scrub "
                "through the stack to see where the labels actually land."
            )

        with feat2:
            st.markdown("**Units and thresholds**")
            st.markdown(
                "The bridge length is in the STL's own length unit (mm if "
                "the file was exported in mm) - the angle is in degrees. "
            )

        with feat3:
            st.markdown("**What this page does not do**")
            st.markdown(
                "No slicing, no scaling, and the support voxels are only a "
                "*preview* - they are not exported in the stl.  "
                "What *is* exported is the mesh already rotated into the "
                "winning orientation, so the slicer is only left with "
                "building the real supports."
            )


# =====================================================================
# 3) simulation_doc
# =====================================================================
@st.cache_data(show_spinner=False)
def simulation_doc():
    """
    ============================================================================
    3) SIMULATION_DOC
    Full-width, purely educational explainer of the simulation pipeline:
    STL -> tetrahedral mesh -> ABAQUS input deck -> solve -> field export.
    Folded into an expander (collapsed by default) so it stays out of the
    way once you know how it works. No state, no side effects - safe to
    call every rerun.
    ============================================================================
    """
    with st.expander(
        "How this works (STL -> tet mesh -> ABAQUS input -> results)",
        expanded=False,
    ):
        st.subheader("How the simulation pipeline works")
        st.markdown(
            "The four numbered sections below are one chain: each step eats "
            "the file the previous one wrote, all of them in the folder next "
            "to your `.stl`. Steps 1 and 3 call external programs and can "
            "take a long time, so they run in a background thread - the live "
            "log is what you watch."
        )
        step1, step2, step3, step4 = st.columns(4)

        with step1:
            st.markdown("**1. Tetrahedral meshing**")
            st.markdown(
                "An STL is a hollow shell; a solver needs *volume* elements. "
                "Here we use **fTetWild** to fill the shell with tetrahedra."
            )
            st.markdown("You have to install **fTetWild** first: https://wildmeshing.github.io/ftetwild/"\
                        "Then set the path to its executable in the box below.")
            st.markdown(
                "**Epsilon** is the envelope the tet mesh is allowed to "
                "deviate from the stl surface. Smaller "
                "means a more faithful mesh."
            )
            st.markdown(
                "**Edge length** is the target edge length of the tetrahedra "
                "(relative to the bounding-box diagonal). Smaller means "
                "more elements."
            )
            st.markdown(
                "Output is converted straight to `<name>.inp`; the "
                "intermediate `.msh` and fTetWild scratch files are deleted."
            )

        with step2:
            st.markdown("**2. create ABAQUS simulation**")
            st.markdown(
                "A generator script is run through ABAQUS in no-GUI mode. It "
                "imports the tet mesh, attaches the **material** (Young's "
                "modulus, Poisson's ratio, density), builds the analysis "
                "step and the boundary conditions, and writes a solver-ready "
                "`Job-<name>.inp` into `<name>_sim/`."
            )
            st.markdown(
                "You must have ABAQUS installed and licensed for this step to work. The script is " \
                "written in Python and uses the ABAQUS Scripting Interface (ASI) to create the input file."
            )

        with step3:
            st.markdown("**3. Run the solve**")
            st.markdown(
                "ABAQUS is launched on that input deck in `<name>_sim/run/`, "
                "writing an `.odb` result database. *CPU cores* is passed "
                "straight to the solver."
            )
            st.markdown(
                "Files from a previous run of the same job are cleared first, "
                "so a re-run doesn't stall on a lock file."
            )

        with step4:
            st.markdown("**4. Extract results**")
            st.markdown(
                "The `.odb` is reopened and the displacement field is pulled "
                "at the top face node set - magnitude plus the three "
                "components - into a `.csv`, then drawn as one boxplot per "
                "component on a shared value axis."
            )
            st.markdown(
                "Divide the load you applied by the displacement you read "
                "here to get the structure's stiffness along the load axis. "
                "Only defined for the static case - a frequency run has no "
                "field export."
            )

        st.caption(
            "Surface mesh -> volume mesh -> input deck -> solve -> field "
            "export. Each section only needs the one above it to have run."
        )
        st.divider()
        st.subheader("Additional features")
        st.markdown(
            "Three things decide whether the numbers coming out mean "
            "anything:"
        )
        feat1, feat2, feat3 = st.columns(3)

        with feat1:
            st.markdown("**Load case preview**")
            st.markdown(
                "For the static case the second preview marks the loaded "
                "face, the supported face and the two pinned nodes, and "
                "prints their coordinates. It is a cheap sanity check before "
                "a long solve."
            )

        with feat2:
            st.markdown("**Boundary conditions**")
            st.markdown("** Static case **")
            st.markdown(
                "The bottom face is held **only** along the load axis - a "
                "roller - so the part stays free to expand sideways and you "
                "measure the lattice's own stiffness rather than a "
                "platen-confined one. Two single nodes on that face are "
                "pinned in-plane to remove the leftover rigid-body motion."
            )
            st.markdown("** Frequency case **")
            st.markdown("No boundary conditions are applied, so the solver finds the " \
            "natural vibration modes of the lattice.")

        with feat3:
            st.markdown("**Units**")
            st.markdown(
                "Nothing here checks or converts units. The material properties and "
                "the load are in whatever length unit the STL was exported "
                "in - with **mm** that means MPa for the modulus, N for the "
                "load, and tonnes/mm3 for the density (hence the `3.9e-09` "
                "default). Mixing conventions gives results that are wrong "
                "by orders of magnitude, silently."
            )


# =====================================================================
# 4) CT_analysis_doc
# =====================================================================
@st.cache_data(show_spinner=False)
def CT_analysis_doc():
    """
    ============================================================================
    4) CT_ANALYSIS_DOC
    Full-width, purely educational explainer of the CT pipeline: image
    stack -> .mhd volume -> segmentation pipeline -> marching cubes ->
    mesh. Folded into an expander (collapsed by default) so it stays out of
    the way once you know how it works. No state, no side effects - safe to
    call every rerun.
    ============================================================================
    """
    with st.expander(
        "How this works (slices -> volume -> mask -> mesh)",
        expanded=False,
    ):
        st.subheader("How CT analysis works")
        st.markdown(
            "A scan arrives as a folder of 2D images. This page stacks that "
            "folder into one volume, segments the material out of it, and "
            "turns the result into a mesh - three steps, each a section "
            "below."
        )
        step1, step2, step3 = st.columns(3)

        with step1:
            st.markdown("**1. Convert slices to a .mhd volume**")
            st.markdown(
                " Slices are saved as a stack of images (JPG,TIFF,DICOM) in a folder. " \
                " The first step is to read them all: they must be saved in one folder "
                " and numbered in ascending order.\n" 
                " A single `.mhd` volume (a small text header plus one raw "
                "binary block), is then created so the rest of the page can treat the scan "
                "as one 3D array instead of a thousand files."
            )
            st.markdown(
                "**Voxel spacing**: JPG and TIFF "
                "carry no spacing metadata, so you have to type the "
                "mm/voxel yourself, while DICOM tags are read "
                "automatically. Everything downstream - mesh dimensions, "
                "print sizes, stiffness - inherits that number."
            )
            st.markdown(
                "*Downscale to 8-bit* normalises the greyvalues into "
                "`uint8`, saving a lot of memory."
            )

        with step2:
            st.markdown("**2. Segmentation pipeline**")
            st.markdown(
                "The loaded volume is still just greyvalues, not geometry. "
                "The pipeline is an **ordered list** of operations, each one "
                "running on the output of the one before it, so you build up "
                "a mask step by step:"
            )
            st.markdown(
                "- **Threshold**: to a binary mask, or keep a range - this "
                "is what separates material from air\n"
                "- **Erode / Dilate**: shrink or grow the mask to kill "
                "speckle and close pinholes\n"
                "- **Connected component**: keep only the region touching a "
                "seed point, dropping everything detached\n"
                "- **Find islands / holes**: isolate the small blobs and "
                "voids, ranked by size, to see what the mask still gets "
                "wrong\n"
                "- **Crop / Apply mask**: trim the volume, or blank it "
                "outside a second `.mhd`\n"
            )
            st.markdown(
                "Steps can be reordered and removed; only the mid-slice "
                "preview is recomputed while you experiment."
            )
        
        with step3:
            st.markdown("**3. Marching cubes -> mesh**")
            st.markdown(
                "Same extraction as on the *Generate TPMS* page: "
                "**marching cubes** walks the volume **X** small cube at a "
                "time and drops a triangle patch wherever the values cross "
                "the **iso level** - the midpoint of the range, for a binary "
                "mask.\n"
                "**X** is the amount of steps the algorithm takes along each axis of the volume. Higher -> less triangles, faster."
            )
            st.markdown(
                "The real voxel spacing is handed to it as coordinates, so "
                "anisotropic voxels come out at their true proportions "
                "rather than stretched. **Step size** above 1 samples every "
                "n-th voxel: faster, coarser."
            )
            st.markdown(
                "The exported `.stl` is an ordinary mesh - it feeds straight "
                "into *Prepare print* or *Simulation*."
            )

        st.caption(
            "Stack -> volume -> mask -> mesh. The mask is where all the "
            "judgement lives; the mesh step is mechanical."
        )
        st.divider()
        st.subheader("Additional features")
        st.markdown(
            "Around the main path there are the tools for choosing "
            "thresholds and for getting results back out:"
        )
        feat1, feat2, feat3 = st.columns(3)

        with feat1:
            st.markdown("**Greyvalue histogram**")
            st.markdown(
                "A histogram of the whole volume."
            )

        with feat2:
            st.markdown("**Interactive desktop viewer**")
            st.markdown(
                "Scroll-to-scrub and click-to-inspect don't survive "
                "Streamlit's rerun-on-every-interaction model, so the full "
                "viewer stays a separate window with its own brush, rainbow "
                "and histogram tooling. The *lightweight* option opens just "
                "a slice slider - much faster on large volumes."
            )

        with feat3:
            st.markdown("**Exports**")
            st.markdown(
                " - The processed volume can be written back out as `.mhd` with "
                "its spacing, origin and direction preserved - so it can be "
                "reloaded later, or used as the mask input of another run.\n" 
                " - The extracted mesh can be saved as `.stl`."
            )
