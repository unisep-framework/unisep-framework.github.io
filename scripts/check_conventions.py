#!/usr/bin/env python3
"""Check the global axis convention of the landmark table (check A5).

For every segment and side, the axis limits are parsed from
anatomical_table.qmd and placed at approximate positions of a canonical body in
the anatomical position (x = subject's right, y = anterior, z = superior; cm).
A frame is built with the reference implementation (primary X, secondary Z;
for the thorax the secondary Z vector is the longitudinal body axis, decision
D1; Y completes the right-handed system). The check passes if every axis
points in its conventional direction (right / anterior / superior), the
limits of every axis project with positive length onto the axis
((B − A) · e > 0), and the frame is right-handed (det = +1).

The landmark positions are rough illustrative values used only to determine
directions; they are not part of the standard. The primary/secondary choice is
an assumption of this check, not a per-segment default (decision D6).

Usage: python scripts/check_conventions.py   (exit code 1 on any violation)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
from compare_inventory import axis_limits  # noqa: E402
from table_inventory import DEFAULT_TABLE, parse_table  # noqa: E402
from unisep import orthonormal_frame  # noqa: E402

# Approximate positions (cm) for the RIGHT side / midline; left side mirrors x.
LANDMARKS = {
    "Head": {"lhj": (-7, 0, 165), "rhj": (7, 0, 165), "inion": (0, -9, 163), "nasion": (0, 9, 165),
             "mmp": (0, -2, 158), "vertex": (0, 0, 178)},
    "Neck": {"lmp": (-6, -2, 158), "rmp": (6, -2, 158), "c7": (0, -6, 145), "jugular notch": (0, 4, 142),
             "mmp": (0, -2, 158)},
    "Torso-chest": {"lap": (-18, 0, 142), "rap": (18, 0, 142), "c7": (0, -6, 145),
                    "xiphoid process": (0, 10, 120)},
    "Abdomen": {"left asis": (-12, 8, 100), "right asis": (12, 8, 100), "midpoint of the psis": (0, -10, 102),
                "midpoint of the asis": (0, 8, 100), "navel": (0, 12, 105), "xiphoid process": (0, 10, 120)},
    # hands and forearms in the anatomical position: palms forward, radius lateral
    "Hand": {"rsp": (28, 0, 85), "usp": (22, 0, 85), "dorsal surface": (25, -1.5, 80),
             "palmar surface at the midpoint rsp-usp": (25, 1.5, 80), "mcp": (25, 0, 72),
             "midpoint rsp-usp": (25, 0, 85)},
    "Upper-arm": {"mhe": (17, 0, 105), "lhe": (23, 0, 105), "olecranon": (20, -4, 105),
                  "cubital fossa": (20, 3, 105), "midpoint mhe-lhe": (20, 0, 105), "acromion": (18, 0, 142)},
    "Forearm": {"rsp": (28, 0, 85), "usp": (22, 0, 85), "olecranon": (20, -4, 105), "cubital fossa": (20, 3, 105),
                "midpoint rsp-usp": (25, 0, 85), "lhe": (23, 0, 105)},
    "Thigh": {"fme": (6, 0, 50), "fle": (14, 0, 50), "popliteal fossa": (10, -5, 50),
              "patellar anterior surface": (10, 5, 50), "midpoint fme-fle": (10, 0, 50),
              "greater trochanter": (16, 0, 92)},
    "Lower-leg": {"mm": (7, 0, 8), "lm": (13, -1, 7), "popliteal fossa": (10, -5, 50),
                  "patellar anterior surface": (10, 5, 50), "midpoint mm-lm": (10, -0.5, 7.5)},
    "Foot": {"mm": (7, 0, 8), "lm": (13, -1, 7), "ct": (10, -5, 2), "fmh": (8, 15, 2),
             "mm-lm line": (10, -0.5, 7.5)},
}
DIRECTION = {"X": (np.array([1.0, 0, 0]), "right"), "Y": (np.array([0, 1.0, 0]), "anterior"),
             "Z": (np.array([0, 0, 1.0]), "superior")}
LONGITUDINAL = np.array([0, 0, 1.0])


def position(name: str, side: str | None, landmark: str) -> np.ndarray:
    p = np.array(LANDMARKS[name][landmark], dtype=float)
    if side == "left":
        p[0] = -p[0]
    return p


def main() -> int:
    rows = parse_table(DEFAULT_TABLE.read_text(encoding="utf-8"))
    failures = 0
    print("| Segment | Side | Axis | Limits (0 % → 100 %) | Direction in anatomical position | (B−A)·e > 0 | det | Result |")
    print("|---|---|---|---|---|---|---|---|")
    for r in rows:
        name, side = r["name"], r["side"]
        lim = {k: tuple(position(name, side, l) for l in axis_limits(r["axes"][k])) for k in "XYZ"}
        names = {k: axis_limits(r["axes"][k]) for k in "XYZ"}
        vec = {k: lim[k][1] - lim[k][0] for k in "XYZ"}
        z_secondary = LONGITUDINAL if name == "Torso-chest" else vec["Z"]
        frame = orthonormal_frame("X", vec["X"], "Z", z_secondary)
        det = float(np.linalg.det(np.column_stack([frame["X"], frame["Y"], frame["Z"]])))
        for k in "XYZ":
            e = frame[k]
            dominant = int(np.argmax(np.abs(e)))
            sign = "+" if e[dominant] > 0 else "−"
            word = {0: ("right", "left"), 1: ("anterior", "posterior"), 2: ("superior", "inferior")}[dominant]
            direction = word[0] if e[dominant] > 0 else word[1]
            proj_ok = float(np.dot(vec[k], e)) > 0
            ok = direction == DIRECTION[k][1] and proj_ok and abs(det - 1) < 1e-12
            failures += not ok
            seg = f"{name} ({r['segment']})"
            print(f"| {seg} | {side or '—'} | {k} | {names[k][0]} → {names[k][1]} | {direction} "
                  f"({sign}{'xyz'[dominant]}) | {'yes' if proj_ok else 'NO'} | {det:+.0f} | "
                  f"{'ok' if ok else 'VIOLATION'} |")
    print()
    print(f"A5 RESULT: {'FAIL' if failures else 'PASS'} — {len(rows)} segment rows, {failures} violation(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
