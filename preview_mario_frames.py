"""
Save a labeled preview of Big Mario frames from NES_Mario_Luigi.png
Band 1: y=31-63, 15 frames each ~16px wide
"""
from PIL import Image, ImageDraw, ImageFont

src = Image.open(r'C:\Local_Workspace\sheep\desktopPet-master\Pets\big_mario\NES_Mario_Luigi.png').convert('RGBA')
BG_RGB = (0, 41, 140)

# Big Mario frame x-coordinates from analysis
frames_x = [
    (0, 15), (20, 35), (38, 53), (56, 71), (76, 91),
    (96, 111), (116, 131), (136, 151), (154, 169), (174, 189),
    (192, 207), (210, 225), (228, 243), (246, 261), (264, 279),
]
Y0, Y1 = 31, 63

SCALE = 5
TW, TH = 100, 60  # tile size for preview (unscaled preview)

n = len(frames_x)
preview = Image.new('RGBA', (n * TW + 10, TH + 30), (30, 30, 30, 255))
draw = ImageDraw.Draw(preview)

for i, (x0, x1) in enumerate(frames_x):
    cell = src.crop((x0, Y0, x1 + 1, Y1 + 1))
    # Replace blue background with transparent
    px = cell.load()
    for y in range(cell.height):
        for x in range(cell.width):
            r, g, b, a = px[x, y]
            if abs(r - BG_RGB[0]) < 10 and abs(g - BG_RGB[1]) < 10 and abs(b - BG_RGB[2]) < 10:
                px[x, y] = (0, 0, 0, 0)
    scaled = cell.resize((cell.width * 3, cell.height * 3), Image.NEAREST)
    ox = i * TW + 5
    preview.alpha_composite(scaled, (ox, 5))
    draw.text((ox + 2, TH + 10), str(i), fill=(255, 255, 0, 255))

preview.save(r'C:\Local_Workspace\sheep\mario_frames_preview.png')
print(f"Saved preview: {n} frames, source size ~16x{Y1-Y0+1}px each")
print("Frame numbers labeled at bottom")
