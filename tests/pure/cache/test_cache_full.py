from __future__ import annotations


def test_cache_128kb_pipelined(sim_env):
    """
    Full cache simulation (128KB, 128-bit width) with pipelining.
    
    Verifies:
    - Read loop across multiple lines
    - Write operation and write-back
    - Cross-check verification
    
    Based on tb_run.py: tb_cache(pipelined=True) testbench
    """
    from tb import tb_cache

    tb = tb_cache.tb_cache(
        test_conversion=False,
        cache_size_m_words=128,      # 128MB words  
        master_data_width=128,       # Bus width in bits
        verbose=False,
        pipelined=True
    )
    tb.config_sim(directory=str(sim_env["waveforms_dir"]), trace=False, filename="cache_128kb_test")
    tb.run_sim(duration=300000)


def test_cache_128kb_comb(sim_env):
    """Full cache simulation (128KB) without pipelining."""
    from tb import tb_cache

    tb = tb_cache.tb_cache(
        test_conversion=False,
        cache_size_m_words=128,
        master_data_width=128,
        verbose=False,
        pipelined=False
    )
    tb.config_sim(directory=str(sim_env["waveforms_dir"]), trace=False, filename="cache_128kb_test_comb")
    tb.run_sim(duration=300000)


def test_cache_128kb_pipelined_with_vcd(sim_env):
    """Full cache with VCD waveform for timing inspection."""
    from tb import tb_cache

    tb = tb_cache.tb_cache(
        test_conversion=False,
        cache_size_m_words=128,
        master_data_width=128,
        verbose=False,
        pipelined=True
    )
    tb.config_sim(directory=str(sim_env["waveforms_dir"]), trace=True, filename="cache_128kb_test")
    tb.run_sim(duration=300000)


def test_cache_with_vhdl_conversion(sim_env):
    """Full cache with VHDL conversion verification."""
    from tb import tb_cache

    tb = tb_cache.tb_cache(
        test_conversion=True,
        cache_size_m_words=128,
        master_data_width=128,
        verbose=False,
        pipelined=True
    )
    tb.config_sim(directory=str(sim_env["waveforms_dir"]), trace=False, filename="cache_vhdl_test")
    tb.run_sim(duration=300000)
