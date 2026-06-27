from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from tests.toolchain import fusesoc_command


def test_ecp5_jtagg_led_demo_icepizero_fusesoc(repo_root: Path):
    invocation = fusesoc_command(
        "run",
        "--target=icepizero",
        "::bonfire-ecp5-jtagg-led-demo:0",
    )
    result = subprocess.run(
        invocation.command,
        cwd=repo_root,
        env=invocation.env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
        check=False,
    )
    print(result.stdout, end="")
    assert result.returncode == 0, result.stdout

    output_dir = (
        repo_root
        / "build"
        / "bonfire-ecp5-jtagg-led-demo_0"
        / "icepizero-trellis"
    )
    bitstream = output_dir / "bonfire-ecp5-jtagg-led-demo_0.bit"
    netlist = output_dir / "bonfire-ecp5-jtagg-led-demo_0.json"
    yosys_log = output_dir / "yosys.log"
    nextpnr_log = output_dir / "next.log"

    assert bitstream.stat().st_size > 0
    assert yosys_log.stat().st_size > 0
    nextpnr_output = nextpnr_log.read_text(encoding="utf-8")
    assert re.search(r"JTAGG:\s+1/\s*1", nextpnr_output)

    design = json.loads(netlist.read_text(encoding="utf-8"))
    cell_types = Counter(
        cell["type"]
        for module in design["modules"].values()
        for cell in module.get("cells", {}).values()
    )
    assert cell_types["JTAGG"] == 1
    assert cell_types["LUT4"] > 0
    assert cell_types["TRELLIS_FF"] > 0
