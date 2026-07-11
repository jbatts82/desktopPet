r"""check_pet.py -- headless regression harness for eSheep pet XML files.

WHY THIS EXISTS
---------------
There is no local build of the C# eSheep app (no .NET SDK here), so the only way
to know whether a pet actually behaves on the desktop used to be "run the Pet
Editor and stare at it".  That let two real bugs ship:

  * the pet fell straight through the taskbar (a fall animation with no
    matching <border> for the taskbar event), and
  * the pet FROZE in mid-air against a screen edge -- a fall animation's
    <border> routed the wall (vertical) event to an animation with a nonzero
    start <x>, which immediately re-triggered the same wall border, forever.
    Position never changed, y was never applied.  A fall-through detector does
    not see this at all; that is exactly why it went unnoticed.

So this script does two things, both offline:

  1. STATIC checks on the XML graph (dangling ids, out-of-range frames, and the
     two structural shapes above).
  2. DYNAMIC checks: a faithful Python port of the eSheep runtime's per-tick
     loop, run over many seeds, in three scenarios.  It watches for BOTH "fell
     through the floor" and "STUCK" (position pinned for >STUCK_TICKS ticks
     while airborne), and counts clean landings as a positive signal.

     The scenarios matter.  A pet that only ever spawns standing on the taskbar
     is airborne only during its own short jumps, near the middle of the screen
     -- it never falls past a wall and never gets high enough to meet a window,
     so neither failure mode can even occur.  That blind spot is why the two
     throwaway sims this replaces reported "no failures" on a pet that visibly
     froze in mid-air.  So we also DROP the pet from a random height (which the
     real app does too: drag-and-drop, and windows opening underneath it):

       bare screen      spawn normally, taskbar only
       bare + drops     dropped from a random height/x -> long falls past walls
       window + drops   same, plus one window -> FallDetect, window borders,
                        standing on a ledge, walking off it

Exit code is nonzero if any pet fails.

THE RUNTIME MODEL (ported from desktopPet-master/src/dotNet/)
------------------------------------------------------------
  Animations.cs:198  TotalSteps = Frames + (Frames - RepeatFrom) * Repeat
  FormPet.cs:352     tick: if step < 0 -> step = 0; NextStep(); step++
  FormPet.cs:397     SetNewAnimation() -> AnimationStep = -1
  FormPet.cs:471     x = start.x + (end.x - start.x) * step / (TotalSteps - 1)
  FormPet.cs:479     if (!IsMovingLeft) x = -x     (only flipped by action="flip")
  FormPet.cs:481+    horizontal borders: screen edge (VERTICAL) when off a
                     window, window edge (WINDOW) when standing on one; if no
                     border matches a window edge, hwndWindow is cleared -> he
                     walks off the ledge.
  FormPet.cs:574     vertical borders: the taskbar/window ground check runs
                     ONLY inside `else if (y > 0)`.  An animation whose first
                     interpolated y is 0 therefore cannot land on its first tick.
  FormPet.cs:630     sequence over -> SetNextSequenceAnimation(where), where =
                     WINDOW if on a window, else TASKBAR if resting on the
                     taskbar, else NONE.  No match -> respawn.
  FormPet.cs:699     gravity: if more than 3px above the ground, switch to the
                     gravity animation.
  FormPet.cs:837     FallDetect(): a window top counts as ground only if the
                     pet's feet cross it this tick, he overlaps the window
                     horizontally (with a half-width slop), and py > 20.
  Animations.cs:759  next-picking: `if (only != NONE && (only & where) == 0) continue;`
  Xml.cs:264-312     only= parsing.  *** only="none" IS NOT "no filter" ***  It
                     parses to TOnly.NONE = 0x7F, which the line above treats as
                     a WILDCARD that matches EVERY border/sequence event.  Any
                     unrecognised only= string also lands on NONE.

USAGE
-----
  python check_pet.py                      # checks big_mario + mario
  python check_pet.py path\to\pet.xml [...]
  python check_pet.py --seeds 200 --ticks 50000 --verbose
"""

import argparse
import base64
import io
import os
import random
import re
import sys
import xml.etree.ElementTree as ET

