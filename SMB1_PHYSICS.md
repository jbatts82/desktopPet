# SMB1 (NES) movement reference → eSheep pet mapping

All values below are read directly out of the Super Mario Bros. 6502 disassembly
(`1wErt3r/4048722`, mirrored at 6502disassembly.com), not from secondary sources.
Label names in parentheses are the actual symbols in that source.

## Units

- **NES frame** = 1/60.0988 s ≈ **16.64 ms**.
- **Horizontal speed** is a signed byte where the high nibble is whole pixels and the
  low nibble is 1/16 px (`MoveObjectHorizontally` shifts the nibbles apart).
  So **16 speed units = 1 px/frame**. `$28` = 2.5 px/f.
- **Acceleration / friction** is an 8-bit fraction (1/256) added to the speed each
  frame, i.e. one unit = 1/256 × 1/16 px = **1/4096 px per frame²**.
- **Vertical speed** is whole px/frame; **gravity** is a 1/256 px/frame² fraction.

## Horizontal speed caps (`MaxRightXSpdData` / `MaxLeftXSpdData`)

| State | Hex | px/frame | px/s |
|---|---|---|---|
| Run (B held, or run timer active) | `$28` | 2.50 | 150.2 |
| Walk | `$18` | 1.50 | 90.1 |
| Underwater / airborne-from-walk | `$10` | 1.00 | 60.1 |
| Pipe entry cutscene | `$0c` | 0.75 | 45.1 |

Walk cap is exactly 3/5 of the run cap.

## Acceleration & friction (`FrictionData: $e4, $98, $d0`)

The same table is used for *both* accelerating and slowing down — the index depends
on state, and the value is added toward the current max speed (`ImposeFriction`).

| Index | Hex | px/frame² | px/s² | Used when |
|---|---|---|---|---|
| 0 | `$e4` | 0.05566 | 201.0 | on ground, holding B, input matches facing → **run accel** |
| 1 | `$98` | 0.03711 | 134.0 | **walk accel**, and normal release friction |
| 2 | `$d0` | 0.05078 | 183.4 | speed ≥ `$21` (2.06 px/f) without run held → **bleed-off from run speed** |

**Skidding doubles it.** In `X_Physics`, if facing direction ≠ moving direction the
friction adder is shifted left once (`asl FrictionAdderLow` / `rol FrictionAdderHigh`),
so turning around decelerates at 2× the table value.

Derived timings (0 → cap, and cap → 0):

| Maneuver | Frames | Seconds | Distance (NES px) |
|---|---|---|---|
| 0 → walk cap | 40 | 0.67 | 30 (≈2 tiles) |
| 0 → run cap | 45 | 0.75 | 56 (≈3.5 tiles) |
| Run cap → 0, released (inertia slide) | ~64 | ~1.07 | ~87 |
| Run cap → 0, skidding (holding back) | ~23 | ~0.38 | ~30 |

While skidding, once speed drops below `$0b` (0.6875 px/f) the game **zeroes X speed
outright** and snaps the moving direction to the facing direction (`ProcSkid`). That
hard snap is what makes the turnaround feel crisp instead of mushy.

## Jumping (`PlayerYSpdData` / `JumpMForceData` / `FallMForceData`)

Which row is used is picked at takeoff from `Player_XSpeedAbsolute` — **your horizontal
speed at the instant you press A decides the whole jump**. Gravity is asymmetric: while
A is held and you're still rising, the weaker "hold" gravity applies; the moment you
release A (or start descending), the game swaps in the stronger fall gravity
(`DumpFall`).

| |vx| at takeoff | Initial vy | Gravity, A held | Gravity, falling / A released | Apex (full hold) |
|---|---|---|---|---|---|
| < 0.5625 px/f (`<$09`) | −4.0 | 0.125 (`$20`) | 0.4375 (`$70`) | 64 px (4 tiles) |
| 0.5625 – 0.9375 | −4.0 | 0.125 | 0.4375 | 64 px |
| 1.0 – 1.5 (`$10`–`$18`) | −4.0 | 0.1172 (`$1e`) | 0.375 (`$60`) | 68 px |
| 1.5625 – 1.6875 (`$19`–`$1b`) | −5.0 | 0.1563 (`$28`) | 0.5625 (`$90`) | 80 px |
| ≥ 1.75 px/f (`$1c`) | −5.0 | 0.1563 | 0.5625 | 80 px (5 tiles) |

