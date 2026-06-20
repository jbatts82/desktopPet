"""
Build a Mario desktop pet for the eSheep (desktopPet) application.

Frame map (from Mario.png row 0, 21 frames total):
  0  = idle right (standing, facing right)
  1  = walk right step 1
  2  = walk right step 2
  3  = walk right step 3
  4  = spin frame A (turning, front-facing)
  5  = jump (airborne, arms out)
  6  = skid (heels-down brake)
  7  = spin frame B
  8  = walk right step 4 / run
  9  = spin frame C
  10 = spin frame D
  11-14 = additional walk-right frames (transition / run)
  15 = idle left (standing, facing left)
  16 = walk left step 1
  17 = walk left step 2
  18 = walk left step 3
  19 = walk left step 4
  20 = walk left step 5

eSheep coordinate system:
  x > 0  =>  sprite moves RIGHT on screen
  x < 0  =>  sprite moves LEFT  on screen
  y > 0  =>  sprite moves DOWN  on screen
  y < 0  =>  sprite moves UP    on screen

So:
  walk_right uses RIGHT-facing frames + positive x
  walk_left  uses LEFT-facing  frames + negative x
"""

import base64, io, os
from PIL import Image

SRC     = r"C:\Local_Workspace\sheep\Mario.png"
OUT_DIR = r"C:\Local_Workspace\sheep\desktopPet-master\Pets\mario"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Extract frames ────────────────────────────────────────────────────────────
img = Image.open(SRC).convert("RGBA")
WHITE   = (255, 255, 255, 255)
MAGENTA = (255,   0, 255, 255)
SCALE   = 3   # 32x64 → 96x192 (nice desktop size)

cells_x = [
    (3,34),(37,68),(71,102),(105,136),(139,170),(173,204),(207,238),
    (241,272),(275,306),(309,340),(343,374),(377,408),(411,442),
    (445,476),(479,510),(513,544),(547,578),(581,612),(615,646),
    (649,680),(683,714),
]
ROW0_Y = (5, 68)   # 64px tall
TILE_W, TILE_H = 32, 64

raw_frames = []
for cx0, cx1 in cells_x:
    cell = img.crop((cx0, ROW0_Y[0], cx1 + 1, ROW0_Y[1] + 1))
    data = [(MAGENTA if px == WHITE else px) for px in cell.getdata()]
    cell.putdata(data)
    raw_frames.append(cell.resize((TILE_W * SCALE, TILE_H * SCALE), Image.NEAREST))

# ── Build 48×48 .ico icon from idle-right frame ───────────────────────────────
icon_src = img.crop((cells_x[0][0], ROW0_Y[0], cells_x[0][1] + 1, ROW0_Y[1] + 1))
icon_rgba = icon_src.resize((48, 48), Image.NEAREST).convert("RGBA")
pixels = list(icon_rgba.getdata())
pixels = [(0, 0, 0, 0) if px[:3] == (255, 255, 255) else px for px in pixels]
icon_rgba.putdata(pixels)
icon_buf = io.BytesIO()
icon_rgba.save(icon_buf, format="ICO", sizes=[(48, 48)])
icon_b64 = base64.b64encode(icon_buf.getvalue()).decode("ascii")

# ── Pack into 7×3 sprite sheet ───────────────────────────────────────────────
COLS, ROWS = 7, 3
TW, TH = TILE_W * SCALE, TILE_H * SCALE   # 96 × 192

