"""
Everything that keeps a page's settings: across page switches (the
widget-state mirror) and across sessions (saving/loading them to a file).

Both work on a page's widget-key prefix (e.g. "fg_" for the field
generator, "tpms_" for Generate TPMS): every setting of a page is a
st.session_state key starting with that prefix.

Usage in a page:
    restore_widget_state("fg_")          # at the top, before any widget
    render_state_io("fg_", ...)          # just below the documentation
    ...
    mirror_widget_state("fg_", ...)      # at the very end of the script
(same exclusions passed to render_state_io and mirror_widget_state).

#=====================================================================================================================
1 - widget-state mirror     (restore_widget_state, mirror_widget_state, _collect_page_state)
2 - save / load to a file   (get_saves_dir, save_page_state, load_page_state, render_state_io)
#=====================================================================================================================
"""
import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from app.state import get_output_dir


# =====================================================================
# 1) Widget-state mirror (keeps a page's settings across page switches)
# =====================================================================
# Streamlit deletes a widget's session_state key at the end of any run in
# which that widget isn't drawn - i.e. as soon as the user opens another
# page - so every setting of a page resets when the user comes back.
# Fix: at the end of each run, copy all of a page's widget values (every
# key starting with that page's prefix) into one plain dict, which
# Streamlit never deletes; at the start of the next run, put back any
# value that went missing, before the widgets are created (the only
# moment Streamlit allows writing a widget's value).
#
# Usage in a page (keys all starting with e.g. "fg_"):
#     restore_widget_state("fg_")    # at the top, before any widget
#     ...
#     mirror_widget_state("fg_")     # at the very end of the script

# Keys whose value can't be written through st.session_state (buttons,
# including the "Browse..." button of file_picker.browse_file) - they
# are skipped on every page.
_ALWAYS_SKIPPED_SUFFIXES = ("_browse_btn",)


def _mirror_key(prefix: str) -> str:
    """Plain session_state key holding the mirrored values of one page."""
    return f"{prefix}_mirror"


def restore_widget_state(prefix: str) -> None:
    """
    ============================================================================
    RESTORE_WIDGET_STATE
    Puts back every widget value saved by mirror_widget_state(prefix) whose
    key is missing from st.session_state (i.e. was deleted by Streamlit
    while the user was on another page). Keys still present are left alone,
    so it never overrides what the user just did.
    ============================================================================

    PARAMETERS
    ----------
    prefix : str
        The page's widget-key prefix, e.g. "fg_". Must be the same as the
        one passed to mirror_widget_state().

    NOTES
    -----
    Must be called at the top of the page, before the widgets are created.
    """
    for k, v in st.session_state.get(_mirror_key(prefix), {}).items():
        if k not in st.session_state:
            st.session_state[k] = v


def mirror_widget_state(prefix: str,
                        exclude_keys: tuple = (),
                        exclude_suffixes: tuple = ()) -> None:
    """
    ============================================================================
    MIRROR_WIDGET_STATE
    Copies the current value of every st.session_state key starting with
    `prefix` into one plain dict (st.session_state[f"{prefix}_mirror"]), for
    restore_widget_state() to put back after a page switch.
    ============================================================================

    PARAMETERS
    ----------
    prefix : str
        The page's widget-key prefix, e.g. "fg_".
    exclude_keys : tuple of str, optional
        Exact keys not to mirror: plain (non-widget) state that survives on
        its own, or widgets whose options change so an old value could be
        invalid.
    exclude_suffixes : tuple of str, optional
        Key endings not to mirror, on top of the always-skipped ones
        (_ALWAYS_SKIPPED_SUFFIXES): buttons, whose value Streamlit refuses to
        have written, and charts, whose key holds selection state rather
        than user input.

    NOTES
    -----
    Must be called at the very end of the page. If part of the page is an
    @st.fragment, a fragment-only rerun does not reach the end of the
    script, so call it at the end of the fragment as well.
    """
    st.session_state[_mirror_key(prefix)] = _collect_page_state(prefix, exclude_keys, exclude_suffixes)


