---------------------------------------------------------------------
-- Test monitor
--
-- Part of the LXP32 testbench
--
-- Copyright (c) 2016 by Alex I. Kuznetsov
--
-- Provide means for a test platform to interact with the testbench.
--
--
-- The Bonfire Processor Project, (c) 2016,2017,2018 Thomas Hornschuh
--
-- License: See LICENSE or LICENSE.txt File in git project root.
---------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library STD;
use STD.textio.all;

use work.txt_util.all;


entity monitor is
  generic(
    VERBOSE: boolean;
    signature_file : string :="signature.log";
    ENABLE_SIG_DUMP : boolean := false
  );
  port(
    clk_i: in std_logic;
    rst_i: in std_logic;

    db_we_i: in std_logic_vector(3 downto 0);
    db_rd: out std_logic_vector(31 downto 0);
    db_wr: in std_logic_vector(31 downto 0);
    db_adr_i: in std_logic_vector(31 downto 0);
    db_error_o: out std_logic;
    db_ack_o: out std_logic;
    db_stall_o: out std_logic;
    db_en_i: in std_logic;

    finished_o: out std_logic;
    result_o: out std_logic_vector(31 downto 0)
  );
end entity;

architecture sim of monitor is

-- Last address of Monitor range is the signature file port.
-- Any value written to it will be written has hex value to the signature file
constant c_signature_port_adr : std_logic_vector(db_adr_i'range) := X"01ffffff";

signal result: std_logic_vector(31 downto 0):=(others=>'0');
signal finished: std_logic:='0';

signal counter : natural := 0;

function hstr_lc(slv: std_logic_vector) return string is
    variable hexlen: integer;
    variable longslv : std_logic_vector(67 downto 0) := (others => '0');
    variable hex : string(1 to 16);
    variable fourbit : std_logic_vector(3 downto 0);
  begin
    hexlen := (slv'left+1)/4;
    if (slv'left+1) mod 4 /= 0 then
      hexlen := hexlen + 1;
    end if;
    longslv(slv'left downto 0) := slv;
    for i in (hexlen -1) downto 0 loop
      fourbit := longslv(((i*4)+3) downto (i*4));
      case fourbit is
        when "0000" => hex(hexlen -I) := '0';
        when "0001" => hex(hexlen -I) := '1';
        when "0010" => hex(hexlen -I) := '2';
        when "0011" => hex(hexlen -I) := '3';
        when "0100" => hex(hexlen -I) := '4';
        when "0101" => hex(hexlen -I) := '5';
        when "0110" => hex(hexlen -I) := '6';
        when "0111" => hex(hexlen -I) := '7';
        when "1000" => hex(hexlen -I) := '8';
        when "1001" => hex(hexlen -I) := '9';
        when "1010" => hex(hexlen -I) := 'a';
        when "1011" => hex(hexlen -I) := 'b';
        when "1100" => hex(hexlen -I) := 'c';
        when "1101" => hex(hexlen -I) := 'd';
        when "1110" => hex(hexlen -I) := 'e';
        when "1111" => hex(hexlen -I) := 'f';
        when "ZZZZ" => hex(hexlen -I) := 'z';
        when "UUUU" => hex(hexlen -I) := 'u';
        when "XXXX" => hex(hexlen -I) := 'x';
        when others => hex(hexlen -I) := '?';
      end case;
    end loop;
    return hex(1 to hexlen);
  end hstr_lc;

begin

db_ack_o<=db_en_i;
db_rd<=(others=>'-');
db_stall_o <= '0';
db_error_o <= '0';

finished_o<=finished;
result_o<=result;

process (clk_i) is
variable temp_adr : std_logic_vector(31 downto 0);
variable csr : string(1 to 10);
begin
  if rising_edge(clk_i) then
    if rst_i='1' then
      finished<='0';
      result<=(others=>'0');
    elsif db_en_i='1' and db_we_i /= "0000" then
        temp_adr := (others=>'0');
        temp_adr(db_adr_i'range):=db_adr_i;
      assert db_we_i="1111"
        report "Monitor doesn't support byte-granular access "&
          "(SEL_I() is 0x"&hstr(db_we_i)&")"
        severity failure;

      if VERBOSE and db_adr_i /= c_signature_port_adr then
        if temp_adr(15 downto 8)=X"10" then -- RISC-V Excpetion output area
          case temp_adr(3 downto 2) is
             when  "00" => csr := "mcause:   ";
             when  "01" => csr := "mepc:     ";
             when  "10" => csr := "mbadaddr: ";
             when  "11" => csr := "mstatus:  ";
             when others => csr := hstr_lc(db_adr_i) & " ";
          end case;
          report  csr & " value: " & hstr_lc(db_wr);
        else
          report "Monitor: value "&
            "0x"&hstr(db_wr)&
            " written to address "&
            "0x"&hstr(temp_adr);
        end if;
      end if;

      if unsigned(db_adr_i)=to_unsigned(0,db_adr_i'length) then
        result<=db_wr;
        finished<='1';

        if VERBOSE and counter > 0 then
            report  str(counter) & " words written to: " & signature_file;
        end if;
      end if;
    end if;
  end if;
end process;

sigdump: if ENABLE_SIG_DUMP generate
    process
    file s_file: TEXT;

    begin
      file_open(s_file,signature_file,WRITE_MODE);
      while finished='0' loop
         wait until rising_edge(clk_i);
         if  db_en_i='1' and db_we_i="1111" and db_adr_i=c_signature_port_adr then
            print(s_file,hstr_lc(db_wr));
            counter <= counter + 1;
         end if;
      end loop ;
      file_close(s_file);
    end process;
  end generate;

end architecture;