from PIL import Image

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

ROOT = r"C:\Local_Workspace\sheep"
DEFAULT_PETS = [
    os.path.join(ROOT, r"desktopPet-master\Pets\big_mario\big_mario.xml"),
    os.path.join(ROOT, r"desktopPet-master\Pets\mario\animations.xml"),
]

NS = {"a": "https://esheep.petrucci.ch/"}

# TNextAnimation.TOnly (Animations.cs:110-135).  NONE is a WILDCARD, not "no filter".
TASKBAR, WINDOW, HORIZONTAL, HORIZONTAL_, VERTICAL, NONE = 0x01, 0x02, 0x04, 0x06, 0x10, 0x7F
ONLY_FLAG = {
    "taskbar": TASKBAR,
    "window": WINDOW,
    "horizontal": HORIZONTAL,
    "horizontal+": HORIZONTAL_,
    "vertical": VERTICAL,
    # anything else (including "none" and a missing attribute) -> NONE wildcard
}

# Simulated desktop.  SCREEN_H is the *work area* (above the taskbar).
SCREEN_X, SCREEN_Y, SCREEN_W, SCREEN_H = 0, 0, 1920, 1040
# One typical on-screen window, used for the "with window" pass.
WINDOW_RECT = dict(left=600, top=500, right=1300, bottom=900)

DEFAULT_SEEDS = 60
DEFAULT_TICKS = 20000
STUCK_TICKS = 60        # same (x, y) for more than this many ticks while airborne == stuck
GROUND_SLOP = 3         # FormPet.cs:702 "allow 3 pixels to move without fall"
FELL_MARGIN = 300       # this far below the work area == fell through the floor
MAX_RESPAWNS = 200      # runaway guard
DROP_MAX_Y = 300        # in a drop scenario, the pet appears somewhere in the top 300px

_EXPR_OK = re.compile(r"^[0-9+\-*/() ]+$")


# --------------------------------------------------------------------------
# XML model
# --------------------------------------------------------------------------

def _text(node, tag, default=None):
    child = node.find("a:" + tag, NS)
    if child is None or child.text is None:
        return default
    return child.text.strip()


class Pet:
    """A parsed pet: sprite-sheet geometry, spawns and the animation graph."""

    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(os.path.dirname(path)) or os.path.basename(path)
        root = ET.parse(path).getroot()

        img = root.find("a:image", NS)
        if img is None:
            raise ValueError("no <image> element")
        self.tilesx = int(_text(img, "tilesx"))
        self.tilesy = int(_text(img, "tilesy"))
        png_b64 = _text(img, "png", "")
        sheet = Image.open(io.BytesIO(base64.b64decode(png_b64)))
        self.sheet_w, self.sheet_h = sheet.size
        # Tile == hitbox: eSheep sizes the pet window to one tile.
        self.width = self.sheet_w // self.tilesx
        self.height = self.sheet_h // self.tilesy
        self.n_tiles = self.tilesx * self.tilesy

        self.spawns = []
        spawns = root.find("a:spawns", NS)
        if spawns is not None:
            for s in spawns.findall("a:spawn", NS):
                self.spawns.append(dict(
                    id=int(s.get("id", 0)),
                    probability=int(s.get("probability", 100)),
                    x=_text(s, "x", "0"),
                    y=_text(s, "y", "0"),
                    next=[(int(n.get("probability", 100)), int(n.text))
                          for n in s.findall("a:next", NS)],
                ))

        self.anims = {}
        for node in root.find("a:animations", NS).findall("a:animation", NS):
            a = Anim(node)
            self.anims[a.id] = a

    def evaluate(self, expr):
        """eSheep allows expressions: random/12+6, areaH-imageH, screenW-imageW-10."""
        if isinstance(expr, int):
            return expr
        e = str(expr).strip()
        for token, value in (("screenW", SCREEN_W), ("screenH", SCREEN_H),
                             ("areaW", SCREEN_W), ("areaH", SCREEN_H),
                             ("imageW", self.width), ("imageH", self.height)):
            e = e.replace(token, str(value))
        e = e.replace("random", str(random.randint(0, 100)))
        if not _EXPR_OK.match(e):
            raise ValueError("unsupported expression: %r" % expr)
        return int(eval(e))  # noqa: S307 - guarded by _EXPR_OK


