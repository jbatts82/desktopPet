"""
Build big_mario_ss.png from NES_Mario_Luigi.png.

Source: Big Mario row — Band 1 (y=31-63, 33px tall, 15 frames, 16px wide each)
Output: same format as existing big_mario_ss.png
  - 14 cols x 3 rows, tile size 96x192
  - Cols 0-6: right-facing originals
  - Cols 7-13: horizontally mirrored (left-facing)
  - 5x integer upscale, centered in tile with transparent padding
"""
from PIL import Image

SRC = r"C:\Local_Workspace\sheep\desktopPet-master\Pets\big_mario\NES_Mario_Luigi.png"
OUT = r"C:\Local_Workspace\sheep\desktopPet-master\Pets\big_mario\big_mario_ss.png"

BG = (0, 41, 140)   # dark blue background in source
TRANSPARENT = (0, 0, 0, 0)

SCALE  = 5
TW, TH = 96, 192    # output tile size (same as before)
COLS_ORIG = 7
ROWS      = 3

# Big Mario frame x-ranges (Band 1, y=31-63)
FRAMES_X = [
    (0, 15), (20, 35), (38, 53), (56, 71), (76, 91),
    (96, 111), (116, 131), (136, 151), (154, 169), (174, 189),
    (192, 207), (210, 225), (228, 243), (246, 261), (264, 279),
]
Y0, Y1 = 31, 63   # Big Mario band

def is_bg(c):
    return abs(c[0] - BG[0]) < 30 and abs(c[1] - BG[1]) < 30 and abs(c[2] - BG[2]) < 30

img = Image.open(SRC).convert("RGBA")

def extract_frame(x0, x1, y0, y1):
    cell = img.crop((x0, y0, x1 + 1, y1 + 1))
    px = cell.load()
    for cy in range(cell.height):
        for cx in range(cell.width):
            r, g, b, a = px[cx, cy]
            if is_bg((r, g, b)):
                px[cx, cy] = TRANSPARENT
    scaled = cell.resize((cell.width * SCALE, cell.height * SCALE), Image.NEAREST)
    # Centre in tile
    tile = Image.new("RGBA", (TW, TH), TRANSPARENT)
    ox = (TW - scaled.width)  // 2
    oy = (TH - scaled.height) // 2
    tile.alpha_composite(scaled, (ox, oy))
    return tile

# Select 7 frames per row from the 15 available
# Row 0: frames 0-6  (idle right, walk1-3, jump, skid, extra)
# Row 1: frames 7-13 (left-facing / other poses)
# Row 2: repeat key frames (idle, walk1-3, jump, skid, extra) — same as row 0 for now
frame_selections = [
    FRAMES_X[0:7],    # row 0
    FRAMES_X[7:14],   # row 1
    FRAMES_X[0:7],    # row 2 — repeats row 0; update once frame purposes are confirmed
]

sheet_w = TW * COLS_ORIG * 2
sheet_h = TH * ROWS
sheet = Image.new("RGBA", (sheet_w, sheet_h), TRANSPARENT)

for row, selection in enumerate(frame_selections):
    for col, (x0, x1) in enumerate(selection):
        tile = extract_frame(x0, x1, Y0, Y1)
        # Original
        sheet.alpha_composite(tile, (col * TW, row * TH))
        # Mirror
        sheet.alpha_composite(tile.transpose(Image.FLIP_LEFT_RIGHT),
                              ((COLS_ORIG + col) * TW, row * TH))

sheet.save(OUT)
print(f"Saved: {OUT}")
print(f"Size: {sheet.width}x{sheet.height}  ({sheet.width//TW} cols x {sheet.height//TH} rows)")
print(f"Tile: {TW}x{TH}, Scale: {SCALE}x")
print()
print("Row 0 — frames 0-6  (right-facing originals + mirrors)")
print("Row 1 — frames 7-13 (second set + mirrors)")
print("Row 2 — frames 0-6  (repeated until frame mapping is confirmed)")
