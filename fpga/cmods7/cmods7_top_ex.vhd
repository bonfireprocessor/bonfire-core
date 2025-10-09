----------------------------------------------------------------------------------

-- Module Name:    bonfire_basic_soc - Behavioral

-- The Bonfire Processor Project, (c) 2016,2017 Thomas Hornschuh

--
-- License: See LICENSE or LICENSE.txt File in git project root.
--
--
----------------------------------------------------------------------------------
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

-- Uncomment the following library declaration if using
-- arithmetic functions with Signed or Unsigned values
use IEEE.NUMERIC_STD.ALL;


entity cmod_s7_top is
 
  port (
      I_RESET   : in  std_logic;
      CLK12MHZ  : in  std_logic;

      -- UART0 signals:
      uart0_txd : out std_logic;
      uart0_rxd : in  std_logic :='1';
      --LEDs
      led : out std_logic_vector(3 downto 0);
      --QSPI FLASH
      qspi_cs : out std_logic;
      qspi_mosi : out std_logic;
      qspi_miso : in std_logic;
      qspi_holdn : out std_logic;
      qspi_sck : out std_logic
  );

end entity;

architecture Behavioral of cmod_s7_top is


    -- Component declaration for bonfire_core_soc_top
    component bonfire_core_soc_top
    generic (
        NUM_SPI  : natural := 1;
        NUM_GPIO : natural := 8;
        ENABLE_UART1    : boolean := False;
        ENABLE_SPI      : boolean := False;
        NUM_LEDS       : natural := 8;
        ENABLE_GPIO     : boolean := true;
        DEBUG          : boolean := false;
        UART_TEST    : boolean := false
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
    end component;


  component clkgen
  port
   (
    sysclk  : out std_logic;    
    reset   : in  std_logic;
    locked  : out    std_logic;
    clk12mhz: in     std_logic
   );
  end component;


--  component gpio_pad
--  port (
--    I  : in  STD_LOGIC;
--    O  : out STD_LOGIC;
--    T  : in  STD_LOGIC;
--    IO : inout STD_LOGIC
--  );
--  end component gpio_pad;

signal sysclk : std_logic;

signal resetn  : std_logic;
signal clk_locked : std_logic;


signal gpio_o         : std_logic_vector(led'range);
signal gpio_i         : std_logic_vector(led'range);
signal gpio_t         : std_logic_vector(led'range);


begin


  qspi_holdn <= '1';
  --qspi_wpn <= '1';

    soc_inst: bonfire_core_soc_top
    -- generic map (
         NUM_SPI => 1,
    --   NUM_GPIO => NUM_GPIO,
    --   ENABLE_UART1 => ENABLE_UART1,
         ENABLE_SPI => true,
         NUM_LEDS => 4,
    --   ENABLE_GPIO => ENABLE_GPIO,
    --   DEBUG => DEBUG
        UART_TEST => false -- Instantiate complete soc_io 
    -- )
    port map(
        sysclk => sysclk,
        resetn => '1',
        i_locked => clk_locked, -- PLL (un) lock will serve as reset signal
        o_resetn => open,

        uart0_txd => uart0_tx,
        uart0_rxd => uart0_rx,
        uart1_txd => open,
        uart1_rxd => '1',
        spi_cs(0)   => qspi_cs,
        spi_clk(0)  => qspi_sck,
        spi_mosi(0) => qspi_mosi,
        spi_miso(0) => qspi_miso,
        gpio_o => open,
        gpio_i => (others=>'0'),
        gpio_t => open,
        led => led
    );


     
    clkgen_inst : clkgen
     port map ( 
   
       sysclk => sysclk,
       reset => i_reset,
       locked => clk_locked,   
       clk12mhz => clk12mhz
     );

     --sysclk <= CLK12MHZ;

      --reset <=  not clk_locked;


end architecture;
