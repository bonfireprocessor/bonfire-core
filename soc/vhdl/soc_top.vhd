---------------------------------------------------------------------------------
-- Genrated by gen_soc.py, do not edit!
-- Genratted at {generated}
-- Module Name:    soc_top 

-- The Bonfire Core  Project, (c) 2025 Thomas Hornschuh

--
-- License: See LICENSE or LICENSE.txt File in git project root.
--
--
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

LIBRARY std;
USE std.textio.all;
use work.txt_util.all;


entity {entity_name} is
    generic (
        NUM_SPI  : natural := {numSPI};
        NUM_GPIO : natural := {numGpio};
        ENABLE_UART1    : boolean := {enableUart1};
        ENABLE_SPI      : boolean := {enableSPI};
        NUM_LEDS       : natural := {numLeds};
        ENABLE_GPIO     : boolean := true;
        DEBUG          : boolean := false
    );

    port(
        sysclk  : in  std_logic;
        -- Reset Logic
        resetn   : in  std_logic; -- Reset button, active low
        i_locked : in std_logic; -- PLL locked input
        o_resetn : out std_logic; -- Reset output, to be connected to PLL
        -- UART0 signals:
        uart0_txd : out std_logic;
        uart0_rxd : in  std_logic :='1';
        -- UART1 signals:
        uart1_txd : out std_logic;
        uart1_rxd : in  std_logic :='1';
        -- SPI
        spi_cs        : out   std_logic_vector(NUM_SPI-1 downto 0);
        spi_clk       : out   std_logic_vector(NUM_SPI-1 downto 0);
        spi_mosi      : out   std_logic_vector(NUM_SPI-1 downto 0);
        spi_miso      : in    std_logic_vector(NUM_SPI-1 downto 0);
         -- GPIO
        gpio_o : out std_logic_vector(NUM_GPIO-1 downto 0);
        gpio_i : in  std_logic_vector(NUM_GPIO-1 downto 0);
        gpio_t : out std_logic_vector(NUM_GPIO-1 downto 0);
        -- LEDs
        led: out std_logic_vector(NUM_LEDS-1 downto 0)

       
    );
end {entity_name};


architecture rtl of {entity_name} is

component {gen_core_name} is
    -- sysclk : cpu clock
    -- resetn : reset button, active low
    -- uart0_tx : UART TX Signal -- not used, to be removed
    -- uart0_rx: UART RX Signal  -- not used, to be removed
    -- led : modbv vector for led(s)
    -- o_resetn : Output, reset PLL
    -- wb_master :  Wishbone Master Interface

    port (
        sysclk: in std_logic;
        resetn: in std_logic;
        uart0_tx: out std_logic;
        uart0_rx: in std_logic;
        led: out std_logic_vector(NUM_LEDS-1 downto 0);
        o_resetn: out std_logic; 
        i_locked: in std_logic;
        wb_master_wbm_cyc_o: out std_logic;
        wb_master_wbm_stb_o: out std_logic;
        wb_master_wbm_ack_i: in std_logic;
        wb_master_wbm_we_o: out std_logic;
        wb_master_wbm_adr_o: out std_logic_vector(29 downto 0);
        wb_master_wbm_db_o: out std_logic_vector(31 downto 0);
        wb_master_wbm_db_i: in std_logic_vector(31 downto 0);
        wb_master_wbm_sel_o: out std_logic_vector(3 downto 0)
    );
end component {gen_core_name};

constant io_adr_high : integer := 25;

signal adr_map: std_logic_vector(29 downto 0);

--I/O Bus
signal io_cyc,io_stb,io_we,io_ack : std_logic;
signal io_sel :  std_logic_vector(3 downto 0);
signal io_dat_rd,io_dat_wr : std_logic_vector(31 downto 0);
signal io_adr : std_logic_vector(io_adr_high downto 2);

signal reset_sync : std_logic := '0';


begin

U_BONFIRE_CORE: {gen_core_name}
    port map(
        sysclk => sysclk,
        resetn => resetn,
        uart0_tx => open,
        uart0_rx => '1',
        led => led,
        o_resetn => o_resetn,
        i_locked => i_locked,
        wb_master_wbm_cyc_o => io_cyc,
        wb_master_wbm_stb_o => io_stb,
        wb_master_wbm_ack_i => io_ack,
        wb_master_wbm_we_o => io_we,
        wb_master_wbm_adr_o => adr_map,
        wb_master_wbm_db_o => io_dat_wr,
        wb_master_wbm_db_i => io_dat_rd,
        wb_master_wbm_sel_o => io_sel
    );

    io_adr(io_adr'range) <= adr_map(io_adr'length-1 downto 0); -- Map different address indexing

Inst_bonfire_soc_io: entity  work.bonfire_soc_io
GENERIC MAP (
  NUM_GPIO_BITS => gpio_o'length,
  ADR_HIGH => io_adr_high,
  UART_FIFO_DEPTH => 6,
  ENABLE_UART0 => true,
  ENABLE_UART1 => ENABLE_UART1,
  ENABLE_SPI => ENABLE_SPI,
  NUM_SPI => NUM_SPI,
  ENABLE_GPIO => ENABLE_GPIO
)
PORT MAP(
        uart0_txd => uart0_txd,
        uart0_rxd => uart0_rxd,
        uart1_txd => uart1_txd,
        uart1_rxd => uart1_rxd,
        gpio_o => gpio_o ,
        gpio_i => gpio_i,
        gpio_t =>  gpio_t,
        spi_cs => spi_cs,
        spi_clk => spi_clk,
        spi_mosi => spi_mosi,
        spi_miso => spi_miso,
        irq_o => open,
        clk_i => sysclk,
        rst_i => reset_sync,
        wb_cyc_i => io_cyc,
        wb_stb_i => io_stb,
        wb_we_i =>  io_we,
        wb_sel_i => io_sel,
        wb_ack_o => io_ack,
        wb_adr_i => io_adr,
        wb_dat_i => io_dat_wr,
        wb_dat_o => io_dat_rd
    );

--Wishbone Bus Monitor (instantiated only when DEBUG is true)
wb_monitor_gen: if DEBUG generate
    wb_monitor : process(sysclk)
      
    begin
        if rising_edge(sysclk) then
            if io_cyc='1' and io_stb='1' then
                print("***");
                print( "WB start: ");
                print("we=" & str(io_we) & " adr=" & hstr(std_logic_vector(resize(unsigned(adr_map & "00"), 32))) & " sel=" & str(io_sel));
                if io_we='1' then
                    print( "WB: write with " & " wr="     & hstr(io_dat_wr));
                end if;    
            end if;    
            if io_ack='1'  then
                if io_we='0' then
                    print( "WB: ACK read with "
                    & " rd="     & hstr(io_dat_rd));
                    for i in io_dat_rd'range loop
                        assert io_dat_rd(i) /= 'X'
                            report "Wishbone read contains undefined (X) bits!" severity error;
                    end loop;
                else
                    print("WB ack write");
                end if;        
             end if;
         end if;
    end process;
end generate;


-- Reset synchronizer: generates synchronous reset_sync (active high) from async resetn (active low)
process(sysclk, resetn)
    variable sync_reg : std_logic_vector(1 downto 0) := (others => '0');
begin
    if resetn = '0' then
        sync_reg := (others => '0');
        reset_sync <= '1';
    elsif rising_edge(sysclk) then
        sync_reg(0) := '1';
        sync_reg(1) := sync_reg(0);
        reset_sync <= not sync_reg(1);
    end if;
end process;

end rtl;