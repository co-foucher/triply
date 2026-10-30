# ============================================================================
# ABAQUS SIMULATION SETUP SCRIPT - LINEAR ELASTIC UNIAXIAL LOAD CASE
#
# Reads the tet mesh produced by fTetWild (<model>.inp), applies a linear
# elastic material, grips the two end faces along a user-chosen axis and
# pushes (or pulls) on the top one with a user-chosen total force. The point
# of the load case is to make the structure's axial stiffness measurable in
# that direction.
#
# BOUNDARY CONDITIONS (coupling to reference points - free lateral expansion)
# --------------------------------------------------------------------------
# Same set-up as the hand-made CAE model (see abaqus.rpy in this folder):
# each end face is driven by one reference point (RP) through a KINEMATIC
# coupling, and every BC / load is applied to the RPs, never to mesh nodes.
#
#   Coupling-Bottom : RP-Bottom  <-> Set-Bottom   (U<axis>, UR1, UR2, UR3 coupled)
#   Coupling-Top    : RP-Top     <-> Set-Top      (U<axis>, UR1, UR2, UR3 coupled)
#                     Only the axial translation is coupled, the two in-plane
#                     translations are left OFF, so each face stays flat (it
#                     moves as a rigid plane along the axis and can only tilt
#                     through the RP rotation) but can still expand/shrink
#                     laterally - no platen confinement in the result.
#   RP-Bottom   : fully fixed (U1=U2=U3=UR1=UR2=UR3=0).
#   RP-Top      : rotations fixed (UR1=UR2=UR3=0) so the top face stays
#                 parallel to the bottom one; the two in-plane translations of
#                 the RP are also set to 0 - they are not coupled to anything,
#                 so this changes nothing physically but stops Abaqus from
#                 seeing two DOFs with zero stiffness. The axial translation
#                 is free and carries the load.
#   Load        : one CLOAD of the *total* force on RP-Top along the axis
#                 (no division by the node count any more - the coupling
#                 distributes it over the face).
#   pin A, pin B: two individual bottom nodes, restrained in-plane only. The
#                 couplings tie only the axial DOF, so the body can still
#                 translate in the two transverse directions and rotate about
#                 the load axis; the pins remove those three rigid-body modes
#                 (otherwise: "numerical singularity" on the first increment).
#
# The stiffness can then be read directly on the RPs: RF<axis> on RP-Bottom
# is the total reaction, U<axis> on RP-Top is the face displacement.
#
# Run by triply.abaqus_tools.create_simulation(); every parameter
# arrives as a key=value argument after the `--` separator.
# ============================================================================

# Import Abaqus modules
import sys
from abaqus import *
from abaqusConstants import *
from caeModules import *
from driverUtils import executeOnCaeStartup
from part import *
from material import *
from section import *
from assembly import *
from step import *
from interaction import *
from load import *
from mesh import *
from optimization import *
from job import *
from sketch import *
from visualization import *
from connectorBehavior import *
import os
import logging


# ============================================================================
# parse_kv_args
# ============================================================================
def parse_kv_args(argv):
    """Parse args like key=value and return a dict."""
    out = {}
    for a in argv:
        if "=" in a:
            k, v = a.split("=", 1)
            out[k.strip()] = v.strip()
        else:
            out.setdefault("_positional", []).append(a)
    return out


# ============================================================================
# _bc_kwargs
# ============================================================================
def _bc_kwargs(fixed_dofs):
    """
    Builds the u1/u2/u3 keyword dict for a DisplacementBC: the DOF indices
    listed in `fixed_dofs` (0-based) are set to 0.0, every other DOF is left
    UNSET (i.e. free) rather than 0.0 - that distinction is the whole point
    of a roller support.
    """
    kw = {"u1": UNSET, "u2": UNSET, "u3": UNSET,
          "ur1": UNSET, "ur2": UNSET, "ur3": UNSET}
    for d in fixed_dofs:
        kw["u%d" % (d + 1)] = 0.0
    return kw

# ============================================================================
# _coupling_kwargs
# ============================================================================
def _coupling_kwargs(axial_dof):
    """
    Builds the u1/u2/u3/ur1/ur2/ur3 keyword dict for a Coupling constraint,
    matching the CAE model: only the translation along the load axis
    (`axial_dof`, 0-based) and the three rotations are coupled (ON); the two
    in-plane translations are OFF, so the face nodes can still move
    laterally (free Poisson expansion).
    """
    kw = {"u1": OFF, "u2": OFF, "u3": OFF,
          "ur1": ON, "ur2": ON, "ur3": ON}
    kw["u%d" % (axial_dof + 1)] = ON
    return kw


