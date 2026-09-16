"""
coroforge GUI - entry point.

Run with (from the repo root, after `pip install -e ".[gui]"`):
    streamlit run app/Home.py

This is a thin front end over the triply library (src/triply):
it implements no pipeline logic itself, only forms/wiring around the
existing TPMS / mesh / simulation / CT functions. See each page for its
current status.

Two things here have to be kept in sync by hand when a page is added or
renamed: the PAGES list (Streamlit builds the sidebar from the filenames
in app/pages/, it does not update this overview) and _PIPELINE_DOT, the
file-flow diagram. Both are plain data at the top of the file.
"""
# Repo root isn't on sys.path by default (app/ is a sibling of src/, not
# part of the installable package) - add it before importing anything
# under `app.*`. See app/_bootstrap.py for why this can't be a shared
# import instead.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

from app.state import init_state
from app.components.branding import PAGE_ICON, LOGO_FULL

st.set_page_config(page_title="coroforge", page_icon=PAGE_ICON, layout="wide")
init_state()

# ============================================================
# ============== define internal variables ===================
# ============================================================

# ---- One card per page (rendered as a bordered column + st.page_link) ----
# "path" is relative to this entry-point file, which is what st.page_link
# expects; it raises if the file doesn't exist, so a renamed page fails
# loudly here rather than silently dropping off the overview.
# "row" groups the cards: 0 is the main TPMS workflow, 1 is the pages that
# feed it and read its results.
PAGES = [
    {
        "row": 0,
        "path": "pages/1_Generate_TPMS.py",
        "label": "Generate TPMS",
        "icon": ":material/deployed_code:",
        "what": "Nine built-in surfaces or a custom equation, three "
                "density-field modes, baseplates and boolean combine, with "
                "live field and mesh previews.",
        "io": "**in** nothing, or an `.stl` / `.npy` to combine "
              "&nbsp;·&nbsp; **out** `.stl`, `.npy`, `.html`",
    },
    {
        "row": 0,
        "path": "pages/2_Prepare_Print.py",
        "label": "Prepare print",
        "icon": ":material/print:",
        "what": "Voxelize a mesh, label its overhangs, bridges and needed "
                "supports, search the print orientation that needs the least "
                "of them, and export the mesh rotated into it.",
        "io": "**in** `.stl` &nbsp;·&nbsp; **out** `.stl`, `.html`",
    },
    {
        "row": 0,
        "path": "pages/2_Simulation.py",
        "label": "Simulation",
        "icon": ":material/science:",
        "what": "Tet-mesh with fTetWild, build and run an ABAQUS job "
                "(frequency or static stiffness), then pull the "
                "displacement fields back out.",
        "io": "**in** `.stl` &nbsp;·&nbsp; **out** `.inp`, `.odb`, `.csv`",
    },
    {
        "row": 1,
        "path": "pages/3_CT_Analysis.py",
        "label": "CT Analysis",
        "icon": ":material/biotech:",
        "what": "Stack JPG / DICOM / TIFF slices into one volume, build a "
                "segmentation pipeline over it, and extract a mesh from the "
                "result.",
        "io": "**in** image slices, or an existing `.mhd` "
              "&nbsp;·&nbsp; **out** `.mhd`, `.stl`",
    },
    {
        "row": 1,
        "path": "pages/4_Library.py",
        "label": "Library",
        "icon": ":material/folder_open:",
        "what": "Browse the output folder: preview each structure and "
                "download its mesh, its saved field files and its saved "
                "preview.",
        "io": "**in** the output folder &nbsp;·&nbsp; **out** downloads",
    },
]

# ---- File-flow diagram (rendered client-side by st.graphviz_chart) ----
# Colors are the page palette re-used from 2_Simulation.py's FIELD_COLORS,
# with white label text on solid fills and mid-grey edges, so the graph
# stays legible in both the light and the dark Streamlit theme without
# needing to know which one is active. Grey nodes are not pages - they are
# the files the pages hand to each other.
_PIPELINE_DOT = """
digraph coroforge {
    rankdir=LR;
    bgcolor="transparent";
    pad=0.15;
    nodesep=0.28;
    ranksep=0.55;
    node [shape=box, style="rounded,filled", color="#00000000",
          fontname="Helvetica", fontsize=11, fontcolor="#ffffff",
          margin="0.18,0.10", height=0.42];
    edge [color="#888888", fontcolor="#888888", fontname="Helvetica",
          fontsize=9, penwidth=1.1, arrowsize=0.7];

    scans [label="CT slices", shape=note, fillcolor="#6b7280"];
    ct    [label="CT Analysis", fillcolor="#8a5cd6"];
    gen   [label="Generate TPMS", fillcolor="#2a78d6"];
    out   [label="output folder", shape=folder, fillcolor="#6b7280"];
    prep  [label="Prepare print", fillcolor="#1baf7a"];
    sim   [label="Simulation", fillcolor="#eb6834"];
    lib   [label="Library", fillcolor="#eda100"];
    res   [label="ABAQUS job", shape=note, fillcolor="#6b7280"];

    scans -> ct   [label="JPG/DICOM/TIFF"];
    ct    -> out  [label=".mhd + .stl"];
    gen   -> out  [label=".stl + .npy + .html"];
    out   -> gen  [label="combine / import", style=dashed, constraint=false];
    out   -> prep [label=".stl in\l.stl + .html out\l", dir=both];
    out   -> sim  [label=".stl"];
    out   -> lib  [label=".stl + .npy"];
    sim   -> res  [label=".inp / .odb / .csv"];
}
"""


# ============================================================
# ============== define internal functions ===================
# ============================================================
def _render_page_cards(row: int) -> None:
    """
    Draws one row of page cards. st.columns(border=True) is what makes them
    cards: sibling columns share the row's height, so the borders line up
    without any injected CSS. One column per page in that row, so a row is
    never padded out with an empty bordered box.
    """
    pages = [p for p in PAGES if p["row"] == row]
    for col, page in zip(st.columns(len(pages), border=True, gap="medium"), pages):
        with col:
            st.page_link(page["path"], label=page["label"], icon=page["icon"])
            st.caption(page["what"])
            st.caption(page["io"], unsafe_allow_html=True)


# ============================================================
# ===================== Start Page ===========================
# ============================================================
# 642 px = 3 screen px per logo pixel, so the pixel art stays crisp.
st.image(LOGO_FULL, width=642)
st.write(
    "GUI front end for the triply pipeline. Each page in the sidebar "
    "is one stage of the workflow, and they chain together through files in "
    "the output folder: an `.stl` exported on one page is what the next one "
    "asks you to select."
)

st.subheader("How the pages fit together")
st.graphviz_chart(_PIPELINE_DOT, width="stretch")
st.caption(
    "Coloured boxes are pages, grey ones are the files they hand to each "
    "other. The dashed edge is *Generate TPMS* reading a mesh or field back "
    "in - to gyroid-fill an existing part, or to pick up where a previous "
    "export left off."
)

st.divider()

st.subheader("Pages")
_render_page_cards(0)
_render_page_cards(1)

st.info(
    "Every page except the Library opens with a collapsed "
    "**\"How this works\"** panel walking through its pipeline step by step. "
    "Start there if a parameter isn't obvious - the panels explain what each "
    "section of the page is actually doing, not just what the widget is "
    "called."
)
st.caption(
    "Simulation additionally needs fTetWild and ABAQUS installed locally, "
    "and CT Analysis' full interactive viewer opens as a separate desktop "
    "window rather than in the browser."
)
st.caption(
    "The sidebar sets the **output folder** every page reads from and writes "
    "to, and the log level for the toolkit's own messages."
)
