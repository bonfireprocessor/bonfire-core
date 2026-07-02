library ieee;
use ieee.std_logic_1164.all;

entity ecp5_jtagg_bridge is
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
end entity ecp5_jtagg_bridge;

architecture rtl of ecp5_jtagg_bridge is

    component JTAGG is
        port (
            TCK     : in  std_logic := 'X';
            TMS     : in  std_logic := 'X';
            TDI     : in  std_logic := 'X';
            JTDO2   : in  std_logic;
            JTDO1   : in  std_logic;
            TDO     : out std_logic;
            JTDI    : out std_logic;
            JTCK    : out std_logic;
            JRTI2   : out std_logic;
            JRTI1   : out std_logic;
            JSHIFT  : out std_logic;
            JUPDATE : out std_logic;
            JRSTN   : out std_logic;
            JCE2    : out std_logic;
            JCE1    : out std_logic
        );
    end component;

begin

    jtagg_inst: JTAGG
        port map (
            TCK     => open,
            TMS     => open,
            TDI     => open,
            JTDO2   => jtdo2,
            JTDO1   => jtdo1,
            TDO     => open,
            JTDI    => jtdi,
            JTCK    => jtck,
            JRTI2   => jrt2,
            JRTI1   => jrt1,
            JSHIFT  => jshift,
            JUPDATE => jupdate,
            JRSTN   => jrstn,
            JCE2    => jce2,
            JCE1    => jce1
        );

end architecture rtl;
