library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

LIBRARY std;
USE std.textio.all;

use work.txt_util.all;

entity clkgen is
  generic (
    CLK_PERIOD : time := 10.42 ns; -- 96 Mhz
    LOCK_CYCLES : natural := 50; -- Number of clock cycles until clkgen is "locked"
    WATCHDOG_TIME : time := 500 ns
  );
  Port (
    sysclk : out STD_LOGIC;
    reset : in STD_LOGIC;
    locked : out STD_LOGIC;
    clk12mhz : in STD_LOGIC
  );

end clkgen;

architecture stub of clkgen is

signal TbClock : std_logic := '0';

signal lock_counter : natural :=0;
signal f_locked : boolean;

signal stop : boolean := false;

shared variable  watch : boolean:= false;


begin
  
   f_locked <=  lock_counter > LOCK_CYCLES;
   
   locked <= '1' when f_locked else '0';


   process(tbClock) begin
   
     if rising_edge(tbClock) then
      
       if reset = '1' then
         lock_counter <= 0;
       else
        if not f_locked then 
          lock_counter <= lock_counter + 1;   
        end if;
      end if;  
     end if;
   
   end process;
   
   
   process(clk12mhz) begin
   
      watch := rising_edge(clk12mhz);
   
   end process;
   
   watchdog: process
   begin
     watch := false; 
     wait for WATCHDOG_TIME;
     -- Check if watch is still false after WATCHDOG_TIME
     -- this happens when there is no sysclock cycle happend in that time
     stop <= not watch;
     
     if not watch then
       print("clkgen_sim : Wait for clk12mhz restart, output clock stopped");
       wait until rising_edge(clk12mhz);
       print("clkgen_sim: clk12Mhz rising edge detected, Output clock enabled");
     end if;  
       
   end process;


   TbClock <= not TbClock after CLK_PERIOD/2 when not stop else '0';
   sysclk <= tbClock;


end;