# ============================================================================
# _set_quadratic_tets
# ============================================================================
def _set_quadratic_tets(part, logger):
    """
    Reassigns every element of `part` to the 10-node quadratic tetrahedron
    (C3D10). fTetWild only ever produces 4-node linear tets, so the whole
    element set is converted in one call - no per-shape branching needed.
    """
    elements = part.elements[0:len(part.elements)]
    if len(elements) == 0:
        logger.error("_set_quadratic_tets(): part %r has no elements to convert." % (part.name,))
        raise ValueError("_set_quadratic_tets(): part %r has no elements to convert." % (part.name,))

    quad_tet = mesh.ElemType(elemCode=C3D10, elemLibrary=STANDARD,
                             secondOrderAccuracy=OFF, distortionControl=DEFAULT)
    part.setElementType(regions=(elements, ), elemTypes=(quad_tet, ))
    logger.info("mesh upgraded to quadratic tets (C3D10): %d elements." % len(elements))

# ============================================================================
# _slab_nodes
# ============================================================================
def _slab_nodes(node_array, low, high, ax, band_lo, band_hi, pad):
    """
    Returns the nodes of `node_array` lying inside the [band_lo, band_hi]
    slab along axis `ax`, spanning the full bounding box in the other two
    directions. Thin wrapper over MeshNodeArray.getByBoundingBox() that
    spares the caller the x/y/z keyword juggling.
    """
    bounds = {"xMin": low[0] - pad, "xMax": high[0] + pad,
              "yMin": low[1] - pad, "yMax": high[1] + pad,
              "zMin": low[2] - pad, "zMax": high[2] + pad}
    bounds["%sMin" % "xyz"[ax]] = band_lo
    bounds["%sMax" % "xyz"[ax]] = band_hi
    return node_array.getByBoundingBox(**bounds)




