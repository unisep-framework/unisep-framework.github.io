#!/usr/bin/env python3
"""Compare the v0.1.1 landmark-table inventory with the current table (check A4).

Reports every change of an axis definition (direction swap or landmark rename)
and every changed example coordinate, then checks that the set of changes is
exactly the set specified for UNISEP 0.2.0 (Section 9.3 of the revision brief,
plus the FME -> FMH renaming of the foot, decision D2). Also runs the left/right
symmetry check of the examples (check A6).

Usage:
    python scripts/compare_inventory.py [--markdown]

Exit code 0 if the observed changes equal the expected changes, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from table_inventory import DEFAULT_TABLE, parse_table  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
BASELINE = REPO / "scripts" / "inventory" / "anatomical_table_v0.1.1.json"

# Expected axis changes: (segment, axis) -> kind
EXPECTED_AXIS = {
    ("2", "Z"): "swap",
    ("3", "Y"): "swap",
    ("7", "X"): "swap",
    ("8", "X"): "swap",
    ("9", "X"): "swap",
    ("4", "X"): "swap",
    ("5", "X"): "swap",
    ("14", "Y"): "rename",  # FME -> FMH (D2)
    ("15", "Y"): "rename",
}

# Expected example changes: (segment, kind, label) -> (old, new)
EXPECTED_COORDS = {
    ("2", "imu", "2"): ((50, 100, 70), (50, 100, 30)),
    ("2", "mocap", "5"): ((50, 100, 70), (50, 100, 30)),
    ("2", "mocap", "A"): ((100, 100, 30), (100, 100, 70)),
    ("2", "mocap", "B"): ((0, 100, 30), (0, 100, 70)),
    ("4", "mocap", "10"): ((100, 50, 50), (0, 50, 50)),
    ("5", "mocap", "11"): ((0, 50, 50), (100, 50, 50)),
    ("8", "imu", "5"): ((100, 50, 30), (0, 50, 30)),
    ("8", "mocap", "8"): ((100, 50, 70), (0, 50, 70)),
    ("9", "imu", "6"): ((0, 50, 30), (100, 50, 30)),
    ("9", "mocap", "9"): ((0, 50, 50), (100, 50, 50)),
}

# Examples on a swapped axis whose value is invariant (50 -> 100 - 50) or that
# are deliberately not converted (left upper-arm exception).
INFO_UNCHANGED = {
    ("8", "mocap", "E"): "X = 50 on swapped axis: 100 - 50 = 50 (no change)",
    ("9", "mocap", "E"): "X = 50 on swapped axis: 100 - 50 = 50 (no change)",
    ("7", "imu", "4"): "left upper-arm exception: kept, author confirmation needed",
    ("7", "mocap", "7"): "left upper-arm exception: kept, author confirmation needed",
    ("7", "mocap", "D"): "left upper-arm exception: kept, author confirmation needed",
}

ALIASES = {
    "olecranon process": "olecranon",
    "dorsal": "dorsal surface",
    "midpoint asis": "midpoint of the asis",
    "midpoint psis": "midpoint of the psis",
    "fme": "fme",
}


def axis_limits(text: str) -> tuple[str, str]:
    """Reduce an axis cell text to its normalized (A, B) landmark pair."""
    s = text.lower()
    m = re.match(r"right-hand rule \(limits: (.*)\)$", s)
    if m:
        s = m.group(1)
    s = s.split(";")[0]
    s = re.sub(r"\((0|100) %[^)]*\)", "", s)
    s = re.sub(r"\((shorter|longer) axis\)", "", s)
    s = s.replace(" to ", " → ")
    a, b = (re.sub(r"\s+", " ", x).strip() for x in s.split("→"))
    return ALIASES.get(a, a), ALIASES.get(b, b)


def _key(row):
    return row["segment"]


def compare(old_rows, new_rows):
    old = {_key(r): r for r in old_rows}
    new = {_key(r): r for r in new_rows}
    problems = []
    if old.keys() != new.keys():
        problems.append(f"segment rows differ: {sorted(old.keys() ^ new.keys())}")
    axis_changes, coord_changes, notes = [], [], []
    for seg in old:
        if seg not in new:
            continue
        o, n = old[seg], new[seg]
        for k in "XYZ":
            oa, ob = axis_limits(o["axes"][k])
            na, nb = axis_limits(n["axes"][k])
            if (oa, ob) == (na, nb):
                kind = None
            elif (oa, ob) == (nb, na):
                kind = "swap"
            else:
                kind = "rename"
            if kind:
                axis_changes.append({"segment": seg, "side": o["side"], "name": o["name"], "axis": k,
                                     "kind": kind, "old": o["axes"][k], "new": n["axes"][k]})
        for kind in ("imu", "mocap"):
            oe = {e["label"]: tuple(e["coords"]) for e in o[kind]}
            ne = {e["label"]: tuple(e["coords"]) for e in n[kind]}
            if oe.keys() != ne.keys():
                problems.append(f"segment {seg} {kind}: example labels differ {sorted(oe.keys() ^ ne.keys())}")
            for label in oe:
                if label in ne and oe[label] != ne[label]:
                    coord_changes.append({"segment": seg, "side": o["side"], "name": o["name"], "kind": kind,
                                          "label": label, "old": oe[label], "new": ne[label]})
                elif (seg, kind, label) in INFO_UNCHANGED:
                    notes.append({"segment": seg, "side": o["side"], "name": o["name"], "kind": kind,
                                  "label": label, "value": oe[label],
                                  "note": INFO_UNCHANGED[(seg, kind, label)]})

    got_axis = {(c["segment"], c["axis"]): c["kind"] for c in axis_changes}
    if got_axis != EXPECTED_AXIS:
        for key in sorted(set(got_axis) | set(EXPECTED_AXIS)):
            if got_axis.get(key) != EXPECTED_AXIS.get(key):
                problems.append(f"axis {key}: expected {EXPECTED_AXIS.get(key)}, observed {got_axis.get(key)}")
    got_coords = {(c["segment"], c["kind"], c["label"]): (c["old"], c["new"]) for c in coord_changes}
    if got_coords != EXPECTED_COORDS:
        for key in sorted(set(got_coords) | set(EXPECTED_COORDS)):
            if got_coords.get(key) != EXPECTED_COORDS.get(key):
                problems.append(f"example {key}: expected {EXPECTED_COORDS.get(key)}, observed {got_coords.get(key)}")
    return axis_changes, coord_changes, notes, problems


def symmetry(rows):
    """Check X_left = 100 - X_right, Y_left = Y_right, Z_left = Z_right (A6).

    Left/right examples of the same segment and label type are paired in the
    order in which they appear in the table cell.
    """
    by = {(r["name"], r["side"]): r for r in rows if r["side"]}
    results = []
    for (name, side), right in by.items():
        if side != "right":
            continue
        left = by[(name, "left")]
        for kind in ("imu", "mocap"):
            for er, el in zip(right[kind], left[kind]):
                (xr, yr, zr), (xl, yl, zl) = er["coords"], el["coords"]
                devs = []
                if xl != 100 - xr:
                    devs.append(f"X: {xl} ≠ 100 − {xr}")
                if yl != yr:
                    devs.append(f"Y: {yl} ≠ {yr}")
                if zl != zr:
                    devs.append(f"Z: {zl} ≠ {zr}")
                results.append({"name": name, "kind": kind,
                                 "right": f"{right['segment']}:{er['label']} {tuple(er['coords'])}",
                                 "left": f"{left['segment']}:{el['label']} {tuple(el['coords'])}",
                                 "ok": not devs, "deviation": "; ".join(devs)})
            if len(right[kind]) != len(left[kind]):
                results.append({"name": name, "kind": kind, "right": str(len(right[kind])),
                                "left": str(len(left[kind])), "ok": False,
                                "deviation": "different number of examples"})
    return results


def _seg(c):
    return f"{c['name']}{' (' + c['side'] + ')' if c['side'] else ''} ({c['segment']})"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--markdown", action="store_true", help="print Markdown tables (for the PR description)")
    args = ap.parse_args(argv)
    old_rows = json.loads(BASELINE.read_text(encoding="utf-8"))
    new_rows = parse_table(DEFAULT_TABLE.read_text(encoding="utf-8"))
    axis_changes, coord_changes, notes, problems = compare(old_rows, new_rows)
    sym = symmetry(new_rows)

    print("### Axis changes\n")
    print("| Segment | Axis | Change | Old | New |\n|---|---|---|---|---|")
    for c in axis_changes:
        print(f"| {_seg(c)} | {c['axis']} | {c['kind']} | {c['old']} | {c['new']} |")
    print("\n### Example-coordinate changes\n")
    print("| Segment | Example | Old | New |\n|---|---|---|---|")
    for c in coord_changes:
        print(f"| {_seg(c)} | {c['kind'].upper()} {c['label']} | {c['old']} | {c['new']} |")
    print("\n### Examples on affected segments left unchanged\n")
    print("| Segment | Example | Value | Note |\n|---|---|---|---|")
    for c in notes:
        print(f"| {_seg(c)} | {c['kind'].upper()} {c['label']} | {c['value']} | {c['note']} |")
    print("\n### Symmetry check (A6)\n")
    print("| Segment | Type | Right | Left | Result |\n|---|---|---|---|---|")
    for s in sym:
        print(f"| {s['name']} | {s['kind'].upper()} | {s['right']} | {s['left']} | "
              f"{'ok' if s['ok'] else 'DEVIATION: ' + s['deviation']} |")
    print()
    if problems:
        print("A4 RESULT: FAIL — observed changes differ from the specification:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"A4 RESULT: PASS — {len(axis_changes)} axis changes and {len(coord_changes)} example changes, "
          "exactly as specified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
