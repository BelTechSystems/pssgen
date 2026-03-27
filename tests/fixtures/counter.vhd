library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity up_down_counter is
    generic (
        WIDTH : integer := 8
    );
    port (
        clk      : in  std_logic;
        rst_n    : in  std_logic;
        enable   : in  std_logic;
        up_down  : in  std_logic;
        count    : out std_logic_vector(7 downto 0)
    );
end entity up_down_counter;

architecture rtl of up_down_counter is
begin
    process(clk, rst_n)
    begin
        if rst_n = '0' then
            count <= (others => '0');
        elsif rising_edge(clk) then
            if enable = '1' then
                if up_down = '1' then
                    count <= std_logic_vector(
                        unsigned(count) + 1);
                else
                    count <= std_logic_vector(
                        unsigned(count) - 1);
                end if;
            end if;
        end if;
    end process;
end architecture rtl;
