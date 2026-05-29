# Universal Runner

The recommended single entry point for day-to-day development is:

- `scripts/bonfire-core`

## Responsibilities of the runner

The existing runner documentation describes it as responsible for:

- activating the repo-local virtual environment,
- ensuring the RISC-V toolchain is available,
- running selected pytest-based test groups,
- running a single HEX program when requested,
- starting the simulated GDB server.

## Common commands

```bash
scripts/bonfire-core --install
scripts/bonfire-core --all
scripts/bonfire-core --ut
scripts/bonfire-core --integration
```

## Related source file

- `scripts/README.md`
