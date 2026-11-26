"""Command-line interface: ``python -m unisep validate [FILES ...]``.

Without files, validates the default example and fixture locations of the
repository (see scripts/validate_examples.py).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m unisep")
    sub = ap.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate", help="validate placement records and EMG coordinate-system files")
    v.add_argument("files", nargs="*", type=Path)
    args = ap.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import validate_examples  # noqa: E402

    return validate_examples.main([str(f) for f in args.files])


if __name__ == "__main__":
    sys.exit(main())
