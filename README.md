[![DOI](https://zenodo.org/badge/797952110.svg)](https://doi.org/10.5281/zenodo.14603935)     [![arXiv](https://img.shields.io/badge/arXiv-2412.21159-b31b1b.svg)](https://arxiv.org/abs/2412.21159)

# UNISEP — Unified Sensor Placement Framework

A unified framework for standardizing sensor placement across different sensing modalities and applications in human motion capture and wearable technology.

## Overview

This framework addresses the critical need for standardized sensor placement protocols in human movement analysis and physiological monitoring. While existing standards like SENIAM address specific applications, there has been no comprehensive framework spanning different sensing modalities and applications. Our standard ensures reproducibility and transferability of human movement data across different recording systems and research domains.

## Key Features

- **Precise Anatomical Landmarks**: Comprehensive set of anatomical landmarks chosen for reliability and accessibility
- **Standardized Coordinate Systems**: Clear definitions for 15 body segments plus the neck
- **Hierarchical Reference Frames**: Structured approach to relating different coordinate systems
- **Quantified Precision Levels**: Three-tier system for placement accuracy
- **BIDS/HED Compatible**: Designed to work with existing data sharing standards

## Documentation

- 📖 [Full Paper on arXiv](https://doi.org/10.48550/arXiv.2412.21159)
- 🌐 [Framework Website](https://unisep-framework.github.io)
- 📊 [Complete Anatomical Table](https://unisep-framework.github.io/anatomical_table.html)
- 🧩 [Use cases](https://unisep-framework.github.io/use_cases.html) and [Schema & vocabularies](https://unisep-framework.github.io/schema.html)
- 📝 [Changelog](CHANGELOG.md)

## Repository structure

| Path | Content |
|---|---|
| `index.qmd`, `anatomical_table.qmd`, `use_cases.qmd`, `schema.qmd`, `authors.qmd` | Quarto website (framework description, landmark table — the normative core —, use cases, schema page, authors) |
| `paper.md` | arXiv preprint (version 1, 2024) as Markdown; superseded by version 0.2.0 where they differ |
| `schema/v0.2/` | Reference schema for placement records (JSON Schema 2020-12) and controlled vocabularies |
| `examples/` | Example placement records, EMG-BIDS coordinate-system files and a minimal EMG-BIDS dataset (`bids_minimal/`) |
| `unisep/` | Python reference implementation (segment frames and normalized coordinates) |
| `scripts/` | Validation and consistency scripts, BIDS example generator |
| `tests/` | Unit tests and valid/invalid fixtures |
| `pics/` | Illustrations |
| `.github/workflows/` | `publish.yml` (website, on push to `main`), `validate.yml` (validation and tests) |

## Validation

Requires Python ≥ 3.10.

```bash
python -m venv .venv && .venv/bin/pip install jsonschema pytest numpy
.venv/bin/python scripts/validate_examples.py   # examples and fixtures against the schema
.venv/bin/python -m pytest                       # unit tests (validation, reference implementation)
```

The same checks run in GitHub Actions on every push and pull request. The minimal BIDS dataset can be regenerated with `scripts/make_bids_minimal.py` (needs `pyedflib`) and checked with the [BIDS validator](https://github.com/bids-standard/bids-validator) (`pip install bids-validator-deno`, then `bids-validator-deno examples/bids_minimal`).

## How to cite

Please cite UNISEP using the metadata in [`CITATION.cff`](CITATION.cff) (GitHub: "Cite this repository").

- Zenodo concept DOI (all versions): [10.5281/zenodo.14603935](https://doi.org/10.5281/zenodo.14603935)
- Version DOI for 0.2.0: TBD
- Preprint: [arXiv:2412.21159](https://doi.org/10.48550/arXiv.2412.21159)

## Contributing

We welcome contributions from the research community in several key areas:

- Opinions on the preprint and the proposed framework (the preprint is available on arXiv as well as here in the repository as `paper.md`)
- Standard vocabulary and communication formats through BIDS, HED, and other specifications
- Validation studies for inter-operator reliability assessment
- Mappings between this framework and existing standards (such as SENIAM)
- Software tools for coordinate calculation and placement visualization

Please submit your suggestions and feedback via the Issues section.

## License

This project is licensed under MIT LICENSE - see the [LICENSE.md](LICENSE.md) file for details.
