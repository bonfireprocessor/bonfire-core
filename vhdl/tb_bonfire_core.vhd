LIBRARY ieee;
USE ieee.std_logic_1164.ALL;

use work.txt_util.all;
use work.log2;

ENTITY tb_bonfire_core IS
  generic (
    testfile : string;
    signature_file : string := ""; -- RISCV compliance signature output
    enable_sig_dump : boolean := false; -- Enable signature dump port
    raise_reset : boolean := false -- Determine if a 5 clock cycle long reset signal is asserted at begin of simulation

  );
END tb_bonfire_core;

ARCHITECTURE behavior OF tb_bonfire_core IS

constant ram_size : natural := 4096;
constant ram_adr_width : natural := log2.log2(ram_size);



signal clock               : std_logic := '0';
signal reset               : std_logic := '0';

signal wb_master_wbm_adr_o : std_logic_vector(29 downto 0);
signal wb_master_wbm_ack_i : std_logic;
signal wb_master_wbm_sel_o : std_logic_vector(3 downto 0);
signal wb_master_wbm_cyc_o : std_logic;
signal wb_master_wbm_db_i  : std_logic_vector(31 downto 0);
signal wb_master_wbm_db_o  : std_logic_vector(31 downto 0);
signal wb_master_wbm_stb_o : std_logic;
signal wb_master_wbm_we_o  : std_logic;
signal db_master_we_o      : std_logic_vector(3 downto 0);
signal db_master_db_rd     : std_logic_vector(31 downto 0);
signal db_master_db_wr     : std_logic_vector(31 downto 0);
signal db_master_adr_o     : std_logic_vector(31 downto 0);
signal db_master_error_i   : std_logic;
signal db_master_ack_i     : std_logic;
signal db_master_stall_i   : std_logic;
signal db_master_en_o      : std_logic;
signal bram_a_dbout        : std_logic_vector(31 downto 0);
signal bram_a_en           : std_logic;
signal bram_a_adrbus       : std_logic_vector(11 downto 0);
signal bram_a_clock        : std_logic;
signal bram_b_en           : std_logic;
signal bram_b_adrbus       : std_logic_vector(11 downto 0);
signal bram_b_clock        : std_logic;
signal bram_b_wren         : std_logic_vector(3 downto 0);
signal bram_b_dbin         : std_logic_vector(31 downto 0);
signal bram_b_dbout        : std_logic_vector(31 downto 0);

-- Simulation control
signal finished :  std_logic :='0';
signal result   :  std_logic_vector(31 downto 0);

signal tbSimEnded : std_logic := '0'; -- Simulation End Flag


-- Clock period definitions
constant clk_i_period : time := 10 ns;


component sim_MainMemory
generic (
  RamFileName      : string;
  mode             : string;
  ADDR_WIDTH       : integer;
  EnableSecondPort : boolean := true
);
port (
  DBOut   : out STD_LOGIC_VECTOR (31 downto 0);
  DBIn    : in  STD_LOGIC_VECTOR (31 downto 0);
  AdrBus  : in  STD_LOGIC_VECTOR (ADDR_WIDTH-1 downto 0);
  ENA     : in  STD_LOGIC;
  WREN    : in  STD_LOGIC_VECTOR (3 downto 0);
  CLK     : in  STD_LOGIC;
  CLKB    : in  STD_LOGIC;
  ENB     : in  STD_LOGIC;
  AdrBusB : in  STD_LOGIC_VECTOR (ADDR_WIDTH-1 downto 0);
  DBOutB  : out STD_LOGIC_VECTOR (31 downto 0)
);
end component sim_MainMemory;



begin

    uut:  entity work.bonfire_core_top
    port map (
      clock               => clock,
      reset               => reset,
      wb_master_wbm_adr_o => wb_master_wbm_adr_o,
      wb_master_wbm_ack_i => wb_master_wbm_ack_i,
      wb_master_wbm_sel_o => wb_master_wbm_sel_o,
      wb_master_wbm_cyc_o => wb_master_wbm_cyc_o,
      wb_master_wbm_db_i  => wb_master_wbm_db_i,
      wb_master_wbm_db_o  => wb_master_wbm_db_o,
      wb_master_wbm_stb_o => wb_master_wbm_stb_o,
      wb_master_wbm_we_o  => wb_master_wbm_we_o,

      db_master_we_o      => db_master_we_o,
      db_master_db_rd     => db_master_db_rd,
      db_master_db_wr     => db_master_db_wr,
      db_master_adr_o     => db_master_adr_o,
      db_master_error_i   => db_master_error_i,
      db_master_ack_i     => db_master_ack_i,
      db_master_stall_i   => db_master_stall_i,
      db_master_en_o      => db_master_en_o,

      bram_a_dbout        => bram_a_dbout,
      bram_a_en           => bram_a_en,
      bram_a_adrbus       => bram_a_adrbus,
      bram_a_clock        => bram_a_clock,

      bram_b_en           => bram_b_en,
      bram_b_adrbus       => bram_b_adrbus,
      bram_b_clock        => bram_b_clock,
      bram_b_wren         => bram_b_wren,
      bram_b_dbin         => bram_b_dbin,
      bram_b_dbout        => bram_b_dbout
    );


    sim_MainMemory_i : sim_MainMemory
        generic map (
          RamFileName      => testfile,
          mode             => "H",
          ADDR_WIDTH       => ram_adr_width,
          EnableSecondPort => true
        )
        port map (
          DBOut   => bram_b_dbout,
          DBIn    => bram_b_dbin,
          AdrBus  => bram_b_adrbus,
          ENA     => bram_b_en,
          WREN    => bram_b_wren,
          CLK     => bram_b_clock,
          CLKB    => bram_a_clock,
          ENB     => bram_a_en,
          AdrBusB => bram_a_adrbus,
          DBOutB  => bram_a_dbout
        );


        Inst_monitor:  entity work.monitor
            generic map(
              VERBOSE=>true,
              signature_file=>signature_file,
              ENABLE_SIG_DUMP=>ENABLE_SIG_DUMP

            )
            PORT MAP(
                clk_i => clock,
                rst_i => reset,
                db_we_i    => db_master_we_o,
                db_rd      => db_master_db_rd,
                db_wr      => db_master_db_wr,
                db_adr_i   => db_master_adr_o(27 downto 2),
                db_error_o => db_master_error_i,
                db_ack_o   => db_master_ack_i,
                db_stall_o => db_master_stall_i,
                db_en_i    => db_master_en_o,
                finished_o => finished,
                result_o => result
            );



-- Clock
clock <= not clock after clk_i_period/2 when TbSimEnded /= '1' else '0';


  stim_proc: process
  begin

    if raise_reset then
      report "Reseting design" severity note;
      reset <= '1';
      wait for clk_i_period*5;
      reset <= '0';
      report "Start" severity note;
    end if;  

    wait until finished='1'; -- or uart_stop;
    report "Test finished with result "& hstr(result) severity note;
    tbSimEnded <= '1'; -- End Simulation
    wait;
  end process;
end;
