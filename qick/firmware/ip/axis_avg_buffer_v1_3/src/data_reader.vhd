library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity data_reader is
   Generic
   (
      -- Address map of memory.
      N : Integer := 8;
      -- Data width.
      B : Integer := 16
   );
   Port
   (
      -- Reset and clock.
      rstn     : in  std_logic;
      clk      : in  std_logic;

      -- Memory I/F.
      mem_en   : out std_logic;
      mem_we   : out std_logic;
      mem_addr : out std_logic_vector (N-1 downto 0);
      mem_dout : in  std_logic_vector (B-1 downto 0);

      -- Data out.
      dout     : out std_logic_vector (B-1 downto 0);
      dready   : in  std_logic;
      dvalid   : out std_logic;
      dlast    : out std_logic;

      -- Registers.
      START_REG: in  std_logic;
      ADDR_REG : in  std_logic_vector (N-1 downto 0);
      LEN_REG  : in  std_logic_vector (N-1 downto 0)
   );
end entity;

architecture rtl of data_reader is
   type fsm_state is (IDLE_ST, ISSUE_READ_ST, CAPTURE_ST, SEND_ST, DONE_ST);
   signal state       : fsm_state;
   signal addr_r      : unsigned(N-1 downto 0);
   signal remaining_r : unsigned(N-1 downto 0);
   signal data_r      : std_logic_vector(B-1 downto 0);
   signal valid_r     : std_logic;
   signal last_r      : std_logic;
begin

   process(clk)
      variable len_eff : unsigned(N-1 downto 0);
   begin
      if rising_edge(clk) then
         if rstn = '0' then
            state       <= IDLE_ST;
            addr_r      <= (others => '0');
            remaining_r <= (others => '0');
            data_r      <= (others => '0');
            valid_r     <= '0';
            last_r      <= '0';
         else
            case state is
               when IDLE_ST =>
                  valid_r <= '0';
                  last_r  <= '0';
                  if START_REG = '1' then
                     if unsigned(LEN_REG) = 0 then
                        len_eff := to_unsigned(1, N);
                     else
                        len_eff := unsigned(LEN_REG);
                     end if;
                     addr_r      <= unsigned(ADDR_REG);
                     remaining_r <= len_eff;
                     state       <= ISSUE_READ_ST;
                  end if;

               when ISSUE_READ_ST =>
                  valid_r <= '0';
                  state   <= CAPTURE_ST;

               when CAPTURE_ST =>
                  data_r  <= mem_dout;
                  valid_r <= '1';
                  if remaining_r = to_unsigned(1, N) then
                     last_r <= '1';
                  else
                     last_r <= '0';
                  end if;
                  state <= SEND_ST;

               when SEND_ST =>
                  if valid_r = '1' and dready = '1' then
                     valid_r <= '0';
                     if last_r = '1' then
                        state <= DONE_ST;
                     else
                        addr_r      <= addr_r + 1;
                        remaining_r <= remaining_r - 1;
                        state       <= ISSUE_READ_ST;
                     end if;
                  end if;

               when DONE_ST =>
                  valid_r <= '0';
                  last_r  <= '0';
                  if START_REG = '0' then
                     state <= IDLE_ST;
                  end if;
            end case;
         end if;
      end if;
   end process;

   mem_en   <= '1';
   mem_we   <= '0';
   mem_addr <= std_logic_vector(addr_r);

   dout   <= data_r;
   dvalid <= valid_r;
   dlast  <= valid_r and last_r;

end rtl;
