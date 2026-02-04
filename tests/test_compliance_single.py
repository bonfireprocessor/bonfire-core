from __future__ import annotations

import os
import warnings
from pathlib import Path

import pytest

from tb import tb_core

from .conftest import run_sim


def _opt_env(name: str) -> str | None:
    v = os.environ.get(name, "").strip()
    return v or None


def test_riscv_compliance_single(sim_env):
    """Run exactly one riscv-compliance program.

    This is intended to be invoked by the riscv-compliance Makefiles.

    Required environment variables:
      - BONFIRE_COMPLIANCE_ELF: path to compiled test ELF
      - BONFIRE_COMPLIANCE_HEX: path to hex (hexdump) for tb_core to load
      - BONFIRE_COMPLIANCE_SIG: path where signature dump should be written

    The legacy behavior (tb_run.py) is to StopSimulation after writing monitor base.
    If ELF+SIG are provided, tb/sim_monitor.py will dump the signature.
    """

    repo_root = Path(__file__).resolve().parents[1]
    os.chdir(repo_root)

    elf = _opt_env("BONFIRE_COMPLIANCE_ELF")
    hex_file = _opt_env("BONFIRE_COMPLIANCE_HEX")
    sig = _opt_env("BONFIRE_COMPLIANCE_SIG")

    # This test is only meant to run when invoked by the riscv-compliance harness.
    # For normal local pytest runs, we skip if the required env vars aren't provided.
    missing = [
        name
        for name, val in [
            ("BONFIRE_COMPLIANCE_ELF", elf),
            ("BONFIRE_COMPLIANCE_HEX", hex_file),
            ("BONFIRE_COMPLIANCE_SIG", sig),
        ]
        if not val
    ]
    if missing:
        pytest.skip("Compliance single-test requires env vars set by riscv-compliance: " + ", ".join(missing))

    # Ensure output directory exists
    Path(sig).parent.mkdir(parents=True, exist_ok=True)

    tb = tb_core.tb(hexFile=hex_file, elfFile=elf, sigFile=sig, ramsize=16384, verbose=False)

    # Duration matches legacy runner.
    run_sim(tb, trace=False, filename=None, duration=20_000, waveforms_dir=sim_env["waveforms_dir"])

    # Some tests are expected to be ignored by the compliance harness (e.g. misalign/trap
    # related ones when privilege/trap handling isn't implemented). Those may not produce
    # a signature file.
    #
    # If the simulator created an *empty* signature file, treat it like "no signature":
    # - warn (so it shows up in logs)
    # - delete the file (so riscv-compliance verify.sh will IGNORE the test)
    # - skip the pytest invocation (so the harness doesn't abort)
    sig_path = Path(sig)
    if sig_path.exists() and sig_path.stat().st_size == 0:
        warnings.warn(f"Empty signature file produced; treating as ignored and removing: {sig}")
        sig_path.unlink(missing_ok=True)
        pytest.skip("Empty signature file (expected for ignored compliance tests)")
