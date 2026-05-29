# Quick Start

The recommended day-to-day entry point is the universal runner script:

- `scripts/bonfire-core`

## Setup

```bash
cd bonfire-core
scripts/bonfire-core --install
```

## Run the main test suite

```bash
scripts/bonfire-core --all
```

## Alternative manual setup

```bash
cd bonfire-core
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install myhdl==0.11.51 pyelftools pytest
```

## What this gives you

After the quick start steps, you should be ready to:

- run pytest-based regressions,
- build core and SoC test programs,
- continue with the workflow and hardware sections.

## Related source files

- `README.md`
- `scripts/README.md`
