#!/usr/bin/env python3
"""Parse the UNISEP landmark table (anatomical_table.qmd) into an inventory.

For every table row this extracts the segment number, label, side, the three
axis definitions and the "Example IMU" / "Example Mocap" coordinates.

Usage:
    python scripts/table_inventory.py                     # print inventory
    python scripts/table_inventory.py --json out.json     # also write JSON
    python scripts/table_inventory.py --table other.qmd   # parse another file
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_TABLE = REPO / "anatomical_table.qmd"

HEADER_START = "| Hanavan Body Part"
AXIS_RE = re.compile(r"\*\*([XYZ]):\*\*\s*(.*?)\s*$")
EXAMPLE_RE = re.compile(r"([0-9A-Z]+)\.\s*\(\s*([^)]*?)\s*\)")


def _cells(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def _parse_examples(cell: str) -> list[dict]:
    if cell.strip() in ("", "n/a"):
        return []
    out = []
    for label, coords in EXAMPLE_RE.findall(cell):
        values = [float(v) for v in coords.split(",")]
        if len(values) != 3:
            raise ValueError(f"cannot parse coordinates {coords!r} in cell {cell!r}")
        out.append({"label": label, "coords": [int(v) if v.is_integer() else v for v in values]})
    # every "(" must have been consumed by a labelled example
    if cell.count("(") != len(out):
        raise ValueError(f"ambiguous example cell: {cell!r}")
    return out


def _parse_axes(cell: str) -> dict:
    axes = {}
    for part in re.split(r"<br\s*/?>", cell):
        part = part.strip()
        if not part:
            continue
        m = AXIS_RE.match(part)
        if not m:
            raise ValueError(f"cannot parse axis definition {part!r}")
        axes[m.group(1)] = m.group(2)
    if set(axes) != {"X", "Y", "Z"}:
        raise ValueError(f"axis cell does not define X, Y, Z exactly once: {cell!r}")
    return axes


def parse_table(text: str) -> list[dict]:
    lines = text.splitlines()
    try:
        start = next(i for i, l in enumerate(lines) if l.startswith(HEADER_START))
    except StopIteration:
        raise ValueError("landmark table header not found")
    header = _cells(lines[start])
    col = {name: header.index(name) for name in
           ("Hanavan Body Part", "HED Label", "Coordinate System", "Example IMU", "Example Mocap")}
    rows = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        cells = _cells(line)
        seg = cells[col["Hanavan Body Part"]]
        label = cells[col["HED Label"]]
        m = re.match(r"\((Right|Left),\s*(.+)\)", label)
        side, name = (m.group(1).lower(), m.group(2)) if m else (None, label)
        rows.append({
            "segment": seg,
            "name": name,
            "side": side,
            "axes": _parse_axes(cells[col["Coordinate System"]]),
            "imu": _parse_examples(cells[col["Example IMU"]]),
            "mocap": _parse_examples(cells[col["Example Mocap"]]),
        })
    return rows


def format_inventory(rows: list[dict]) -> str:
    out = []
    for r in rows:
        side = r["side"] or "-"
        out.append(f"[{r['segment']:>3}] {r['name']} (side: {side})")
        for k in "XYZ":
            out.append(f"      {k}: {r['axes'][k]}")
        for kind in ("imu", "mocap"):
            ex = ", ".join(f"{e['label']}={tuple(e['coords'])}" for e in r[kind]) or "n/a"
            out.append(f"      {kind.upper():5}: {ex}")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--table", type=Path, default=DEFAULT_TABLE)
    ap.add_argument("--json", type=Path, help="write the inventory as JSON to this path")
    args = ap.parse_args(argv)
    rows = parse_table(args.table.read_text(encoding="utf-8"))
    print(format_inventory(rows))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