class Anim:
    def __init__(self, node):
        self.id = int(node.get("id"))
        self.name = _text(node, "name", "?")
        start, end = node.find("a:start", NS), node.find("a:end", NS)
        self.sx, self.sy = int(_text(start, "x", 0)), int(_text(start, "y", 0))
        self.ex, self.ey = int(_text(end, "x", 0)), int(_text(end, "y", 0))

        seq = node.find("a:sequence", NS)
        self.repeat_from = int(seq.get("repeatfrom", 0))
        self.repeat_expr = seq.get("repeat", "0")
        self.action = seq.get("action", "")
        self.frames = [int(f.text) for f in seq.findall("a:frame", NS)]
        self.nexts = self._nexts(seq)

        border, gravity = node.find("a:border", NS), node.find("a:gravity", NS)
        self.border = self._nexts(border) if border is not None else []
        self.gravity = self._nexts(gravity) if gravity is not None else []
        self.has_gravity = bool(self.gravity)

    @staticmethod
    def _nexts(parent):
        out = []
        for n in parent.findall("a:next", NS):
            only = ONLY_FLAG.get((n.get("only") or "none").strip().lower(), NONE)
            out.append((int(n.get("probability", 100)), only, int(n.text)))
        return out

    def total_steps(self, pet):
        """Animations.cs:198 CalculateTotalSteps()."""
        n = len(self.frames)
        return n + (n - self.repeat_from) * pet.evaluate(self.repeat_expr)

    def is_airborne(self):
        """A fall or a jump: it has vertical motion of its own."""
        return self.sy != 0 or self.ey != 0

    def __repr__(self):
        return "#%d %s" % (self.id, self.name)


def pick(lst, where):
    """Animations.cs:749 SetNextGeneralAnimation().  NONE (0x7F) is a wildcard."""
    cand = [(p, i) for (p, only, i) in lst if only == NONE or (only & where)]
    if not cand:
        return -1
    rand_max = sum(p for p, _ in cand)
    v = random.randint(0, max(rand_max - 1, 0))
    total = 0
    for p, i in cand:
        total += p
        if total >= v:
            return i
    return -1


# --------------------------------------------------------------------------
# 1. Static checks
# --------------------------------------------------------------------------

def static_checks(pet):
    """Returns (errors, warnings) as lists of strings."""
    errors, warnings = [], []
    ids = set(pet.anims)

    def check_targets(anim, kind, lst):
        for _p, _only, target in lst:
            if target not in ids:
                errors.append("%s <%s> points at animation id %d, which does not exist"
                              % (anim, kind, target))

    for anim in pet.anims.values():
        check_targets(anim, "next", anim.nexts)
        check_targets(anim, "border", anim.border)
        check_targets(anim, "gravity", anim.gravity)

        for f in anim.frames:
            if not 0 <= f < pet.n_tiles:
                errors.append("%s uses frame %d, but the sheet only has %d tiles (%dx%d)"
                              % (anim, f, pet.n_tiles, pet.tilesx, pet.tilesy))

    if not pet.spawns:
        errors.append("no <spawn> defined")
    for s in pet.spawns:
        if not s["next"]:
            errors.append("<spawn id=%d> has no <next>" % s["id"])
        for _p, target in s["next"]:
            if target not in ids:
                errors.append("<spawn id=%d> points at animation id %d, which does not exist"
                              % (s["id"], target))

    # --- the mid-air wall freeze -------------------------------------------
    # An airborne animation that hits a screen edge gets x clamped to 0 and is
    # replaced by its border target.  If that target's start <x> is nonzero it
    # walks straight back into the same edge on its very first tick, which
    # re-fires the border, forever: position frozen, y never applied.
    for anim in pet.anims.values():
        if not anim.is_airborne():
            continue
        for _p, only, target in anim.border:
            if not (only == NONE or (only & VERTICAL)):
                continue
            dest = pet.anims.get(target)
            if dest is not None and dest.sx != 0:
                errors.append(
                    "MID-AIR WALL FREEZE: airborne %s routes a wall border "
                    "(only=%s) to %s, whose start <x> is %d (must be 0)"
                    % (anim, "none/WILDCARD" if only == NONE else "vertical",
                       dest, dest.sx))

    # --- fall targets that cannot land on their first tick ------------------
    # FormPet.cs:574 only ground-checks inside `else if (y > 0)`.
    fall_targets = set()
    for anim in pet.anims.values():
        for _p, _only, target in anim.gravity:
            fall_targets.add(target)
    for target in sorted(fall_targets):
        dest = pet.anims.get(target)
        if dest is not None and dest.sy == 0:
            warnings.append(
                "%s is a gravity/fall target but its start <y> is 0; the ground "
                "check at FormPet.cs:574 only runs when y > 0, so it cannot land "
                "on its first tick" % dest)

    return errors, warnings


