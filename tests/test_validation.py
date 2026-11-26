"""Tests for scripts/validate_examples.py (milestone M6)."""
import copy
import io
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import validate_examples as ve  # noqa: E402

INVALID = sorted((REPO / "tests" / "fixtures" / "invalid").glob("*.json"))


@pytest.fixture(scope="module")
def validator():
    return ve.make_validator()


def test_all_default_files_pass():
    buf = io.StringIO()
    assert ve.run(ve.discover(), out=buf) == 0, buf.getvalue()


def test_seven_invalid_fixtures_present():
    assert len(INVALID) == 7


@pytest.mark.parametrize("path", INVALID, ids=lambda p: p.stem)
def test_invalid_fixture_fails_for_exactly_its_rule(path, validator):
    kind, errors, _ = ve.check_file(path, validator)
    expected = path.with_suffix(".expected").read_text(encoding="utf-8").strip()
    assert len(errors) == 1, errors
    assert expected in errors[0]


def test_removing_side_from_foot_record_fails(validator):
    obj = json.loads((REPO / "examples" / "foot" / "foot_placements.json").read_text())
    rec = copy.deepcopy(obj["UNISEPPlacements"]["OMC_Heel_M4"])
    del rec["Side"]
    assert any("'Side' is a required property" in e for e in ve.check_placement(rec, validator))


def test_invalid_fixture_passing_makes_run_fail(tmp_path):
    good = REPO / "examples" / "thorax" / "thorax_v1_placement.json"
    assert ve.run([(good, False)], out=io.StringIO()) == 1


def test_vocabulary_consistency():
    assert ve.check_vocabulary_consistency(ve.load_schema()) == []


def test_bids_minimal_non_coordsystem_files_excluded():
    for path, _ in ve.discover():
        if "bids_minimal" in path.parts:
            assert path.name.endswith("_coordsystem.json")
