-- Authors: Jeonghyun Park (jeonghyun.park@ubc.ca or alexist@snu.ac.kr), Farbod
-- AXI-Lite register map for axis_avg_buffer v1.3.
--
-- reg0  0x00 AVG_START_REG
--       bit 0: enable AVG path
--       bit 1: trace accumulation mode
--       bits 31:16 are reserved in v1.3; trace repetition count is reg16.
-- reg1  0x04 AVG_ADDR_REG
-- reg2  0x08 AVG_LEN_REG
--       Number of stored output points. Input samples consumed per trigger are
--       AVG_LEN_REG * effective(AVG_ACCUM_LEN_REG).
-- reg3  0x0c AVG_DR_START_REG
-- reg4  0x10 AVG_DR_ADDR_REG
-- reg5  0x14 AVG_DR_LEN_REG
-- reg6  0x18 BUF_START_REG
-- reg7  0x1c BUF_ADDR_REG
-- reg8  0x20 BUF_LEN_REG
-- reg9  0x24 BUF_DR_START_REG
-- reg10 0x28 BUF_DR_ADDR_REG
-- reg11 0x2c BUF_DR_LEN_REG
-- reg12 0x30 AVG_PHOTON_MODE_REG
-- reg13 0x34 AVG_H_THRSH_REG
-- reg14 0x38 AVG_L_THRSH_REG
-- reg15 0x3c AVG_ACCUM_LEN_REG[23:0], effective M = 1 for values 0 or 1
-- reg16 0x40 AVG_TRACE_REPS_REG[23:0], effective R = 1 for value 0
--       Upper bits of reg15/reg16 are forced to zero on write/read.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity axi_slv_avg_buf is
    generic (
        DATA_WIDTH : integer := 32;
        ADDR_WIDTH : integer := 7
    );
    port (
        aclk    : in  std_logic;
        aresetn : in  std_logic;

        awaddr  : in  std_logic_vector(ADDR_WIDTH-1 downto 0);
        awprot  : in  std_logic_vector(2 downto 0);
        awvalid : in  std_logic;
        awready : out std_logic;

        wdata   : in  std_logic_vector(DATA_WIDTH-1 downto 0);
        wstrb   : in  std_logic_vector((DATA_WIDTH/8)-1 downto 0);
        wvalid  : in  std_logic;
        wready  : out std_logic;

        bresp   : out std_logic_vector(1 downto 0);
        bvalid  : out std_logic;
        bready  : in  std_logic;

        araddr  : in  std_logic_vector(ADDR_WIDTH-1 downto 0);
        arprot  : in  std_logic_vector(2 downto 0);
        arvalid : in  std_logic;
        arready : out std_logic;

        rdata   : out std_logic_vector(DATA_WIDTH-1 downto 0);
        rresp   : out std_logic_vector(1 downto 0);
        rvalid  : out std_logic;
        rready  : in  std_logic;

        AVG_START_REG      : out std_logic_vector(31 downto 0);
        AVG_ADDR_REG       : out std_logic_vector(31 downto 0);
        AVG_LEN_REG        : out std_logic_vector(31 downto 0);
        AVG_PHOTON_MODE_REG: out std_logic;
        AVG_H_THRSH_REG    : out std_logic_vector(31 downto 0);
        AVG_L_THRSH_REG    : out std_logic_vector(31 downto 0);
        AVG_ACCUM_LEN_REG  : out std_logic_vector(23 downto 0);
        AVG_TRACE_REPS_REG : out std_logic_vector(23 downto 0);
        AVG_DR_START_REG   : out std_logic;
        AVG_DR_ADDR_REG    : out std_logic_vector(31 downto 0);
        AVG_DR_LEN_REG     : out std_logic_vector(31 downto 0);
        BUF_START_REG      : out std_logic;
        BUF_ADDR_REG       : out std_logic_vector(31 downto 0);
        BUF_LEN_REG        : out std_logic_vector(31 downto 0);
        BUF_DR_START_REG   : out std_logic;
        BUF_DR_ADDR_REG    : out std_logic_vector(31 downto 0);
        BUF_DR_LEN_REG     : out std_logic_vector(31 downto 0)
    );
end axi_slv_avg_buf;

architecture rtl of axi_slv_avg_buf is
    constant ADDR_LSB      : integer := (DATA_WIDTH/32) + 1;
    constant REG_ADDR_BITS : integer := 5;
    constant NUM_REGS      : integer := 17;

    type reg_array_t is array (0 to NUM_REGS-1) of std_logic_vector(DATA_WIDTH-1 downto 0);

    signal axi_awaddr  : std_logic_vector(ADDR_WIDTH-1 downto 0);
    signal axi_awready : std_logic;
    signal axi_wready  : std_logic;
    signal axi_bresp   : std_logic_vector(1 downto 0);
    signal axi_bvalid  : std_logic;
    signal axi_araddr  : std_logic_vector(ADDR_WIDTH-1 downto 0);
    signal axi_arready : std_logic;
    signal axi_rdata   : std_logic_vector(DATA_WIDTH-1 downto 0);
    signal axi_rresp   : std_logic_vector(1 downto 0);
    signal axi_rvalid  : std_logic;

    signal slv_regs     : reg_array_t := (others => (others => '0'));
    signal slv_reg_rden : std_logic;
    signal slv_reg_wren : std_logic;
    signal reg_data_out : std_logic_vector(DATA_WIDTH-1 downto 0);
    signal aw_en        : std_logic;
