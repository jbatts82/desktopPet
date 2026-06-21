"""
Analyze NES_Mario_Luigi.png to find Big Mario frame coordinates.
Background color: (0, 41, 140) dark blue.
"""
from PIL import Image

img = Image.open(r'C:\Local_Workspace\sheep\desktopPet-master\Pets\big_mario\NES_Mario_Luigi.png').convert('RGB')
px = img.load()
W, H = img.size
BG = (0, 41, 140)

def is_bg(c):
    # strict exact match or very close
    return abs(c[0] - BG[0]) < 5 and abs(c[1] - BG[1]) < 5 and abs(c[2] - BG[2]) < 5

def is_white(c):
    return c[0] > 200 and c[1] > 200 and c[2] > 200

def is_sprite(c):
    # not bg, not white (labels)
    return not is_bg(c) and not is_white(c)

# Find rows with sprite pixels in left half (x < 292)
row_sprite = [any(is_sprite(px[x, y]) for x in range(292)) for y in range(H)]

bands = []
in_band = False
for y, has in enumerate(row_sprite):
    if has and not in_band:
        start = y; in_band = True
    elif not has and in_band:
        bands.append((start, y - 1)); in_band = False
if in_band:
    bands.append((start, H - 1))

print(f"Image: {W}x{H}, BG={BG}")
print(f"\nSprite row bands (x<292, excluding white text):")
for i, (y0, y1) in enumerate(bands):
    print(f"  Band {i}: y={y0}-{y1} (height={y1-y0+1}px)")

print(f"\nFrame columns per band:")
for i, (y0, y1) in enumerate(bands):
    col_sprite = [any(is_sprite(px[x, y]) for y in range(y0, y1+1)) for x in range(292)]
    frames = []
    in_f = False
    for x, has in enumerate(col_sprite):
        if has and not in_f:
            fx = x; in_f = True
        elif not has and in_f:
            frames.append((fx, x-1)); in_f = False
    if in_f:
        frames.append((fx, 291))
    print(f"  Band {i} (y={y0}-{y1}, h={y1-y0+1}): {len(frames)} frames")
    for j, (x0, x1) in enumerate(frames):
        print(f"    Frame {j}: x={x0}-{x1} (w={x1-x0+1})")
