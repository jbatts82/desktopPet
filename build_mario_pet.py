"""
Build a Mario desktop pet for the eSheep (desktopPet) application.

MOVEMENT IS DERIVED FROM THE ORIGINAL SUPER MARIO BROS. (NES) PHYSICS.
Every interval / x / y below is computed from the constants in the SMB 6502
disassembly rather than hand-tuned. See SMB1_PHYSICS.md for the full writeup.

Source art
----------
Mario.png row 0 holds big Mario at 2x NES size (32x64 cells; NES big Mario is
16x32). Only the first seven cells are trustworthy, and they are the canonical
SMB1 pose order:

    0 stand | 1,2,3 walk | 4 skid | 5 jump | 6 crouch

Cells 7-14 of that row are *swimming* poses and 15-20 are a left-facing set that
is not a clean mirror, so none of them are used. We build the left-facing frames
by horizontally flipping cells 0-6, which is exactly what the NES hardware does.
That gives a 7x2 sheet with a frame map that cannot be wrong:

    row 0 (right):  0 IDLE_R  1,2,3 WALK_R  4 SKID_R  5 JUMP_R  6 CROUCH_R
    row 1 (left) :  7 IDLE_L  8,9,10 WALK_L 11 SKID_L 12 JUMP_L 13 CROUCH_L

eSheep coordinate system
------------------------
    x > 0 => RIGHT, x < 0 => LEFT, y > 0 => DOWN (gravity), y < 0 => UP (jump)

A left-facing walk therefore needs left-facing frames *and* a negative x.
"""

import base64, io, os
from PIL import Image

SRC     = r"C:\Local_Workspace\sheep\Mario.png"
OUT_DIR = r"C:\Local_Workspace\sheep\desktopPet-master\Pets\mario"
os.makedirs(OUT_DIR, exist_ok=True)

# ── SMB1 physics constants (from the 6502 disassembly) ────────────────────────
# Horizontal speeds are px per NES frame. MaxRightXSpdData stores them as a byte
# whose high nibble is whole px and low nibble is 1/16 px, so $18 = 1.5, $28 = 2.5.
NES_FRAME_MS = 16.639          # 1 / 60.0988 Hz
V_WALK       = 1.5             # $18  MaxRightXSpdData
V_RUN        = 2.5             # $28  MaxRightXSpdData
V_TERMINAL   = 4.0             # $04  MovePlayerVertically, max fall speed
VY_JUMP_WALK = 4.0             # $fc  PlayerYSpdData, takeoff below 1.75 px/f
VY_JUMP_RUN  = 5.0             # $fb  PlayerYSpdData, takeoff at/above 1.75 px/f

# PlayerAnimTmrData: NES frames each sprite frame is held, chosen by |vx|.
# Setting one eSheep tick to one sprite frame makes the animation self-timing.
T_RUN, T_WALK, T_CREEP = 2, 4, 7        # $02, $04, $07

# Rise takes 32 NES frames in every row of the jump table (weak gravity while A
# is held); the descent uses ~3.5x stronger gravity, hence separate animations.
JUMP_RISE_STEPS  = 32 // T_RUN          # 16 ticks
FALL_ACCEL_STEPS = 5                    # ticks to reach terminal velocity
SKID_STEPS       = 12                   # ~23 NES frames of doubled friction

# ── Extract the seven real frames ────────────────────────────────────────────
img = Image.open(SRC).convert("RGBA")
WHITE   = (255, 255, 255, 255)
MAGENTA = (255,   0, 255, 255)
SCALE   = 3                              # 32x64 -> 96x192

# The source art is already 2x NES, so on screen one NES pixel is this many px.
S = 2 * SCALE                            # 6

cells_x = [(3, 34), (37, 68), (71, 102), (105, 136), (139, 170), (173, 204), (207, 238)]
ROW0_Y  = (5, 68)                        # 64px tall
TILE_W, TILE_H = 32, 64

right_frames = []
for cx0, cx1 in cells_x:
    cell = img.crop((cx0, ROW0_Y[0], cx1 + 1, ROW0_Y[1] + 1))
    cell.putdata([(MAGENTA if px == WHITE else px) for px in cell.getdata()])
    right_frames.append(cell.resize((TILE_W * SCALE, TILE_H * SCALE), Image.NEAREST))

left_frames = [f.transpose(Image.FLIP_LEFT_RIGHT) for f in right_frames]
frames = right_frames + left_frames

# ── Frame indices (7x2 sheet, left-to-right then top-to-bottom) ──────────────
IDLE_R, WALK_R1, WALK_R2, WALK_R3, SKID_R, JUMP_R, CROUCH_R = range(7)
IDLE_L, WALK_L1, WALK_L2, WALK_L3, SKID_L, JUMP_L, CROUCH_L = range(7, 14)

