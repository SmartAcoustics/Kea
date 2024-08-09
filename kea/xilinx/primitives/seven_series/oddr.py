from myhdl import block, always, Signal

from kea.xilinx.primitives import myhdl_to_vhdl_primitive_conversion_setup

oddr_block_count = 0

@block
def xil_oddr(
    clock, clock_enable, data_in_0, data_in_1, data_out, reset=None,
    set_high=None):
    ''' This is a block to instantiate a Xilinx ODDR.
    '''

    # NOTE: This block only offers the functionality required at the time it
    # was written. The underlying primitive offers more flexibility in use but
    # this has been left out for simplicity. If it becomes necessary to
    # incorporate this extended functionality, further information can be
    # found in UG471 and UG953.
    #
    # Behaviour not included:
    #     DDR_CLK_EDGE - Inputs can be driven on OPPOSITE_EDGE or SAME_EDGE
    #     INIT - Initial value for data_out
    #     SRTYPE - Set and Reset can be ASYNC or SYNC

    # NOTE on usage: From observation, the data_out signal is held low until
    # clock_enable goes high. When clock_enable goes high, the data_out is
    # driven on the next rising edge of clock. When clock_enable goes low,
    # data_out holds its current value.

    global oddr_block_count

    # Need to specify if the signals are inputs or outputs for the conversion
    clock.read = True
    clock_enable.read = True
    data_in_0.read = True
    data_in_1.read = True
    data_out.driven = 'wire'

    inst_count = oddr_block_count
    oddr_block_count += 1

    if reset is not None and set_high is not None:
        raise ValueError('ODDR can take either a set or a reset signal.')

    elif reset is not None and set_high is None:
        ###################
        # ODDR with reset #
        ###################

        reset.read = True

        # Behavioural model for Myhdl simulations
        # =======================================

        enabled = Signal(False)

        @always(clock.posedge, clock.negedge)
        def oddr_behavioural_model():

            # From observation, the clock_enable rising edge is read on rising
            # edges of the clock
            if clock == True:
                enabled.next = clock_enable

            if clock:
                # On rising edges of clock data_in_0 is forwarded
                if clock_enable:
                    data_out.next = data_in_0

            else:
                # On falling edges of clock data_in_1 is forwarded
                if enabled and clock_enable:
                    data_out.next = data_in_1

            if reset:
                enabled.next = False
                data_out.next = False

        # Verilog instantiation for conversion
        # ====================================
        xil_oddr.verilog_code = """

            // ODDR: Output Double DataRate Output Register with Set, Reset
            //       and Clock Enable.
            //       7Series
            // Xilinx HDL Libraries Guide, version 2012.2

            ODDR #(
                .DDR_CLK_EDGE("SAME_EDGE"), // "OPPOSITE_EDGE" or "SAME_EDGE"
                .INIT(1'b0),    // Initial value of Q: 1'b0 or 1'b1
                .SRTYPE("SYNC") // Set/Reset type:"SYNC"or"ASYNC"
            ) ODDR_inst_$inst_count (
                .Q($data_out),      // 1-bit DDR output
                .C($clock),         // 1-bit clock input
                .CE($clock_enable), // 1-bit clock enable input
                .D1($data_in_0),    // 1-bit data input (positive edge)
                .D2($data_in_1),    // 1-bit data input (negative edge)
                .R($reset),         // 1-bit reset
                .S(1'b0)            // 1-bit set
            );

            // End of ODDR_inst instantiation
        """

        # VHDL instantiation for conversion
        # =================================
        # Add the required VHDL libraries for conversion
        myhdl_to_vhdl_primitive_conversion_setup.update(
            library='UNISIM', use_clauses='UNISIM.vcomponents.all')
        xil_oddr.vhdl_code = """
            -- ODDR: Output Double Data Rate Output Register with Set, Reset
            --       and Clock Enable.
            --       7Series
            -- Xilinx HDL Libraries Guide, version 2012.2

            ODDR_inst_$inst_count: ODDR
            generic map(
                DDR_CLK_EDGE => "SAME_EDGE", -- "OPPOSITE_EDGE" or "SAME_EDGE"
                INIT => '0',      -- Initial value for Q port ('1' or '0')
                SRTYPE => "SYNC") -- Reset Type("ASYNC" or "SYNC")
            port map (
                Q => $data_out,      -- 1-bit DDR output
                C => $clock,         -- 1-bit clock input
                CE => $clock_enable, -- 1-bit clock enable input
                D1 => $data_in_0,    -- 1-bit data input (positive edge)
                D2 => $data_in_1,    -- 1-bit data input (negative edge)
                R => $reset,         -- 1-bit reset input
                S => '0'             -- 1-bit set input
            );

            -- End of ODDR_inst instantiation
        """

    elif reset is None and set_high is not None:
        #################
        # ODDR with set #
        #################

        set_high.read = True

        # Behavioural model for Myhdl simulations
        # =======================================

        enabled = Signal(False)

        @always(clock.posedge, clock.negedge)
        def oddr_behavioural_model():

            # From observation, the clock_enable rising edge is read on rising
            # edges of the clock
            if clock == True:
                enabled.next = clock_enable

            if clock:
                # On rising edges of clock data_in_0 is forwarded
                if clock_enable:
                    data_out.next = data_in_0

            else:
                # On falling edges of clock data_in_1 is forwarded
                if enabled and clock_enable:
                    data_out.next = data_in_1

            if set_high:
                enabled.next = False
                data_out.next = True

        # Verilog instantiation for conversion
        # ====================================
        xil_oddr.verilog_code = """

            // ODDR: Output Double DataRate Output Register with Set, Reset
            //       and Clock Enable.
            //       7Series
            // Xilinx HDL Libraries Guide, version 2012.2

            ODDR #(
                .DDR_CLK_EDGE("SAME_EDGE"), // "OPPOSITE_EDGE" or "SAME_EDGE"
                .INIT(1'b0),    // Initial value of Q: 1'b0 or 1'b1
                .SRTYPE("SYNC") // Set/Reset type:"SYNC"or"ASYNC"
            ) ODDR_inst_$inst_count (
                .Q($data_out),      // 1-bit DDR output
                .C($clock),         // 1-bit clock input
                .CE($clock_enable), // 1-bit clock enable input
                .D1($data_in_0),    // 1-bit data input (positive edge)
                .D2($data_in_1),    // 1-bit data input (negative edge)
                .R(1'b0),           // 1-bit reset
                .S($set_high)       // 1-bit set
            );

            // End of ODDR_inst instantiation
        """

        # VHDL instantiation for conversion
        # =================================
        # Add the required VHDL libraries for conversion
        myhdl_to_vhdl_primitive_conversion_setup.update(
            library='UNISIM', use_clauses='UNISIM.vcomponents.all')
        xil_oddr.vhdl_code = """
            -- ODDR: Output Double Data Rate Output Register with Set, Reset
            --       and Clock Enable.
            --       7Series
            -- Xilinx HDL Libraries Guide, version 2012.2

            ODDR_inst_$inst_count: ODDR
            generic map(
                DDR_CLK_EDGE => "SAME_EDGE", -- "OPPOSITE_EDGE" or "SAME_EDGE"
                INIT => '0',      -- Initial value for Q port ('1' or '0')
                SRTYPE => "SYNC") -- Reset Type("ASYNC" or "SYNC")
            port map (
                Q => $data_out,      -- 1-bit DDR output
                C => $clock,         -- 1-bit clock input
                CE => $clock_enable, -- 1-bit clock enable input
                D1 => $data_in_0,    -- 1-bit data input (positive edge)
                D2 => $data_in_1,    -- 1-bit data input (negative edge)
                R => '0',            -- 1-bit reset input
                S => $set_high       -- 1-bit set input
            );

            -- End of ODDR_inst instantiation
        """

    else:
        raise ValueError('ODDR requires either a set or a reset signal.')

    return oddr_behavioural_model
