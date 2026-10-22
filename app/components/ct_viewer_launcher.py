"""
Launches triply.CT_visualization_window's interactive viewer as a
separate process for a given .mhd file already on disk. Shared by
app/pages/3_CT_Analysis.py (loaded volume) and app/components/ct_pipeline.py
(processed mask preview) so the subprocess/backend-forcing logic and the
full-vs-lightweight toggle only live in one place.

Two viewer modes, both from CT_visualization_window.py:
- Full (open_window): brush/rainbow/histogram tooling, scroll-to-scrub.
- Lightweight (lightweigth_open): just a Z-slice slider + click-to-inspect
  greyvalues - opens faster and uses less memory, handy for a quick look
  or for large volumes where the full toolset isn't needed.

Split into a toggle (render_lightweight_toggle) and a launcher
(launch_ct_viewer) rather than one combined button, so callers that need
to do work before launching (e.g. ct_pipeline.py writing a temp .mhd for
the current result) can keep that work gated behind their own "open
viewer" button click instead of it re-running on every page rerun.
"""
import os
import subprocess
import sys
import numpy as np
import plotly.graph_objects as go

import streamlit as st

"""
#=====================================================================================================================
0 - (reserved)
1 - render_lightweight_toggle
2 - launch_ct_viewer
3 - CT_histogram
4 - launch_ct_viewer_for_selection
#=====================================================================================================================
"""

__all__ = ["render_lightweight_toggle", "launch_ct_viewer", "CT_histogram",
           "launch_ct_viewer_for_selection"]


# =====================================================================
# 1) render_lightweight_toggle
# =====================================================================
def render_lightweight_toggle(key: str) -> bool:
    """
    ============================================================================
    1) RENDER_LIGHTWEIGHT_TOGGLE
    Renders the "use lightweight viewer" checkbox and returns its state.
    ============================================================================

    PARAMETERS
    ----------
    key : str
        Prefix used to namespace this checkbox's Streamlit widget key
        (f"{key}_lightweight"), so multiple toggles can coexist on the
        same page.

    RETURNS
    -------
    lightweight : bool
        True if the lightweight viewer should be used.
    """
    return st.checkbox(
        "Use lightweight viewer (slider only - faster, less memory)",
        value=False,
        key=f"{key}_lightweight",
    )


# =====================================================================
# 2) launch_ct_viewer
# =====================================================================
def launch_ct_viewer(mhd_path: str, lightweight: bool = False) -> None:
    """
    ============================================================================
    2) LAUNCH_CT_VIEWER
    Launches triply.CT_visualization_window on `mhd_path` in a
    separate process - open_window (full) or lightweigth_open, depending
    on `lightweight`.
    ============================================================================

    PARAMETERS
    ----------
    mhd_path : str
        Path to the .mhd file to open.
    lightweight : bool, optional
        If True, launches the lightweight (slider-only) viewer instead of
        the full one (default = False).

    RETURNS
    -------
    None
    """
    # CT_visualization_window.py is written for Jupyter, where the user
    # runs `%matplotlib qt` themselves before calling it - it never sets
    # a backend on its own. Here there's no such magic, so matplotlib
    # falls back to whatever it auto-detects; if Streamlit's own process
    # has MPLBACKEND=Agg set (it often does, being headless-by-default),
    # a plain subprocess would inherit that env var and get the
    # non-interactive Agg backend ("FigureCanvasAgg is non-interactive"
    # warning, no window ever appears). Force QtAgg explicitly, and
    # strip any inherited MPLBACKEND so it can't override that.
    env = os.environ.copy()
    env.pop("MPLBACKEND", None)
    entrypoint = "lightweigth_open" if lightweight else "open_window"
    subprocess.Popen(
        [
            sys.executable, "-c",
            "import matplotlib; matplotlib.use('QtAgg'); "
            "import SimpleITK as sitk, triply.CT_visualization_window as w; "
            f"w.{entrypoint}(sitk.ReadImage(r'{mhd_path}'))",
        ],
        env=env,
    )
    st.info(
        "Launching in a separate window - requires a local display "
        "and PyQt5/PySide installed (see CT_visualization_window.py)."
    )


