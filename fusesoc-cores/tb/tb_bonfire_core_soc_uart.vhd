library ieee;
use ieee.std_logic_1164.all;

library std;
use std.env.all;
use std.textio.all;


entity tb_bonfire_core_soc is
end entity tb_bonfire_core_soc;


architecture testbench of tb_bonfire_core_soc is
    constant clock_period : time := 10 ns;
    constant uart_bit_time : time := 8 * clock_period;

    signal sysclk : std_logic := '0';
    signal resetn : std_logic := '1';
    signal i_locked : std_logic := '0';
    signal uart0_tx : std_logic;
    signal uart0_rx : std_logic;
    signal led : std_logic_vector(3 downto 0);
    signal uart_stop : boolean := false;
    signal framing_errors : natural := 0;
    signal total_count : natural := 0;
begin
    sysclk <= not sysclk after clock_period / 2;
    uart0_rx <= uart0_tx;

    dut : entity work.bonfire_core_soc_top
        port map (
            sysclk => sysclk,
            resetn => resetn,
            uart0_tx => uart0_tx,
            uart0_rx => uart0_rx,
            led => led,
            o_resetn => open,
            i_locked => i_locked
        );

    capture_tx : entity work.tb_uart_capture_tx
        generic map (
            bit_time => uart_bit_time,
            send_log_name => "uart0.log",
            echo_output => true,
            stop_mark => x"1a"
        )
        port map (
            txd => uart0_tx,
            stop => uart_stop,
            framing_errors => framing_errors,
            total_count => total_count
        );

    stimulus : process
        variable output_line : line;
    begin
        for cycle in 1 to 5 loop
            wait until rising_edge(sysclk);
        end loop;
        i_locked <= '1';

        wait until uart_stop;
        wait until led = "1111" for 5 us;
        writeline(output, output_line);
        report "UART capture total bytes: " & integer'image(total_count);
        report "UART capture framing errors: " & integer'image(framing_errors);
        report "UART loopback LED value: " & to_hstring(led);

        assert total_count = 6
            report "UART capture did not receive 'Hello' plus stop marker"
            severity failure;
        assert framing_errors = 0
            report "UART capture reported framing errors"
            severity failure;
        assert led = "1111"
            report "UART loopback firmware did not report success"
            severity failure;

        stop;
        wait;
    end process;
end architecture testbench;