def _collect_page_state(prefix: str,
                        exclude_keys: tuple = (),
                        exclude_suffixes: tuple = ()) -> dict:
    """
    {key: value} of every st.session_state key starting with `prefix`,
    except the mirror itself, `exclude_keys`, and keys ending with one of
    `exclude_suffixes` or _ALWAYS_SKIPPED_SUFFIXES. Shared by
    mirror_widget_state() and save_page_state(), so a saved file holds
    exactly what a page switch keeps.
    """
    skipped_suffixes = _ALWAYS_SKIPPED_SUFFIXES + tuple(exclude_suffixes)
    mirror_key = _mirror_key(prefix)
    return {
        k: st.session_state[k] for k in list(st.session_state.keys())
        if isinstance(k, str) and k.startswith(prefix)
        and k != mirror_key
        and k not in exclude_keys
        and not k.endswith(skipped_suffixes)
    }


# =====================================================================
# 2) Save / load a page's settings to a file
# =====================================================================
# One JSON file per save, in <output folder>/sessions_saves/, holding the
# same values as the page's mirror (see _collect_page_state) plus a small
# header:
#     {"format_version": 1, "prefix": "fg_", "saved_at": "...", "state": {...}}
# "prefix" ties a file to its page: a file saved on one page is not listed
# on another.
#
# Usage in a page, just below its documentation:
#     render_state_io("fg_", exclude_keys=..., exclude_suffixes=...)
# with the same exclusions as passed to mirror_widget_state().
#
# KNOWN LIMITATION: values are not checked against the widgets' options.
# A file saved before an option was renamed/removed can hold a value the
# widget no longer accepts: a selectbox then silently returns it to the
# page code, a segmented_control raises "The default value ... is not part
# of the options". Files written by the current version are always valid;
# "format_version" is there to migrate old files if that ever becomes
# necessary.

SAVES_DIRNAME = "sessions_saves"
STATE_FILE_VERSION = 1


def get_saves_dir() -> Path:
    """<output folder>/sessions_saves, created if needed."""
    d = get_output_dir() / SAVES_DIRNAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_page_state(prefix: str,
                    name: str,
                    exclude_keys: tuple = (),
                    exclude_suffixes: tuple = ()) -> Path:
    """
    ============================================================================
    SAVE_PAGE_STATE
    Writes the current settings of one page (every `prefix` key, as selected
    by _collect_page_state) to get_saves_dir() / f"{name}.json". An
    existing file of the same name is overwritten.
    ============================================================================

    PARAMETERS
    ----------
    prefix : str
        The page's widget-key prefix, e.g. "fg_".
    name : str
        File name typed by the user (".json" is added if missing).
    exclude_keys, exclude_suffixes : tuple of str, optional
        Same exclusions as the page passes to mirror_widget_state().

    RETURNS
    -------
    path : Path
        The file written.

    RAISES
    ------
    ValueError
        If the name is empty or a value can't be written as JSON.
    """
    name = name.strip()
    if not name:
        raise ValueError("Please type a file name.")
    path = get_saves_dir() / (name if name.endswith(".json") else name + ".json")
    content = {
        "format_version": STATE_FILE_VERSION,
        "prefix": prefix,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "state": _collect_page_state(prefix, exclude_keys, exclude_suffixes),
    }
    try:
        text = json.dumps(content, indent=2)
    except TypeError as e:  # a value JSON can't represent (e.g. a numpy array)
        raise ValueError(f"These settings can't be saved as JSON: {e}") from e
    path.write_text(text, encoding="utf-8")
    return path