# =====================================================================
# 3) CT_histogram
# =====================================================================
def CT_histogram(hist: np.ndarray, bin_edges: np.ndarray) -> None:
    """
    ============================================================================
    3) CT_HISTOGRAM
    Renders a greyvalue histogram from an already-computed (hist,
    bin_edges) pair - e.g. from app.pages.3_CT_Analysis._load_histogram,
    which caches that computation separately, keyed on (mhd_path, bins)
    rather than on the volume array itself (hashing a full CT volume on
    every rerun would cost more than just recomputing the histogram - see
    that function's docstring). Kept as a pure "given numbers, draw a
    chart" function so the (cached) computation and the (cheap, always-
    rerun) rendering stay decoupled, the same way _build_result_fig and
    _run_pipeline are decoupled in ct_pipeline.py.

    Renders via Plotly + st.plotly_chart, matching every other figure in
    this app (see the Heatmap previews in 3_CT_Analysis.py/ct_pipeline.py/
    equation_input.py) - a bare matplotlib plt.show(), which this used to
    call, has nowhere to display to inside the Streamlit server process
    and never reaches the browser at all.
    ============================================================================

    PARAMETERS
    ----------
    hist : np.ndarray
        Histogram counts per bin.
    bin_edges : np.ndarray
        Bin edge values (length len(hist) + 1).

    RETURNS
    -------
    None
    """
    ignore_zeroes = st.toggle("Ignore zeroes", value=False, key="histogram_ignore_zeroes")
    # one centre and one width per bin, computed from the full set of edges
    # (len(bin_edges) = len(hist) + 1), before any bin is removed
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    bin_width = bin_edges[1] - bin_edges[0]
    if ignore_zeroes:
        # one boolean per bin (length len(hist)): True for the bin whose
        # interval [left edge, right edge) contains the greyvalue 0
        bin_contains_zero = (bin_edges[:-1] <= 0) & (bin_edges[1:] > 0)
        hist = hist[~bin_contains_zero]
        bin_centers = bin_centers[~bin_contains_zero]
    fig = go.Figure(go.Bar(x=bin_centers, y=hist, width=bin_width))
    fig.update_layout(
        xaxis_title="Greyvalue",
        yaxis_title="Count",
        bargap=0,
        height=350,
        margin=dict(l=0, r=0, t=20, b=0),
    )
    st.plotly_chart(fig, width="stretch")


# =====================================================================
# 4) launch_ct_viewer_for_selection
# =====================================================================
def launch_ct_viewer_for_selection(mhd_path: str, selection_path: str) -> None:
    """
    ============================================================================
    4) LAUNCH_CT_VIEWER_FOR_SELECTION
    Opens the full viewer (open_window) on `mhd_path` in a separate
    process, like launch_ct_viewer, and - when the user closes the window -
    saves the voxels clicked with the brush to `selection_path`. Used by
    the "Manual selection (viewer)" step of ct_pipeline.py.
    ============================================================================

    PARAMETERS
    ----------
    mhd_path : str
        Path to the .mhd file to open (the loaded, original volume).
    selection_path : str
        .npz file written when the window is closed, holding:
          - "pixels": int array of shape (N, 3), one row (x, y, slice) per
            selected voxel - exactly what open_window returns;
          - "shape": the (Z, Y, X) shape of the volume the clicks were made
            on (SimpleITK's GetSize() is (X, Y, Z), hence the [::-1]).

    RETURNS
    -------
    None
        Returns immediately: the viewer runs in its own process, and the
        app only notices the new file on its next rerun.

    NOTES
    -----
    - Why a file: open_window does return the selected voxels, but in the
      subprocess, so the Streamlit process never sees that return value.
      The subprocess saves it instead.
    - Written to "<name>.tmp.npz" first, then renamed (os.replace): the
      app never reads a half-written file.
    - If the window is closed with no voxel selected, nothing is written,
      so a previous selection is not wiped by just opening and closing
      the viewer. Each saved selection REPLACES the previous one (the
      viewer always starts with nothing selected).
    - Same matplotlib backend handling as launch_ct_viewer (QtAgg forced,
      inherited MPLBACKEND removed) - see the comment there.
    - `!r` writes each path as a quoted Python string literal, so Windows
      backslashes and spaces in the paths survive inside the -c script.
    """
    env = os.environ.copy()
    env.pop("MPLBACKEND", None)
    os.makedirs(os.path.dirname(selection_path), exist_ok=True)
    temporary_path = selection_path[:-len(".npz")] + ".tmp.npz"   # keeps the .npz ending, so np.savez doesn't add one
    # the Python script run by the subprocess, one line per list entry
    script = "\n".join([
        "import os",
        "import numpy as np",
        "import matplotlib",
        "matplotlib.use('QtAgg')",
        "import SimpleITK as sitk",
        "import triply.CT_visualization_window as w",
        f"image = sitk.ReadImage({mhd_path!r})",
        "pixels = np.asarray(w.open_window(image), dtype=np.int64).reshape(-1, 3)   # blocks until the window is closed",
        "shape = np.array(image.GetSize()[::-1], dtype=np.int64)                    # (X, Y, Z) -> (Z, Y, X)",
        "if len(pixels) > 0:",
        f"    np.savez({temporary_path!r}, pixels=pixels, shape=shape)",
        f"    os.replace({temporary_path!r}, {selection_path!r})",
    ])
    subprocess.Popen([sys.executable, "-c", script], env=env)
