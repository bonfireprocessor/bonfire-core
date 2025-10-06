---------------------------------------------------------------------------------
-- Genrated by gen_soc.py, do not edit!
-- Genratted at {generated}
-- Module Name:    tb_soc  

-- The Bonfire Core  Project, (c) 2025 Thomas Hornschuh

--
-- License: See LICENSE or LICENSE.txt File in git project root.
--
--
----------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;


entity gpio_pad is
    Port ( I : in  STD_LOGIC;
           O : out  STD_LOGIC;
           T : in  STD_LOGIC;
           IO : inout  STD_LOGIC);
end gpio_pad;

architecture Behavioral of gpio_pad is

begin

   O <= IO;

   process(I,T) begin
     if T='1' then
       IO <= 'Z';
     else
       IO <= I;
     end if;

   end process;


end Behavioral;

-- When starting a new entity all libraries must be declared again
library ieee;
use ieee.std_logic_1164.all;
use IEEE.numeric_std.all;

LIBRARY std;
USE std.textio.all;

use work.txt_util.all;


entity tb_soc is
    generic (
        NUM_SPI  : natural := {numSPI};
        NUM_GPIO : natural := {numGpio};
        ENABLE_UART1    : boolean := {enableUart1};
        ENABLE_SPI      : boolean := {enableSPI};
        NUM_LEDS       : natural := {numLeds};
        ENABLE_GPIO     : boolean := true;
        CLK_FREQ_MHZ  : natural := 25;
        UART_BAUDRATE : natural := 38400;
        DEBUG          : boolean := false
    );
end tb_soc;

architecture tb of tb_soc is

    component {entity_name}
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
        I_RESET   : in  std_logic;
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
    end component;
  

    signal sysclk         : std_logic;
    signal I_RESET        : std_logic :='0';
    signal uart0_txd      : std_logic;
    signal uart0_rxd      : std_logic :='1';
    signal uart1_txd      : std_logic;
    signal uart1_rxd      : std_logic := '1';
    signal spi_cs   : std_logic_vector(NUM_SPI-1 downto 0);
    signal spi_clk  :  std_logic_vector(NUM_SPI-1 downto 0);
    signal spi_mosi :  std_logic_vector(NUM_SPI-1 downto 0);
    signal spi_miso :  std_logic_vector(NUM_SPI-1 downto 0);

    signal gpio_io           : std_logic_vector (NUM_GPIO-1 downto 0);

    signal gpio_o         : std_logic_vector(NUM_GPIO-1 downto 0);
    signal gpio_i         : std_logic_vector(NUM_GPIO-1 downto 0);
    signal gpio_t         : std_logic_vector(NUM_GPIO-1 downto 0);
    signal led            : std_logic_vector(NUM_LEDS-1 downto 0);  


    constant ClockPeriod : time :=  ( 1000.0 / real(CLK_FREQ_MHZ) ) * 1 ns;

    signal TbClock : std_logic := '0';
    signal TbSimEnded : std_logic := '0';

    -- UART Capture Module
    constant bit_time : time := ( 1_000_000.0 / real(UART_BAUDRATE) ) * 1 us;
    subtype t_uartnum is natural range 0 to 1;
    type t_uart_kpi is array (t_uartnum) of natural;

    signal total_count : t_uart_kpi;
    signal framing_errors : t_uart_kpi;
    signal uart0_stop : boolean;

    COMPONENT tb_uart_capture_tx
    GENERIC (
      baudrate : natural;
      bit_time : time;
      SEND_LOG_NAME : string ;
      echo_output : boolean ;
      stop_mark : std_logic_vector(7 downto 0) -- Stop marker byte
     );
    PORT(
        txd : IN std_logic;
        stop : OUT boolean;
        framing_errors : OUT natural;
        total_count : OUT natural
        );
    END COMPONENT;

