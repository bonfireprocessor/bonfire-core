from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Callable


def test_ecp5_jtagg_led_demo_icepizero_fusesoc(
    repo_root: Path,
    run_fusesoc: Callable[..., str],
    ecp5_fpga_toolchain_available: bool,
):
    command = ["run", "--target=icepizero"]
    if not ecp5_fpga_toolchain_available:
        command.append("--setup")
    command.append("::bonfire-ecp5-jtagg-led-demo:0")

    run_fusesoc(*command, timeout=180)
    if not ecp5_fpga_toolchain_available:
        return

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
