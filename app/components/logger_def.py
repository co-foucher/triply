# triply: design, meshing, simulation and CT analysis of TPMS structures
# Copyright (C) 2026, Empa, Laboratory for High Performance Ceramics (201), Corentin Foucher
# SPDX-License-Identifier: MIT

import streamlit as st
from triply.logger import logger

@st.fragment
def set_log_level():
    """
    ============================================================================
    SET_LOG_LEVEL
    Set the log level for the logger based on the user's selection in the Streamlit app.
    ============================================================================

    RETURNS
    -------
    None

    NOTES
    -----
    - Draws a selectbox (DEBUG, INFO, WARNING, ERROR, CRITICAL; default INFO;
      key "log_level_selector") and sets the level of the shared "triply" logger.
    - An @st.fragment: changing the level reruns only this function, not the page.
    """
    log_level = st.selectbox(
        "Select Log Level",
        options=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        index=1,  # Default to INFO
        key="log_level_selector"
    )
    logger.setLevel(log_level)