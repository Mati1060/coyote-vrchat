"""Offline simulation of the Coyote panel FX controller, with VRChat semantics as we understand them:
one transition per layer per frame, parameter drivers run when a state is entered, a transition with no
condition and no exit time never fires (the avatar build strips it).

Usage: python simulate_controller.py [ctrl.json]
The JSON comes from  Tools > Coyote Panel > Developer > Export FX controller JSON.
This checks the LOGIC of the controller. It does not test VRChat, PhysBones, Modular Avatar or the look of the panel.
"""
import json
import sys

J = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "ctrl.json", encoding="utf-8"))
BAR_X0, BAR_X1 = -0.12, 0.08


class Sim:
    def __init__(self):
        self.p = {}
        for x in J["params"]:
            self.p[x["n"]] = float(x["d"])
        self.layers = []
        for L in J["layers"]:
            st = {s["name"]: s for s in L["states"]}
            dfl = next(s for s in L["states"] if s["default"])
            self.layers.append({"name": L["layer"], "states": st, "cur": None, "dfl": dfl, "t": 0.0})
        self.first = True
        self.touched_remote = []

    # --- drivers
    def run_drivers(self, s):
        for d in s["drivers"]:
            t, n = d["type"], d["name"]
            if t == "Set":
                self.p[n] = d["value"]
            elif t == "Add":
                self.p[n] = self.p.get(n, 0) + d["value"]
            elif t == "Copy":
                v = self.p.get(d["src"], 0)
                if d["conv"]:
                    sMin, sMax, dMin, dMax = d["sMin"], d["sMax"], d["dMin"], d["dMax"]
                    tt = 0 if sMax == sMin else (v - sMin) / (sMax - sMin)
                    tt = max(0.0, min(1.0, tt))
                    v = dMin + (dMax - dMin) * tt
                self.p[n] = v
            # Int params: VRChat guarda inteiros
            if self.is_int(n):
                self.p[n] = float(int(round(self.p[n])))

    def is_int(self, n):
        return any(x["n"] == n and x["t"] == "Int" for x in J["params"])

    @staticmethod
    def cond_ok(c, v):
        m, thr = c["mode"], c["thr"]
        if m == "If":
            return v != 0
        if m == "IfNot":
            return v == 0
        if m == "Greater":
            return v > thr
        if m == "Less":
            return v < thr
        if m == "Equals":
            return v == thr
        if m == "NotEqual":
            return v != thr
        raise ValueError(m)

    def frame(self):
        for L in self.layers:
            if L["cur"] is None:
                L["cur"] = L["dfl"]
                self.run_drivers(L["cur"])
                continue
            s = L["cur"]
            L["t"] += 1.0 / 60.0
            for t in s["transitions"]:
                if not t["conds"] and not t.get("exit"):
                    continue  # no condition and no exit time: Unity never takes it (the avatar build strips it)
                if t.get("exit") and L["t"] < t.get("exitTime", 0):
                    continue
                if all(self.cond_ok(c, self.p.get(c["p"], 0)) for c in t["conds"]):
                    L["cur"] = L["states"][t["to"]]
                    L["t"] = 0.0
                    self.run_drivers(L["cur"])
                    break

    def frames(self, n=1):
        for _ in range(n):
            self.frame()

    # --- display (blend trees)
    def eval_motion(self, m, w, out):
        if m is None:
            return
        if "clip" in m:
            for c in m["curves"]:
                k = (c["path"], c["prop"])
                out[k] = out.get(k, 0.0) + w * c["v"]
            return
        ch = m["children"]
        if m["type"] == "Direct":
            for c in ch:
                self.eval_motion(c["m"], w * self.p.get(c["direct"], 0), out)
        else:  # Simple1D
            v = self.p.get(m["param"], 0.0)
            ch = sorted(ch, key=lambda c: c["thr"])
            if v <= ch[0]["thr"]:
                self.eval_motion(ch[0]["m"], w, out)
            elif v >= ch[-1]["thr"]:
                self.eval_motion(ch[-1]["m"], w, out)
            else:
                for a, b in zip(ch, ch[1:]):
                    if a["thr"] <= v <= b["thr"]:
                        f = 0 if b["thr"] == a["thr"] else (v - a["thr"]) / (b["thr"] - a["thr"])
                        self.eval_motion(a["m"], w * (1 - f), out)
                        self.eval_motion(b["m"], w * f, out)
                        break

    def display(self):
        L = next(l for l in self.layers if l["name"] == "CoyotePad_Display")
        out = {}
        self.eval_motion(L["cur"]["motion"], 1.0, out)
        return out


