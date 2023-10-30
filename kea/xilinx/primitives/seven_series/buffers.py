from myhdl import *

from kea.xilinx.primitives import myhdl_to_vhdl_primitive_conversion_setup

ibufds_block_count = 0

@block
def xil_ibufds(in_p, in_n, signal_out):
    ''' This is a block to instantiate an IBUFDS.
    '''
    global ibufds_block_count

    # Need to specify if the signals are inputs or outputs for the conversion
    in_p.read = True
    in_n.read = True
    signal_out.driven = 'wire'

    inst_count = ibufds_block_count
    ibufds_block_count += 1

    # Behavioural model for Myhdl simulations
    # =======================================
    @always_comb
    def behavioural_model():

        if in_p and not in_n:
            signal_out.next = True
        elif in_n and not in_p:
            signal_out.next = False
        else:
            pass

    # Verilog instantiation for conversion
    # ====================================
    xil_ibufds.verilog_code = """
        // IBUFDS: Differential Input Buffer
        //         7 Series
        // Xilinx HDL Libraries Guide, version 2012.3

        IBUFDS #(
            .DIFF_TERM("FALSE"),   // Differential Termination
            .IBUF_LOW_PWR("TRUE"), // Low power="TRUE", Highest performance="FALSE"
            .IOSTANDARD("LVDS")    // Specify the input I/O standard
        ) IBUFDS_inst_$inst_count (
            .O($signal_out),       // Buffer output
            .I($in_p),             // Diff_p buffer input (connect directly to top-level port)
            .IB($in_n)             // Diff_n buffer input (connect directly to top-level port)
        );

        // End of IBUFDS_inst instantiation
        """

    # VHDL instantiation for conversion
    # =================================
    # Add the required VHDL libraries for conversion
    myhdl_to_vhdl_primitive_conversion_setup.update(
        library='UNISIM', use_clauses='UNISIM.vcomponents.all')
    xil_ibufds.vhdl_code = """
        -- IBUFDS: Differential Input Buffer
        --         7 Series
        -- Xilinx HDL Libraries Guide, version 2012.3

        IBUFDS_inst_$inst_count : IBUFDS
        generic map (
            DIFF_TERM => FALSE,        -- Differential Termination
            IBUF_LOW_PWR => TRUE,      -- Low power (TRUE) vs. performance (FALSE) setting for referenced I/O standards
            IOSTANDARD => "LVDS")
        port map (
            O => $signal_out,          -- Buffer output
            I => $in_p,                -- Diff_p buffer input (connect directly to top-level port)
            IB => $in_n                -- Diff_n buffer input (connect directly to top-level port)
        );

        -- End of IBUFDS_inst instantiation
        """

    return behavioural_model

bufio_block_count = 0

@block
def xil_bufio(clock_in, clock_out):
    ''' This is a block to instantiate a BUFIO.
    '''
    global bufio_block_count

    # Need to specify if the signals are inputs or outputs for the conversion
    clock_in.read = True
    clock_out.driven = 'wire'

    inst_count = bufio_block_count
    bufio_block_count += 1

    # Behavioural model for Myhdl simulations
    # =======================================
    @always_comb
    def behavioural_model():

        clock_out.next = clock_in

    # Verilog instantiation for conversion
    # ====================================
    xil_bufio.verilog_code = """
        // BUFIO: Local Clock Buffer for I/O
        //        7 Series
        // Xilinx HDL Libraries Guide, version 2012.3

        BUFIO BUFIO_inst_$inst_count (
            .O($clock_out),  // 1-bit output: Clock output (connect to I/O clock loads).
            .I($clock_in)    // 1-bit input: Clock input (connect to an IBUFG or BUFMR).
        );

        // End of BUFIO_inst instantiation
        """

    # VHDL instantiation for conversion
    # =================================
    # Add the required VHDL libraries for conversion
    myhdl_to_vhdl_primitive_conversion_setup.update(
        library='UNISIM', use_clauses='UNISIM.vcomponents.all')
    xil_bufio.vhdl_code = """
        -- BUFIO: Local Clock Buffer for I/O
        --        7 Series
        -- Xilinx HDL Libraries Guide, version 2012.3

        BUFIO_inst_$inst_count : BUFIO
        port map (
            O => $clock_out, -- 1-bit output: Clock output (connect to I/O clock loads).
            I => $clock_in   -- 1-bit input: Clock input (connect to an IBUFG or BUFMR).
        );

        -- End of BUFIO_inst instantiation
        """

    return behavioural_model

