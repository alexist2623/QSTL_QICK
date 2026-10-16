library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

-- Timed-instruction dispatcher for QICK:QICK:axis_tproc64x32_x8:2.0.
-- The upstream FIFO has a synchronous, one-clock read port (not FWFT).
-- Prefetching decouples that read from timestamp dispatch; the output remains
-- registered exactly as in v1. A prequeued timestamp T becomes visible after
-- the comparison edge at t_cnt=T and is sampled downstream at t_cnt=T+1.
-- Consecutive queued timestamps can therefore be sampled on consecutive edges.
--
-- FIFO word: opcode[215:208], timestamp[207:160], payload[159:0].
-- SET/SETI retain the ISA's nonblocking, one-clock pulse semantics. SETB/SETBI
-- retain valid and data until ready. WAIT/WAITI retain waitt until waitt_ack.
-- Equal or late timestamps are dispatched in FIFO order, never coalesced.
-- Unsigned timestamp comparison and reset/epoch semantics are unchanged: only
-- rstn clears pending instructions; changing t_cnt alone does not flush them.
entity timed_ictrl is
    port (
        clk             : in std_logic;
        rstn            : in std_logic;
        t_cnt           : in unsigned (47 downto 0);
        fifo_rd_en      : out std_logic;
        fifo_dout       : in std_logic_vector (215 downto 0);
        fifo_empty      : in std_logic;
        waitt           : out std_logic;
        waitt_ack       : in std_logic;
        m_axis_tdata    : out std_logic_vector (159 downto 0);
        m_axis_tvalid   : out std_logic;
        m_axis_tready   : in std_logic
    );
end timed_ictrl;

architecture rtl of timed_ictrl is
    type queue_type is array (0 to 1) of std_logic_vector (215 downto 0);
    signal queue_data : queue_type;
    signal queue_count : integer range 0 to 2;
    -- fifo_dout is captured one edge after an accepted read request. Reserve
    -- room for this in-flight response even if downstream becomes blocked.
    signal read_pending : std_logic;
    signal read_request : std_logic;
    signal pop_head : std_logic;

    type issue_type is (IDLE, NONBLOCKING_SET, BLOCKING_SET, WAIT_ACK);
    signal issue_kind : issue_type;
    signal issue_data : std_logic_vector (159 downto 0);
    signal issue_available : std_logic;
begin
    issue_available <= '1' when issue_kind = IDLE or
                               issue_kind = NONBLOCKING_SET or
                               (issue_kind = BLOCKING_SET and m_axis_tready = '1') or
                               (issue_kind = WAIT_ACK and waitt_ack = '1') else '0';

    pop_head <= '1' when queue_count /= 0 and issue_available = '1' and
                         unsigned(queue_data(0)(207 downto 160)) <= t_cnt else '0';

    -- Use both occupied and reserved slots. A simultaneous dispatch releases
    -- one slot, permitting continuous reads without overrun during stalls.
    process (rstn, fifo_empty, queue_count, read_pending, pop_head)
        variable reserved : integer range -1 to 3;
    begin
        reserved := queue_count;
        if read_pending = '1' then reserved := reserved + 1; end if;
        if pop_head = '1' then reserved := reserved - 1; end if;
        read_request <= '0';
        if rstn = '1' and fifo_empty = '0' and reserved < 2 then
            read_request <= '1';
        end if;
    end process;

    process (clk)
        variable next_queue : queue_type;
        variable next_count : integer range 0 to 3;
        variable opcode : std_logic_vector (7 downto 0);
    begin
        if rising_edge(clk) then
            if rstn = '0' then
                queue_data <= (others => (others => '0'));
                queue_count <= 0;
                read_pending <= '0';
                issue_kind <= IDLE;
                issue_data <= (others => '0');
            else
                next_queue := queue_data;
                next_count := queue_count;
                if issue_available = '1' then
                    issue_kind <= IDLE;
                    if pop_head = '1' then
                        opcode := queue_data(0)(215 downto 208);
                        if opcode = x"15" or opcode = x"54" then
                            issue_kind <= WAIT_ACK;
                        elsif opcode = x"13" or opcode = x"51" then
                            issue_kind <= NONBLOCKING_SET;
                        elsif opcode = x"1A" or opcode = x"58" then
                            issue_kind <= BLOCKING_SET;
                        end if;
                        if opcode = x"13" or opcode = x"1A" then
                            issue_data <= (159 downto 32 => '0') & queue_data(0)(31 downto 0);
                        else
                            issue_data <= queue_data(0)(159 downto 0);
                        end if;
                        next_queue(0) := queue_data(1);
                        next_count := next_count - 1;
                    end if;
                end if;
                if read_pending = '1' then
                    -- synthesis translate_off
                    assert next_count < 2 report "timed_ictrl prefetch overflow" severity failure;
                    -- synthesis translate_on
                    next_queue(next_count) := fifo_dout;
                    next_count := next_count + 1;
                end if;
                queue_data <= next_queue;
                queue_count <= next_count;
                read_pending <= read_request;
            end if;
        end if;
    end process;

    fifo_rd_en <= read_request;
    m_axis_tdata <= issue_data;
    m_axis_tvalid <= '1' when issue_kind = NONBLOCKING_SET or issue_kind = BLOCKING_SET else '0';
    waitt <= '1' when issue_kind = WAIT_ACK else '0';
end rtl;