def _build_static_simulation(logger:logging.Logger,
                             mesh_path:str,
                             output_dir:str,
                             output_name:str,
                             young_modulus:float,
                             poisson_ratio:float,
                             density:float,
                             axis:str,
                             load:float,
                             compression:bool,
                             tol_frac:float,
                             num_cpus:int,
                             pin_a_coords:tuple,
                             pin_b_coords:tuple,
                             non_linear_geometry:int,
                             quadratic_tets:int):
    # ================================================================
    # SECTION 0 : validate the inputs
    # ================================================================
    # validate the pin coordinates: they must be 3D tuples, not 2D or 1D.
    for name, coords in (("pin_a_coords", pin_a_coords), ("pin_b_coords", pin_b_coords)):
        if len(coords) != 3:
            logger.error("_build_static_simulation(): %s must be an (x, y, z) "
                         "coordinate, got %r." % (name, coords))
            raise ValueError("_build_static_simulation(): %s must be an (x, y, z) "
                             "coordinate, got %r." % (name, coords))
    
    # validate the axis: it must be x, y, or z (or 0, 1, 2).
    # and convert them to 0-based indices for the rest of the code.
    axis_table = {"x": 0, "y": 1, "z": 2, "0": 0, "1": 1, "2": 2}
    axis_key = str(axis).strip().lower()
    if axis_key not in axis_table:
        raise ValueError("Unknown axis %r - use x, y or z." % (axis,))
    ax = axis_table[axis_key]                   # 0-based index of the load axis
    t1, t2 = [i for i in range(3) if i != ax]   # the two transverse axes (0-based)
    axis_letter = "XYZ"[ax]                     # the (load) axis letter for logging and the step description

    # ================================================================
    # SECTION 1 : setup paths
    # ================================================================
    # The model and the job are both named after the output name
    # (e.g. "my_tpms-static"), so the job file becomes Job-<output_name>.inp.
    model_name = output_name
    # writeInput() writes Job-<model_name>.inp into the current directory, so
    # move there explicitly instead of relying on the folder Abaqus started in.
    os.chdir(output_dir)
    logger.info("Output folder: %s" % output_dir)

    # ================================================================
    # SECTION 2 : load inp file
    # ================================================================
    # mesh_path is given directly by the caller: <mesh_dir>/<mesh_name>.inp
    logger.info("loading file : %s" % mesh_path)

    mdb.ModelFromInputFile(name=model_name, inputFileName=mesh_path)
    M = mdb.models[model_name]

    # ================================================================
    # SECTION 3 : get the imported part / instance
    # ================================================================
    part_name = list(M.parts.keys())[0]
    P = M.parts[part_name]
    A = M.rootAssembly
    instance_name = list(A.instances.keys())[0]
    I = A.instances[instance_name]

    # ================================================================
    # SECTION 3.1 : optionally upgrade the mesh to quadratic tets
    # ================================================================
    if quadratic_tets == 1:
        _set_quadratic_tets(P, logger)

    # ================================================================
    # SECTION 4 : apply material properties
    # ================================================================
    E, v, d = young_modulus, poisson_ratio, density

    M.Material(name='ALUMINA')
    M.materials['ALUMINA'].Density(table=((d, ), ))
    M.materials['ALUMINA'].Elastic(table=((E, v), ))
    M.HomogeneousSolidSection(material='ALUMINA', name='Section-ALUMINA', thickness=None)

    e = P.elements
    elements = e[0:len(e)]
    region = P.Set(elements=elements, name='Set-allelements')
    P.SectionAssignment(region=region,
                        sectionName='Section-ALUMINA',
                        offset=0.0,
                        offsetType=MIDDLE_SURFACE,
                        offsetField='',
                        thicknessAssignment=FROM_SECTION)
    
    logger.info("material assigned: E=%g, nu=%g, rho=%g" % (E, v, d))

    # ================================================================
    # SECTION 5 : locate the two end faces
    # ================================================================
    # Sets are built on the *assembly instance* rather than on the part so
    # that the BC/load regions below are unambiguous - part sets only reach
    # the assembly through the instance, and orphan meshes imported from an
    # .inp make that propagation easy to get wrong.
    
    # get the bounding box of the mesh, and the extent along the load axis.
    bbox = I.nodes.getBoundingBox()
    low, high = bbox['low'], bbox['high']
    extent = high[ax] - low[ax]
    if extent <= 0:
        raise ValueError("The mesh has zero extent along %s - nothing to load."
                         % axis_letter)

    # compute the tolerance for face selection as an absolute value (user gives relative thickness).
    tol = tol_frac * extent
    # pad the four non-load bounds outwards so getByBoundingBox() can't drop
    pad = 1.0e-4 * max(high[0] - low[0], high[1] - low[1], high[2] - low[2])

    # create a set of the bottom face nodes and a set of the top face nodes
    bottom_nodes = _slab_nodes(I.nodes, low, high, ax,
                               low[ax] - pad, low[ax] + tol, pad)
    top_nodes = _slab_nodes(I.nodes, low, high, ax,
                            high[ax] - tol, high[ax] + pad, pad)

    n_bot, n_top = len(bottom_nodes), len(top_nodes)
    logger.info("axis=%s, extent=%g, face tolerance=%g (%g %%)"
                % (axis_letter, extent, tol, 100.0 * tol_frac))
    logger.info("bottom face: %d nodes | top face: %d nodes" % (n_bot, n_top))
    if n_bot < 3 or n_top < 1:
        raise ValueError(
            "Face selection failed (%d bottom / %d top nodes). Increase the "
            "face tolerance, or check that the STL really has flat ends along %s."
            % (n_bot, n_top, axis_letter))

    A.Set(nodes=bottom_nodes, name='Set-Bottom')
    A.Set(nodes=top_nodes, name='Set-Top')

    # ---- the two rigid-body pins, picked as the bottom nodes closest to
    # the caller-supplied pin_a_coords / pin_b_coords ----
    def _closest_bottom_node(target_coords):
        best_label, best_sq_dist = None, None
        for n in bottom_nodes:
            nx, ny, nz = n.coordinates
            tx, ty, tz = target_coords
            sq_dist = (nx - tx) ** 2 + (ny - ty) ** 2 + (nz - tz) ** 2
            if best_sq_dist is None or sq_dist < best_sq_dist:
                best_sq_dist, best_label = sq_dist, n.label
        return best_label

    best_a = _closest_bottom_node(pin_a_coords)
    best_b = _closest_bottom_node(pin_b_coords)
    if best_a == best_b:
        logger.error(
            "_build_static_simulation(): pin_a_coords %r and pin_b_coords %r "
            "both resolved to bottom node %s - move them further apart."
            % (tuple(pin_a_coords), tuple(pin_b_coords), best_a))
        raise ValueError(
            "pin_a_coords and pin_b_coords resolved to the same bottom node "
            "(node %s) - move them further apart." % (best_a,))

    P.SetFromNodeLabels(name='Set-Pin-A', nodeLabels=(best_a,))
    P.SetFromNodeLabels(name='Set-Pin-B', nodeLabels=(best_b,))
    logger.info("rigid-body pins: node %s near %r (U%d, U%d) and node %s near %r (U%d)"
                % (best_a, tuple(pin_a_coords), t1 + 1, t2 + 1,
                   best_b, tuple(pin_b_coords), t2 + 1))

    # ================================================================
    # SECTION 5.1 : reference points + kinematic couplings
    # ================================================================
    # One RP per end face, placed at the centre of the bounding box in the
    # two transverse directions and exactly on the face plane along the
    # axis. 
    def _face_centre(axial_coordinate):
        centre = [0.5 * (low[0] + high[0]),
                  0.5 * (low[1] + high[1]),
                  0.5 * (low[2] + high[2])]
        centre[ax] = axial_coordinate
        return tuple(centre)

    bottom_centre = _face_centre(low[ax])
    top_centre = _face_centre(high[ax])

    # A.ReferencePoint() returns a Feature; the actual ReferencePoint object
    # is stored in A.referencePoints under that feature's id.
    rp_bottom_feature = A.ReferencePoint(point=bottom_centre)
    rp_top_feature = A.ReferencePoint(point=top_centre)
    rp_bottom = A.referencePoints[rp_bottom_feature.id]
    rp_top = A.referencePoints[rp_top_feature.id]

    # create a set of the reference points
    A.Set(referencePoints=(rp_bottom, ), name='Set-RP-Bottom')
    A.Set(referencePoints=(rp_top, ), name='Set-RP-Top')

    # The mesh comes from an .inp (orphan mesh, no geometric faces), so the
    # coupled region is the face *node set* - Abaqus turns it into a
    # node-based surface, which is exactly what a coupling needs.
    M.Coupling(name='Coupling-Bottom', controlPoint=A.sets['Set-RP-Bottom'],
               surface=A.sets['Set-Bottom'], influenceRadius=WHOLE_SURFACE,
               couplingType=KINEMATIC, alpha=0.0, localCsys=None,
               **_coupling_kwargs(ax))
    M.Coupling(name='Coupling-Top', controlPoint=A.sets['Set-RP-Top'],
               surface=A.sets['Set-Top'], influenceRadius=WHOLE_SURFACE,
               couplingType=KINEMATIC, alpha=0.0, localCsys=None,
               **_coupling_kwargs(ax))
    logger.info("kinematic couplings created: U%d + UR1/UR2/UR3 coupled, "
                "U%d and U%d left free on both faces" % (ax + 1, t1 + 1, t2 + 1))

    # ================================================================
    # SECTION 6 : CREATE ANALYSIS STEP
    # ================================================================
    if non_linear_geometry == 1:
        NL_GEM = ON
        logger.info("non-linear geometry analysis enabled (NLGEOM=ON)")
    else:
        NL_GEM = OFF
    M.StaticStep(name='Step-Static', previous='Initial',
                 description='Linear elastic uniaxial load along %s' % axis_letter,
                 timePeriod=1.0, initialInc=1.0, minInc=1.0e-8, maxInc=1.0,
                 nlgeom=NL_GEM)

    if non_linear_geometry == 1:
        M.steps['Step-Static'].setValues(maxNumInc=1000, 
        initialInc=0.1)
    try:
        M.fieldOutputRequests['F-Output-1'].setValues(
            variables=('S', 'E', 'U', 'RF', 'CF'))
    except Exception as exc:
        logger.warning("could not override the field output request: %s" % exc)

    # History output on the two faces. Nothing reads it yet, but it makes the
    # stiffness post-processing (sum RF on the bottom / mean U on the top) a
    # pure ODB read later on, with no re-solve.
    try:
        M.HistoryOutputRequest(name='H-Bottom-RF', createStepName='Step-Static',
                               variables=('RF1', 'RF2', 'RF3'),
                               region=A.sets['Set-Bottom'], sectionPoints=DEFAULT)
        M.HistoryOutputRequest(name='H-Top-U', createStepName='Step-Static',
                               variables=('U1', 'U2', 'U3'),
                               region=A.sets['Set-Top'], sectionPoints=DEFAULT)
        # with the couplings, the two RPs alone carry the whole load path:
        # RF<axis> on RP-Bottom = total reaction, U<axis> on RP-Top = face
        # displacement -> stiffness = RF / U from two single values.
        M.HistoryOutputRequest(name='H-RP-Bottom-RF', createStepName='Step-Static',
                               variables=('RF1', 'RF2', 'RF3', 'RM1', 'RM2', 'RM3'),
                               region=A.sets['Set-RP-Bottom'], sectionPoints=DEFAULT)
        M.HistoryOutputRequest(name='H-RP-Top-U', createStepName='Step-Static',
                               variables=('U1', 'U2', 'U3', 'UR1', 'UR2', 'UR3'),
                               region=A.sets['Set-RP-Top'], sectionPoints=DEFAULT)
    except Exception as exc:
        logger.warning("could not create the history output requests: %s" % exc)

    # ================================================================
    # SECTION 7 : BOUNDARY CONDITIONS
    # ================================================================
    # RP-Bottom: fully fixed (BC-1 in the CAE model).
    M.DisplacementBC(name='BC-RP-Bottom', createStepName='Initial',
                     region=A.sets['Set-RP-Bottom'], amplitude=UNSET,
                     distributionType=UNIFORM, fieldName='', localCsys=None,
                     u1=0.0, u2=0.0, u3=0.0, ur1=0.0, ur2=0.0, ur3=0.0)

    # RP-Top: rotations fixed (BC-2 in the CAE model) + the two uncoupled
    # in-plane translations, axial translation left free for the load.
    top_rp_bc = _bc_kwargs([t1, t2])
    top_rp_bc.update({"ur1": 0.0, "ur2": 0.0, "ur3": 0.0})
    M.DisplacementBC(name='BC-RP-Top', createStepName='Initial',
                     region=A.sets['Set-RP-Top'], amplitude=UNSET,
                     distributionType=UNIFORM, fieldName='', localCsys=None,
                     **top_rp_bc)

    M.DisplacementBC(name='BC-Pin-A', createStepName='Initial',
                     region=I.sets['Set-Pin-A'], amplitude=UNSET,
                     distributionType=UNIFORM, fieldName='', localCsys=None,
                     **_bc_kwargs([t1, t2]))

    M.DisplacementBC(name='BC-Pin-B', createStepName='Initial',
                     region=I.sets['Set-Pin-B'], amplitude=UNSET,
                     distributionType=UNIFORM, fieldName='', localCsys=None,
                     **_bc_kwargs([t2]))

    # ================================================================
    # SECTION 8 : APPLY LOAD
    # ================================================================
    # The region is the single RP-Top, so the *total* force goes on it
    # directly; the coupling spreads it over the top face nodes.
    sense = -1.0 if compression else 1.0
    total_force = sense * float(load)
    force_components = {"cf1": 0.0, "cf2": 0.0, "cf3": 0.0}
    load_axis_component = f"cf{ax + 1}"
    force_components[load_axis_component] = total_force

    M.ConcentratedForce(name='Load-Axial', createStepName='Step-Static',
                        region=A.sets['Set-RP-Top'], distributionType=UNIFORM,
                        field='', localCsys=None, **force_components)
    load_mode = "compression" if compression else "tension"
    logger.info(
        f"load: total {load:g} in {load_mode} along {axis_letter} applied on RP-Top "
        f"(coupled to {n_top} top nodes)"
    )

    # ================================================================
    # SECTION 9 : CREATE JOB
    # ================================================================
    mdb.Job(name='Job-' + model_name, model=model_name, description='',
            type=ANALYSIS, atTime=None, waitMinutes=0, waitHours=0, queue=None,
            memory=90, memoryUnits=PERCENTAGE, getMemoryFromAnalysis=True,
            explicitPrecision=SINGLE, nodalOutputPrecision=SINGLE, echoPrint=OFF,
            modelPrint=OFF, contactPrint=OFF, historyPrint=OFF, userSubroutine='',
            scratch='', resultsFormat=ODB, multiprocessingMode=DEFAULT,
            numCpus=num_cpus, numDomains=num_cpus, numGPUs=0)
    mdb.jobs['Job-' + model_name].writeInput(consistencyChecking=ON)

    logger.info(f"job has been created : {output_dir}/Job-{model_name}.inp")
    logger.info("Simulation created successfully.")
    sys.stdout.flush()