- **Rise time is ~32 frames (0.53 s) in every row** — the faster you go, the higher you
  jump, but not the longer. Total airtime lands around 49 frames (~0.82 s).
- **Minimum hop** (tap A, release immediately): vy=−4.0 decelerating at 0.4375 →
  apex only ~18 px, ~9 frames up. That 3.5× height range from one button is the
  signature SMB1 feel.
- **Terminal fall speed = 4.0 px/frame** (`MovePlayerVertically` sets max = `$04`) = 240 px/s.
- **Air control:** airborne with |vx| < `$19` uses the *walk* accel/cap; at or above it you
  keep run physics. You can't reach run speed from a standing jump.

## Animation timing (`PlayerAnimTmrData: $02, $04, $07`)

Mario's walk cycle is **3 frames**, and SMB1 has **no separate run frames** — running
is the same 3-frame cycle played faster. `GetPlayerAnimSpeed` picks the hold time per
sprite frame purely from |vx|:

| |vx| | NES frames per sprite frame | ms per sprite frame |
|---|---|---|---|
| ≥ 1.75 px/f (`$1c`) — running | 2 | 33 |
| 0.875 – 1.75 (`$0e`) — walking | 4 | 67 |
| < 0.875 — creeping | 7 | 117 |

The complete authentic sprite set is: **stand, walk×3, skid, jump (1 frame)** (+ swim,
climb, crouch/death for big Mario). Left-facing is a horizontal mirror, not new art.

## Mapping to eSheep

eSheep's timer fires every `interval` ms and moves the pet by `x`/`y` **pixels per tick**,
linearly interpolating both from `<start>` to `<end>` across the sequence's total steps
(`FormPet.NextStep`, lines 454–472). Linear interpolation of `y` from a negative start to
a positive end **is** constant gravity, so jumps come out genuinely parabolic.

Conversion rule, where `T` = NES frames per tick and `S` = sprite scale factor:

```
interval_ms  = T × 16.64
x_per_tick   = v_px_per_NES_frame × S × T
```

Set `T` equal to the animation timer above, and one eSheep tick = one sprite frame.
At **S = 3** (the scale `build_mario_pet.py` uses):

| Animation | T | interval | x per tick | Resulting speed |
|---|---|---|---|---|
| Creep | 7 | 117 ms | 16 | 135 px/s |
| Walk | 4 | 67 ms | 18 | 270 px/s |
| Run | 2 | 33 ms | 15 | 450 px/s |
| Jump rise (from walk) | 2 | 33 ms | y: −24 → 0 over 16 steps | apex 192 px |
| Jump rise (from run) | 2 | 33 ms | y: −30 → 0 over 16 steps | apex 240 px |
| Fall accel | 2 | 33 ms | y: 0 → 24 over ~5 steps | reaches terminal |
| Fall terminal | 2 | 33 ms | y: 24 | 720 px/s |

Acceleration is expressed by interpolating `x` and `interval` together across the
sequence: a walk-up animation runs `x` 0 → 18 with `interval` 117 → 67 over ~10 steps
(0.67 s), and a run-up runs `x` 18 → 15 with `interval` 67 → 33 over ~6 steps (0.30 s).
A skid is the same in reverse but ~2.5× faster, ending on the skid frame.

> **Current pet is ~12× too slow.** `build_mario_pet.py` walks at `x=3` per 130 ms
> = 23 px/s, and runs at `x=8` per 65 ms = 123 px/s, against the authentic 270 / 450 px/s.

## Sources

- [A Comprehensive Super Mario Bros. Disassembly (1wErt3r)](https://gist.github.com/1wErt3r/4048722)
- [SuperMarioBros Disassembly, annotated](https://6502disassembly.com/nes-smb/SuperMarioBros.html)
- [TASVideos — Game Resources / NES / Super Mario Bros](https://tasvideos.org/GameResources/NES/SuperMarioBros)
- [SDA Knowledge Base — Super Mario Bros.](https://kb.speeddemosarchive.com/Super_Mario_Bros.)
