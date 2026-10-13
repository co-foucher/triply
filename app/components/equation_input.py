"""
Custom TPMS equation support: parsing/validation/evaluation of user-typed
formula strings, the Streamlit widgets that collect them, and the one call
site (evaluate_custom_inputs) that turns them into the plain numpy arrays
triply.TPMS_classes.tpms_custom.CustomTPMSModel expects. Used by
app/pages/1_Generate_TPMS.py.

WHY THIS LIVES HERE, NOT IN THE LIBRARY
-----------------------------------------
CustomTPMSModel takes a precomputed `field` array (and a precomputed
`thickness` array/scalar) - plain numpy data, exactly like every other
TPMSModel subclass. It has no idea a user might have typed a formula
string into a text box; that's a GUI concern, not a library one.
Everything about turning that string into numbers - parsing, validating,
sympy, the max/min duck-typing behavior described below - lives here
instead, so the library stays a plain numerical package that only ever
sees numpy arrays. 1_Generate_TPMS.py doesn't need to know equations are
involved at all - it just calls render_equation_input() for the widgets
and evaluate_custom_inputs() to get arrays back.
"""
from typing import Callable, Optional, Tuple

import numpy as np
import plotly.graph_objects as go
import sympy as sp
import streamlit as st

__all__ = ["render_equation_input", "evaluate_custom_inputs", "EquationError"]


# =====================================================================
# 0 - (reserved)
# 1 - EquationError (exception)
# 2 - parse_equation
# 3 - validate_equation
# 4 - evaluate_equation
# 5 - render_equation_input
# 6 - evaluate_custom_inputs
# =====================================================================

# Only these symbols may appear in a user equation. No px/py/pz: for a
# custom equation, the user's formula *is* the whole field definition -
# there's nothing left for a separate period to parameterize (see
# CustomTPMSModel's docstring in the library for the same point from the
# library side).
_ALLOWED_SYMBOLS = ("x", "y", "z")


# =====================================================================
# max/min: same dual behavior as Python's own builtins
# =====================================================================
# Plain sympy Max/Min always compare N pointwise arguments elementwise
# (Max(x, y) -> the larger of the two arrays, elementwise).
# Thus, "max(abs(x))" # would silently evaluate to abs(x) unchanged, 
# not "the largest |x| over the whole domain".
# This fixes it
class _ReduceOrCompareMax(sp.Function):
    @classmethod
    def eval(cls, *args):
        if len(args) > 1:
            return sp.Max(*args)
        return None  # single arg: stay unevaluated -> reduction at eval time


class _ReduceOrCompareMin(sp.Function):
    @classmethod
    def eval(cls, *args):
        if len(args) > 1:
            return sp.Min(*args)
        return None


# Passed as the first entry of lambdify's `modules` list so a leftover,
# unevaluated single-argument _ReduceOrCompareMax/Min prints as a call to
# numpy's full-array reduction instead of sympy's elementwise one. Falls
# through to the second entry ("numpy") for every other allowed function.
_LAMBDIFY_MODULES = [
    {"_ReduceOrCompareMax": np.max, "_ReduceOrCompareMin": np.min},
    "numpy",
]

# Only these functions may appear in a user equation. Deliberately a small,
# conservative set - extend if a use case needs more.
_ALLOWED_FUNCS = {
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
    "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "exp": sp.exp, "log": sp.log, "sqrt": sp.sqrt,
    "abs": sp.Abs, "Abs": sp.Abs,
    "max": _ReduceOrCompareMax, "min": _ReduceOrCompareMin,
    "pi": sp.pi,
}


# =====================================================================
# 1) EquationError
# =====================================================================
class EquationError(ValueError):
    """
    ============================================================================
    1) EQUATIONERROR
    Raised when a user-supplied equation string is invalid.
    ============================================================================
    """