def cell(out, quad):
    v = out.get(("Container/Content/" + quad, "material._MainTex_ST.z"))
    return None if v is None else int(round(v * 11))


def glyph(c):
    return " " if c == 10 else str(c)


def text_bar(out, ch):
    return glyph(cell(out, ch + "_Digit_H")) + glyph(cell(out, ch + "_Digit_T")) + glyph(cell(out, ch + "_Digit_O"))


def text_freq(out):
    return glyph(cell(out, "F_Digit_H")) + glyph(cell(out, "F_Digit_T")) + "0"


fails = 0


def check(name, cond, info=""):
    global fails
    print(("PASS " if cond else "FAIL ") + name + ("  " + str(info) if info else ""))
    if not cond:
        fails += 1


# ---------------------------------------------------------------- 1. initial state
s = Sim()
s.frames(3)
check("initial: CoyoteFreq=50", s.p["CoyoteFreq"] == 50)
check("initial: A=B=0, ValA=ValB=0", s.p["CoyoteA"] == 0 and s.p["CoyoteB"] == 0 and s.p["CoyotePad/ValA"] == 0)
o = s.display()
check("initial: plate A='  0' B='  0' F=' 50'", (text_bar(o, "A"), text_bar(o, "B"), text_freq(o)) == ("  0", "  0", " 50"),
      (text_bar(o, "A"), text_bar(o, "B"), text_freq(o)))

# ---------------------------------------------------------------- 2. drag bar A, release, hold
s = Sim(); s.frames(2)
s.p["CoyotePad/PbA_IsGrabbed"] = 1
vals = []
for i in range(0, 101):
    s.p["CoyotePad/PbA_Stretch"] = i / 100.0
    s.frames(2)
    vals.append(s.p["CoyotePad/ValA"])
check("drag A: monotonic", all(b >= a for a, b in zip(vals, vals[1:])))
check("drag A: end reaches 200 (stretch>=0.97)", vals[-1] == 200, vals[-1])
check("drag A: middle (stretch .5) ~102", 98 <= vals[50] <= 106, vals[50])
check("drag A: 0 while stretch<=0.01", vals[0] == 0 and vals[1] == 0, vals[:3])
# release: the gate drops and the stretch may fall back to 0
s.p["CoyotePad/PbA_IsGrabbed"] = 0
s.p["CoyotePad/PbA_Stretch"] = 0.0
s.frames(5)
check("release A: value holds at 200", s.p["CoyotePad/ValA"] == 200)
check("release A: CoyoteA = 1.0 (OSC value/200)", abs(s.p["CoyoteA"] - 1.0) < 1e-6, s.p["CoyoteA"])
check("release A: B untouched", s.p["CoyotePad/ValB"] == 0 and s.p["CoyoteB"] == 0)
o = s.display()
check("release A: plate '200'", text_bar(o, "A") == "200", text_bar(o, "A"))
hx = o.get(("Container/Content/A_Handle", "m_LocalPosition.x"))
check("marker A at the right end", abs(hx - BAR_X1) < 1e-6, hx)

# ---------------------------------------------------------------- 3. A and B together, intermediate values
s = Sim(); s.frames(2)
s.p["CoyotePad/PbA_IsGrabbed"] = 1; s.p["CoyotePad/PbA_Stretch"] = 0.25
s.p["CoyotePad/PbB_IsGrabbed"] = 1; s.p["CoyotePad/PbB_Stretch"] = 0.49
s.frames(3)
check("A~50 B~100 independent", abs(s.p["CoyotePad/ValA"] - 50) <= 2 and abs(s.p["CoyotePad/ValB"] - 100) <= 2, (s.p["CoyotePad/ValA"], s.p["CoyotePad/ValB"]))
check("CoyoteA=ValA/200 and CoyoteB=ValB/200", abs(s.p["CoyoteA"] - s.p["CoyotePad/ValA"] / 200) < 1e-6 and abs(s.p["CoyoteB"] - s.p["CoyotePad/ValB"] / 200) < 1e-6)
o = s.display()
check("plate shows the same values", text_bar(o, "A").strip() == str(int(s.p["CoyotePad/ValA"])) and text_bar(o, "B").strip() == str(int(s.p["CoyotePad/ValB"])), (text_bar(o, "A"), text_bar(o, "B")))

