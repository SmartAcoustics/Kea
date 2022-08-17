from myhdl import *

from . import myhdl_to_vhdl_primitive_conversion_setup

serdes_block_count = 0

@block
def xil_serdes(
    bit_clock, div_clock, reset, clock_enable, parallel_data_out,
    serial_data_out, serial_data_in, delayed_serial_data_in, data_width=8):
    ''' This is a block to instantiate a basic SERDES block.
    '''

    # NOTE: This block only offers the functionality required at the time it
    # was written. The underlying primitive offers more flexibility in use but
    # this has been left out for simplicity. If it becomes necessary to
    # incorporate this extended functionality, further information can be
    # found in UG471 and UG953.

    global serdes_block_count

    # Need to specify if the signals are inputs or outputs for the conversion
    bit_clock.read = True
    div_clock.read = True
    reset.read = True
    clock_enable.read = True
    parallel_data_out.driven = 'wire'
    serial_data_out.driven = 'wire'
    serial_data_in.read = True
    delayed_serial_data_in.read = True

    inst_count = serdes_block_count
    serdes_block_count += 1

    # Behavioural model for Myhdl simulations
    # =======================================

    shift_reg = [Signal(False) for i in range(data_width)]
    propagation_delay_reg = Signal(intbv(0)[len(parallel_data_out):])

    @always_comb
    def comb_output():
        serial_data_out.next = delayed_serial_data_in

    @always(bit_clock.posedge)
    def bit_clock_behavioural_model():
        if reset:
            for n in range(data_width):
                # Set all values to 0
                shift_reg[n].next = 0
        else:
            if clock_enable:
                for n in range(data_width-1):
                    # Shift all values up the shift register
                    shift_reg[data_width-n-1].next = shift_reg[data_width-n-2]

                shift_reg[0].next = serial_data_in

    @always(div_clock.posedge)
    def div_clock_behavioural_model():
        if reset:
            for n in range(data_width):
                # set all values to 0
                propagation_delay_reg.next[n] = 0
                parallel_data_out.next[n] = 0

        else:
            if clock_enable:
                for n in range(data_width):
                    propagation_delay_reg.next[n] = shift_reg[n]

            # Correctly model the latency of the ISERDES block
            parallel_data_out.next = propagation_delay_reg

    # Verilog instantiation for conversion
    # ====================================
    xil_serdes.verilog_code = """

        // ISERDESE2: Input SERial/DESerializer with bitslip
        //            7 Series
        // Xilinx HDL Libraries Guide, version 2012.2

        ISERDESE2 #(
            .DATA_RATE("SDR"),              // DDR, SDR
            .DATA_WIDTH($data_width),       // Parallel data width (2-8,10,14)
            .DYN_CLKDIV_INV_EN("FALSE"),    // Enable DYNCLKDIVINVSEL inversion (FALSE, TRUE)
            .DYN_CLK_INV_EN("FALSE"),       // Enable DYNCLKINVSEL inversion (FALSE, TRUE)
            .INIT_Q1(1'b0),                 // INIT_Q1 - INIT_Q4: Initial value on the Q outputs (0/1)
            .INIT_Q2(1'b0),
            .INIT_Q3(1'b0),
            .INIT_Q4(1'b0),
            .INTERFACE_TYPE("NETWORKING"),  // MEMORY, MEMORY_DDR3, MEMORY_QDR, NETWORKING, OVERSAMPLE
            .IOBDELAY("IBUF"),              // NONE, BOTH, IBUF, IFD
            .NUM_CE(1),                     // Number of clock enables (1,2)
            .OFB_USED("FALSE"),             // Select OFB path (FALSE, TRUE)
            .SERDES_MODE("MASTER"),         // MASTER, SLAVE
            .SRVAL_Q1(1'b0),                // SRVAL_Q1 - SRVAL_Q8: Q output values when SR is used (0/1)
            .SRVAL_Q2(1'b0),
            .SRVAL_Q3(1'b0),
            .SRVAL_Q4(1'b0)
        ) ISERDESE2_inst_$inst_count (
            .O($serial_data_out),           // 1-bit output: Combinatorial output
            .Q1($parallel_data_out[0]),     // Q1 - Q4: 1-bit (each) output: Registered data outputs
            .Q2($parallel_data_out[1]),
            .Q3($parallel_data_out[2]),
            .Q4($parallel_data_out[3]),
            .Q5($parallel_data_out[4]),
            .Q6($parallel_data_out[5]),
            .Q7($parallel_data_out[6]),
            .Q8($parallel_data_out[7]),
            .SHIFTOUT1(),                   // SHIFTOUT1-SHIFTOUT2: 1-bit (each) output: Data width expansion output ports
            .SHIFTOUT2(),
            .BITSLIP(1'b0),                 // 1-bit input: The BITSLIP pin performs a Bitslip operation synchronous to
                                            // CLKDIV when asserted (active High). Subsequently, the data seen on the Q1
                                            // to Q8 output ports will shift, as in a barrel-shifter operation, one
                                            // position every time Bitslip is invoked (DDR operation is different from
                                            // SDR).
            .CE1($clock_enable),            // CE1, CE2: 1-bit (each) input: Data register clock enable inputs
            .CE2(1'b0),
            .CLKDIVP(1'b0),                 // 1-bit input: TBD
            .CLK($bit_clock),               // 1-bit input: High-speed clock
            .CLKB(!$bit_clock),             // 1-bit input: High-speed secondary clock
            .CLKDIV($div_clock),            // 1-bit input: Divided clock
            .OCLK(1'b0),                    // 1-bit input: High speed output clock used when INTERFACE_TYPE="MEMORY"
            .DYNCLKDIVSEL(1'b0),            // 1-bit input: Dynamic CLKDIV inversion
            .DYNCLKSEL(1'b0),               // 1-bit input: Dynamic CLK/CLKB inversion
            .D($serial_data_in),            // 1-bit input: Data input
            .DDLY($delayed_serial_data_in), // 1-bit input: Serial data from IDELAYE2
            .OFB(1'b0),                     // 1-bit input: Data feedback from OSERDESE2
            .OCLKB(1'b0),                   // 1-bit input: High speed negative edge output clock
            .RST($reset),                   // 1-bit input: Active high asynchronous reset
            .SHIFTIN1(1'b0),                // SHIFTIN1-SHIFTIN2: 1-bit (each) input: Data width expansion input ports
            .SHIFTIN2(1'b0)
        );

        // End of ISERDESE2_inst instantiation
        """

    # VHDL instantiation for conversion
    # =================================
    # Add the required VHDL libraries for conversion
    myhdl_to_vhdl_primitive_conversion_setup.update(
        library='UNISIM', use_clauses='UNISIM.vcomponents.all')
    xil_serdes.vhdl_code = """
        --ISERDESE2: Input SERial/DESerializer with bitslip
        --           7 Series
        -- Xilinx HDL Libraries Guide, version 2012.3

        ISERDESE2_inst_$inst_count : ISERDESE2
        generic map (
            DATA_RATE => "SDR",              -- DDR, SDR
            DATA_WIDTH => $data_width,       -- Parallel data width (2-8,10,14)
            DYN_CLKDIV_INV_EN => "FALSE",    -- Enable DYNCLKDIVINVSEL inversion (FALSE, TRUE)
            DYN_CLK_INV_EN => "FALSE",       -- Enable DYNCLKINVSEL inversion (FALSE, TRUE)
            INIT_Q1 => '0',                  -- INIT_Q1 - INIT_Q4: Initial value on the Q outputs (0/1)
            INIT_Q2 => '0',
            INIT_Q3 => '0',
            INIT_Q4 => '0',
            INTERFACE_TYPE => "NETWORKING",  -- MEMORY, MEMORY_DDR3, MEMORY_QDR, NETWORKING, OVERSAMPLE
            IOBDELAY => "IBUF",              -- NONE, BOTH, IBUF, IFD
            NUM_CE => 1,                     -- Number of clock enables (1,2)
            OFB_USED => "FALSE",             -- Select OFB path (FALSE, TRUE)
            SERDES_MODE => "MASTER",         -- MASTER, SLAVE
            SRVAL_Q1 => '0',                 -- SRVAL_Q1 - SRVAL_Q4: Q output values when SR is used (0/1)
            SRVAL_Q2 => '0',
            SRVAL_Q3 => '0',
            SRVAL_Q4 => '0'
            )
        port map (
            O => $serial_data_out,           -- 1-bit output: Combinatorial output
            Q1 => $parallel_data_out(0),     -- Q1 - Q8: 1-bit (each) output: Registered data outputs
            Q2 => $parallel_data_out(1),
            Q3 => $parallel_data_out(2),
            Q4 => $parallel_data_out(3),
            Q5 => $parallel_data_out(4),
            Q6 => $parallel_data_out(5),
            Q7 => $parallel_data_out(6),
            Q8 => $parallel_data_out(7),
            SHIFTOUT1 => open,               -- SHIFTOUT1-SHIFTOUT2: 1-bit (each) output: Data width expansion output ports
            SHIFTOUT2 => open,
            BITSLIP => '0',                  -- 1-bit input: The BITSLIP pin performs a Bitslip operation synchronous to
                                             -- CLKDIV when asserted (active High). Subsequently, the data seen on the Q1
                                             -- to Q8 output ports will shift, as in a barrel-shifter operation, one
                                             -- position every time Bitslip is invoked (DDR operation is different from
                                             -- SDR).
            CE1 => $clock_enable,            -- CE1, CE2: 1-bit (each) input: Data register clock enable inputs
            CE2 => '0',
            CLKDIVP => '0',                  -- 1-bit input: TBD
            CLK => $bit_clock,               -- 1-bit input: High-speed clock
            CLKB => not($bit_clock),         -- 1-bit input: High-speed secondary clock
            CLKDIV => $div_clock,            -- 1-bit input: Divided clock
            OCLK => '0',                     -- 1-bit input: High speed output clock used when INTERFACE_TYPE="MEMORY"
            DYNCLKDIVSEL => '0',             -- 1-bit input: Dynamic CLKDIV inversion
            DYNCLKSEL => '0',                -- 1-bit input: Dynamic CLK/CLKB inversion
            D => $serial_data_in,            -- 1-bit input: Data input
            DDLY => $delayed_serial_data_in, -- 1-bit input: Serial data from IDELAYE2
            OFB => '0',                      -- 1-bit input: Data feedback from OSERDESE2
            OCLKB => '0',                    -- 1-bit input: High speed negative edge output clock
            RST => $reset,                   -- 1-bit input: Active high asynchronous reset
            SHIFTIN1 => '0',
            SHIFTIN2 => '0'
            );

        -- End of ISERDESE2_inst instantiation
        """

    return (
        comb_output, bit_clock_behavioural_model, div_clock_behavioural_model)
