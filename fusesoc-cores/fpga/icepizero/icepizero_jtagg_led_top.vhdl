library ieee;
use ieee.std_logic_1164.all;

entity icepizero_jtagg_led_top is
    port (
        sysclk    : in  std_logic;
        uart0_tx  : out std_logic;
        uart0_rx  : in  std_logic;
        led       : out std_logic_vector(4 downto 0)
    );
end entity icepizero_jtagg_led_top;

architecture rtl of icepizero_jtagg_led_top is

    component ecp5_jtagg_led_demo is
        port (
            led              : out std_logic_vector(4 downto 0);
            jtagg_i_jtck     : in  std_logic;
            jtagg_i_jtdi     : in  std_logic;
            jtagg_i_jshift   : in  std_logic;
            jtagg_i_jupdate  : in  std_logic;
            jtagg_i_jrstn    : in  std_logic;
            jtagg_i_jce1     : in  std_logic;
            jtagg_i_jce2     : in  std_logic;
            jtagg_i_jrt1     : in  std_logic;
            jtagg_i_jrt2     : in  std_logic;
            jtagg_o_jtdo1    : out std_logic;
            jtagg_o_jtdo2    : out std_logic
        );
    end component;

    component ecp5_jtagg_bridge is
        port (
            jtck    : out std_logic;
            jtdi    : out std_logic;
            jshift  : out std_logic;
            jupdate : out std_logic;
            jrstn   : out std_logic;
            jce1    : out std_logic;
            jce2    : out std_logic;
            jrt1    : out std_logic;
            jrt2    : out std_logic;
            jtdo1   : in  std_logic;
            jtdo2   : in  std_logic
        );
    end component;

    signal jtck         : std_logic;
    signal jtdi         : std_logic;
    signal jshift       : std_logic;
    signal jupdate      : std_logic;
    signal jrstn        : std_logic;
    signal jce1         : std_logic;
    signal jce2         : std_logic;
    signal jrt1         : std_logic;
    signal jrt2         : std_logic;
    signal jtdo1        : std_logic;
    signal jtdo2        : std_logic;

begin

    uart0_tx <= '1';
    jtagg_bridge_inst: ecp5_jtagg_bridge
        port map (
            jtck    => jtck,
            jtdi    => jtdi,
            jshift  => jshift,
            jupdate => jupdate,
            jrstn   => jrstn,
            jce1    => jce1,
            jce2    => jce2,
            jrt1    => jrt1,
            jrt2    => jrt2,
            jtdo1   => jtdo1,
            jtdo2   => jtdo2
        );

    led_demo_inst: ecp5_jtagg_led_demo
        port map (
            led             => led,
            jtagg_i_jtck    => jtck,
            jtagg_i_jtdi    => jtdi,
            jtagg_i_jshift  => jshift,
            jtagg_i_jupdate => jupdate,
            jtagg_i_jrstn   => jrstn,
            jtagg_i_jce1    => jce1,
            jtagg_i_jce2    => jce2,
            jtagg_i_jrt1    => jrt1,
            jtagg_i_jrt2    => jrt2,
            jtagg_o_jtdo1   => jtdo1,
            jtagg_o_jtdo2   => jtdo2
        );

end architecture rtl;