# ── Derived eSheep values ────────────────────────────────────────────────────
# eSheep moves <x>/<y> pixels once per <interval> ms, and interpolates both
# linearly from <start> to <end> across the sequence. Linear interpolation of y
# from a negative start to a positive end IS constant acceleration, so the jump
# arcs come out genuinely parabolic.
#
#     interval = T * 16.64 ms        distance = v_nes_px_per_frame * S * T
ms = lambda T: round(T * NES_FRAME_MS)
px = lambda v, T: round(v * S * T)

I_RUN, I_WALK, I_CREEP = ms(T_RUN), ms(T_WALK), ms(T_CREEP)

X_WALK    = px(V_WALK, T_WALK)      # cruising on the ground
X_RUN     = px(V_RUN,  T_RUN)
X_AIR     = px(V_WALK, T_RUN)       # airborne at walk speed (shorter tick!)
X_AIR_RUN = px(V_RUN,  T_RUN)       # SMB1 keeps your run speed in the air
VY_WALK   = px(VY_JUMP_WALK, T_RUN)
VY_RUN    = px(VY_JUMP_RUN,  T_RUN)
V_FALL    = px(V_TERMINAL,   T_RUN)

print(f"scale S={S} (source art is 2x NES, SCALE={SCALE})")
print(f"  walk  {X_WALK:>3} px / {I_WALK:>3} ms  = {X_WALK/I_WALK*1000:>4.0f} px/s")
print(f"  run   {X_RUN:>3} px / {I_RUN:>3} ms  = {X_RUN/I_RUN*1000:>4.0f} px/s")
print(f"  jump  vy {VY_WALK} (walk) / {VY_RUN} (run), rise {JUMP_RISE_STEPS} ticks")
print(f"  apex  {round(VY_JUMP_WALK**2 / (2*0.125) * S)} px (walk) / "
      f"{round(VY_JUMP_RUN**2 / (2*0.15625) * S)} px (run)")
print(f"  fall  terminal {V_FALL} px/tick")

# ── Pack into a 7x2 sprite sheet ─────────────────────────────────────────────
COLS, ROWS = 7, 2
TW, TH = TILE_W * SCALE, TILE_H * SCALE   # 96 x 192

