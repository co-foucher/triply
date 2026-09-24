"""
Field generator: build a custom 3D scalar field step by step (gradients,
primitives, equations, distance-to-geometry, imported arrays, remaps,
smoothing...), preview it, and save it as a .npy that the Generate TPMS
page can pick up through any of its "Import from file" inputs (implicit
field, threshold, thickness, or period X/Y/Z).

STATUS: first version.


...
SESSION-STATE KEYS
------------------
Every key of this page starts with "fg_", so app.components.page_state.mirror_widget_state("fg_")
can save them all when the user leaves the page. `sid` is a step's id: 8 hex
characters from uuid4, generated once in add_step().

Page-level keys (2_field_generator.py)
    fg_size_x, fg_size_y, fg_size_z   number_input   grid size
    fg_resolution                     slider         grid resolution
    fg_new_step_kind                  segmented      "Generator" / "Modifier"
    fg_new_step_type                  selectbox      step type to add
    fg_show_step                      selectbox      which step's result to preview   (not mirrored)
    fg_preview_orientation            selectbox      slice orientation, made by render_field_slice(key="fg_preview")
    fg_preview_fieldfig               chart          slice view                        (not mirrored)
    fg_hist                           chart          histogram                         (not mirrored)
    fg_intended_use                   segmented      intended use check
    fg_name                           text_input     output file name

Per-step keys (field_generator_source.render_step / _render_params)
    fg_{sid}_enabled                  toggle         step on/off
    fg_{sid}_up / _down / _del        button         move / delete                     (not mirrored)
    fg_{sid}_blend                    selectbox      blend (layers only)
    fg_{sid}_weight                   slider         weight / strength w
    fg_{sid}_k                        number_input   smoothing k (smooth blends only)
    fg_{sid}_{name}                   one per Param in STEP_TYPES[type]["params"]
    fg_{sid}_{name}_0 / _1 / _2       the 3 components of a "vec3" Param
    fg_{sid}_eq_text                  text_area      Equation step (render_equation_input, key_prefix=f"fg_{sid}_eq")
    fg_{sid}_eq_preview               chart          its preview                       (not mirrored)
    fg_{sid}_path                     text_input     file path (Import .stl / Import .npy steps)
    fg_{sid}_path_browse_btn          button         its "Browse..." button            (not mirrored)
    fg_{sid}_path_browse_error        plain state    its error message, if any

Plain (non-widget) state
    fg_steps                          list of {"id": sid, "type": step_type}: order and type of the steps

"""
# Repo root isn't on sys.path by default - add it before importing
# anything under `app.*`. See app/_bootstrap.py for why this is inlined
# per-file rather than a shared import.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import os
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

import numpy as np
import streamlit as st

from app.components.branding import PAGE_ICON

st.set_page_config(page_title="Field generator", page_icon=PAGE_ICON, layout="wide")

with st.spinner("Loading triply toolkit..."):
    import pandas as pd
    import plotly.graph_objects as go

    from app.state import init_state, get_output_dir
    from app.components.page_state import restore_widget_state, mirror_widget_state, render_state_io

    from app.components.field_view import render_field_slice
    from app.components.documentation import generate_field_doc
    from app.components.field_generator_source import (
        GENERATOR_TYPES, MODIFIER_TYPES, STEP_TYPES, INTENDED_USES, 
        check_intended_use,
        render_step, 
        get_steps, 
        add_step, 
        clear_steps,
        run_pipeline, 
        make_grid,
    )

init_state()

# ====================================================================
# ===================== Internal variables ===========================
# ====================================================================
DEFAULT_GRID = {"size_x": 10.0, "size_y": 10.0, "size_z": 10.0, "resolution": 64}
FG_NOT_MIRRORED_KEYS = ("fg_show_step", "fg_hist")
FG_NOT_MIRRORED_SUFFIXES = ("_up", "_down", "_del", "_preview", "_fieldfig")
# ============================================================
# ===================== Start Page ===========================
# ============================================================
restore_widget_state("fg_")
st.title("Field Generator")
generate_field_doc()
# save / load this page's settings to <output folder>/sessions_saves/ (see app.components.page_state)
render_state_io("fg_", exclude_keys=FG_NOT_MIRRORED_KEYS, exclude_suffixes=FG_NOT_MIRRORED_SUFFIXES)

# ==========================================================
# ==================== grid parameters =====================
# ==========================================================
st.subheader("Grid parameters")
st.caption("Note: the saved file is a .npy. Thus it only carries matrices values, no pixel size or coordinate information.")
for k, v in DEFAULT_GRID.items():
    st.session_state.setdefault(f"fg_{k}", v)       #fg stands for field generator

# ----- ask user for grid parameters in a row of 4 widgets ----
g0, g1, g2, g3 = st.columns([2, 1, 1, 1])
g0.slider("Grid resolution (per axis)", 16, 256, step=8, key="fg_resolution",
          help="The field can be generated at a lower resolution than the TPMS: it is resampled there.")
