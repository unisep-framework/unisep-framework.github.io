"""UNISEP reference implementation (version 0.2.0).

Implements the formal definition of UNISEP segment coordinate systems and
normalized coordinates (https://unisep-framework.github.io/#formal-definition).

The choice of primary and secondary axis for constructing a segment frame is
*not* defined per segment in UNISEP 0.2.0 (pending decision D6). Callers must
therefore pass both axes explicitly to :func:`orthonormal_frame`; this package
deliberately provides no per-segment defaults.
"""
from .geometry import normalized_coordinate, normalized_coordinates, orthonormal_frame

__version__ = "0.2.0"
__all__ = ["orthonormal_frame", "normalized_coordinate", "normalized_coordinates", "__version__"]
