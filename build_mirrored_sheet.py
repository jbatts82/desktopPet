"""
Regenerate spritesheet_mirrored.png for the big_mario project.

Extracts 21 Mario frames directly from Mario.png, trims 1px from each
edge of each source cell, scales 3x, then centers in a 96x192 tile with
3px magenta padding on every side — guaranteeing no sprite pixels ever
touch a tile boundary.

Output layout  (1344 x 576,  14 cols x 3 rows):
  Cols  0-6 : original right-facing frames (row 0 = frames 0-6, row 1 = 7-13, row 2 = 14-20)
  Cols 7-13 : per-tile horizontal mirror  (left-facing)
"""

from PIL import Image
import os

SRC = r"C:\Local_Workspace\sheep\Mario.png"
OUT = r"C:\Local_Workspace\sheep\desktopPet-master\Pets\big_mario\spritesheet_mirrored.png"

MAGENTA = (255, 0, 255, 255)
WHITE   = (255, 255, 255, 255)

# Source crop coordinates for each of the 21 frames (x-start, x-end inclusive)
cells_x = [
    (3,34),(37,68),(71,102),(105,136),(139,170),(173,204),(207,238),
    (241,272),(275,306),(309,340),(343,374),(377,408),(411,442),
    (445,476),(479,510),(513,544),(547,578),(581,612),(615,646),
    (649,680),(683,714),
]
ROW0_Y  = (5, 68)   # inclusive y-range for big Mario row  (64px tall)

TRIM   = 1          # source pixels to remove from each edge before scaling
SCALE  = 3          # integer upscale factor
TW, TH = 96, 192    # final tile size in the sheet

COLS_ORIG = 7
ROWS      = 3

img = Image.open(SRC).convert("RGBA")

# Source region for each cell (30x62 after 1px trim)
src_w = (cells_x[0][1] - cells_x[0][0] + 1) - 2 * TRIM   # 32 - 2 = 30
src_h = (ROW0_Y[1] - ROW0_Y[0] + 1) - 2 * TRIM            # 64 - 2 = 62

# Scaled sprite size
spr_w = src_w * SCALE   # 90
spr_h = src_h * SCALE   # 186

# Padding so the sprite sits centered in TW x TH
pad_x = (TW - spr_w) // 2   # 3
pad_y = (TH - spr_h) // 2   # 3

print(f"Source cell (trimmed): {src_w}x{src_h}")
print(f"Scaled sprite:         {spr_w}x{spr_h}")
print(f"Tile size:             {TW}x{TH}  (padding {pad_x}px on each side)")

tiles = []
for cx0, cx1 in cells_x:
    x0 = cx0 + TRIM
    x1 = cx1 + 1 - TRIM   # PIL crop right is exclusive
    y0 = ROW0_Y[0] + TRIM
    y1 = ROW0_Y[1] + 1 - TRIM

    cell = img.crop((x0, y0, x1, y1))
    # Replace white background with magenta
    pixels = cell.load()
    for py in range(cell.height):
        for px_ in range(cell.width):
            if pixels[px_, py] == WHITE:
                pixels[px_, py] = MAGENTA
    # Scale with NEAREST to keep crisp pixel art
    scaled = cell.resize((spr_w, spr_h), Image.NEAREST)

    # Place centered in a clean magenta tile
    tile = Image.new("RGBA", (TW, TH), MAGENTA)
    tile.paste(scaled, (pad_x, pad_y))
    tiles.append(tile)

# Build 14-col x 3-row sheet
sheet_w = TW * COLS_ORIG * 2
sheet_h = TH * ROWS
sheet = Image.new("RGBA", (sheet_w, sheet_h), MAGENTA)

for idx, tile in enumerate(tiles):
    col = idx % COLS_ORIG
    row = idx // COLS_ORIG
    # Original on left half
    sheet.paste(tile, (col * TW, row * TH))
    # Mirror on right half
    sheet.paste(tile.transpose(Image.FLIP_LEFT_RIGHT), ((COLS_ORIG + col) * TW, row * TH))

sheet.save(OUT)

print(f"\nSaved: {OUT}")
print(f"Size:  {sheet.width}x{sheet.height}  ({sheet.width // TW} cols x {sheet.height // TH} rows)")
print(f"Tile:  {TW}x{TH}  ->  {sheet.width // TW * sheet.height // TH} total tiles")
print(f"14 divisible: {sheet.width % 14 == 0}   3 divisible: {sheet.height % 3 == 0}")
print()
print("Frame layout:")
print("  Cols  0-6  = right-facing originals")
print("  Cols 7-13  = left-facing mirrors")
print("  Row 0 frames  0-6:  IDLE_R WALK_R1 WALK_R2 WALK_R3 SPIN_A JUMP SKID")
print("  Row 1 frames  7-13: SPIN_B WALK_R4 SPIN_C SPIN_D TR1 TR2 TR3")
print("  Row 2 frames 14-20: TR4 IDLE_L WALK_L1 WALK_L2 WALK_L3 WALK_L4 WALK_L5")
