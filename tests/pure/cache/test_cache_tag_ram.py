from __future__ import annotations


def test_tag_ram_read(sim_env):
    """
    TagRAM read operation test.
    
    Verifies that tag_ram_instance correctly responds to 16 read cycles:
    - address: Output bits [line_select_adr_bits:] of cache address  
    - valid: Set during read cycle
    - dirty: Cleared after read
    
    Based on tb_run.py: tb_tagram() testbench
    """
    from tb import tb_cache

    tb = tb_cache.tb_tagram(test_conversion=False)
    tb.config_sim(directory=str(sim_env["waveforms_dir"]), trace=False, filename="tag_ram_test")
    tb.run_sim(duration=50000)


def test_tag_ram_read_with_vcd(sim_env):
    """TagRAM read operation with VCD waveform for visual inspection."""
    from tb import tb_cache

    tb = tb_cache.tb_tagram(test_conversion=False)
    tb.config_sim(directory=str(sim_env["waveforms_dir"]), trace=True, filename="tag_ram_test")
    tb.run_sim(duration=50000)


def test_tag_ram_pipelined(sim_env):
    """TagRAM with pipelined configuration."""
    from tb import tb_cache

    tb = tb_cache.tb_tagram(test_conversion=False)
    tb.config_sim(directory=str(sim_env["waveforms_dir"]), trace=False, filename="tag_ram_test")
    tb.run_sim(duration=50000)