begin

    awready <= axi_awready;
    wready  <= axi_wready;
    bresp   <= axi_bresp;
    bvalid  <= axi_bvalid;
    arready <= axi_arready;
    rdata   <= axi_rdata;
    rresp   <= axi_rresp;
    rvalid  <= axi_rvalid;

    process (aclk)
    begin
        if rising_edge(aclk) then
            if aresetn = '0' then
                axi_awready <= '0';
                aw_en       <= '1';
            else
                if axi_awready = '0' and awvalid = '1' and wvalid = '1' and aw_en = '1' then
                    axi_awready <= '1';
                    aw_en       <= '0';
                elsif bready = '1' and axi_bvalid = '1' then
                    aw_en       <= '1';
                    axi_awready <= '0';
                else
                    axi_awready <= '0';
                end if;
            end if;
        end if;
    end process;

    process (aclk)
    begin
        if rising_edge(aclk) then
            if aresetn = '0' then
                axi_awaddr <= (others => '0');
            else
                if axi_awready = '0' and awvalid = '1' and wvalid = '1' and aw_en = '1' then
                    axi_awaddr <= awaddr;
                end if;
            end if;
        end if;
    end process;

    process (aclk)
    begin
        if rising_edge(aclk) then
            if aresetn = '0' then
                axi_wready <= '0';
            else
                if axi_wready = '0' and wvalid = '1' and awvalid = '1' and aw_en = '1' then
                    axi_wready <= '1';
                else
                    axi_wready <= '0';
                end if;
            end if;
        end if;
    end process;

    slv_reg_wren <= axi_wready and wvalid and axi_awready and awvalid;

    process (aclk)
        variable loc_addr : integer;
    begin
        if rising_edge(aclk) then
            if aresetn = '0' then
                slv_regs <= (others => (others => '0'));
            else
                loc_addr := to_integer(unsigned(axi_awaddr(ADDR_LSB + REG_ADDR_BITS - 1 downto ADDR_LSB)));
                if slv_reg_wren = '1' and loc_addr < NUM_REGS then
                    for byte_index in 0 to (DATA_WIDTH/8 - 1) loop
                        if wstrb(byte_index) = '1' then
                            slv_regs(loc_addr)(byte_index*8+7 downto byte_index*8) <=
                                wdata(byte_index*8+7 downto byte_index*8);
                        end if;
                    end loop;
                    if loc_addr = 15 or loc_addr = 16 then
                        slv_regs(loc_addr)(DATA_WIDTH-1 downto 24) <= (others => '0');
                    end if;
                end if;
            end if;
        end if;
    end process;

    process (aclk)
    begin
        if rising_edge(aclk) then
            if aresetn = '0' then
                axi_bvalid <= '0';
                axi_bresp  <= "00";
            else
                if axi_awready = '1' and awvalid = '1' and axi_wready = '1' and
                   wvalid = '1' and axi_bvalid = '0' then
                    axi_bvalid <= '1';
                    axi_bresp  <= "00";
                elsif bready = '1' and axi_bvalid = '1' then
                    axi_bvalid <= '0';
                end if;
            end if;
        end if;
    end process;

    process (aclk)
    begin
        if rising_edge(aclk) then
            if aresetn = '0' then
                axi_arready <= '0';
                axi_araddr  <= (others => '0');
            else
                if axi_arready = '0' and arvalid = '1' then
                    axi_arready <= '1';
                    axi_araddr  <= araddr;
                else
                    axi_arready <= '0';
                end if;
            end if;
        end if;
    end process;

    process (aclk)
    begin
        if rising_edge(aclk) then
            if aresetn = '0' then
                axi_rvalid <= '0';
                axi_rresp  <= "00";
            else
                if axi_arready = '1' and arvalid = '1' and axi_rvalid = '0' then
                    axi_rvalid <= '1';
                    axi_rresp  <= "00";
                elsif axi_rvalid = '1' and rready = '1' then
                    axi_rvalid <= '0';
                end if;
            end if;
        end if;
    end process;

    slv_reg_rden <= axi_arready and arvalid and (not axi_rvalid);

    process (slv_regs, axi_araddr)
        variable loc_addr : integer;
    begin
        loc_addr := to_integer(unsigned(axi_araddr(ADDR_LSB + REG_ADDR_BITS - 1 downto ADDR_LSB)));
        if loc_addr < NUM_REGS then
            reg_data_out <= slv_regs(loc_addr);
        else
            reg_data_out <= (others => '0');
        end if;
    end process;

    process (aclk)
    begin
        if rising_edge(aclk) then
            if aresetn = '0' then
                axi_rdata <= (others => '0');
            else
                if slv_reg_rden = '1' then
                    axi_rdata <= reg_data_out;
                end if;
            end if;
        end if;
    end process;

    AVG_START_REG       <= slv_regs(0);
    AVG_ADDR_REG        <= slv_regs(1);
    AVG_LEN_REG         <= slv_regs(2);
    AVG_DR_START_REG    <= slv_regs(3)(0);
    AVG_DR_ADDR_REG     <= slv_regs(4);
    AVG_DR_LEN_REG      <= slv_regs(5);
    BUF_START_REG       <= slv_regs(6)(0);
    BUF_ADDR_REG        <= slv_regs(7);
    BUF_LEN_REG         <= slv_regs(8);
    BUF_DR_START_REG    <= slv_regs(9)(0);
    BUF_DR_ADDR_REG     <= slv_regs(10);
    BUF_DR_LEN_REG      <= slv_regs(11);
    AVG_PHOTON_MODE_REG <= slv_regs(12)(0);
    AVG_H_THRSH_REG     <= slv_regs(13);
    AVG_L_THRSH_REG     <= slv_regs(14);
    AVG_ACCUM_LEN_REG   <= slv_regs(15)(23 downto 0);
    AVG_TRACE_REPS_REG  <= slv_regs(16)(23 downto 0);

end rtl;
