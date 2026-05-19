library ieee;
use ieee.std_logic_1164.all;

entity fireant_top is
    port (
        sysclk    : in  std_logic;
        uart0_tx  : out std_logic;
        uart0_rx  : in  std_logic;
        led       : out std_logic_vector(7 downto 0)
    );
end entity fireant_top;

architecture rtl of fireant_top is

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


    -- signal sysclk         : std_logic;
    signal I_RESET        : std_logic :='0';
    
    -- signal uart1_txd      : std_logic;
    -- signal uart1_rxd      : std_logic := '1';
    -- signal spi_cs   : std_logic_vector(NUM_SPI-1 downto 0);
    -- signal spi_clk  :  std_logic_vector(NUM_SPI-1 downto 0);
    -- signal spi_mosi :  std_logic_vector(NUM_SPI-1 downto 0);
    -- signal spi_miso :  std_logic_vector(NUM_SPI-1 downto 0);

    -- signal gpio_io           : std_logic_vector (NUM_GPIO-1 downto 0);

    -- signal gpio_o         : std_logic_vector(NUM_GPIO-1 downto 0);
    -- signal gpio_i         : std_logic_vector(NUM_GPIO-1 downto 0);
    -- signal gpio_t         : std_logic_vector(NUM_GPIO-1 downto 0);



begin

    soc_inst: bonfire_core_soc_top
    -- generic map (
    --   NUM_SPI => NUM_SPI,
    --   NUM_GPIO => NUM_GPIO,
    --   ENABLE_UART1 => ENABLE_UART1,
    --   ENABLE_SPI => ENABLE_SPI,
    --   NUM_LEDS => NUM_LEDS,
    --   ENABLE_GPIO => ENABLE_GPIO,
    --   DEBUG => DEBUG
    -- )
    port map(
        sysclk => sysclk,
        I_RESET => I_RESET,
        uart0_txd => uart0_tx,
        uart0_rxd => uart0_rx,
        uart1_txd => open,
        uart1_rxd => '1',
        spi_cs   => open,
        spi_clk  => open,
        spi_mosi => open,
        spi_miso => (others=>'1'),
        gpio_o => open,
        gpio_i => (others=>'0'),
        gpio_t => open,
        led => led
    );

end architecture rtl;