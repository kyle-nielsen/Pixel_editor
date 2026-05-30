# Pixel Art Editor

A small Pygame editor for drawing **animated 32×32 sprites** — built to create
character and prop assets for a narrative game.

It ships with four sprites out of the box (`char1`, `char2`, `char3`, `props`),
each with its own animation frames and playback speed.

## Features

- 32×32 pixel canvas with a transparency checkerboard and toggleable grid
- Tools: **pencil**, **eraser**, **fill bucket**, **eyedropper/colour picker**
- 32-colour palette + current-colour readout
- **Animation**: multiple frames per sprite, add / duplicate / delete / clear,
  onion-skin overlay, and live playback at an adjustable FPS
- Scrolling timeline (mouse wheel steps through frames; the strip auto-scrolls
  to keep the current frame in view)
- Multiple sprites (3 characters + props) via top tabs
- Undo / redo
- Save & load the whole project as JSON
- Export the current sprite as a horizontal **spritesheet PNG** plus
  per-frame PNGs (drop straight into a game engine)

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
. .venv/bin/activate
python main.py
```

## Keyboard & mouse

| Action | Input |
| --- | --- |
| Pencil / Eraser / Fill / Picker | `P` / `E` / `F` / `I` |
| New / Duplicate / Delete / Clear frame | `N` / `D` / `Del` / `C` |
| Previous / Next frame | `,` / `.` or **mouse wheel** |
| Select sprite tab | `1` – `4` |
| Play / pause animation | `Space` |
| Toggle grid / onion skin | `G` / `O` |
| Undo / Redo | `Ctrl+Z` / `Ctrl+Shift+Z` (or `Ctrl+Y`) |
| Save / Load / Export | `Ctrl+S` / `Ctrl+O` / `Ctrl+E` |

The mouse drives everything else: click the tool buttons, palette swatches,
sprite tabs, and frame thumbnails; draw on the canvas by clicking/dragging.

## Output files

- `project.json` — the saved project (all sprites and frames)
- `export/<sprite>_sheet.png` — horizontal spritesheet
- `export/<sprite>/<sprite>_NN.png` — individual frames

## Layout

```
editor/
  constants.py   layout, palette, colours
  model.py       Frame/Sprite/Project data + JSON save/load + undo stack
  export.py      PNG spritesheet / per-frame export
  app.py         rendering, input handling, main loop
main.py          entry point
```
