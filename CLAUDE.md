# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A workspace for building custom **Super Mario desktop pets** on top of the third-party **eSheep / desktopPet** framework (Adrianotiger). A "pet" is a single `animations.xml` file (with the sprite sheet embedded as base64) that the eSheep app loads to render an animated character that walks, runs, jumps, and falls around the Windows desktop, respecting screen/window edges.

Two things live here:
1. **Our work** — Python scripts (root) that slice Mario sprite sheets and generate pet XML, plus the generated pets under `desktopPet-master/Pets/`.
2. **The vendored framework** — `desktopPet-master/` is the upstream eSheep repo (C# source, docs, sample pets). We don't build it; `desktopPet-master/docs/` and `pet_editor/` are gitignored.

## Environment / commands

- **Python** with **Pillow** (installed, 12.2.0) is the only toolchain. There is no build system, test suite, or linter.
- Regenerate the script-based pet: `python build_mario_pet.py` — writes `desktopPet-master/Pets/mario/animations.xml` and `spritesheet_preview.png`.
- Sprite tooling (run from repo root; all write into `catalogs/`):
  - `python catalog_sprites.py` — labeled visual catalogs of each source sheet + regenerates `sprite_catalog_data.py` (per-frame coordinates).
  - `python extract_frames.py` — dumps every frame as an individual labeled PNG under `catalogs/frames/`.
- All scripts use **hardcoded absolute Windows paths** (`C:\Local_Workspace\sheep\...`). If the repo moves, update the `SRC`/`ROOT`/`OUT_DIR` constants at the top of each script.

## Running a pet (there is no local build of the app)

The C# eSheep app is **not** built here (.NET SDK / MSBuild are not installed). To see a pet live, either:
- Run a prebuilt eSheep exe (from https://github.com/Adrianotiger/desktopPet/releases) with the pet folder in its `Pets/`, or
- Open the `.xml` in the bundled **Pet Editor** (`pet_editor/Pet Editor.exe`) — it has Test/Run, View XML, and a GraphViz animation-flow view. See `desktopPet-master/Pets/big_mario/pet_editor_guide.md` for a field-by-field guide.

## Two pets, two workflows — don't confuse them

- **`Pets/mario/`** — generated entirely by `build_mario_pet.py` from `Mario.png`. **Never hand-edit `Pets/mario/animations.xml`; it is overwritten.** Edit the Python instead.
- **`Pets/big_mario/`** — the current focus (branch `big-mario`). Hand/editor-authored `big_mario.xml` built from a NES sprite sheet (`NES_Mario_Luigi.png`), not produced by the build script. Edit its XML (or use the Pet Editor) directly.

Note: the eSheep app conventionally loads a pet from `animations.xml`; `big_mario.xml` is the working/authoring name.

## How a pet works (the model to understand before editing animations)

A pet XML has: `<header>` (name, base64 `.ico` icon), `<image>` (`tilesx`/`tilesy` grid dimensions + base64 PNG sprite sheet + `<transparency>` color/keyword), `<spawns>`, and `<animations>`. Key concepts:

- **Sprite sheet is a grid.** Frames are numbered left-to-right, top-to-bottom, indexed from 0. `tilesx`×`tilesy` defines the grid. In `build_mario_pet.py` the frame index constants (`WALK_R1`, `SPIN_A`, `IDLE_L`, …) map source poses to sheet positions — this mapping is the crux of getting animations right, and is documented in the docstring + the `sprite_catalog_data.py` coordinates.

- **Coordinate system:** `x>0` moves the sprite RIGHT, `x<0` LEFT; `y>0` DOWN (gravity), `y<0` UP (jump). So a left-facing walk uses left-facing frames **and** negative `x`.

- **Animations are a state machine.** Each `<animation>` has a `<sequence>` of `<frame>`s and one or more `<next probability="..">ID</next>` edges chosen by weighted random at the end of the sequence (weights should sum to 100). Additional transition triggers: `<border>` (hit a screen/window edge — used to turn around), `<gravity>` (start falling). `repeat` on the sequence controls loop count (`repeat="0"` plays once — important, was a past bug where walks looped forever), and supports expressions like `random/40+15`. `<spawn>` picks the initial animation.

- **Transparency is the recurring pain point.** Sprite-sheet cell backgrounds must be keyed out. `build_mario_pet.py` recolors the source's white cell background to **magenta** and sets `<transparency>Magenta</transparency>`; the icon keys white→alpha. `big_mario` sets `<transparency>transparent</transparency>`, which makes eSheep rely on the PNG's **alpha channel** — so the embedded PNG must actually have one. It originally did not: only the 8px margin around each 80×160 sprite cell was alpha, while the cell background itself was opaque RGB(146,144,255), which is what rendered as a blue box. That colour has since been keyed to alpha 0 in the embedded sheet. When a pet renders with colored boxes around it, this is why — check the real pixels, don't trust the `<transparency>` tag.

## Source assets (root)

- `Mario.png` — 21-frame sheet used by `build_mario_pet.py` (white cell bg, purple grid; see script docstring for the full frame map and cell x-ranges).
- `NES - Super Mario Bros - Mario & Luigi.png`, `NES - Super Mario Bros 3 - Mario & Luigi.png` — full NES sprite databases (multiple characters). Cataloged by `catalog_sprites.py`; the SMB1 sheet is the basis for `big_mario`.
- `sprite_catalog_data.py` — **generated**, do not hand-edit; regenerate via `catalog_sprites.py`.