g1.number_input("Size X", min_value=0.01, key="fg_size_x")
g2.number_input("Size Y", min_value=0.01, key="fg_size_y")
g3.number_input("Size Z", min_value=0.01, key="fg_size_z")

# ----- compute the grid key for caching the generated layers ----
# dictionnary defining the grid parameters, used to compute the generated layers
grid = {k: st.session_state[f"fg_{k}"] for k in DEFAULT_GRID}
# the grid key is used to cache the generated layers, so that if the user changes a step parameter but not the grid, the layer is not recomputed
grid_key = (float(grid["size_x"]), float(grid["size_y"]), float(grid["size_z"]), int(grid["resolution"]))


st.divider()
# ==========================================================
# ======================= step stack =======================
# ==========================================================
col_steps, col_preview = st.columns([1.4, 1])
with col_steps:
    st.subheader("Steps")
    # ---- check if steps have already been added ----
    steps = get_steps()
    if not steps:
        st.info("Add a first step below - e.g. a *Linear gradient* - then keep stacking steps "
                "and choose how each one blends with the result so far.")

    # ----- render each step in its own expander ----
    configs = [render_step(i = i, 
                           n_steps = len(steps), 
                           step = s, 
                           grid = grid) for i, s in enumerate(steps)]

    # ---- add a new step or clear all ----
    a1, a2, a3 = st.columns([3, 1.2, 1], vertical_alignment="bottom")
    with a1:
        next_step_kind = st.segmented_control(
            "New step type", ["Generator", "Modifier"], 
            key="fg_new_step_kind",
            default="Generator",
            help="A generator produces a new field from scratch that you combine with the previous one, a modifier only transforms the field so far."
            )
        if next_step_kind == "Generator":
            step_types = GENERATOR_TYPES
        else:
            step_types = MODIFIER_TYPES
        st.selectbox(
            "New step", step_types, key="fg_new_step_type",
            format_func=lambda t: f"{'Layer' if STEP_TYPES[t]['kind'] == 'generator' else 'Modifier'} - {t}",
            label_visibility="collapsed",
            )
    a2.button("Add step", icon=":material/add:", type="primary", on_click=add_step)
    a3.button("Clear all", on_click=clear_steps, disabled=not steps)

# ==========================================================
# ======================= compute ==========================
# ==========================================================
final, snapshots, rows, messages = None, [], [], {}
if configs:
    with st.spinner("Computing field..."):
        final, snapshots, rows, messages = run_pipeline(configs, grid_key)
    for cfg in configs:
        level, text = messages.get(cfg["id"], (None, None))
        if level == "error":
            cfg["message_slot"].error(text)
        elif level == "info":
            cfg["message_slot"].info(text)
    if configs and not snapshots:
        final = None
    if configs[0]["enabled"] and STEP_TYPES[configs[0]["type"]]["kind"] == "modifier":
        with col_steps:
            st.warning("The first step is a modifier: it acts on the initial zero field.")

# ==========================================================
# ================== preview & export ======================
# ==========================================================
with col_preview:
    st.subheader("Field preview (2D slice)")
    if final is None:
        st.info("Add at least one working step to see the field.")
    else:
        X, Y, Z = make_grid(*grid_key)
        labels = [lab for lab, _ in snapshots]
        shown = st.selectbox("Show result after step", labels, index=len(labels) - 1,
                             key="fg_show_step")
        field_shown = dict(snapshots)[shown]
        render_field_slice(field_shown, X, Y, Z, key="fg_preview",
                           value_range=(float(field_shown.min()), float(field_shown.max())))

        with st.expander("Statistics & histogram", expanded=False):
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            flat = field_shown.ravel()
            stride = max(1, flat.size // 200_000)          # subsample so the histogram stays light
            fig = go.Figure(go.Histogram(x=flat[::stride], nbinsx=80))
            fig.update_layout(height=250, margin=dict(l=0, r=0, t=20, b=0),
                              xaxis_title="field value", yaxis_title="voxels (subsampled)")
            st.plotly_chart(fig, width="stretch", key="fg_hist")

        st.subheader("Check & save")
        use = st.segmented_control("Intended use on Generate TPMS", INTENDED_USES,
                                   default="Thickness", key="fg_intended_use")
        if use:
            check_intended_use(use, final)

        name = st.text_input("File name", value="custom_field", key="fg_name")
        if st.button("Save field (.npy)", type="primary"):
            out_path = get_output_dir() / name
            np.save(str(out_path) + ".npy", final)
            st.success(f"Saved {out_path}.npy")

mirror_widget_state("fg_", exclude_keys=FG_NOT_MIRRORED_KEYS, exclude_suffixes=FG_NOT_MIRRORED_SUFFIXES)
