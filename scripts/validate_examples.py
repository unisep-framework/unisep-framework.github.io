#!/usr/bin/env python3
"""Validate the UNISEP example files and test fixtures.

Discovers JSON files and classifies each one:

  (i)   objects with key ``UNISEPPlacements``   -> every entry is validated
        against the placement-record schema;
  (ii)  objects with key ``BodySegment``         -> validated against the schema;
  (iii) objects with key ``EMGCoordinateSystem`` -> checked as a BIDS EMG
        coordinate-system file (EMG-BIDS, BIDS 1.11).

Files below ``examples/bids_minimal/`` are only checked if they are
coordinate-system files (``*_coordsystem.json``); all other files there are
BIDS files and are checked by the BIDS validator instead.

Searched locations (relative to the repository root, unless paths are given):
  examples/**/*.json                 must be valid
  tests/fixtures/valid/**/*.json     must be valid
  tests/fixtures/invalid/**/*.json   must be invalid; the companion
                                     ``<name>.expected`` file holds a text that
                                     must occur in one of the error messages

Also checks that the enumerations of ``MeasurementMethod`` and
``LandmarkIdentification`` in the schema equal the values in
``vocabularies.json``.

Prints one line per file and exits non-zero if any valid file fails, any
invalid fixture passes (or fails for an unexpected reason), or the
consistency check fails.

Usage:
    python scripts/validate_examples.py            # default locations
    python scripts/validate_examples.py FILE ...   # only these files (must be valid)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO / "schema" / "v0.2" / "placement-record.schema.json"
VOCAB_PATH = REPO / "schema" / "v0.2" / "vocabularies.json"

#: Keys of ``*_coordsystem.json`` for EMG defined by BIDS 1.11.
BIDS_EMG_COORDSYSTEM_KEYS = {
    "EMGCoordinateSystem",
    "EMGCoordinateUnits",
    "EMGCoordinateSystemDescription",
    "ParentCoordinateSystem",
    "AnchorElectrode",
    "AnchorCoordinates",
}
EMG_COORDINATE_UNITS = {"m", "mm", "cm", "percent", "n/a"}


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def make_validator(schema: dict | None = None) -> Draft202012Validator:
    schema = schema or load_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_placement(record, validator) -> list[str]:
    """Return schema error messages for one placement record."""
    errors = sorted(validator.iter_errors(record), key=lambda e: list(e.absolute_path))
    out = []
    for e in errors:
        where = "/".join(str(p) for p in e.absolute_path)
        out.append(f"{where + ': ' if where else ''}{e.message}")
    return out


def check_coordsystem(obj: dict) -> tuple[list[str], list[str]]:
    """Check a BIDS EMG coordinate-system file. Returns (errors, info)."""
    errors, info = [], []
    if obj.get("EMGCoordinateSystem") != "Other":
        errors.append(f"EMGCoordinateSystem must be \"Other\" (BIDS 1.11), got {obj.get('EMGCoordinateSystem')!r}")
    if obj.get("EMGCoordinateUnits") not in EMG_COORDINATE_UNITS:
        errors.append(f"EMGCoordinateUnits must be one of {sorted(EMG_COORDINATE_UNITS)}, "
                      f"got {obj.get('EMGCoordinateUnits')!r}")
    if not isinstance(obj.get("EMGCoordinateSystemDescription"), str):
        errors.append("EMGCoordinateSystemDescription is required (EMGCoordinateSystem is \"Other\")")
    if "ParentCoordinateSystem" in obj:
        parent = obj["ParentCoordinateSystem"]
        if not isinstance(parent, str):
            errors.append("ParentCoordinateSystem must be a string")
        elif parent.startswith("space-"):
            errors.append(f"ParentCoordinateSystem must be the space label without the 'space-' prefix, got {parent!r}")
        if not isinstance(obj.get("AnchorElectrode"), str):
            errors.append("AnchorElectrode (string) is required when ParentCoordinateSystem is present")
        anchor = obj.get("AnchorCoordinates")
        if not (isinstance(anchor, list) and len(anchor) == 3 and all(_is_number(v) for v in anchor)):
            errors.append("AnchorCoordinates (array of 3 numbers) is required when ParentCoordinateSystem is present")
    extra = sorted(set(obj) - BIDS_EMG_COORDSYSTEM_KEYS)
    if extra:
        info.append("UNISEP extension keys (not BIDS): " + ", ".join(extra))
    return errors, info


def check_file(path: Path, validator) -> tuple[str, list[str], list[str]]:
    """Classify and check one file. Returns (kind, errors, info)."""
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return "invalid-json", [f"JSON parse error: {exc}"], []
    if not isinstance(obj, dict):
        return "unknown", ["top-level JSON value is not an object"], []
    if "UNISEPPlacements" in obj:
        placements = obj["UNISEPPlacements"]
        if not isinstance(placements, dict) or not placements:
            return "placements", ["UNISEPPlacements must be a non-empty object"], []
        errors = []
        for name, rec in placements.items():
            errors += [f"{name}: {m}" for m in check_placement(rec, validator)]
        return f"placements[{len(placements)}]", errors, []
    if "BodySegment" in obj:
        return "placement", check_placement(obj, validator), []
    if "EMGCoordinateSystem" in obj:
        errors, info = check_coordsystem(obj)
        return "coordsystem", errors, info
    return "unknown", ["cannot classify: none of UNISEPPlacements, BodySegment, EMGCoordinateSystem"], []


def check_vocabulary_consistency(schema: dict) -> list[str]:
    vocab = json.loads(VOCAB_PATH.read_text(encoding="utf-8"))
    problems = []
    for key in ("MeasurementMethod", "LandmarkIdentification"):
        in_schema = schema["properties"][key]["enum"]
        in_vocab = [entry["value"] for entry in vocab[key]]
        if in_schema != in_vocab:
            problems.append(f"{key}: schema enum {in_schema} != vocabularies.json {in_vocab}")
    return problems


def _in_bids_minimal(path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(REPO / "examples" / "bids_minimal")
    except ValueError:
        return False
    return rel is not None


def discover() -> list[tuple[Path, bool]]:
    """Return (path, must_be_valid) for the default locations."""
    files = []
    for p in sorted((REPO / "examples").rglob("*.json")):
        if _in_bids_minimal(p) and not p.name.endswith("_coordsystem.json"):
            continue
        files.append((p, True))
    files += [(p, True) for p in sorted((REPO / "tests" / "fixtures" / "valid").rglob("*.json"))]
    files += [(p, False) for p in sorted((REPO / "tests" / "fixtures" / "invalid").rglob("*.json"))]
    return files


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(REPO))
    except ValueError:
        return str(p)


def run(files: list[tuple[Path, bool]], out=sys.stdout) -> int:
    schema = load_schema()
    validator = make_validator(schema)
    failures = 0
    for path, must_be_valid in files:
        kind, errors, info = check_file(path, validator)
        note = f" [{'; '.join(info)}]" if info else ""
        if must_be_valid:
            if errors:
                failures += 1
                print(f"FAIL  {_rel(path)} ({kind}): " + " | ".join(errors), file=out)
            else:
                print(f"ok    {_rel(path)} ({kind}){note}", file=out)
        else:
            expected_file = path.with_suffix(".expected")
            expected = expected_file.read_text(encoding="utf-8").strip() if expected_file.exists() else None
            if not errors:
                failures += 1
                print(f"FAIL  {_rel(path)} ({kind}): invalid fixture passed validation", file=out)
            elif expected is None:
                failures += 1
                print(f"FAIL  {_rel(path)} ({kind}): missing {expected_file.name}", file=out)
            elif not any(expected in e for e in errors):
                failures += 1
                print(f"FAIL  {_rel(path)} ({kind}): failed for an unexpected reason: "
                      + " | ".join(errors) + f" (expected: {expected})", file=out)
            else:
                print(f"ok    {_rel(path)} ({kind}): rejected as expected — {expected}", file=out)
    problems = check_vocabulary_consistency(schema)
    if problems:
        failures += 1
        for p in problems:
            print(f"FAIL  vocabulary consistency: {p}", file=out)
    else:
        print("ok    vocabulary consistency: schema enumerations equal vocabularies.json", file=out)
    print(f"{'FAILED' if failures else 'PASSED'}: {len(files)} files checked, {failures} failure(s)", file=out)
    return 1 if failures else 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    files = [(Path(a), True) for a in argv] if argv else discover()
    return run(files)


if __name__ == "__main__":
    sys.exit(main())