sheet = Image.new("RGBA", (TW * COLS, TH * ROWS), MAGENTA)
for idx, frame in enumerate(frames):
    sheet.paste(frame, ((idx % COLS) * TW, (idx // COLS) * TH))
sheet.save(os.path.join(OUT_DIR, "spritesheet_preview.png"))

buf = io.BytesIO()
sheet.save(buf, format="PNG")
b64 = base64.b64encode(buf.getvalue()).decode("ascii")
print(f"Sheet {TW*COLS}x{TH*ROWS}px | base64 {len(b64)} chars")

# ── Build a 48x48 .ico icon from the idle frame ──────────────────────────────
icon_src  = img.crop((cells_x[0][0], ROW0_Y[0], cells_x[0][1] + 1, ROW0_Y[1] + 1))
icon_rgba = icon_src.resize((48, 48), Image.NEAREST).convert("RGBA")
icon_rgba.putdata([(0, 0, 0, 0) if p[:3] == (255, 255, 255) else p
                   for p in icon_rgba.getdata()])
icon_buf = io.BytesIO()
icon_rgba.save(icon_buf, format="ICO", sizes=[(48, 48)])
icon_b64 = base64.b64encode(icon_buf.getvalue()).decode("ascii")


def anim(id_, name, frames_, *, x0=0, y0=0, x1=None, y1=None,
         i0=I_WALK, i1=None, repeat="0", nexts=(), border=None, gravity=None):
    """Emit one <animation>. x1/y1/i1 default to x0/y0/i0 (no interpolation)."""
    x1 = x0 if x1 is None else x1
    y1 = y0 if y1 is None else y1
    i1 = i0 if i1 is None else i1
    seq = "\n".join(f"        <frame>{f}</frame>" for f in frames_)
    nxt = "\n".join(f'        <next probability="{p}" only="none">{t}</next>'
                    for p, t in nexts)
    out = f'''    <animation id="{id_}">
      <name>{name}</name>
      <start><x>{x0}</x><y>{y0}</y><offsety>0</offsety><opacity>1</opacity><interval>{i0}</interval></start>
      <end><x>{x1}</x><y>{y1}</y><offsety>0</offsety><opacity>1</opacity><interval>{i1}</interval></end>
      <sequence repeatfrom="0" repeat="{repeat}">
{seq}
{nxt}
        <action>none</action>
      </sequence>'''
    if border is not None:
        out += f'\n      <border>\n        <next probability="100" only="none">{border}</next>\n      </border>'
    if gravity is not None:
        out += f'\n      <gravity>\n        <next probability="100" only="none">{gravity}</next>\n      </gravity>'
    return out + "\n    </animation>"


WALK_CYCLE_R = [WALK_R1, WALK_R2, WALK_R3]
WALK_CYCLE_L = [WALK_L1, WALK_L2, WALK_L3]

animations = [
    # Ground cruise. SMB1 has no separate run art - running replays the same
    # three walk frames at T=2 instead of T=4.
    anim(1, "walk_left", WALK_CYCLE_L, x0=-X_WALK, i0=I_WALK, repeat="random/12+6",
         nexts=[(45, 1), (30, 13), (15, 3), (10, 19)], border=18, gravity=23),
    anim(2, "walk_right", WALK_CYCLE_R, x0=X_WALK, i0=I_WALK, repeat="random/12+6",
         nexts=[(45, 2), (30, 14), (15, 4), (10, 20)], border=17, gravity=24),

    anim(3, "idle_left", [IDLE_L], i0=400, repeat="random/25+2",
         nexts=[(65, 9), (35, 18)], gravity=5),
    anim(4, "idle_right", [IDLE_R], i0=400, repeat="random/25+2",
         nexts=[(65, 10), (35, 17)], gravity=5),

    # "fall" is bound by name - eSheep plays it when the user drops the pet.
    anim(5, "fall", [JUMP_R], y0=0, y1=V_FALL, i0=I_RUN,
         repeat=FALL_ACCEL_STEPS - 1, nexts=[(100, 31)], border=4),
    anim(6, "sync", [IDLE_R], i0=400, repeat="2", nexts=[(100, 4)]),
    anim(7, "drag", [JUMP_R], i0=I_WALK, repeat="0", nexts=[(100, 7)]),
    anim(8, "kill", [JUMP_R], y0=V_FALL // 2, y1=V_FALL, i0=I_RUN, repeat="30"),

    # Accelerate from a standstill: 0.0371 px/f^2, ~40 NES frames to walk speed.
    # x ramps 0 -> walk while the frame hold tightens from creep to walk.
    anim(9, "accel_left", WALK_CYCLE_L, x0=0, x1=-X_WALK, i0=I_CREEP, i1=I_WALK,
         repeat="2", nexts=[(100, 1)], border=18, gravity=23),
    anim(10, "accel_right", WALK_CYCLE_R, x0=0, x1=X_WALK, i0=I_CREEP, i1=I_WALK,
         repeat="2", nexts=[(100, 2)], border=17, gravity=24),

    anim(11, "run_left", WALK_CYCLE_L, x0=-X_RUN, i0=I_RUN, repeat="random/10+8",
         nexts=[(60, 11), (15, 21), (15, 16), (10, 1)], border=18, gravity=27),
    anim(12, "run_right", WALK_CYCLE_R, x0=X_RUN, i0=I_RUN, repeat="random/10+8",
         nexts=[(60, 12), (15, 22), (15, 15), (10, 2)], border=17, gravity=28),

    # Walk -> run: 0.0557 px/f^2, ~18 NES frames from 1.5 to 2.5 px/f.
    anim(13, "runup_left", WALK_CYCLE_L, x0=-X_WALK, x1=-X_RUN, i0=I_WALK, i1=I_RUN,
         repeat="1", nexts=[(100, 11)], border=18, gravity=27),
    anim(14, "runup_right", WALK_CYCLE_R, x0=X_WALK, x1=X_RUN, i0=I_WALK, i1=I_RUN,
         repeat="1", nexts=[(100, 12)], border=17, gravity=28),

    # Skid: holding back doubles friction, bleeding run speed to 0 in ~0.4s while
    # Mario already faces the NEW direction - so the sprite is the opposite skid.
    anim(15, "skid_R_to_L", [SKID_L], x0=X_RUN, x1=0, i0=I_RUN,
         repeat=SKID_STEPS - 1, nexts=[(100, 1)], border=17, gravity=23),
    anim(16, "skid_L_to_R", [SKID_R], x0=-X_RUN, x1=0, i0=I_RUN,
         repeat=SKID_STEPS - 1, nexts=[(100, 2)], border=18, gravity=24),

    # Turning at a wall does not move (x=0): running into a wall zeroes Mario's
    # speed in SMB1, and a border animation that still moves into the wall would
    # re-trigger the border check on every tick.
    anim(17, "turn_R_to_L", [SKID_L, SKID_L, IDLE_L], i0=60, repeat="0",
         nexts=[(100, 9)]),
    anim(18, "turn_L_to_R", [SKID_R, SKID_R, IDLE_R], i0=60, repeat="0",
         nexts=[(100, 10)]),

    # Jumps. Takeoff speed picks the arc: below 1.75 px/f you get vy 4.0 and a
    # 64-NES-px apex, at or above it vy 5.0 and 80. Both rise for 32 NES frames.
    anim(19, "jump_left", [JUMP_L], x0=-X_AIR, y0=-VY_WALK, y1=0, i0=I_RUN,
         repeat=JUMP_RISE_STEPS - 1, nexts=[(100, 23)], border=23),
    anim(20, "jump_right", [JUMP_R], x0=X_AIR, y0=-VY_WALK, y1=0, i0=I_RUN,
         repeat=JUMP_RISE_STEPS - 1, nexts=[(100, 24)], border=24),
    anim(21, "jump_run_left", [JUMP_L], x0=-X_AIR_RUN, y0=-VY_RUN, y1=0, i0=I_RUN,
         repeat=JUMP_RISE_STEPS - 1, nexts=[(100, 27)], border=27),
    anim(22, "jump_run_right", [JUMP_R], x0=X_AIR_RUN, y0=-VY_RUN, y1=0, i0=I_RUN,
         repeat=JUMP_RISE_STEPS - 1, nexts=[(100, 28)], border=28),

    # Falls: accelerate to terminal (0.4375 px/f^2), then hold it.
    anim(23, "fall_left", [JUMP_L], x0=-X_AIR, y0=0, y1=V_FALL, i0=I_RUN,
         repeat=FALL_ACCEL_STEPS - 1, nexts=[(100, 25)], border=1),
    anim(24, "fall_right", [JUMP_R], x0=X_AIR, y0=0, y1=V_FALL, i0=I_RUN,
         repeat=FALL_ACCEL_STEPS - 1, nexts=[(100, 26)], border=2),
    anim(25, "fall_left_fast", [JUMP_L], x0=-X_AIR, y0=V_FALL, i0=I_RUN,
         repeat="40", nexts=[(100, 25)], border=1),
    anim(26, "fall_right_fast", [JUMP_R], x0=X_AIR, y0=V_FALL, i0=I_RUN,
         repeat="40", nexts=[(100, 26)], border=2),
    anim(27, "fall_run_left", [JUMP_L], x0=-X_AIR_RUN, y0=0, y1=V_FALL, i0=I_RUN,
         repeat=FALL_ACCEL_STEPS - 1, nexts=[(100, 29)], border=11),
    anim(28, "fall_run_right", [JUMP_R], x0=X_AIR_RUN, y0=0, y1=V_FALL, i0=I_RUN,
         repeat=FALL_ACCEL_STEPS - 1, nexts=[(100, 30)], border=12),
    anim(29, "fall_run_left_fast", [JUMP_L], x0=-X_AIR_RUN, y0=V_FALL, i0=I_RUN,
         repeat="40", nexts=[(100, 29)], border=11),
    anim(30, "fall_run_right_fast", [JUMP_R], x0=X_AIR_RUN, y0=V_FALL, i0=I_RUN,
         repeat="40", nexts=[(100, 30)], border=12),
    anim(31, "fall_fast", [JUMP_R], y0=V_FALL, i0=I_RUN,
         repeat="40", nexts=[(100, 31)], border=4),
]

xml = f'''<?xml version="1.0" encoding="utf-8"?>
<animations
  xmlns:xsd="https://esheep.petrucci.ch/ https://raw.githubusercontent.com/Adrianotiger/desktopPet/master/Resources/animations.xsd"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns="https://esheep.petrucci.ch/">
  <header>
    <author>jbatts82</author>
    <title>Super Mario Bros Desktop Pet</title>
    <petname>Mario</petname>
    <version>2.0</version>
    <info>8-bit Super Mario from NES Super Mario Bros walking across your desktop![br]Movement timed to the original game's physics.</info>
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
    GENERATED BY build_mario_pet.py - DO NOT HAND-EDIT.

    Movement is derived from the Super Mario Bros. (NES) 6502 disassembly; see
    SMB1_PHYSICS.md. Sprites are big Mario (16x32 NES) at {S}x, so every NES
    velocity is multiplied by {S}. One eSheep tick == one SMB1 sprite frame.

        walk  {X_WALK} px / {I_WALK} ms   run  {X_RUN} px / {I_RUN} ms
        jump  vy {VY_WALK} (walk) / {VY_RUN} (run), rising for {JUMP_RISE_STEPS} ticks
        fall  terminal {V_FALL} px/tick
  -->

  <spawns>
    <spawn id="1" probability="50">
      <x>10</x>
      <y>areaH-imageH</y>
      <next probability="100">10</next>
    </spawn>
    <spawn id="2" probability="50">
      <x>screenW-imageW-10</x>
      <y>areaH-imageH</y>
      <next probability="100">9</next>
    </spawn>
  </spawns>

  <animations>
{chr(10).join(animations)}
  </animations>

  <childs />

</animations>
'''

out_xml = os.path.join(OUT_DIR, "animations.xml")
with open(out_xml, "w", encoding="utf-8") as fh:
    fh.write(xml)

print(f"Written: {out_xml}")
