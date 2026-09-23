# **triply**

**triply** is a Python library for designing TPMS (triply periodic minimal surface) structures: generating them, meshing them, checking them for 3D printing, simulating them in ABAQUS, and analysing CT scans of the printed parts.

**coroforge** is its point-and-click app: a local web interface over the same functions, for people who don't want to write code. It isn't a separate package: it ships with triply as the optional `[gui]` extra.

<img width="1531" height="865" alt="triply use cases and structure" src="https://github.com/user-attachments/assets/2d937bd7-631f-4cb0-888b-6f7126523808" />

## I want to use the app (coroforge)

On Windows, no Python or terminal needed:

1. Download the repository (**Code > Download ZIP** on GitHub, then extract it).
2. Double-click **`launcher.bat`**.
3. The app opens in your browser. The first launch downloads about 450 MB and takes a few minutes.

Everything else, from other ways to start it to what each page does, is in the **[coroforge guide](docs/coroforge.md)**.

## I want to use the library (triply)

Requires **Python 3.10**.

```powershell
conda create -n triply python=3.10
conda activate triply
pip install git+https://github.com/co-foucher/triply.git
```

```python
from triply.TPMS_classes import create_a_gyroid
```

Installation options, a quick start, and the list of modules are in the **[triply guide](docs/triply.md)**.

## Good to know
- **Renamed in v4.0.0:** this project used to be `gyroid_utils` (repo `GYROIDS`). Replace `import gyroid_utils` with `import triply`.
- **License:** EMPA, see the `license` field in `pyproject.toml`.
