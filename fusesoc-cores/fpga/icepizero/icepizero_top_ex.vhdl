library ieee;
use ieee.std_logic_1164.all;

entity icepizero_top is
    port (
        sysclk    : in  std_logic;
        uart0_tx  : out std_logic;
        uart0_rx  : in  std_logic;
        led       : out std_logic_vector(4 downto 0)
    );
end entity icepizero_top;

architecture rtl of icepizero_top is

    component bonfire_core_soc_top
    generic (
        NUM_SPI         : natural := 1;
        NUM_GPIO        : natural := 8;
        ENABLE_UART1    : boolean := false;
        ENABLE_SPI      : boolean := false;
        NUM_LEDS        : natural := 5;
        ENABLE_GPIO     : boolean := true;
        DEBUG           : boolean := false;
        UART_FIFO_DEPTH : natural := 6;
        INST_UART_ONLY  : boolean := false
    );
    port (
        sysclk    : in  std_logic;
        resetn    : in  std_logic;
        i_locked  : in  std_logic;
        o_resetn  : out std_logic;

        uart0_txd : out std_logic;
        uart0_rxd : in  std_logic := '1';
        uart1_txd : out std_logic;
        uart1_rxd : in  std_logic := '1';

        spi_cs    : out std_logic_vector(NUM_SPI-1 downto 0);
        spi_clk   : out std_logic_vector(NUM_SPI-1 downto 0);
        spi_mosi  : out std_logic_vector(NUM_SPI-1 downto 0);
        spi_miso  : in  std_logic_vector(NUM_SPI-1 downto 0);

        gpio_o    : out std_logic_vector(NUM_GPIO-1 downto 0);
        gpio_i    : in  std_logic_vector(NUM_GPIO-1 downto 0);
        gpio_t    : out std_logic_vector(NUM_GPIO-1 downto 0);

        led       : out std_logic_vector(NUM_LEDS-1 downto 0)
    );
    end component;

    signal resetn : std_logic := '1';

    signal mosi, miso : std_logic_vector(0 downto 0);

begin

   miso <= mosi; -- Loopback

    soc_inst: bonfire_core_soc_top
    generic map (
        INST_UART_ONLY => false,
        ENABLE_SPI => true
    )
    port map (
        sysclk    => sysclk,
        resetn    => resetn,
        i_locked  => '1',
        o_resetn  => open,

        uart0_txd => uart0_tx,
        uart0_rxd => uart0_rx,
        uart1_txd => open,
        uart1_rxd => '1',

        spi_cs    => open,
        spi_clk   => open,
        spi_mosi  => mosi,
        spi_miso  => miso,

        gpio_o    => open,
        gpio_i    => (others => '0'),
        gpio_t    => open,

        led       => led
    );

end architecture rtl;
