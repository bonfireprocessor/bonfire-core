from __future__ import annotations

import os
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass(frozen=True)
class CommandInvocation:
    command: list[str]
    env: dict[str, str] | None = None


def _oss_cad_suite_env_script() -> Path | None:
    env_script = os.environ.get("OSS_CAD_SUITE_ENV")
    if not env_script:
        return None

    path = Path(env_script).expanduser()
    if not path.is_file():
        pytest.fail(f"OSS_CAD_SUITE_ENV points to a missing file: {path}", pytrace=False)

    return path


def _with_ghdl_bin_on_path() -> dict[str, str] | None:
    ghdl_bin = os.environ.get("GHDL_BIN")
    if not ghdl_bin:
        return None

    ghdl_path = Path(ghdl_bin).expanduser()
    if not ghdl_path.is_file():
        pytest.fail(f"GHDL_BIN points to a missing file: {ghdl_path}", pytrace=False)

    env = os.environ.copy()
    env["PATH"] = f"{ghdl_path.parent}{os.pathsep}{env.get('PATH', '')}"
    return env


def ghdl_command(*args: str) -> CommandInvocation:
    ghdl_bin = os.environ.get("GHDL_BIN")
    if ghdl_bin:
        ghdl_path = Path(ghdl_bin).expanduser()
        if not ghdl_path.is_file():
            pytest.fail(f"GHDL_BIN points to a missing file: {ghdl_path}", pytrace=False)
        return CommandInvocation([str(ghdl_path), *args])

    env_script = _oss_cad_suite_env_script()
    if env_script is not None:
        command = " ".join(["ghdl", *[shlex.quote(arg) for arg in args]])
        return CommandInvocation(
            ["bash", "-lc", f"source {shlex.quote(str(env_script))} && {command}"],
            os.environ.copy(),
        )

    ghdl = shutil.which("ghdl")
    if ghdl is None:
        pytest.skip("ghdl not available")

    return CommandInvocation([ghdl, *args])


def fusesoc_command(*args: str) -> CommandInvocation:
    env_script = _oss_cad_suite_env_script()
    if env_script is not None:
        command = " ".join(["fusesoc", *[shlex.quote(arg) for arg in args]])
        return CommandInvocation(
            ["bash", "-lc", f"source {shlex.quote(str(env_script))} && {command}"],
            os.environ.copy(),
        )

    env = _with_ghdl_bin_on_path()
    fusesoc = shutil.which("fusesoc")
    if fusesoc is not None and (env is not None or shutil.which("ghdl") is not None):
        return CommandInvocation([fusesoc, *args], env)

    pytest.skip("fusesoc/ghdl not available")