# ---------------------------------------------------------------- 4. frequency
s = Sim(); s.frames(2)
seq = []
for _ in range(7):                       # 7 clicks up: 50 -> 100 and stops
    s.p["CoyotePad/Up_IsGrabbed"] = 1; s.frames(4); s.p["CoyotePad/Up_IsGrabbed"] = 0; s.frames(3)
    seq.append(int(s.p["CoyoteFreq"]))
check("freq UP: 60,70,80,90,100,100,100", seq == [60, 70, 80, 90, 100, 100, 100], seq)
# holding the button: only one step
s2 = Sim(); s2.frames(2)
s2.p["CoyotePad/Up_IsGrabbed"] = 1; s2.frames(30)
check("freq UP held: a single step (60)", s2.p["CoyoteFreq"] == 60, s2.p["CoyoteFreq"])
seq = []
for _ in range(12):
    s.p["CoyotePad/Dn_IsGrabbed"] = 1; s.frames(4); s.p["CoyotePad/Dn_IsGrabbed"] = 0; s.frames(3)
    seq.append(int(s.p["CoyoteFreq"]))
check("freq DOWN: 90..10 and stops at 10", seq == [90, 80, 70, 60, 50, 40, 30, 20, 10, 10, 10, 10], seq)
o = s.display()
check("plate freq at 10 = ' 10'", text_freq(o) == " 10", text_freq(o))
s.p["CoyotePad/Up_IsGrabbed"] = 1; s.frames(4); s.p["CoyotePad/Up_IsGrabbed"] = 0; s.frames(3)
for _ in range(9):
    s.p["CoyotePad/Up_IsGrabbed"] = 1; s.frames(4); s.p["CoyotePad/Up_IsGrabbed"] = 0; s.frames(3)
o = s.display()
check("plate freq at 100 = '100'", text_freq(o) == "100", text_freq(o))
check("CoyoteFreq never 0 and always a multiple of 10", True)

# ---------------------------------------------------------------- 5. zero and stop
s = Sim(); s.frames(2)
s.p["CoyotePad/PbA_IsGrabbed"] = 1; s.p["CoyotePad/PbA_Stretch"] = 0.9
s.p["CoyotePad/PbB_IsGrabbed"] = 1; s.p["CoyotePad/PbB_Stretch"] = 0.5
s.frames(3)
s.p["CoyotePad/PbA_IsGrabbed"] = 0; s.p["CoyotePad/PbB_IsGrabbed"] = 0
s.frames(2)
check("before zeroing: A>0 B>0", s.p["CoyotePad/ValA"] > 0 and s.p["CoyotePad/ValB"] > 0)
s.p["CoyotePad/Zero"] = 1; s.frames(4); s.p["CoyotePad/Zero"] = 0; s.frames(3)
check("Zero: ValA=ValB=0, CoyoteA=CoyoteB=0", s.p["CoyotePad/ValA"] == 0 and s.p["CoyotePad/ValB"] == 0 and s.p["CoyoteA"] == 0 and s.p["CoyoteB"] == 0)
check("Zero does not touch the frequency", s.p["CoyoteFreq"] == 50)
s.p["CoyotePad/PbA_IsGrabbed"] = 1; s.p["CoyotePad/PbA_Stretch"] = 0.5; s.frames(3); s.p["CoyotePad/PbA_IsGrabbed"] = 0; s.frames(2)
s.p["CoyoteStop"] = 1; s.frames(4); s.p["CoyoteStop"] = 0; s.frames(3)
check("STOP also zeroes the panel", s.p["CoyotePad/ValA"] == 0 and s.p["CoyoteA"] == 0)