# --------------------------------------------------------------------------
# 2. Dynamic check: the simulated runtime
# --------------------------------------------------------------------------

class Sim:
    """One pet on one simulated desktop.  window=None -> bare screen + taskbar."""

    def __init__(self, pet, seed, window=None, drop=False):
        random.seed(seed)
        self.pet = pet
        self.win = window
        self.drop = drop
        self.bottom = SCREEN_Y + SCREEN_H
        self.floor = self.bottom - pet.height
        self.moving_left = True          # FormPet.cs:53
        self.on_window = False           # hwndWindow != 0
        self.respawns = 0
        self.landings = 0
        self.history = []
        self.spawn()

    # -- helpers ---------------------------------------------------------
    def spawn(self):
        pet = self.pet
        total = sum(s["probability"] for s in pet.spawns) or 1
        v = random.randint(0, total - 1)
        acc = 0
        chosen = pet.spawns[-1]
        for s in pet.spawns:
            acc += s["probability"]
            if acc > v:
                chosen = s
                break
        self.px = float(pet.evaluate(chosen["x"]))
        self.py = float(pet.evaluate(chosen["y"]))
        if self.drop:
            # Appear in mid-air, as after a drag-and-drop or when a window the
            # pet was standing on closes.  This is what makes long falls (and
            # therefore falls alongside a wall, and landings on windows) happen.
            self.px = float(random.randint(SCREEN_X, SCREEN_X + SCREEN_W - pet.width))
            self.py = float(random.randint(SCREEN_Y + 21, SCREEN_Y + DROP_MAX_Y))
        self.on_window = False
        nxt = pick([(p, NONE, i) for p, i in chosen["next"]], NONE)
        self.set_anim(nxt if nxt >= 0 else next(iter(pet.anims)))

    def set_anim(self, aid):
        self.cur = self.pet.anims[aid]
        self.step = -1
        self.total = self.cur.total_steps(self.pet)

    def fall_detect(self, y):
        """FormPet.cs:837.  Returns the window top, or -1 if still falling."""
        w = self.win
        if w is None:
            return -1
        feet = self.py + self.pet.height
        if (feet < w["top"] and feet + y >= w["top"]
                and self.px >= w["left"] - self.pet.width / 2.0
                and self.px + self.pet.width <= w["right"] + self.pet.width / 2.0
                and self.py > 20 + SCREEN_Y):
            self.on_window = True       # side effect, even if no border matches
            return w["top"]
        return -1

    # -- one timer tick --------------------------------------------------
    def tick(self):
        pet = self.pet
        W, H = pet.width, pet.height
        if self.step < 0:
            self.step = 0

        ts = max(self.total, 1)
        x, y = float(self.cur.sx), float(self.cur.sy)
        if ts > 1:
            x += (self.cur.ex - self.cur.sx) * self.step / (ts - 1.0)
            y += (self.cur.ey - self.cur.sy) * self.step / (ts - 1.0)
        if not self.moving_left:
            x = -x

        new_anim = leaving = False

        # ---- horizontal borders (FormPet.cs:481-569) ----
        if x < 0:
            if not self.on_window:
                if self.px + x < SCREEN_X:
                    b = pick(self.cur.border, VERTICAL)
                    if b >= 0:
                        self.px, x = float(SCREEN_X), 0.0
                        self.set_anim(b)
                        new_anim = True
                    else:
                        leaving = True
            elif self.px + x < self.win["left"]:
                b = pick(self.cur.border, WINDOW)
                if b >= 0:
                    self.px, x = float(self.win["left"]), 0.0
                    self.set_anim(b)
                    new_anim = True
                else:
                    self.on_window = False          # walked off the left ledge
        elif x > 0:
            if not self.on_window:
                if self.px + x + W > SCREEN_X + SCREEN_W:
                    b = pick(self.cur.border, VERTICAL)
                    if b >= 0:
                        self.px, x = float(SCREEN_X + SCREEN_W - W), 0.0
                        self.set_anim(b)
                        new_anim = True
                    else:
                        leaving = True
            elif self.px + x + W > self.win["right"]:
                b = pick(self.cur.border, WINDOW)
                if b >= 0:
                    self.px, x = float(self.win["right"] - W), 0.0
                    self.set_anim(b)
                    new_anim = True
                else:
                    self.on_window = False          # walked off the right ledge

        # ---- vertical borders (FormPet.cs:570-628) ----
        if new_anim or leaving:
            pass
        elif y > 0:
            if self.py + y > self.bottom - H:                    # taskbar
                b = pick(self.cur.border, TASKBAR)
                if b >= 0:
                    self.py, y = float(self.bottom - H), 0.0
                    self.on_window = False
                    self.set_anim(b)
                    new_anim = True
                    self.landings += 1
                # no else: unmatched taskbar event == fall straight through
            else:
                top = self.fall_detect(y)
                if top > 0:
                    b = pick(self.cur.border, WINDOW)
                    if b >= 0:
                        self.py, y = float(top - H), 0.0
                        self.set_anim(b)
                        new_anim = True
                        self.landings += 1
                        if self.cur.sy != 0:
                            self.on_window = False
        elif y < 0:
            if self.py + y < SCREEN_Y:                           # ceiling
                b = pick(self.cur.border, HORIZONTAL)
                if b >= 0:
                    self.py, y = float(SCREEN_Y), 0.0
                    self.set_anim(b)
                    new_anim = True
                else:
                    leaving = True

        # ---- sequence over (FormPet.cs:630) ----
        if self.step >= self.total:
            if self.cur.action == "flip":
                self.moving_left = not self.moving_left
            if self.on_window:
                nxt = pick(self.cur.nexts, WINDOW)
            elif (self.px < SCREEN_X - W or self.px > SCREEN_X + SCREEN_W
                  or self.py < SCREEN_Y - H or self.py > SCREEN_Y + SCREEN_H):
                nxt = -1
            else:
                where = TASKBAR if self.py + H + y >= self.bottom - 2 else NONE
                nxt = pick(self.cur.nexts, where)
            if nxt < 0:
                self.respawns += 1
                self.spawn()
                return None
            self.set_anim(nxt)
            new_anim = True

        # ---- gravity (FormPet.cs:699) ----
        elif self.cur.has_gravity:
            if not self.on_window:
                if self.py + y < self.floor:
                    if self.py + y + GROUND_SLOP >= self.floor:
                        y = self.floor - self.py
                    else:
                        g = pick(self.cur.gravity, NONE)
                        if g < 0:
                            self.respawns += 1
                            self.spawn()
                            return None
                        self.set_anim(g)
                        new_anim = True
            # window never moves and is never covered here, so CheckTopWindow(true)
            # is False and the on-window gravity branch does nothing.

        self.px += x
        self.py += y
        self.step += 1
        self.history.append((self.cur.name, round(self.px), round(self.py),
                             round(y, 1), self.on_window))

        if self.py > self.bottom + FELL_MARGIN:
            return "FELL THROUGH FLOOR"
        if self.respawns > MAX_RESPAWNS:
            return "RESPAWN STORM (%d respawns)" % self.respawns
        return None

    def airborne(self):
        """Not resting on the taskbar and not standing on the window."""
        if self.on_window:
            return False
        return self.py + self.pet.height < self.bottom - GROUND_SLOP


