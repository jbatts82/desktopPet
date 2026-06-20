"""
Take the existing 7x3 Mario sprite sheet and produce a 14x3 sheet:
  - Columns 0-6  (frames 0-20):  originals (right-facing)
  - Columns 7-13 (frames 21-41): each tile flipped left-right (left-facing)

Input:  desktopPet-master/Pets/mario/spritesheet_preview.png
Output: desktopPet-master/Pets/mario/spritesheet_mirrored.png
"""

from PIL import Image
import os

SRC  = r"C:\Local_Workspace\sheep\desktopPet-master\Pets\mario\spritesheet_preview.png"
OUT  = r"C:\Local_Workspace\sheep\desktopPet-master\Pets\mario\spritesheet_mirrored.png"

COLS, ROWS = 7, 3

sheet = Image.open(SRC)
TW = sheet.width  // COLS   # tile width  (96)
TH = sheet.height // ROWS   # tile height (192)

new_sheet = Image.new("RGBA", (TW * COLS * 2, TH * ROWS))

for row in range(ROWS):
    for col in range(COLS):
        tile = sheet.crop((col * TW, row * TH, (col + 1) * TW, (row + 1) * TH))
        # original on left half
        new_sheet.paste(tile, (col * TW, row * TH))
        # mirrored on right half
        new_sheet.paste(tile.transpose(Image.FLIP_LEFT_RIGHT), ((COLS + col) * TW, row * TH))

new_sheet.save(OUT)
print(f"Saved {new_sheet.width}x{new_sheet.height}  ({COLS*2} cols x {ROWS} rows)")
print(f"  frames  0-20 = original right-facing")
print(f"  frames 21-41 = mirrored left-facing")
print(f"Output: {OUT}")