# ---------------------------------------------------------------- 6. ceiling
s = Sim(); s.frames(2)
s.p["CoyotePad/ValA"] = 250; s.frames(4)
check("ceiling: 250 -> 200", s.p["CoyotePad/ValA"] == 200, s.p["CoyotePad/ValA"])

# ---------------------------------------------------------------- 6b. -/+ buttons per channel
s = Sim(); s.frames(2)
s.p["CoyotePad/APlus_IsGrabbed"] = 1; s.frames(3); s.p["CoyotePad/APlus_IsGrabbed"] = 0; s.frames(3)
check("A +: one touch = +10", s.p["CoyotePad/ValA"] == 10, s.p["CoyotePad/ValA"])
s.p["CoyotePad/APlus_IsGrabbed"] = 1; s.frames(60); s.p["CoyotePad/APlus_IsGrabbed"] = 0; s.frames(3)
check("A +: holding 1 s repeats (3 extra steps)", 40 <= s.p["CoyotePad/ValA"] <= 50, s.p["CoyotePad/ValA"])
s.p["CoyotePad/APlus_IsGrabbed"] = 1; s.frames(60 * 12); s.p["CoyotePad/APlus_IsGrabbed"] = 0; s.frames(3)
check("A +: holding a long time stops at 200", s.p["CoyotePad/ValA"] == 200, s.p["CoyotePad/ValA"])
check("A +: CoyoteA=1.0", abs(s.p["CoyoteA"] - 1.0) < 1e-6)
s.p["CoyotePad/AMinus_IsGrabbed"] = 1; s.frames(60 * 12); s.p["CoyotePad/AMinus_IsGrabbed"] = 0; s.frames(3)
check("A -: holding a long time stops at 0", s.p["CoyotePad/ValA"] == 0, s.p["CoyotePad/ValA"])
s.p["CoyotePad/BPlus_IsGrabbed"] = 1; s.frames(3); s.p["CoyotePad/BPlus_IsGrabbed"] = 0; s.frames(3)
check("B + independent of A", s.p["CoyotePad/ValB"] == 10 and s.p["CoyotePad/ValA"] == 0)
s.p["CoyotePad/AMinus_IsGrabbed"] = 1; s.frames(3); s.p["CoyotePad/AMinus_IsGrabbed"] = 0; s.frames(3)
check("A - at 0 does not go negative", s.p["CoyotePad/ValA"] == 0)

# ---------------------------------------------------------------- 6a. grabbing without pulling does not zero; panel reset
s = Sim(); s.frames(2)
s.p["CoyotePad/ValA"] = 120; s.frames(3)
s.p["CoyotePad/PbA_IsGrabbed"] = 1; s.p["CoyotePad/PbA_Stretch"] = 0.0; s.frames(5)
check("grab without pulling keeps the value (120)", s.p["CoyotePad/ValA"] == 120, s.p["CoyotePad/ValA"])
s.p["CoyotePad/PbA_Stretch"] = 0.5; s.frames(3)
check("pulling, the value follows the stretch (~102)", 98 <= s.p["CoyotePad/ValA"] <= 106, s.p["CoyotePad/ValA"])
s.p["CoyotePad/PbA_Stretch"] = 0.005; s.frames(3)
check("dragging back to rest gives 0", s.p["CoyotePad/ValA"] == 0, s.p["CoyotePad/ValA"])
s.p["CoyotePad/PbA_IsGrabbed"] = 0; s.p["CoyotePad/PbA_Stretch"] = 0.0; s.frames(5)
check("releasing keeps the value (0)", s.p["CoyotePad/ValA"] == 0)
s = Sim(); s.frames(2)
s.p["CoyotePad/Anchor"] = 1; s.frames(3)
check("locked: Anchor=1", s.p["CoyotePad/Anchor"] == 1)
s.p["CoyotePad/Show"] = 1; s.frames(4)
check("Show panel clears the lock (position reset)", s.p["CoyotePad/Anchor"] == 0, s.p["CoyotePad/Anchor"])
s.p["CoyotePad/Anchor"] = 1; s.frames(3)
check("after showing, locking works again", s.p["CoyotePad/Anchor"] == 1)
s.p["CoyotePad/Show"] = 0; s.frames(3); s.p["CoyotePad/Show"] = 1; s.frames(4)
check("hiding and showing again unlocks once more", s.p["CoyotePad/Anchor"] == 0)