SCENARIOS = [
    # label,            window,       drop
    ("bare screen",     None,         False),
    ("bare + drops",    None,         True),
    ("window + drops",  WINDOW_RECT,  True),
]


def dynamic_check(pet, seeds, ticks, window, drop):
    """Run the sim. Returns (failures, stats)."""
    failures = []
    landings = respawns = 0
    for seed in range(seeds):
        sim = Sim(pet, seed, window, drop)
        last_pos, same = None, 0
        verdict = None
        for t in range(ticks):
            verdict = sim.tick()
            if verdict:
                break
            pos = (round(sim.px), round(sim.py))
            if pos == last_pos and sim.airborne():
                same += 1
                if same > STUCK_TICKS:
                    verdict = ("STUCK in '%s' at (x=%d, y=%d) for %d ticks while "
                               "airborne (floor is y=%d)"
                               % (sim.cur.name, pos[0], pos[1], same, sim.floor))
                    break
            else:
                same = 0
                last_pos = pos
        landings += sim.landings
        respawns += sim.respawns
        if verdict:
            failures.append((seed, t, verdict, sim.history[-6:]))
    return failures, dict(landings=landings, respawns=respawns)


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------

def check(path, seeds, ticks, verbose):
    print("=" * 78)
    print("PET  %s" % path)
    try:
        pet = Pet(path)
    except Exception as exc:                                   # noqa: BLE001
        print("  FAIL  cannot parse: %s: %s" % (type(exc).__name__, exc))
        return False
    print("  sheet %dx%d px, %dx%d tiles -> tile/hitbox %dx%d px, %d animations"
          % (pet.sheet_w, pet.sheet_h, pet.tilesx, pet.tilesy,
             pet.width, pet.height, len(pet.anims)))
    print("  screen %dx%d, floor y=%d" % (SCREEN_W, SCREEN_H, SCREEN_H - pet.height))

    ok = True
    errors, warnings = static_checks(pet)
    print("\n  -- static --")
    for w in warnings:
        print("  WARN  %s" % w)
    for e in errors:
        print("  FAIL  %s" % e)
    if not errors:
        print("  ok    graph, spawns, frame indices, border routing")
    else:
        ok = False

    print("\n  -- dynamic (%d seeds x %d ticks) --" % (seeds, ticks))
    for label, window, drop in SCENARIOS:
        failures, stats = dynamic_check(pet, seeds, ticks, window, drop)
        if failures:
            ok = False
            print("  FAIL  %-14s %d/%d seeds failed  (%d landings)"
                  % (label, len(failures), seeds, stats["landings"]))
            for seed, t, verdict, hist in failures[:len(failures) if verbose else 2]:
                print("        seed %d, tick %d: %s" % (seed, t, verdict))
                for h in hist:
                    print("            anim=%-20s x=%-6d y=%-6d dy=%-6s onWindow=%s" % h)
        else:
            print("  ok    %-14s %d seeds clean, %d landings, %d respawns"
                  % (label, seeds, stats["landings"], stats["respawns"]))
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pets", nargs="*", default=DEFAULT_PETS,
                    help="pet XML paths (default: big_mario + mario)")
    ap.add_argument("--seeds", type=int, default=DEFAULT_SEEDS)
    ap.add_argument("--ticks", type=int, default=DEFAULT_TICKS)
    ap.add_argument("--verbose", action="store_true", help="print every failing seed")
    args = ap.parse_args()

    results = [(p, check(p, args.seeds, args.ticks, args.verbose))
               for p in (args.pets or DEFAULT_PETS)]

    print("=" * 78)
    bad = [p for p, ok in results if not ok]
    for p, ok in results:
        print("  %-4s %s" % ("OK" if ok else "FAIL", p))
    if bad:
        print("\n%d/%d pets FAILED" % (len(bad), len(results)))
        return 1
    print("\nOK: %d/%d pets pass all static and dynamic checks." % (len(results), len(results)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
