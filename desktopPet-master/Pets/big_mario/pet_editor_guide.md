# Pet Editor Guide — Big Mario

## Project tree (left panel)

- **Header** — pet name, author, version info
- **Image** — sprite sheet settings (tilesx, tilesy, transparency colour)
- **Spawns** — where and how the pet appears on screen
- **Animations** — the movement and frame sequences
- **Childs** — secondary pets that spawn from animations
- **Sounds** — audio tied to animations
- **Tools → View XML** — see the raw XML the editor is generating
- **Tools → Test/Run** — preview the pet live
- **Tools → GraphViz** — visualise the animation flow as a graph

---

## Spawns

A spawn defines where Mario appears when the pet first starts (or restarts after going off-screen).
You can have multiple spawns with different probabilities — the engine picks one at random.

| Field | Meaning |
|-------|---------|
| `id` | Unique number for this spawn |
| `probability` | Chance this spawn is chosen. All spawns should add up to 100 |
| `x` | Horizontal start position |
| `y` | Vertical start position |
| `next → id` | Which animation to run immediately after spawning |
| `next → probability` | Should be 100 if there is only one next |

### Common position expressions

| Expression | Meaning |
|-----------|---------|
| `screenW` | Right edge of screen |
| `0` | Left edge of screen |
| `screenW/2` | Centre of screen |
| `areaH-imageH` | Bottom of desktop, sitting just above the taskbar |

### Example — spawn at right edge, walk left
```
probability:  100
x:            screenW
y:            areaH-imageH
next id:      1       (your walk_left animation)
next prob:    100
```

---

## Animations

### Sequence section

| Field | Meaning |
|-------|---------|
| **Repeats** | How many times the frame sequence plays before "If sequence is over" fires. `0` = loop forever |
| **Repeat From** | Which frame index (0-based) to jump back to on each repeat. `0` = restart from beginning |
| **End effect** | Visual effect when sequence ends. `none` = no effect |

---

### Frames section

The numbered tiles are frames from your sprite sheet.
- The number in brackets `(0)`, `(1)`, `(2)` = position in the sequence (first, second, third frame played)
- The number above e.g. `8`, `9`, `10` = the frame index from the sprite sheet

Frame index is calculated as: `row × tilesx + column` (zero-indexed)
For big_mario: tilesx = 14, so row 0 = frames 0–13, row 1 = frames 14–27, row 2 = frames 28–41.

---

### Start parameters / End parameters

These control how Mario moves during the animation.
Values lerp (smoothly change) from Start to End over the course of the sequence.
If Start and End are the same, movement is constant throughout.

| Field | Meaning |
|-------|---------|
| **X** | Horizontal movement per tick. Negative = left, Positive = right, 0 = stationary |
| **Y** | Vertical movement per tick. Positive = down, Negative = up (jumping), 0 = stationary |
| **Interval** | Milliseconds between each frame. Lower = faster animation |
| **Offset Y** | Shifts the sprite up/down visually without affecting position logic (used for jump arcs) |
| **Opacity** | 1.00 = fully visible, 0.00 = invisible. Start 0 → End 1 creates a fade-in |

### Interval reference

| Value | Speed |
|-------|-------|
| 200ms | Slow (~5 fps) |
| 120ms | Medium (~8 fps) |
| 80ms | Fast (~12 fps) |

---

### Next animation section

**"If sequence is over"**
Fires when the frame sequence finishes (controlled by Repeats count).
Add multiple rows and the engine picks one based on probability.

**"If border is detected"**
Fires when Mario hits the left or right screen edge.
Use this to make him turn around.

| Column | Meaning |
|--------|---------|
| Animation ID | Which animation to go to next |
| Probability | Chance this row is chosen. Multiple rows should add up to 100 |
| Control | Usually `none` |

---

### Right panel

| Field | Meaning |
|-------|---------|
| **ID** | Unique number for this animation. Other animations reference it by this number |
| **Name** | Label for your own reference only |
| **Total steps** | Total frames that will play (read-only, calculated) |
| **Total movement X/Y** | How far Mario travels during this animation (read-only) |
| **Total animation time** | How long the full animation takes in ms (read-only) |

---

## Simple walk left/right setup

### Spawn
```
probability:  100
x:            screenW        (start at right edge)
y:            areaH-imageH   (sit on taskbar)
next:         animation 1    (walk_left)
```

### Animation 1 — walk_left
```
Frames:           8, 9, 10
Start X:          -3
End X:            -3
Interval:         120
Repeats:          0           (loop forever)
If sequence over: none needed (Repeats = 0 means it never fires)
If border:        → animation 2 (walk_right)
```

### Animation 2 — walk_right
```
Frames:           1, 2, 3
Start X:          +3
End X:            +3
Interval:         120
Repeats:          0
If sequence over: none needed
If border:        → animation 1 (walk_left)
```

---

## Tips

- Always check **Tools → View XML** to see what the editor has generated — it helps you understand what each control produces
- The yellow warning "Animation X is using this ID as next" just means an animation loops to itself — this is normal and correct for walking
- If Mario walks the wrong direction, your frame numbers are for the opposite facing — swap the frames between walk_left and walk_right
- **Total movement X (pixels)** in the right panel should be negative for walk_left and positive for walk_right — use this to confirm your X values are correct
