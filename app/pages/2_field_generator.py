"""
Field generator: build a custom 3D scalar field step by step (gradients,
primitives, equations, distance-to-geometry, imported arrays, remaps,
smoothing...), preview it, and save it as a .npy that the Generate TPMS
page can pick up through any of its "Import from file" inputs (implicit
field, threshold, thickness, or period X/Y/Z).

STATUS: first version.

HOW THE PAGE IS BUILT
---------------------
The field is a stack of steps kept in st.session_state["fg_steps"]
(a list of {"id", "type"} dicts - only the identity and order of the
steps). Every parameter of a step lives in its own keyed widget,
f"fg_{step_id}_{param_name}", so moving/deleting a step never mixes
up the parameters of the others. Each rerun reads all widgets back into
a plain config dict per step and runs the pipeline:

    acc_0 = 0
    acc_i = (1 - w_i) * acc_{i-1} + w_i * op_i(acc_{i-1}, layer_i)

where layer_i is what a "generator" step produces on its own (cached,
see _compute_layer) and op_i is the chosen blend. A "modifier" step has
no layer of its own and just transforms acc_{i-1}. The page's own
"How this works" expander spells out every formula.

Nothing outside this file is modified: shared components are only
imported (equation input, field slice view, file picker, STL loader,
pad_to_square).
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

    from app.components.field_view import render_field_slice
    from app.components.documentation import generate_field_doc
    from app.components.field_generator_source import (
        GENERATOR_TYPES, MODIFIER_TYPES, STEP_TYPES, INTENDED_USES, 
        check_intended_use,
        render_step, 
        get_steps, 
        add_step, 
        restore_widget_state, 
        mirror_widget_state, 
        clear_steps,
        run_pipeline, 
        make_grid,
    )

init_state()

# ====================================================================
# ===================== Internal variables ===========================
# ====================================================================
DEFAULT_GRID = {"size_x": 10.0, "size_y": 10.0, "size_z": 10.0, "resolution": 64}

# ============================================================
# ===================== Start Page ===========================
# ============================================================
restore_widget_state()
st.title("Field Generator")
generate_field_doc()

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

mirror_widget_state()