bufr_block_count = 0

@block
def xil_bufr(clock_in, clock_out, clear, divide_by=8, clock_in_period=2285):
    ''' This is a block to instantiate a BUFR.

    Clock_out frequency is the clock_in frequency divided by `divide_by`.

    Clear holds the output clock low.

    Clock_in_period gives this block the period of the clock_in.

    This block has a startup up period of 100,000ps.

    This block expects `time_units='ps'` in the cosimulate call.
    '''
    global bufr_block_count

    # Need to specify if the signals are inputs or outputs for the conversion
    clock_in.read = True
    clear.read = True
    clock_out.driven = 'wire'

    inst_count = bufr_block_count
    bufr_block_count += 1

    # Behavioural model for Myhdl simulations
    # =======================================
    count = Signal(intbv(0, 0, divide_by+1))
    internal_clock = Signal(False)

    # The BUFR primitive has a startup period of 100ns
    startup_period = 100000
    startup_ncycles = startup_period/clock_in_period
    startup_complete = Signal(False)
    startup_count = Signal(intbv(0, 0, startup_ncycles+1))

    half_cycle = int(divide_by/2)
    full_cycle = divide_by

    @always(clock_in.posedge)
    def divider():

        if startup_count < startup_ncycles-1:
            # Count the startup period
            startup_count.next = startup_count + 1
        else:
            startup_complete.next = True

        if not startup_complete or clear:
            count.next = 0
            internal_clock.next = False

        else:
            if count == 0:
                internal_clock.next = True
                count.next = count+1
            elif count==half_cycle:
                internal_clock.next = False
                count.next = count+1
            elif count==full_cycle-1:
                count.next = 0
            else:
                count.next = count + 1

    @always_comb
    def signal_assignment():
        clock_out.next = internal_clock

    # Verilog instantiation for conversion
    # ====================================
    xil_bufr.verilog_code = """
        // BUFR: Regional Clock Buffer for I/O and Logic Resources within a Clock Region
        //       7 Series
        // Xilinx HDL Libraries Guide, version 2012.3

        BUFR #(
            .BUFR_DIVIDE("$divide_by"), // Values: "BYPASS, 1, 2, 3, 4, 5, 6, 7, 8"
            .SIM_DEVICE("7SERIES")      // Must be set to "7SERIES"
        ) BUFR_inst_$inst_count (
            .O($clock_out),             // 1-bit output: Clock output port
            .CE(1'b1),                  // 1-bit input: Active high, clock enable (Divided modes only)
            .CLR($clear),               // 1-bit input: Active high, asynchronous clear (Divided modes only)
            .I($clock_in)               // 1-bit input: Clock buffer input driven by an IBUFG, MMCM or local interconnect
        );

        // End of BUFR_inst instantiation
        """

    # VHDL instantiation for conversion
    # =================================
    # Add the required VHDL libraries for conversion
    myhdl_to_vhdl_primitive_conversion_setup.update(
        library='UNISIM', use_clauses='UNISIM.vcomponents.all')
    xil_bufr.vhdl_code = """
        -- BUFR: Regional Clock Buffer for I/O and Logic Resources within a Clock Region
        --       7 Series
        -- Xilinx HDL Libraries Guide, version 2012.3

        BUFR_inst_$inst_count : BUFR
        generic map (
            BUFR_DIVIDE => "$divide_by", -- Values: "BYPASS, 1, 2, 3, 4, 5, 6, 7, 8"
            SIM_DEVICE => "7SERIES"      -- Must be set to "7SERIES"
            )
        port map (
            O => $clock_out, -- 1-bit output: Clock output port
            CE => '1',       -- 1-bit input: Active high, clock enable (Divided modes only)
            CLR => $clear,   -- 1-bit input: Active high, asynchronous clear (Divided modes only)
            I => $clock_in   -- 1-bit input: Clock buffer input driven by an IBUFG, MMCM or local interconnect
            );

        -- End of BUFR_inst instantiation
        """

    return divider, signal_assignment

bufmr_block_count = 0

