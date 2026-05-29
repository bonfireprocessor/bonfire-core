# Testing

Bonfire Core uses a pytest-based test suite for unit and integration testing.

## Current test categories

The repository-level test documentation currently distinguishes:

- module unit tests,
- load/store unit tests,
- pipeline integration tests,
- core integration tests,
- SoC integration tests.

## Typical entry points

Run everything:

```bash
pytest
```

or through the project runner:

```bash
scripts/bonfire-core --all
```

## Related source files

- `tests/README.md`
- `README.md`
- `scripts/README.md`