# =====================================================================
# 2) parse_equation
# =====================================================================
def parse_equation(equation: str) -> Tuple[sp.Expr, Callable]:
    """
    ============================================================================
    2) PARSE_EQUATION
    Parses a formula string into a validated sympy expression and a fast
    numpy-vectorized callable fn(x, y, z) -> ndarray.
    ============================================================================

    PARAMETERS
    ----------
    equation : str
        Implicit surface formula, e.g.
        "sin(pi*x/2)*cos(pi*y/2) + sin(pi*y/2)*cos(pi*z/2)
        + sin(pi*z/2)*cos(pi*x/2)".
        Allowed variables: x, y, z.
        Allowed functions: sin, cos, tan, sinh, cosh, tanh, exp, log, sqrt,
        abs/Abs, max/min (see the module-level note above on their
        Python-like, argument-count-dependent behavior), plus the
        constant pi.

    RETURNS
    -------
    expr : sympy.Expr
        The parsed symbolic expression (useful for display/debugging).
    fn : callable
        fn(x, y, z) -> ndarray, vectorized with numpy.

    RAISES
    ------
    EquationError
        If the string can't be parsed, or references a symbol/function
        outside the allowed set.
    """
    symbols = {name: sp.Symbol(name) for name in _ALLOWED_SYMBOLS}
    namespace = {**_ALLOWED_FUNCS, **symbols}

    try:
        expr = sp.sympify(equation, locals=namespace)
    except (sp.SympifyError, TypeError, SyntaxError, AttributeError) as e:
        raise EquationError(f"Could not parse equation '{equation}': {e}") from e

    unknown = expr.free_symbols - set(symbols.values())
    if unknown:
        names = ", ".join(sorted(str(s) for s in unknown))
        raise EquationError(
            f"Equation uses unknown symbol(s): {names}. "
            f"Allowed variables are: {', '.join(_ALLOWED_SYMBOLS)}."
        )

    try:
        fn = sp.lambdify([symbols[n] for n in _ALLOWED_SYMBOLS], expr, modules=_LAMBDIFY_MODULES)
    except Exception as e:
        raise EquationError(f"Could not compile equation '{equation}': {e}") from e

    return expr, fn


# =====================================================================
# 3) validate_equation
# =====================================================================
def validate_equation(equation: str) -> Tuple[bool, str]:
    """
    ============================================================================
    3) VALIDATE_EQUATION
    Validates a formula string without needing a full-resolution coordinate
    grid - parses it, then smoke-tests it on a tiny 4x4x4 grid to catch
    runtime issues sympy's parser can't (e.g. log of a negative number,
    shape mismatches). Intended for a GUI "validate as you type" widget.
    ============================================================================

    PARAMETERS
    ----------
    equation : str
        The formula string to validate.

    RETURNS
    -------
    ok : bool
        True if the equation parsed and evaluated cleanly.
    message : str
        Human-readable explanation (error detail, or the parsed form on
        success).

    EXAMPLE
    -------
    >>> validate_equation("sin(x) + cos(y)")
    (True, 'OK - parsed as: sin(x) + cos(y)')
    >>> validate_equation("sin(x) + banana(y)")
    (False, "Could not parse equation ...")
    """
    try:
        expr, fn = parse_equation(equation)
    except EquationError as e:
        return False, str(e)

    try:
        g = np.linspace(-1.0, 1.0, 4)
        gx, gy, gz = np.meshgrid(g, g, g, indexing="ij")
        result = np.asarray(fn(gx, gy, gz), dtype=float)
        result = np.broadcast_to(result, gx.shape)
        if not np.all(np.isfinite(result)):
            return False, "Equation produced non-finite values (inf/nan) on a test grid."
    except Exception as e:
        return False, f"Equation failed on test evaluation: {e}"

    # cosmetic only: show the user-facing names they typed rather than the
    # internal _ReduceOrCompareMax/Min class names used to get max/min's
    # argument-count-dependent behavior (see the module-level note above).
    display = sp.sstr(expr).replace("_ReduceOrCompareMax", "max").replace("_ReduceOrCompareMin", "min")
    return True, f"OK - parsed as: {display}"