@block
def xil_bufmr(clock_in, clock_out):
    ''' This is a block to instantiate a BUFMR.
    '''
    global bufmr_block_count

    # Need to specify if the signals are inputs or outputs for the conversion
    clock_in.read = True
    clock_out.driven = 'wire'

    inst_count = bufmr_block_count
    bufmr_block_count += 1

    # Behavioural model for Myhdl simulations
    # =======================================
    @always_comb
    def behavioural_model():

        clock_out.next = clock_in

    # Verilog instantiation for conversion
    # ====================================
    xil_bufmr.verilog_code = """
        // BUFMR: Multi-Region Clock Buffer
        //        7 Series
        // Xilinx HDL Libraries Guide, version 2012.3

        BUFMR BUFMR_inst_$inst_count (
            .O($clock_out),  // 1-bit output: Clock output (connect to BUFIOs/BUFRs).
            .I($clock_in)    // 1-bit input: Clock input (connect to IBUFG).
        );

        // End of BUFMR_inst instantiation
        """

    # VHDL instantiation for conversion
    # =================================
    # Add the required VHDL libraries for conversion
    myhdl_to_vhdl_primitive_conversion_setup.update(
        library='UNISIM', use_clauses='UNISIM.vcomponents.all')
    xil_bufmr.vhdl_code = """
        -- BUFMR: Multi-Region Clock Buffer
        --        7 Series
        -- Xilinx HDL Libraries Guide, version 2012.3

        BUFMR_inst_$inst_count : BUFMR
        port map (
            O => $clock_out, -- 1-bit output: Clock output (connect to BUFIOs/BUFRs).
            I => $clock_in   -- 1-bit input: Clock input (connect to IBUFG).
        );

        -- End of BUFMR_inst instantiation
        """

    return behavioural_model

iobuf_block_count = 0

@block
def xil_iobuf(ts_wr, ts_rd, ts_t, ts_io):
    ''' This is a block to instantiate an IOBUF.
    '''
    global iobuf_block_count

    # Need to specify if the signals are inputs or outputs for the conversion
    ts_wr.read = True
    ts_t.read = True
    ts_rd.driven = 'wire'

    ts_io.read = True
    ts_io.driven = 'wire'

    inst_count = iobuf_block_count
    iobuf_block_count += 1

    # Behavioural model for Myhdl simulations
    # =======================================
    ts_io_driver = ts_io.driver()

    @always_comb
    def behavioural_model():

        if ts_io:
            ts_rd.next = True

        else:
            ts_rd.next = False

        if ts_t:
            ts_io_driver.next = None

        else:
            ts_io_driver.next = ts_wr

    # Verilog instantiation for conversion
    # ====================================
    xil_iobuf.verilog_code = """
        // IOBUF: Single-ended Bi-directional Buffer
        // All devices
        // Xilinx HDL Libraries Guide, version 2012.2

        IOBUF #(
            .DRIVE(12),             // Specify the output drive strength
            .IBUF_LOW_PWR("TRUE"),  // Low Power - "TRUE", High Perforrmance = "FALSE"
            .IOSTANDARD("DEFAULT"), // Specify the I/O standard
            .SLEW("SLOW")           // Specify the output slew rate
        ) IOBUF_inst_$inst_count (
            .O($ts_rd),             // Buffer output
            .IO($ts_io),            // Buffer inout port (connect directly to top-level port)
            .I($ts_wr),             // Buffer input
            .T($ts_t)               // 3-state enable input, high=input, low=output
        );

        // End of IOBUF_inst instantiation
        """

    # VHDL instantiation for conversion
    # =================================
    # Add the required VHDL libraries for conversion
    myhdl_to_vhdl_primitive_conversion_setup.update(
        library='UNISIM', use_clauses='UNISIM.vcomponents.all')
    xil_iobuf.vhdl_code = """
        -- IOBUF: Single-ended Bi-directional Buffer
        -- 7 Series
        -- Xilinx HDL Libraries Guide, version 2012.2

        IOBUF_inst_$inst_count : IOBUF
        generic map (
            DRIVE => 12,
            IOSTANDARD => "DEFAULT",
            SLEW => "SLOW")
        port map (
            O => $ts_rd,  -- Buffer output
            IO => $ts_io, -- Buffer inout port (connect directly to top-level port)
            I => $ts_wr,  -- Buffer input
            T => $ts_t    -- 3-state enable input, high=input, low=output
        );

        -- End of IOBUF_inst instantiation
        """

    return behavioural_model
