import numpy as np

from .tpms_base import TPMSModel, create_a_tpms


"""
#=====================================================================================================================
0 - (reserved)
1 - CustomTPMSModel (class)
2 - CustomTPMSModel._implicit_field
2b - CustomTPMSModel._implicit_field_at
3 - create_a_custom_tpms
#=====================================================================================================================
"""


# =====================================================================
# 1) CustomTPMSModel
# =====================================================================
class CustomTPMSModel(TPMSModel):
    """
    ============================================================================
    1) CUSTOMTPMSMODEL
    TPMS model whose implicit surface is supplied directly as a
    precomputed scalar field array, instead of being computed from a
    hardcoded formula like GyroidModel/SchwartzPModel/etc. Same API as
    every other TPMSModel subclass otherwise (compute_field, generate_mesh,
    simplify_mesh, ...), except it takes no px/py/pz (see module NOTE).
    ============================================================================

    PARAMETERS
    ----------
    x, y, z, thickness : see TPMSModel. thickness must already be a plain
        scalar or numpy array (same shape as x) - this class does no
        parsing of its own; see app/components/equation_input.py if the
        caller is starting from a formula string instead of a plain array.
    field : np.ndarray
        Precomputed implicit surface values F(x, y, z), same shape as x.
        Returned as-is by _implicit_field().
    field_function : callable, optional
        The formula of F, given as a Python function, so that F can be
        computed at any point (needed only by generate_mesh_adaptive).
        example: `  def my_surface(x, y, z):
                        return np.sin(x) * np.cos(y) + np.sin(y) * np.cos(z) + np.sin(z) * np.cos(x)

                    model = CustomTPMSModel(x, y, z, thickness,
                                            field=my_surface(x, y, z),     # values on the grid
                                            field_function=my_surface)     # the formula itself
                 `
        RULES FOR THAT FUNCTION
        - Input: three numpy arrays x, y, z (same shape, ANY shape) holding
          positions in the same units as the model's grid.
        - Output: one numpy array of the same shape, the value of F there.
        - Use numpy functions (np.sin, np.cos, ...), not the math module and
          not a loop over points: it receives many points at once.
        - It must give the same surface as `field`
          (my_surface(x, y, z) == field on the grid). Nothing checks this.
        - It must give finite numbers everywhere in the box: no log or sqrt
          of negative values (NaN leaves holes in the mesh).
        - Return F itself, not the density field: the field mode ("band",
          "signed", ...) is applied afterwards, as for `field`.

    RAISES
    ------
    ValueError
        If `field`'s shape doesn't match x's shape.

    NOTES
    -----
    - Reloading via `TPMSModel.load()` restores the saved field/params
      (the field itself is fully valid) but obviously has no formula to
      "re-show" - there never was one at this layer.

    EXAMPLE
    -------
    >>> field = np.sin(x) + np.cos(y) + np.sin(z)  # or however the caller computed it
    >>> model = CustomTPMSModel(x, y, z, 0.2, field=field)
    >>> field_out = model.compute_field()
    """

    DEFAULT_FIELD_MODE = "distance"

    def __init__(self, x, y, z, thickness, field: np.ndarray, field_function=None):
        field = np.asarray(field, dtype=float)
        x_shape = np.asarray(x).shape
        if field.shape != x_shape:
            raise ValueError(
                f"CustomTPMSModel: field shape {field.shape} does not match "
                f"x/y/z shape {x_shape}."
            )
        self._field = field
        self._field_function = field_function

        # TPMSModel.__init__ requires px/py/pz positionally (it stores and
        # later saves them, like every other parameter) even though this
        # subclass has no use for them - 1.0 is an arbitrary placeholder,
        # never read back by anything that affects the field.
        super().__init__(x, y, z, 1.0, 1.0, 1.0, thickness)

    # =====================================================================
    # 2) _implicit_field
    # =====================================================================
    def _implicit_field(self) -> np.ndarray:
        """
        ============================================================================
        2) _IMPLICIT_FIELD
        Returns the field array supplied at construction time, unchanged.
        ============================================================================

        RETURNS
        -------
        implicit_field : np.ndarray
            F(x, y, z), same shape as self.x.
        """
        return self._field
    
    # =====================================================================
    # 2b) _implicit_field_at
    # =====================================================================
    def _implicit_field_at(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
        """
        ============================================================================
        2b) _IMPLICIT_FIELD_AT
        Returns F at any given points by calling the field_function supplied
        at construction time. Used by density_field_at() and therefore by
        generate_mesh_adaptive().
        ============================================================================

        PARAMETERS
        ----------
        x, y, z : np.ndarray
            Positions where F is evaluated, any shape (all three the same).

        RETURNS
        -------
        implicit_field : np.ndarray
            F(x, y, z), same shape as x.

        RAISES
        ------
        NotImplementedError
            If the model was built without field_function (e.g. a field
            imported from a file): only the grid values exist, so F cannot
            be evaluated anywhere else.
        """
        if self._field_function is None:
            raise NotImplementedError(
                "This CustomTPMSModel only has a field array on its grid: "
                "pass field_function=... to use adaptive meshing.")
        return self._field_function(x, y, z)
    
# =====================================================================
# 3) create_a_custom_tpms
# =====================================================================
def create_a_custom_tpms(x: np.ndarray,
                         y: np.ndarray,
                         z: np.ndarray,
                         t: np.ndarray,
                         field: np.ndarray,
                         save_path: str,
                         baseplate_thickness: float = 0.0,
                         step_size: int = 2,
                         simplification_factor=0.9,
                         field_mode: str = None):
    """
    ============================================================================
    3) CREATE_A_CUSTOM_TPMS
    Convenience function mirroring create_a_gyroid()/create_a_diamond()/etc.
    for the precomputed-field case. Delegates to the shared
    tpms_base.create_a_tpms() pipeline, same as every built-in type - see
    the module-level NOTE for how px/py/pz (always 1.0, unused by
    CustomTPMSModel) are bridged across that shared helper's uniform
    calling convention.
    ============================================================================

    PARAMETERS
    ----------
    x, y, z, t : see create_a_gyroid.
    field : np.ndarray
        Precomputed implicit surface values (see CustomTPMSModel).
    save_path, baseplate_thickness, step_size, simplification_factor,
    field_mode : see create_a_gyroid.

    RETURNS
    -------
    success : bool
        True if a valid mesh was generated and exported, False otherwise.
    """
    # create_a_tpms() instantiates every model type uniformly as
    # model_cls(x, y, z, px, py, pz, thickness). CustomTPMSModel doesn't
    # take px/py/pz (see module NOTE), so this thin wrapper absorbs and
    # discards them before forwarding to the real constructor.
    def _model_cls(x, y, z, px, py, pz, thickness):
        return CustomTPMSModel(x, y, z, thickness, field=field)

    return create_a_tpms(
        _model_cls,
        x, y, z, 1.0, 1.0, 1.0, t,
        save_path,
        baseplate_thickness=baseplate_thickness,
        step_size=step_size,
        simplification_factor=simplification_factor,
        field_mode=field_mode,
    )
