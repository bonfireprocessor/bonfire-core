from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Callable

import pytest

from tests.toolchain import fusesoc_command, toolchain_commands_available


@pytest.fixture(scope="session")
def ecp5_fpga_toolchain_available() -> bool:
    return toolchain_commands_available("yosys", "nextpnr-ecp5")


@pytest.fixture
def run_fusesoc(repo_root: Path, pytestconfig: pytest.Config) -> Callable[..., str]:
    def run(*args: str, cwd: Path | None = None, timeout: int = 120) -> str:
        capture_disabled = pytestconfig.getoption("capture") == "no"
        # pytest.ini adds -q, so an explicit -vv results in verbosity level 1.
        show_process_output = capture_disabled and pytestconfig.getoption("verbose") >= 1
        if capture_disabled:
            print("[fusesoc] {}".format(shlex.join(["fusesoc", *args])))

        invocation = fusesoc_command(*args)
        result = subprocess.run(
            invocation.command,
            cwd=cwd or repo_root,
            env=invocation.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        if show_process_output:
            print(result.stdout, end="")
        assert result.returncode == 0, result.stdout
        return result.stdout

    return run