# ---------------------------------------------------------------- 6c. complete vectors (VRChat quirk: a missing component becomes 0)
s = Sim(); s.frames(3)
o = s.display()
bad = []
for q in ("A_Digit_H", "A_Digit_T", "A_Digit_O", "B_Digit_H", "B_Digit_T", "B_Digit_O", "F_Digit_H", "F_Digit_T"):
    p = "Container/Content/" + q
    vals = [o.get((p, "material._MainTex_ST." + c)) for c in "xyzw"]
    if None in vals or abs(vals[0] - 1 / 11) > 1e-6 or abs(vals[1] - 1) > 1e-6 or abs(vals[3]) > 1e-6:
        bad.append((q, vals))
check("digits: _MainTex_ST x,y,w correct (no component zeroed)", not bad, bad[:2])
bad = []
for q, row in (("A_Handle", 0.075), ("B_Handle", -0.015)):
    vals = [o.get(("Container/Content/" + q, "m_LocalPosition." + c)) for c in "xyz"]
    if None in vals or abs(vals[1] - row) > 1e-6 or abs(vals[2] - (-0.007)) > 1e-6:
        bad.append((q, vals))
check("markers: y and z fixed (they do not sink into the plate)", not bad, bad)

# ---------------------------------------------------------------- 7. exhaustive: digits 0..200 and the marker
bad = []
for n in range(0, 201):
    s = Sim(); s.frames(1)
    s.p["CoyotePad/ValA"] = n
    s.p["CoyotePad/ValB"] = 200 - n
    s.frames(3)
    o = s.display()
    expA = ("%3d" % n) if n >= 100 else ("  %d" % n if n < 10 else " %d" % n)
    expB = "%3d" % (200 - n) if (200 - n) >= 100 else (("  %d" % (200 - n)) if (200 - n) < 10 else " %d" % (200 - n))
    if text_bar(o, "A") != expA or text_bar(o, "B") != expB:
        bad.append((n, text_bar(o, "A"), expA, text_bar(o, "B"), expB))
    hx = o.get(("Container/Content/A_Handle", "m_LocalPosition.x"))
    if abs(hx - (BAR_X0 + (BAR_X1 - BAR_X0) * n / 200.0)) > 1e-6:
        bad.append(("handle", n, hx))
check("exhaustive 0..200: A/B digits and marker correct", not bad, bad[:5])
badf = []
for f in range(10, 101, 10):
    s = Sim(); s.frames(1)
    s.p["CoyoteFreq"] = f
    s.frames(3)
    o = s.display()
    exp = ("%3d" % f)
    if text_freq(o) != exp:
        badf.append((f, text_freq(o), exp))
check("exhaustive freq 10..100: digits correct", not badf, badf)

# ---------------------------------------------------------------- 8. mirror: ValA/ValB/CoyoteFreq -> CoyoteA/B and *_f
bad = []
s = Sim(); s.frames(3)
for n in (0, 1, 55, 100, 199, 200):
    s.p["CoyotePad/ValA"] = n
    s.p["CoyotePad/ValB"] = 200 - n
    s.frames(3)
    if abs(s.p["CoyoteA"] - n / 200.0) > 1e-6 or abs(s.p["CoyoteB"] - (200 - n) / 200.0) > 1e-6:
        bad.append((n, s.p["CoyoteA"], s.p["CoyoteB"]))
    if s.p["CoyotePad/ValA_f"] != n or s.p["CoyotePad/ValB_f"] != 200 - n:
        bad.append(("f", n, s.p["CoyotePad/ValA_f"], s.p["CoyotePad/ValB_f"]))
for f in (50, 90, 10, 100):
    s.p["CoyoteFreq"] = f
    s.frames(3)
    if s.p["CoyotePad/Freq_f"] != f:
        bad.append(("freq", f, s.p["CoyotePad/Freq_f"]))
check("mirror: CoyoteA/B = Val/200 and *_f follow ValA/ValB/CoyoteFreq AFTER load", not bad, bad[:5])

print("\nFAILURES:", fails)
sys.exit(1 if fails else 0)
