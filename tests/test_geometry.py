"""Tests for the UNISEP reference implementation (check A3)."""
import itertools

import numpy as np
import pytest

from unisep import normalized_coordinate, normalized_coordinates, orthonormal_frame

RNG = np.random.default_rng(20261126)
A = np.array([1.0, -2.0, 0.5])
B = np.array([4.0, 2.0, 0.5])
E = (B - A) / np.linalg.norm(B - A)


# --- normalized_coordinate: trivial cases ------------------------------------------------------

def test_point_at_A_gives_0():
    assert normalized_coordinate(A, A, B, E) == 0.0


def test_point_at_B_gives_100():
    assert normalized_coordinate(B, A, B, E) == pytest.approx(100.0, abs=1e-12)


def test_midpoint_gives_50():
    assert normalized_coordinate((A + B) / 2, A, B, E) == pytest.approx(50.0, abs=1e-12)


def test_beyond_B_gives_above_100_and_before_A_below_0():
    assert normalized_coordinate(B + 0.2 * (B - A), A, B, E) == pytest.approx(120.0)
    assert normalized_coordinate(A - 0.2 * (B - A), A, B, E) == pytest.approx(-20.0)


def test_offaxis_component_is_ignored():
    off = np.cross(E, [0, 0, 1.0])
    assert normalized_coordinate((A + B) / 2 + 3 * off, A, B, E) == pytest.approx(50.0)


@pytest.mark.parametrize("seed", range(20))
def test_swapping_limits_gives_100_minus_u(seed):
    rng = np.random.default_rng(seed)
    a, b, p = rng.normal(size=(3, 3))
    e = (b - a) / np.linalg.norm(b - a)
    u = normalized_coordinate(p, a, b, e)
    assert normalized_coordinate(p, b, a, e) == pytest.approx(100.0 - u, abs=1e-9)
    # also when the unit vector is reversed together with the limits
    assert normalized_coordinate(p, b, a, -e) == pytest.approx(100.0 - u, abs=1e-9)


def test_degenerate_limits_raise():
    with pytest.raises(ValueError, match="do not span the axis"):
        normalized_coordinate(A, A, A, E)
    perp = np.cross(E, [0, 0, 1.0])
    perp /= np.linalg.norm(perp)
    with pytest.raises(ValueError, match="do not span the axis"):
        normalized_coordinate(A, A, B, perp)
    with pytest.raises(ValueError, match="zero length"):
        normalized_coordinate(A, A, B, [0, 0, 0])


# --- orthonormal_frame -------------------------------------------------------------------------

def _check_frame(f):
    M = np.column_stack([f["X"], f["Y"], f["Z"]])
    assert np.allclose(np.linalg.norm(M, axis=0), 1.0, atol=1e-12)
    G = M.T @ M
    assert np.all(np.abs(G - np.eye(3)) < 1e-12)
    assert np.linalg.det(M) == pytest.approx(1.0, abs=1e-12)
    assert np.allclose(np.cross(f["X"], f["Y"]), f["Z"], atol=1e-12)


PAIRS = list(itertools.permutations("XYZ", 2))


@pytest.mark.parametrize("primary,secondary", PAIRS)
@pytest.mark.parametrize("seed", range(10))
def test_frames_orthonormal_and_right_handed(primary, secondary, seed):
    rng = np.random.default_rng(seed)
    p, s = rng.normal(size=(2, 3)) * rng.uniform(0.1, 10)
    f = orthonormal_frame(primary, p, secondary, s)
    _check_frame(f)
    assert np.allclose(f[primary], p / np.linalg.norm(p), atol=1e-12)
    # the secondary axis lies in the plane of p and s, on the side of s
    assert np.dot(f[secondary], s) > 0
    assert abs(np.dot(np.cross(p, s), f[secondary])) < 1e-9


@pytest.mark.parametrize("primary,secondary", PAIRS)
def test_canonical_axes_reproduce_identity(primary, secondary):
    unit = {"X": [1, 0, 0], "Y": [0, 1, 0], "Z": [0, 0, 1]}
    f = orthonormal_frame(primary, unit[primary], secondary, unit[secondary])
    for k in "XYZ":
        assert np.allclose(f[k], unit[k], atol=1e-15)


def test_secondary_is_gram_schmidt_orthogonalized():
    f = orthonormal_frame("X", [2, 0, 0], "Z", [0.3, 0, 5])
    assert np.allclose(f["X"], [1, 0, 0])
    assert np.allclose(f["Z"], [0, 0, 1])
    assert np.allclose(f["Y"], [0, 1, 0])


@pytest.mark.parametrize("p,s,msg", [
    ([0, 0, 0], [0, 0, 1], "primary_vector .* zero length"),
    ([1, 0, 0], [0, 0, 0], "secondary_vector .* zero length"),
    ([1, 0, 0], [3, 0, 0], "parallel"),
    ([1, 0, 0], [-2, 0, 0], "parallel"),
    ([1, 0, 0], [1, 1e-8, 0], "parallel"),
])
def test_degenerate_frames_raise(p, s, msg):
    with pytest.raises(ValueError, match=msg):
        orthonormal_frame("X", p, "Z", s)


def test_invalid_labels_raise():
    with pytest.raises(ValueError, match="must differ"):
        orthonormal_frame("X", [1, 0, 0], "X", [0, 1, 0])
    with pytest.raises(ValueError, match="must be one of"):
        orthonormal_frame("W", [1, 0, 0], "X", [0, 1, 0])
    with pytest.raises(ValueError, match="3-vector"):
        orthonormal_frame("X", [1, 0], "Z", [0, 0, 1])


def test_nearly_parallel_but_above_tolerance_is_accepted():
    _check_frame(orthonormal_frame("X", [1, 0, 0], "Z", [1, 0, 1e-4]))


# --- synthetic segment with landmarks on the unit vectors ----------------------------------------

def test_synthetic_segment_on_unit_vectors():
    # 0 % landmarks at the origin, 100 % landmarks on the unit vectors
    O = np.zeros(3)
    ex, ey, ez = np.eye(3)
    limits = {"X": (O, ex), "Y": (O, ey), "Z": (O, ez)}
    frame = orthonormal_frame("X", ex - O, "Z", ez - O)
    P = np.array([0.25, 0.5, 1.2])
    u = normalized_coordinates(P, limits, frame)
    assert u == pytest.approx({"X": 25.0, "Y": 50.0, "Z": 120.0}, abs=1e-12)


def test_synthetic_segment_with_separate_axis_limits():
    # each axis has its own limits: X from -1 to 1 (centre at 50 %), Y from 2 to 4, Z from 0 to 10
    limits = {"X": ([-1, 0, 0], [1, 0, 0]), "Y": ([0, 2, 0], [0, 4, 0]), "Z": ([0, 0, 0], [0, 0, 10])}
    frame = orthonormal_frame("X", [2, 0, 0], "Z", [0, 0, 10])
    u = normalized_coordinates([0.5, 3, -1], limits, frame)
    assert u == pytest.approx({"X": 75.0, "Y": 50.0, "Z": -10.0}, abs=1e-12)


def test_normalized_coordinates_requires_all_axes():
    with pytest.raises(ValueError, match="missing"):
        normalized_coordinates([0, 0, 0], {"X": ([0, 0, 0], [1, 0, 0])}, {"X": [1, 0, 0]})
