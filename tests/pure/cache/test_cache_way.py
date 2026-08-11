from __future__ import annotations


def test_cache_way_miss_hit(sim_env):
    """
    CacheWay miss handling and tag update test.
    
    Verifies cache_way_instance correctly handles:
    - Miss detection (hit=False, miss=True)
    - Tag validity assertion  
    - Tag update after miss
    
    Based on tb_run.py: tb_cache_way() testbench
    """
    from tb import tb_cache

    tb = tb_cache.tb_cache_way(test_conversion=False)
    tb.config_sim(directory=str(sim_env["waveforms_dir"]), trace=False, filename="cache_way_test")
    tb.run_sim(duration=50000)


def test_cache_way_miss_hit_with_vcd(sim_env):
    """CacheWay with VCD waveform for debugging miss/hit transitions."""
    from tb import tb_cache

    tb = tb_cache.tb_cache_way(test_conversion=False)
    tb.config_sim(directory=str(sim_env["waveforms_dir"]), trace=True, filename="cache_way_test")
    tb.run_sim(duration=50000)


def test_cache_way_with_vhdl(sim_env):
    """CacheWay with VHDL conversion (verification test)."""
    from tb import tb_cache

    tb = tb_cache.tb_cache_way(test_conversion=True)
    tb.config_sim(directory=str(sim_env["waveforms_dir"]), trace=False, filename="cache_way_vhdl")
    tb.run_sim(duration=50000)