# =====================================================================
# 4) evaluate_equation
# =====================================================================
def evaluate_equation(equation: str, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
    """
    ============================================================================
    4) EVALUATE_EQUATION
    Parses and evaluates a formula on a real coordinate grid, broadcasting
    scalars/reductions (e.g. a single-argument max(...)) up to the grid
    shape. This is the one call site the GUI needs: it turns a raw string
    into the plain numpy array CustomTPMSModel expects.
    ============================================================================

    PARAMETERS
    ----------
    equation : str
        The formula string (see parse_equation for allowed syntax).
    x, y, z : np.ndarray
        Coordinate grids of identical shape.

    RETURNS
    -------
    field : np.ndarray
        The evaluated formula, broadcast to x's shape.

    RAISES
    ------
    EquationError
        If the formula is invalid or fails to evaluate on this grid.

    EXAMPLE
    -------
    >>> field = evaluate_equation("sin(pi*x/2) + cos(pi*y/2)", x, y, z)
    """
    _, fn = parse_equation(equation)
    try:
        result = fn(x, y, z)
    except Exception as e:
        raise EquationError(f"Equation '{equation}' failed to evaluate: {e}") from e

    return np.broadcast_to(np.asarray(result, dtype=float), np.asarray(x).shape).copy()




'''
# =====================================================================
# 5) render_equation_input
# =====================================================================
def render_equation_input(key_prefix: str = "eq") -> Optional[str]:
    """
    ============================================================================
    5) RENDER_EQUATION_INPUT
    Renders the formula text box, validates it, and (if valid) shows a
    cheap 2D mid-slice preview computed on a small grid - independent of
    the full-resolution grid used for actual generation, so feedback is
    near-instant even before clicking "Generate".
    ============================================================================

    PARAMETERS
    ----------
    key_prefix : str, optional
        Prefix used to namespace this widget's Streamlit session_state
        keys (default = "eq"), so multiple equation inputs can coexist
        on the same page.

    RETURNS
    -------
    equation, thickness : tuple[str, str], or None
        The (equation, thickness) formula strings if both validated
        successfully. None if either failed validation (the caller should
        disable the Generate button while this is None).
    """
    st.caption("Variables: x, y, z, pi ")
    st.caption("functions: sin, cos, tan, sinh, cosh, tanh, exp, log, sqrt, abs, max, min")

    # =================================================
    # ============ define implicit field ==============
    # =================================================
    equation = st.text_area(
        "Implicit surface equation F(x, y, z)",
        value=st.session_state.get(f"{key_prefix}_text", DEFAULT_EQUATION),
        key=f"{key_prefix}_text",
        height=80,
    )
    ok_eq, message = validate_equation(equation)
    if not ok_eq:
        st.error(message)
        return None
    st.success(message)

    # =================================================
    # =========== visualize implicit field ============
    # =================================================

    with st.expander("Preview of Field (mid z-slice, low-res, sample from -2 to 2)", expanded=False):
        _, fn = parse_equation(equation)
        n = 120
        g = np.linspace(-2.0, 2.0, n)
        gx, gy = np.meshgrid(g, g, indexing="ij")
        gz = np.zeros_like(gx)
        field = fn(gx, gy, gz)
        field = np.broadcast_to(np.asarray(field, dtype=float), gx.shape)

        fig = go.Figure(go.Heatmap(x=g, y=g, z=field.T, colorscale="Portland"))
        fig.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, width="stretch")

    # =================================================
    # ======== define thickness of surface ============
    # =================================================
    thickness = st.text_area(
        "Thickness",
        value=st.session_state.get(f"{key_prefix}_thickness", "0.5 + 0.8 * x / max(abs(x))"),
        key=f"{key_prefix}_thickness",
        height=80,
    )
    ok_th, message = validate_equation(thickness)
    if not ok_th:
        st.error(message)
        return None
    st.success(message)

    return equation, thickness
'''

# =====================================================================
# 6) evaluate_custom_inputs
# =====================================================================
def evaluate_custom_inputs(equation: str, 
                           x: np.ndarray, y: np.ndarray, z: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    ============================================================================
    6) EVALUATE_CUSTOM_INPUTS
    Turns the (equation, thickness) strings captured by
    render_equation_input() into the plain numpy arrays CustomTPMSModel
    expects, evaluated on the real generation grid. This is the only place
    that should call evaluate_equation() for the "Generate" flow - keeps
    1_Generate_TPMS.py itself free of any parsing-related imports.
    ============================================================================

    PARAMETERS
    ----------
    equation : str
        The string returned by render_equation_input().
    x, y, z : np.ndarray
        The real (full-resolution) coordinate grids to evaluate on - not
        the small preview grid used inside render_equation_input().

    RETURNS
    -------
    field : np.ndarray
        Evaluated array

    RAISES
    ------
    EquationError
        If either formula fails to evaluate on this grid. This can happen
        even though render_equation_input() already validated both
        strings: that validation only smoke-tests on a tiny grid, and
        formulas involving log/sqrt/etc. can behave differently over the
        real domain.
    """
    field = evaluate_equation(equation, x, y, z)
    return field

# =====================================================================
# 6b) create_the_function_that_evaluates_the_field_at_any_point
# =====================================================================
def make_field_function(equation: str,
                                                              grid_x: np.ndarray,
                                                              grid_y: np.ndarray,
                                                              grid_z: np.ndarray) -> Callable:
    """
    ============================================================================
    6b) make_field_function
    Turns an equation (text) into a Python function that gives the field at
    ANY points, with the same meaning as on the full grid.

    NECESSARY because max(...) / min(...) functions are not definted localy: 
    asking the values at one point without giving the whole field size is not possible.
    For adaptive resolution, we need to be able to evaluate the field at any point INDEPENDATLY
    ============================================================================

    PARAMETERS
    ----------
    equation : str
        The formula text (see parse_equation for what is allowed).
    grid_x, grid_y, grid_z : np.ndarray
        The full generation grid that max/min are meant over.

    RETURNS
    -------
    field_at_points : callable
        field_at_points(x, y, z) -> np.ndarray of the same shape as x,
        for x, y, z of any shape.

    EXAMPLE
    -------
    >>> field_at_points = make_field_function(
    ...     "0.3 + 0.8 * x / max(abs(x))", grid_x, grid_y, grid_z)   # max(abs(x)) -> 10 on a -10..10 grid
    >>> field_at_points(np.array([5.0]), np.array([0.0]), np.array([0.0]))
    array([0.7])                                                     # 0.3 + 0.8 * 5 / 10
    """
    # 1) Text -> sympy formula 
    formula, _ = parse_equation(equation)
    variables = [sp.Symbol(name) for name in _ALLOWED_SYMBOLS]          # the symbols x, y, z

    # which numpy reduction each piece stands for
    numpy_reduction_of = {_ReduceOrCompareMax: np.max, _ReduceOrCompareMin: np.min}

    # 2) Replace every max/min piece by its value on the full grid.
    while True:
        # all max/min pieces in the formula ...
        all_reduction_pieces = formula.atoms(_ReduceOrCompareMax, _ReduceOrCompareMin)
        # ... keeping those with no other max/min inside them
        innermost_pieces = [piece for piece in all_reduction_pieces
                            if not piece.args[0].has(_ReduceOrCompareMax, _ReduceOrCompareMin)]
        if not innermost_pieces:
            break                                       # no max/min left: done

        for piece in innermost_pieces:
            # what is inside the brackets, e.g. Abs(x) for max(abs(x)), as a numpy function
            inside_of_brackets = sp.lambdify(variables, piece.args[0], modules="numpy")
            # its values on the full grid (broadcast: a constant like max(2) gives one number)
            inside_values_on_grid = np.broadcast_to(
                np.asarray(inside_of_brackets(grid_x, grid_y, grid_z), dtype=float),
                np.asarray(grid_x).shape)
            # the max (or min) over the whole grid: one number
            number = float(numpy_reduction_of[type(piece)](inside_values_on_grid))
            # put that number in the formula instead of the piece
            formula = formula.subs(piece, number)

    # 3) The formula has no max/min left: compile it once into a fast numpy function
    compiled_formula = sp.lambdify(variables, formula, modules="numpy")

    # 4) The function handed to CustomTPMSModel: points in -> field values out
    def field_at_points(x, y, z):
        values = compiled_formula(x, y, z)
        # a formula without x, y or z (e.g. "0.5") gives one number: repeat it to the points' shape
        return np.broadcast_to(np.asarray(values, dtype=float), np.asarray(x).shape)

    return field_at_points


# =====================================================================
# 7) render_equation_input_implicit_field
# =====================================================================

DEFAULT_EQUATION = (
    "sin(pi * x / 2) * cos(pi * y / 2) + "
    "sin(pi * y / 2) * cos(pi * z / 2) + "
    "sin(pi * z / 2) * cos(pi * x / 2) "
)
def render_equation_input(label: str = "Default label", 
                          default_equation: str = DEFAULT_EQUATION,
                          key_prefix: str = "eq",
                          size_x: float = 10.0,
                          size_y: float = 10.0,
                          size_z: float = 10.0,
                          origin_x: float = 0.0,
                          origin_y: float = 0.0,
                          origin_z: float = 0.0,
                          ) -> Optional[str]:
    """
    ============================================================================
    5) RENDER_EQUATION_INPUT
    Renders the formula text box, validates it, and (if valid) shows a
    cheap 2D mid-slice preview computed on a small grid - independent of
    the full-resolution grid used for actual generation, so feedback is
    near-instant even before clicking "Generate".
    ============================================================================

    PARAMETERS
    ----------
    key_prefix : str, optional
        Prefix used to namespace this widget's Streamlit session_state
        keys (default = "eq"), so multiple equation inputs can coexist
        on the same page.
    size_x, size_y, size_z : float, optional
        Box edge lengths of the preview grid.
    origin_x, origin_y, origin_z : float, optional
        Box corner with the smallest coordinates (default 0), so the
        preview covers the same physical box [origin, origin + size] as
        the real grid.

    RETURNS
    -------
    equation, thickness : tuple[str, str], or None
        The (equation, thickness) formula strings if both validated
        successfully. None if either failed validation (the caller should
        disable the Generate button while this is None).
    """
    st.caption("Variables: x, y, z, pi ")
    st.caption("functions: sin, cos, tan, sinh, cosh, tanh, exp, log, sqrt, abs, max, min")

    # =================================================
    # ============ define implicit field ==============
    # =================================================
    equation = st.text_area(
        f"{label} equation F(x, y, z)",
        value=st.session_state.get(f"{key_prefix}_text", default_equation),
        key=f"{key_prefix}_text",
        height=80,
    )
    ok_eq, message = validate_equation(equation)
    if not ok_eq:
        st.error(message)
        return None
    st.success(message)

    # =================================================
    # =========== visualize implicit field ============
    # =================================================

    with st.expander("Preview of Field (mid z-slice, low-res)", expanded=False):
        _, fn = parse_equation(equation)
        n = 120
        g1 = np.linspace(origin_x, origin_x + size_x, n)
        g2 = np.linspace(origin_y, origin_y + size_y, n)
        gx, gy = np.meshgrid(g1, g2, indexing="ij")
        gz = np.zeros_like(gx) + origin_z + size_z / 2.0
        field = fn(gx, gy, gz)
        field = np.broadcast_to(np.asarray(field, dtype=float), gx.shape)

        # Keep the drawn slice physically proportioned: height / width = size_y / size_x.
        # The longest side is capped at BASE_PX, and COLORBAR_PX reserves the strip the
        # colorbar eats on the right so the heatmap itself (not the figure box) gets the ratio.
        BASE_PX = 450.0
        COLORBAR_PX = 90.0
        ratio = float(size_y) / float(size_x) if size_x else 1.0
        plot_h, plot_w = (BASE_PX, BASE_PX / ratio) if ratio >= 1.0 else (BASE_PX * ratio, BASE_PX)

        fig = go.Figure(go.Heatmap(x=g1, y=g2, z=field.T, colorscale="Portland"))
        fig.update_layout(
            width=int(round(plot_w + COLORBAR_PX)),
            height=int(round(plot_h)),
            margin=dict(l=0, r=0, t=20, b=0),
        )
        # one unit along x renders the same length as one unit along y
        fig.update_xaxes(constrain="domain")
        fig.update_yaxes(scaleanchor="x", scaleratio=1.0, constrain="domain")
        st.plotly_chart(fig, width="content", key=f"{key_prefix}_preview")
    return equation