# ============================================================================
# entry point - every value arrives as a string on the Abaqus command line,
# so each one is cast here and given the same default as the GUI's widget.
# ============================================================================
#
# COMMAND-LINE INPUTS (passed as key=value after "--")
# ------------------------------------------------------
# Required:
#   input=<str>
#       <mesh_dir>/<mesh_name> - path of the tetrahedral mesh, without .inp.
#   output=<str>
#       <sim_dir>/<output_name> - the folder where Job-<output_name>.inp and
#       the log are written, joined to the model/job name (without "Job-"),
#       e.g. C:/tmp/my_model_sim/my_model-static.
#
# Optional (with defaults):
#   young_modulus=<float>         default: 300000
#   poisson_ratio=<float>         default: 0.21
#   density=<float>               default: 3.9e-09
#   axis=<str>                    default: z      (x, y, z, 0, 1, or 2)
#   quadratic_tets=<int>          default: 0      (0=keep linear, 1=convert to C3D10)
#   load=<float>                  default: 1.0
#   compression=<bool-like>       default: 1      (1/true/yes => compression)
#   tol_frac=<float>              default: 0.01   (face-selection slab fraction)
#   num_cpus=<int>                default: 1
#   pin_a_coords=<x,y,z>          default: 0,0,0  (comma-separated floats)
#   pin_b_coords=<x,y,z>          default: 0,0,0  (comma-separated floats)
#   non_linear_geometry=<int>     default: 0      (0=OFF, 1=ON)
#
# Example:
#   abaqus cae noGUI=generate_static_sim.py -- input=C:/tmp/my_model output=C:/tmp/my_model_sim/my_model-static
#       axis=z load=1000 compression=1 pin_a_coords=0,0,0 pin_b_coords=1,0,0
#
if __name__ == "__main__":
    args = parse_kv_args(sys.argv[1:])
    if "input" not in args or not args["input"]:
        raise SystemExit('Missing required argument: input="..."')
    # see the naming contract in triply.abaqus_tools.create_simulation()
    input_arg = args["input"]                      # <mesh_dir>/<mesh_name>
    output_arg = args["output"]                    # <sim_dir>/<mesh_name>-<kind>
    mesh_path = input_arg + ".inp"                 # the tetrahedral mesh to load
    output_dir = os.path.dirname(output_arg)       # where Job-<output_name>.inp and the log are written
    output_name = os.path.basename(output_arg)     # model name AND job name (without "Job-")
    young_modulus = float(args.get("young_modulus", 300000))
    poisson_ratio = float(args.get("poisson_ratio", 0.21))
    density = float(args.get("density", 3.9e-09))
    axis = args.get("axis", "z")
    quadratic_tets = int(args.get("quadratic_tets", 0))
    load = float(args.get("load", 1.0))
    compression = str(args.get("compression", "1")).lower() in ("1", "true", "yes")
    tol_frac = float(args.get("tol_frac", 0.01))
    num_cpus = int(args.get("num_cpus", 1))
    pin_a_coords = tuple(float(x) for x in args.get("pin_a_coords", "0,0,0").replace("'", "").replace("[", "").replace("]", "").split(",")) 
    pin_b_coords = tuple(float(x) for x in args.get("pin_b_coords", "0,0,0").replace("'", "").replace("[", "").replace("]", "").split(","))
    non_linear_geometry = int(args.get("non_linear_geometry", "0"))

    # define logger and log file path
    log_file = os.path.join(output_dir, "generate_sim_logger_" + output_name + ".txt")
    logging.basicConfig(filename=log_file, level=logging.DEBUG,
                        format="%(asctime)s - %(levelname)s - %(message)s",
                        filemode='a')
    logger = logging.getLogger(__name__)

    # launcgh the simulation creation
    logger.info("Starting simulation creation...")
    try:
        _build_static_simulation(
            logger=logger,
            mesh_path=mesh_path,
            output_dir=output_dir,
            output_name=output_name,
            young_modulus=young_modulus,
            poisson_ratio=poisson_ratio,
            density=density,
            axis=axis,
            load=load,
            compression=compression,
            tol_frac=tol_frac,
            num_cpus=num_cpus,
            pin_a_coords=pin_a_coords,
            pin_b_coords=pin_b_coords,
            non_linear_geometry=non_linear_geometry,
            quadratic_tets=quadratic_tets,
        )
    except Exception as exc:
        import traceback
        logger.error("traceback:\n%s" % traceback.format_exc())
        reason = " ".join(str(exc).split())
        logger.error("Simulation creation FAILED: %s" % reason)
        sys.stdout.flush()
        raise