sheet = Image.new("RGBA", (TW * COLS, TH * ROWS), MAGENTA)
for idx, frame in enumerate(raw_frames):
    sheet.paste(frame, ((idx % COLS) * TW, (idx // COLS) * TH))

sheet.save(os.path.join(OUT_DIR, "spritesheet_preview.png"))

buf = io.BytesIO()
sheet.save(buf, format="PNG")
b64 = base64.b64encode(buf.getvalue()).decode("ascii")
print(f"Sheet {TW*COLS}x{TH*ROWS}px | base64 {len(b64)} chars")

# ── Frame indices (source order = sheet order, 7 cols x 3 rows) ──────────────
IDLE_R  = 0
WALK_R1 = 1
WALK_R2 = 2
WALK_R3 = 3
SPIN_A  = 4
JUMP    = 5
SKID    = 6
SPIN_B  = 7
WALK_R4 = 8
SPIN_C  = 9
SPIN_D  = 10
TR1     = 11   # transition / run frames
TR2     = 12
TR3     = 13
TR4     = 14
IDLE_L  = 15
WALK_L1 = 16
WALK_L2 = 17
WALK_L3 = 18
WALK_L4 = 19
WALK_L5 = 20

# ── Build XML ─────────────────────────────────────────────────────────────────
xml = f'''<?xml version="1.0" encoding="utf-8"?>
<animations
  xmlns:xsd="https://esheep.petrucci.ch/ https://raw.githubusercontent.com/Adrianotiger/desktopPet/master/Resources/animations.xsd"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns="https://esheep.petrucci.ch/">
  <header>
    <author>jbatts82</author>
    <title>Super Mario Bros Desktop Pet</title>
    <petname>Mario</petname>
    <version>1.0</version>
    <info>8-bit Super Mario from NES Super Mario Bros walking across your desktop![br]Sprites from the original NES game.</info>
    <application>1</application>
    <icon><![CDATA[{icon_b64}]]></icon>
  </header>
  <image>
    <tilesx>{COLS}</tilesx>
    <tilesy>{ROWS}</tilesy>
    <png><![CDATA[{b64}]]></png>
    <transparency>Magenta</transparency>
  </image>

  <!--
    Spawn: Mario appears from the right edge and walks left.
    Animation IDs:
      1  = walk_left       (x=-3, left-facing frames, main locomotion left)
      2  = walk_right      (x=+3, right-facing frames, main locomotion right)
      3  = idle_left       (stationary, facing left)
      4  = idle_right      (stationary, facing right)
      5  = turn_R_to_L     (spin turn, switches to walk_left)
      6  = turn_L_to_R     (spin turn, switches to walk_right)
      7  = fall            (gravity fall, both directions, use jump frame)
      8  = jump_right      (Mario bounces up while moving right)
      9  = jump_left       (Mario bounces up while moving left)
     10  = spawn_in        (fade-in at start)
  -->

  <spawns>
    <spawn id="1" probability="100">
      <x>screenW</x>
      <y>areaH-imageH</y>
      <next probability="100">10</next>
    </spawn>
  </spawns>

  <animations>

    <!-- 10: Spawn fade-in, then start walking left -->
    <animation id="10">
      <name>spawn_in</name>
      <start>
        <x>0</x><y>0</y><offsety>0</offsety>
        <opacity>0</opacity><interval>80</interval>
      </start>
      <end>
        <x>0</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>80</interval>
      </end>
      <sequence repeatfrom="0" repeat="10">
        <frame>{IDLE_L}</frame>
        <next probability="100" only="none">1</next>
        <action>none</action>
      </sequence>
    </animation>

    <!-- 1: Walk LEFT (Mario moves left across the screen, uses left-facing sprites) -->
    <animation id="1">
      <name>walk_left</name>
      <start>
        <x>-3</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>130</interval>
      </start>
      <end>
        <x>-3</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>130</interval>
      </end>
      <sequence repeatfrom="0" repeat="random/40+15">
        <frame>{WALK_L1}</frame>
        <frame>{WALK_L2}</frame>
        <frame>{WALK_L3}</frame>
        <frame>{WALK_L4}</frame>
        <frame>{WALK_L5}</frame>
        <next probability="85" only="none">1</next>
        <next probability="10" only="none">3</next>
        <next probability="5"  only="none">9</next>
        <action>none</action>
      </sequence>
      <border>
        <next probability="100" only="none">6</next>
      </border>
      <gravity>
        <next probability="100" only="none">7</next>
      </gravity>
    </animation>

    <!-- 2: Walk RIGHT (Mario moves right across the screen, uses right-facing sprites) -->
    <animation id="2">
      <name>walk_right</name>
      <start>
        <x>3</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>130</interval>
      </start>
      <end>
        <x>3</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>130</interval>
      </end>
      <sequence repeatfrom="0" repeat="random/40+15">
        <frame>{WALK_R1}</frame>
        <frame>{WALK_R2}</frame>
        <frame>{WALK_R3}</frame>
        <frame>{WALK_R1}</frame>
        <next probability="85" only="none">2</next>
        <next probability="10" only="none">4</next>
        <next probability="5"  only="none">8</next>
        <action>none</action>
      </sequence>
      <border>
        <next probability="100" only="none">5</next>
      </border>
      <gravity>
        <next probability="100" only="none">7</next>
      </gravity>
    </animation>

    <!-- 3: Idle LEFT (Mario stands still, facing left) -->
    <animation id="3">
      <name>idle_left</name>
      <start>
        <x>0</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>500</interval>
      </start>
      <end>
        <x>0</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>500</interval>
      </end>
      <sequence repeatfrom="0" repeat="random/20+3">
        <frame>{IDLE_L}</frame>
        <next probability="70" only="none">1</next>
        <next probability="20" only="none">6</next>
        <next probability="10" only="none">4</next>
        <action>none</action>
      </sequence>
      <border>
        <next probability="100" only="none">6</next>
      </border>
      <gravity>
        <next probability="100" only="none">7</next>
      </gravity>
    </animation>

    <!-- 4: Idle RIGHT (Mario stands still, facing right) -->
    <animation id="4">
      <name>idle_right</name>
      <start>
        <x>0</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>500</interval>
      </start>
      <end>
        <x>0</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>500</interval>
      </end>
      <sequence repeatfrom="0" repeat="random/20+3">
        <frame>{IDLE_R}</frame>
        <next probability="70" only="none">2</next>
        <next probability="20" only="none">5</next>
        <next probability="10" only="none">3</next>
        <action>none</action>
      </sequence>
      <border>
        <next probability="100" only="none">5</next>
      </border>
      <gravity>
        <next probability="100" only="none">7</next>
      </gravity>
    </animation>

    <!-- 5: Turn RIGHT→LEFT (skid, spin, settle facing left) -->
    <animation id="5">
      <name>turn_R_to_L</name>
      <start>
        <x>0</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>110</interval>
      </start>
      <end>
        <x>0</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>110</interval>
      </end>
      <sequence repeatfrom="0" repeat="0">
        <frame>{SKID}</frame>
        <frame>{SPIN_A}</frame>
        <frame>{SPIN_B}</frame>
        <frame>{SPIN_C}</frame>
        <frame>{SPIN_D}</frame>
        <frame>{IDLE_L}</frame>
        <next probability="100" only="none">1</next>
        <action>none</action>
      </sequence>
    </animation>

    <!-- 6: Turn LEFT→RIGHT (spin, settle facing right) -->
    <animation id="6">
      <name>turn_L_to_R</name>
      <start>
        <x>0</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>110</interval>
      </start>
      <end>
        <x>0</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>110</interval>
      </end>
      <sequence repeatfrom="0" repeat="0">
        <frame>{IDLE_L}</frame>
        <frame>{SPIN_D}</frame>
        <frame>{SPIN_C}</frame>
        <frame>{SPIN_B}</frame>
        <frame>{SPIN_A}</frame>
        <frame>{SKID}</frame>
        <frame>{IDLE_R}</frame>
        <next probability="100" only="none">2</next>
        <action>none</action>
      </sequence>
    </animation>

    <!-- 7: Fall (gravity, accelerates downward, lands at bottom) -->
    <animation id="7">
      <name>fall</name>
      <start>
        <x>0</x><y>2</y><offsety>0</offsety>
        <opacity>1</opacity><interval>80</interval>
      </start>
      <end>
        <x>0</x><y>10</y><offsety>0</offsety>
        <opacity>1</opacity><interval>40</interval>
      </end>
      <sequence repeatfrom="0" repeat="20">
        <frame>{JUMP}</frame>
        <next probability="100" only="none">7</next>
        <action>none</action>
      </sequence>
      <border>
        <next probability="100" only="none">3</next>
      </border>
    </animation>

    <!-- 8: Jump RIGHT (Mario hops while walking right) -->
    <animation id="8">
      <name>jump_right</name>
      <start>
        <x>3</x><y>-7</y><offsety>0</offsety>
        <opacity>1</opacity><interval>80</interval>
      </start>
      <end>
        <x>3</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>80</interval>
      </end>
      <sequence repeatfrom="0" repeat="8">
        <frame>{JUMP}</frame>
        <next probability="100" only="none">7</next>
        <action>none</action>
      </sequence>
      <border>
        <next probability="100" only="none">4</next>
      </border>
    </animation>

    <!-- 9: Jump LEFT (Mario hops while walking left) -->
    <animation id="9">
      <name>jump_left</name>
      <start>
        <x>-3</x><y>-7</y><offsety>0</offsety>
        <opacity>1</opacity><interval>80</interval>
      </start>
      <end>
        <x>-3</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>80</interval>
      </end>
      <sequence repeatfrom="0" repeat="8">
        <frame>{JUMP}</frame>
        <next probability="100" only="none">7</next>
        <action>none</action>
      </sequence>
      <border>
        <next probability="100" only="none">3</next>
      </border>
    </animation>

    <!-- 11: drag — played while the user drags Mario around -->
    <animation id="11">
      <name>drag</name>
      <start>
        <x>0</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>80</interval>
      </start>
      <end>
        <x>0</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>80</interval>
      </end>
      <sequence repeatfrom="0" repeat="0">
        <frame>{JUMP}</frame>
        <next probability="100" only="none">11</next>
        <action>none</action>
      </sequence>
    </animation>

    <!-- 12: kill — played when the pet is removed (fall off screen) -->
    <animation id="12">
      <name>kill</name>
      <start>
        <x>0</x><y>3</y><offsety>0</offsety>
        <opacity>1</opacity><interval>80</interval>
      </start>
      <end>
        <x>0</x><y>12</y><offsety>0</offsety>
        <opacity>1</opacity><interval>40</interval>
      </end>
      <sequence repeatfrom="0" repeat="30">
        <frame>{JUMP}</frame>
        <next probability="100" only="none">12</next>
        <action>none</action>
      </sequence>
    </animation>

    <!-- 13: sync — played when syncing with another pet instance -->
    <animation id="13">
      <name>sync</name>
      <start>
        <x>0</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>200</interval>
      </start>
      <end>
        <x>0</x><y>0</y><offsety>0</offsety>
        <opacity>1</opacity><interval>200</interval>
      </end>
      <sequence repeatfrom="0" repeat="3">
        <frame>{IDLE_R}</frame>
        <next probability="100" only="none">4</next>
        <action>none</action>
      </sequence>
    </animation>

  </animations>

  <childs />

</animations>
'''

out_xml = os.path.join(OUT_DIR, "animations.xml")
with open(out_xml, "w", encoding="utf-8") as fh:
    fh.write(xml)

print(f"Written: {out_xml}")
print(f"\nTo run:")
print(f"  1. Download / build desktopPet-master (eSheep app)")
print(f"  2. The mario/ folder is already in Pets/")
print(f"  OR load animations.xml directly via the app's File > Open")
