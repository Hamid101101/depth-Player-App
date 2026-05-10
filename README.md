# Depth Player App

A desktop GUI application for visualizing and comparing stereo disparity / depth estimation results across multiple methods (e.g. FoundationStereo, RAFTStereo, RAFT). It loads an RGB image sequence alongside per-method `.npy` / `.npz` disparity files and plays them back synchronously with interactive zoom, pan, colormap, and visualization-range controls.

## Features

- Side-by-side viewing of an RGB sequence and up to three disparity/depth methods.
- Playback controls: play/pause, frame stepping (±1, ±10), slider scrubbing, reset.
- Switch between **Disparity** mode and **Depth** mode (depth computed from `focal`, `baseline`, `cx0`, `cx1`).
- Per-method visualization range (min/max) with a "from min/max" auto-fit button and a lock that synchronizes ranges across methods.
- Selectable Matplotlib colormaps (RdBu, plasma, magma, viridis, turbo, …).
- Zoom in / out / reset, mouse-wheel zoom, and click-drag panning on every canvas.
- Fullscreen visualization window per method with its own zoom/pan state.
- Method manager dialog to rename methods or change their default data path.
- Parameters and method config persisted to JSON in `application/assets/`.

## Project structure

```
depth-Player-App/
└── application/
    ├── main.py              # entry point — creates the ttkbootstrap window
    ├── manager_ui.py        # UIManager — all Tk/ttkbootstrap widgets and layout
    ├── controller.py        # Controller — file loading, disp/depth processing, playback
    ├── __init__.py
    └── assets/
        ├── parameters.json          # camera params, colormap, per-method min/max
        ├── compared_methods.json    # method names + default data paths
        ├── dataset_structure.json
        └── icons/
```

## Requirements

- Python 3.10+
- Packages: `ttkbootstrap`, `Pillow`, `numpy`, `matplotlib`, `seaborn`

Install:

```bash
pip install ttkbootstrap Pillow numpy matplotlib seaborn
```

On Linux you also need Tk available (`sudo apt install python3-tk`).

## Running

```bash
cd application
python main.py
```

## Usage

1. **Upload image sequence** — pick a folder of `.png` / `.jpg` / `.jpeg` frames for the RGB panel. Sibling folders matching each method name (or each method's `default_path`) are auto-resolved.
2. **Upload `<method>` Data** — pick a folder of `.npy` / `.npz` disparity files for any method that wasn't auto-resolved.
3. Use the playback bar to scrub or play the sequence.
4. Switch **Disp** ↔ **Depth** in the *Mode* panel; depth needs valid `focal length` and `baseline`.
5. Adjust per-method **min / max** in *Visualisation range*, or click **from min/max** to auto-fit. Toggle **Locked** on a method to sync its range with the first method.
6. Pick a colormap, then **Update parameters** to apply and persist to `assets/parameters.json`.
7. **Update methods** opens a dialog to rename a method or change its default path (saved to `assets/compared_methods.json`).

## File format notes

- Disparity files: `.npy` (raw array) or `.npz` (uses key `disparity` if present, else the first key).
- Values for `RAFT` and `RAFTStereo` are negated on load to match the sign convention of the other methods.
- Disparity is clipped to the range `[0, 150]` for the cached visualization data; out-of-range values are masked.

## Configuration files

- `application/assets/parameters.json` — `cx0`, `cx1`, `focal_lenght`, `baseline`, `color_map`, `is_depth_mode`, and per-method `min`/`max`.
- `application/assets/compared_methods.json` — list of methods with their `default_path` (relative paths are resolved against the selected RGB folder).
