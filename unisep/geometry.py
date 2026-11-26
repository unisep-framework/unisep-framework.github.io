"""Geometry of UNISEP segment coordinate systems.

Conventions (UNISEP 0.2.0): in the anatomical position X points to the
subject's right, Y anteriorly and Z superiorly; every segment frame is a
right-handed orthonormal basis (e_X × e_Y = e_Z).
"""
from __future__ import annotations

from typing import Mapping, Sequence

import numpy as np

AXES = ("X", "Y", "Z")
#: Tolerance on |sin θ| below which two axis vectors count as parallel.
PARALLEL_TOL = 1e-6
#: Relative tolerance below which a length or projection counts as zero.
ZERO_TOL = 1e-12

ArrayLike = Sequence[float] | np.ndarray


def _vec(v: ArrayLike, name: str) -> np.ndarray:
    a = np.asarray(v, dtype=float)
    if a.shape != (3,):
        raise ValueError(f"{name} must be a 3-vector, got shape {a.shape}")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name} must contain finite numbers, got {a.tolist()}")
    return a


def _label(label: str, name: str) -> str:
    if label not in AXES:
        raise ValueError(f"{name} must be one of {AXES}, got {label!r}")
    return label


def orthonormal_frame(primary_label: str, primary_vector: ArrayLike,
                      secondary_label: str, secondary_vector: ArrayLike) -> dict[str, np.ndarray]:
    """Construct a right-handed orthonormal segment frame.

    The primary axis is the normalized ``primary_vector``. The secondary axis
    is ``secondary_vector`` with its component parallel to the primary axis
    removed (Gram–Schmidt), then normalized. The third axis is the cross
    product of the two, taken in the order that makes (e_X, e_Y, e_Z)
    right-handed.

    The caller chooses which axes are primary and secondary (no per-segment
    defaults are defined in UNISEP 0.2.0, decision D6). For example, a thigh
    frame could be built with X (medial → lateral epicondyle) as primary and Z
    (epicondyle midpoint → greater trochanter) as secondary; for the thorax
    the secondary Z vector is the longitudinal body axis (decision D1).

    Returns:
        dict mapping "X", "Y", "Z" to unit vectors (numpy arrays of shape (3,)).

    Raises:
        ValueError: if labels are invalid or identical, a vector has zero
            length, or the two vectors are (nearly) parallel (|sin θ| < 1e-6).
    """
    p_lab = _label(primary_label, "primary_label")
    s_lab = _label(secondary_label, "secondary_label")
    if p_lab == s_lab:
        raise ValueError(f"primary and secondary axis must differ, both are {p_lab!r}")
    p = _vec(primary_vector, "primary_vector")
    s = _vec(secondary_vector, "secondary_vector")
    p_norm, s_norm = np.linalg.norm(p), np.linalg.norm(s)
    if p_norm <= ZERO_TOL:
        raise ValueError(f"primary_vector for axis {p_lab} has zero length")
    if s_norm <= ZERO_TOL:
        raise ValueError(f"secondary_vector for axis {s_lab} has zero length")
    sin_theta = np.linalg.norm(np.cross(p, s)) / (p_norm * s_norm)
    if sin_theta < PARALLEL_TOL:
        raise ValueError(f"primary ({p_lab}) and secondary ({s_lab}) vectors are (nearly) parallel: "
                         f"|sin θ| = {sin_theta:.3g} < {PARALLEL_TOL:g}")
    e_p = p / p_norm
    s_orth = s - np.dot(s, e_p) * e_p
    e_s = s_orth / np.linalg.norm(s_orth)
    t_lab = next(a for a in AXES if a not in (p_lab, s_lab))
    # (p, s, t) is a cyclic permutation of (X, Y, Z)  <=>  e_t = e_p × e_s
    cyclic = (AXES.index(s_lab) - AXES.index(p_lab)) % 3 == 1
    e_t = np.cross(e_p, e_s) if cyclic else np.cross(e_s, e_p)
    e_t = e_t / np.linalg.norm(e_t)
    return {p_lab: e_p, s_lab: e_s, t_lab: e_t}


def normalized_coordinate(P: ArrayLike, A: ArrayLike, B: ArrayLike, e: ArrayLike) -> float:
    """Normalized coordinate u = 100 · ((P − A) · e) / ((B − A) · e), in percent.

    ``A`` defines 0 %, ``B`` defines 100 % of the axis with unit vector ``e``.
    Values outside 0–100 are admissible.

    Raises:
        ValueError: if (B − A) · e is (nearly) zero, i.e. the axis limits do
            not span the axis.
    """
    P, A, B, e = (_vec(v, n) for v, n in ((P, "P"), (A, "A"), (B, "B"), (e, "e")))
    e_norm = np.linalg.norm(e)
    if e_norm <= ZERO_TOL:
        raise ValueError("axis unit vector e has zero length")
    denom = float(np.dot(B - A, e))
    scale = max(np.linalg.norm(B - A) * e_norm, 1.0)
    if abs(denom) <= ZERO_TOL * scale:
        raise ValueError(f"axis limits do not span the axis: (B − A) · e = {denom:.3g} is (nearly) zero")
    return 100.0 * float(np.dot(P - A, e)) / denom


def normalized_coordinates(P: ArrayLike, limits: Mapping[str, tuple[ArrayLike, ArrayLike]],
                           frame: Mapping[str, ArrayLike]) -> dict[str, float]:
    """Normalized coordinates of ``P`` along X, Y and Z.

    Args:
        P: point (3-vector) in the same Cartesian space as the landmarks.
        limits: {"X": (A_X, B_X), "Y": (A_Y, B_Y), "Z": (A_Z, B_Z)}, the 0 % and
            100 % landmarks (or landmark midpoints / surface points) per axis.
        frame: {"X": e_X, "Y": e_Y, "Z": e_Z}, e.g. from :func:`orthonormal_frame`.

    Returns:
        {"X": u_X, "Y": u_Y, "Z": u_Z} in percent.
    """
    missing = [k for k in AXES if k not in limits or k not in frame]
    if missing:
        raise ValueError(f"limits and frame must define axes {AXES}; missing {missing}")
    return {k: normalized_coordinate(P, limits[k][0], limits[k][1], frame[k]) for k in AXES}