begin

    dut: {entity_name}
    generic map (
      NUM_SPI => NUM_SPI,
      NUM_GPIO => NUM_GPIO,
      ENABLE_UART1 => ENABLE_UART1,
      ENABLE_SPI => ENABLE_SPI,
      NUM_LEDS => NUM_LEDS,
      ENABLE_GPIO => ENABLE_GPIO,
      DEBUG => DEBUG
    )
    port map(
        sysclk => TbClock,
        I_RESET => I_RESET,
        uart0_txd => uart0_txd,
        uart0_rxd => uart0_rxd,
        uart1_txd => uart1_txd,
        uart1_rxd => uart1_rxd,
        spi_cs   => spi_cs,
        spi_clk  => spi_clk,
        spi_mosi => spi_mosi,
        spi_miso => spi_miso,
        gpio_o => gpio_o,
        gpio_i => gpio_i,
        gpio_t => gpio_t,
        led => led
    );

   
    



    gpio_pads: for i in gpio_io'range generate
      pad : entity work.gpio_pad

      port map (
         O => gpio_i(i),   -- Buffer output
         IO => gpio_io(i),    -- Buffer inout port
         I => gpio_o(i),   -- Buffer input
         T => gpio_t(i)    -- 3-state enable input, high=input, low=output
      );

    end generate;


   capture_tx_0 :  tb_uart_capture_tx
    GENERIC MAP (
        baudrate => natural(UART_BAUDRATE),
        bit_time => bit_time,
        SEND_LOG_NAME => "send0.log",
        echo_output => True,
        stop_mark => X"1A"
    )
    PORT MAP(
            txd => uart0_txd,
            stop => uart0_stop ,
            framing_errors => framing_errors(0),
            total_count =>total_count(0)
        );

-- Write Changes to gpio to console        
process
    begin
      wait on gpio_io;
      print("IO Pads:" & str(gpio_io) & "(" & hstr(gpio_io) & ")");

end process;

-- Write Chages to LED to console
process
    begin
      wait on led;
      print("LEDs:" & str(led) & "(" & hstr(led) & ")");

end process;

--Wishbone Bus Monitor
-- wb_monitor : process
--     alias io_cyc_tb    is << signal dut.io_cyc    : std_logic >>;
--     alias io_stb_tb    is << signal dut.io_stb    : std_logic >>;
--     alias io_we_tb     is << signal dut.io_we     : std_logic >>;
--     alias io_ack_tb    is << signal dut.io_ack    : std_logic >>;

--     alias io_sel_tb    is << signal dut.io_sel    : std_logic_vector(3 downto 0) >>;
--     alias io_dat_rd_tb is << signal dut.io_dat_rd : std_logic_vector(31 downto 0) >>;
--     alias io_dat_wr_tb is << signal dut.io_dat_wr : std_logic_vector(31 downto 0) >>;

   
--     alias io_adr_tb    is << signal dut.io_adr    : std_logic_vector >>;
-- begin
--   if  rising_edge(sysclk) then
--     if io_cyc_tb='1' and io_stb_tb='1' then
--         print( "WB start: " & str((io_we_tb)) & " " & hstr(io_adr_tb) & " sel=" & str(io_sel_tb));
        
--       wait until io_ack_tb='1';
--       print( "WB: ACK with "
--        & " wr="     & hstr(io_dat_wr_tb)
--        & " rd="     & str(io_dat_rd_tb));
--     end if;
--   end if;
  
-- end process;



    TbClock <= not TbClock after ClockPeriod / 2 when TbSimEnded /= '1' else '0';

    -- EDIT: Check that sysclk is really your main clock signal
    sysclk <= TbClock;

    -- SPI Loopback
    spi_miso <= spi_mosi;



    stimuli : process
    begin

        wait for ClockPeriod;
        I_RESET <= '1';
        wait for ClockPeriod * 3;
        I_RESET <= '0';
        print("Start simulation");

        wait until uart0_stop;
        print("");
        print("UART0 Test captured bytes: " & str(total_count(0)) & " framing errors: " & str(framing_errors(0)));

        TbSimEnded <= '1';
        wait;
    end process;


end tb;      