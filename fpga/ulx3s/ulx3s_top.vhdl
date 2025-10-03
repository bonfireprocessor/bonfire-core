library ieee;
use ieee.std_logic_1164.all;

entity ulx3s_top is
    port (
        sysclk    : in  std_logic;
        uart0_tx  : out std_logic;
        uart0_rx  : in  std_logic;
        led       : out std_logic_vector(3 downto 0)
       
    );
end entity ulx3s_top;

architecture rtl of ulx3s_top is

    -- Component declaration for bonfire_core_soc_top
    component bonfire_core_soc_top is
        port (
            sysclk    : in  std_logic;
            resetn    : in  std_logic;
            uart0_tx  : out std_logic;
            uart0_rx  : in  std_logic;
            led       : out std_logic_vector(3 downto 0);
            o_resetn  : out std_logic;
            i_locked  : in  std_logic
        );
    end component;


    signal resetn   : std_logic := '1'; -- Active low reset
    signal o_resetn : std_logic;
    signal i_locked : std_logic := '1'; -- Assuming the PLL is locked for simplicity
begin

    soc_inst: bonfire_core_soc_top
        port map (
            sysclk    => sysclk,
            resetn    => resetn,
            uart0_tx  => uart0_tx,
            uart0_rx  => uart0_rx,
            led       => led,
            o_resetn  => o_resetn,
            i_locked  => i_locked
        );

end architecture rtl;