def load_page_state(prefix: str, path: Path) -> int:
    """
    ============================================================================
    LOAD_PAGE_STATE
    Replaces the current settings of one page with those saved in `path`.
    Must run from a widget callback (on_click), i.e. before the page's
    widgets are drawn - the only moment Streamlit allows writing their
    values.
    ============================================================================

    PARAMETERS
    ----------
    prefix : str
        The page's widget-key prefix, e.g. "fg_".
    path : Path
        A file written by save_page_state() for this page.

    RETURNS
    -------
    n : int
        Number of values loaded.

    RAISES
    ------
    ValueError
        If the file is unreadable, belongs to another page, or was written
        by a newer format version.

    NOTES
    -----
    All current `prefix` keys are deleted first (buttons aside), so a
    setting missing from the file goes back to its default instead of
    keeping its current value.
    """
    try:
        content = json.loads(Path(path).read_text(encoding="utf-8"))
        state = content["state"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise ValueError(f"Could not read {Path(path).name}: {e}") from e
    if content.get("prefix") != prefix:
        raise ValueError(f"{Path(path).name} was saved on another page.")
    if content.get("format_version", 0) > STATE_FILE_VERSION:
        raise ValueError(f"{Path(path).name} was saved by a newer version of the app.")

    # clear the page's current settings (button values can't be written, so leave them)
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith(prefix) and not k.endswith(_ALWAYS_SKIPPED_SUFFIXES):
            del st.session_state[k]
    # write the saved ones, and the mirror so a page switch keeps them too
    loaded = {k: v for k, v in state.items()
              if k.startswith(prefix) and not k.endswith(_ALWAYS_SKIPPED_SUFFIXES)}
    for k, v in loaded.items():
        st.session_state[k] = v
    st.session_state[_mirror_key(prefix)] = dict(loaded)
    return len(loaded)


def _list_state_files(prefix: str) -> list:
    """Files of get_saves_dir() saved for this page, newest first (unreadable ones skipped)."""
    files = []
    for p in sorted(get_saves_dir().glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            if json.loads(p.read_text(encoding="utf-8")).get("prefix") == prefix:
                files.append(p)
        except (OSError, ValueError, AttributeError):
            continue
    return files


def _on_save(prefix: str, exclude_keys: tuple, exclude_suffixes: tuple) -> None:
    ui = f"stateio_{prefix}"
    try:
        path = save_page_state(prefix, st.session_state.get(ui + "name", ""), exclude_keys, exclude_suffixes)
        st.session_state[ui + "msg"] = ("success", f"Settings saved to {path}")
        st.session_state[ui + "file"] = path.name   # select it in the load list
    except (ValueError, OSError) as e:
        st.session_state[ui + "msg"] = ("error", str(e))


def _on_load(prefix: str) -> None:
    ui = f"stateio_{prefix}"
    name = st.session_state.get(ui + "file")
    try:
        n = load_page_state(prefix, get_saves_dir() / name)
        st.session_state[ui + "msg"] = ("success", f"Loaded {n} settings from {name}")
    except (ValueError, OSError, TypeError) as e:
        st.session_state[ui + "msg"] = ("error", str(e))


def render_state_io(prefix: str,
                    exclude_keys: tuple = (),
                    exclude_suffixes: tuple = ()) -> None:
    """
    ============================================================================
    RENDER_STATE_IO
    Draws the "Save settings" / "Load settings" row of a page: a file name
    box + Save button, and a list of this page's saved files + Load button.
    Files go to <output folder>/sessions_saves/.
    ============================================================================

    PARAMETERS
    ----------
    prefix : str
        The page's widget-key prefix, e.g. "fg_".
    exclude_keys, exclude_suffixes : tuple of str, optional
        Same exclusions as the page passes to mirror_widget_state().

    NOTES
    -----
    Its own widget keys start with f"stateio_{prefix}", not with `prefix`,
    so they are never saved, mirrored or cleared by a load.
    """
    ui = f"stateio_{prefix}"
    files = [p.name for p in _list_state_files(prefix)]
    if st.session_state.get(ui + "file") not in files:   # e.g. file deleted since
        st.session_state.pop(ui + "file", None)

    with st.expander(
            "Load and save session settings",
            expanded=False,
        ):
        c_save, c_load = st.columns(2, vertical_alignment="bottom")
        with c_save:
            s1, s2 = st.columns([3, 1.2], vertical_alignment="bottom")
            s1.text_input("Save page settings as", key=ui + "name", placeholder="file name",
                          help=f"Saved to <output folder>/{SAVES_DIRNAME}/<name>.json")
            s2.button("Save", icon=":material/save:", key=ui + "save_btn", width="stretch",
                      on_click=_on_save, args=(prefix, tuple(exclude_keys), tuple(exclude_suffixes)),
                      disabled=not st.session_state.get(ui + "name", "").strip())
        with c_load:
            l1, l2 = st.columns([3, 1.2], vertical_alignment="bottom")
            l1.selectbox("Load page settings", files, key=ui + "file",
                         placeholder="no saved settings for this page yet" if not files else "choose a file",
                         index=None if not files else 0)
            l2.button("Load", icon=":material/upload_file:", key=ui + "load_btn", width="stretch",
                      on_click=_on_load, args=(prefix,), disabled=not files)
        msg = st.session_state.pop(ui + "msg", None)   # shown once, right after the click
        if msg:
            (st.success if msg[0] == "success" else st.error)(msg[1])
