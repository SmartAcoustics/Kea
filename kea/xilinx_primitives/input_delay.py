import collections

from myhdl import *

from . import myhdl_to_vhdl_primitive_conversion_setup

input_delay_block_count = 0

@block
def xil_input_delay(
    clock, load_tap_value, enable_delay_change, increase_delay, tap_value,
    data_in, data_out, current_tap_value, delay_period=78,
    n_iodelay_group=0):
    ''' This is a block to instantiate a basic IDELAYE2 block. This block will
    instantiate an IDELAYE2 block in clock mode.

    This block expects `time_units='ps'` in the cosimulate call.
    '''

    # NOTE: This block only offers the functionality required at the time it
    # was written. The underlying primitive offers more flexibility in use but
    # this has been left out for simplicity. If it becomes necessary to
    # incorporate this extended functionality, further information can be
    # found in UG471 and UG953.

    global input_delay_block_count

    # Need to specify if the signals are inputs or outputs for the conversion
    clock.read = True
    load_tap_value.read = True
    enable_delay_change.read = True
    increase_delay.read = True
    tap_value.read = True
    data_in.read = True
    data_out.driven = 'wire'
    current_tap_value.driven = 'wire'

    inst_count = input_delay_block_count
    input_delay_block_count += 1

    # Behavioural model for Myhdl simulations
    # =======================================
    n_delay_taps = 32
    tap_index = Signal(modbv(0, 0, n_delay_taps))
    fixed_delay_tap_index = Signal(modbv(0, 0, n_delay_taps))

    rising_edge = Signal(False)
    falling_edge = Signal(False)

    # The IDELAYE2 block has a fixed delay of 600ps
    fixed_delay = 600

    delay_pipeline_length = n_delay_taps*delay_period+fixed_delay+1
    delay_pipeline = collections.deque(
        [False]*delay_pipeline_length, delay_pipeline_length)

    @always(clock.posedge)
    def behavioural_model():
        if load_tap_value:
            # Load the set tap value
            tap_index.next = tap_value

        elif enable_delay_change:
            # The delay change is enabled
            if increase_delay:
                # Delay change is positive therefore increase the delay
                tap_index.next =  tap_index + 1
            else:
                # Delay change is negative therefore decrease the delay
                tap_index.next =  tap_index - 1

    @always_comb
    def signal_assignment():
        current_tap_value.next = tap_index

    @instance
    def tap_index_model():
        while True:
            # The IDELAYE2 block has a 600ps propagation time after the tap
            # index is set before the output responds.
            yield(tap_index)
            # -1 is necessary to account for the propagation delay
            yield(delay(fixed_delay-1))
            fixed_delay_tap_index.next = tap_index

    @instance
    def pipeline_model():
        while True:
            # Load data_in into data pipeline
            delay_pipeline.appendleft(data_in.val)
            # Output the value at the correct tap. -1 is necessary to account
            # for propagation delay
            data_out.next = delay_pipeline[
                fixed_delay_tap_index*delay_period+fixed_delay-1]
            yield(delay(1))

    # Verilog instantiation for conversion
    # ====================================
    xil_input_delay.verilog_code = """
        // IDELAYE2: Input Fixed or Variable Delay Element
        //           7 Series
        // Xilinx HDL Libraries Guide, version 2012.2

        (* IODELAY_GROUP = "iodelay_group_$n_iodelay_group" *) // Specifies group name for associated IDELAYs/ODELAYs and IDELAYCTRL

        IDELAYE2 #(
            .CINVCTRL_SEL("FALSE"),             // Enable dynamic clock inversion (FALSE, TRUE)
            .DELAY_SRC("IDATAIN"),              // Delay input (IDATAIN, DATAIN)
            .HIGH_PERFORMANCE_MODE("TRUE"),     // Reduced jitter ("TRUE"), Reduced power ("FALSE")
            .IDELAY_TYPE("VAR_LOAD"),           // FIXED, VARIABLE, VAR_LOAD, VAR_LOAD_PIPE
            .IDELAY_VALUE(0),                   // Input delay tap setting (0-31)
            .PIPE_SEL("FALSE"),                 // Select pipelined mode, FALSE, TRUE
            .REFCLK_FREQUENCY(200.0),           // IDELAYCTRL clock input frequency in MHz (190.0-210.0).
            .SIGNAL_PATTERN("CLOCK")            // DATA, CLOCK input signal
        ) IDELAYE2_inst_$inst_count (
            .CNTVALUEOUT($current_tap_value),   // 5-bit output: Counter value output
            .DATAOUT($data_out),                // 1-bit output: Delayed data output
            .C($clock),                         // 1-bit input: Clock input
            .CE($enable_delay_change),          // 1-bit input: Active high enable increment/decrement input
            .CINVCTRL(1'b0),                    // 1-bit input: Dynamic clock inversion input
            .CNTVALUEIN($tap_value),            // 5-bit input: Counter value input
            .DATAIN(1'b0),                      // 1-bit input: Internal delay data input
            .IDATAIN($data_in),                 // 1-bit input: Data input from the I/O
            .INC($increase_delay),              // 1-bit input: Increment / Decrement tap delay input
            .LD($load_tap_value),               // 1-bit input: Load IDELAY_VALUE input or CNTVALUEIN input
            .LDPIPEEN(1'b0),                    // 1-bit input: Enable PIPELINE register to load data input
            .REGRST(1'b0)                       // 1-bit input: Active-high reset tap-delay input
        );

        // End of IDELAYE2_inst instantiation
    """

    # VHDL instantiation for conversion
    # =================================
    # Add the required VHDL libraries for conversion
    myhdl_to_vhdl_primitive_conversion_setup.update(
        library='UNISIM', use_clauses='UNISIM.vcomponents.all')
    xil_input_delay.vhdl_code = """
        -- IDELAYE2: Input Fixed or Variable Delay Element
        --           7 Series
        -- Xilinx HDL Libraries Guide, version 2012.3

        IDELAYE2_inst_$inst_count : IDELAYE2
        generic map (
            CINVCTRL_SEL => "FALSE",          -- Enable dynamic clock inversion (FALSE, TRUE)
            DELAY_SRC => "IDATAIN",           -- Delay input (IDATAIN, DATAIN)
            HIGH_PERFORMANCE_MODE => "TRUE",  -- Reduced jitter ("TRUE"), Reduced power ("FALSE")
            IDELAY_TYPE => "VAR_LOAD",        -- FIXED, VARIABLE, VAR_LOAD, VAR_LOAD_PIPE
            IDELAY_VALUE => 0,                -- Input delay tap setting (0-31)
            PIPE_SEL => "FALSE",              -- Select pipelined mode, FALSE, TRUE
            REFCLK_FREQUENCY => 200.0,        -- IDELAYCTRL clock input frequency in MHz (190.0-210.0).
            SIGNAL_PATTERN => "CLOCK"         -- DATA, CLOCK input signal
            )
        port map (
            unsigned(CNTVALUEOUT) => $current_tap_value, -- 5-bit output: Counter value output
            DATAOUT => $data_out,                        -- 1-bit output: Delayed data output
            C => $clock,                                 -- 1-bit input: Clock input
            CE => $enable_delay_change,                  -- 1-bit input: Active high enable increment/decrement input
            CINVCTRL => '0',                             -- 1-bit input: Dynamic clock inversion input
            CNTVALUEIN => std_logic_vector($tap_value),  -- 5-bit input: Counter value input
            DATAIN => '0',                               -- 1-bit input: Internal delay data input
            IDATAIN => $data_in,                         -- 1-bit input: Data input from the I/O
            INC => $increase_delay,                      -- 1-bit input: Increment/Decrement tap delay input
            LD => $load_tap_value,                       -- 1-bit input: Load IDELAY_VALUE input
            LDPIPEEN => '0',                             -- 1-bit input: Enable PIPELINE register to load data input
            REGRST => '0'                                -- 1-bit input: Active-high reset tap-delay input
        );

        -- End of IDELAYE2_inst instantiation
    """

    return (
        behavioural_model, signal_assignment, pipeline_model, tap_index_model)

input_delay_control_block_count = 0

@block
def xil_input_delay_control(ref_clock, reset, ready, n_iodelay_group=0):
    ''' This is a block to instantiate a IDELAYCTRL block.

    NOTE: ref_clock should be a 200 MHz clock.
    '''
    global input_delay_control_block_count

    # Need to specify if the signals are inputs or outputs for the conversion
    ref_clock.read = True
    reset.read = True
    ready.driven = 'wire'

    inst_count = input_delay_control_block_count
    input_delay_control_block_count += 1

    # Behavioural model for Myhdl simulations
    # =======================================
    # The delay control block is a low level primitive which does not
    # influence the behaviour of the system.
    reset_clock_cycle_count = Signal(intbv(0, 0, 16))
    # The reset should be set high for 50ns (according to the Xilinx libraries
    # guide) therefore we require 10 clock cycles at 200 MHz (which is the
    # required ref_clock frequency.
    minimum_reset_clock_cycles = 10

    ref_clock_valid = Signal(False)

    previous_reset = Signal(False)

    @always(ref_clock.posedge)
    def behavioural_model():

        previous_reset.next = reset

        if reset:
            if not previous_reset:
                # We have just recieved a rising edge on reset so set the
                # count back to 1
                reset_clock_cycle_count.next = 1
                ref_clock_valid.next = False

            elif reset_clock_cycle_count < minimum_reset_clock_cycles:
                # The number of reset cycles is less than the min so keep
                # counting
                reset_clock_cycle_count.next = reset_clock_cycle_count + 1

        else:
            # Not currently being reset.
            if reset_clock_cycle_count >= minimum_reset_clock_cycles:
                if ref_clock_valid:
                    # Reset count is greater than or equal to the minimum
                    ready.next = True

                else:
                    # The IDELAYCTRL block waits one cycle to check the ref
                    # clock is valid before setting ready high
                    ref_clock_valid.next = True

    # Verilog instantiation for conversion
    # ====================================
    xil_input_delay_control.verilog_code = """
        // IDELAYCTRL: IDELAYE2/ODELAYE2 Tap Delay Value Control
        //             7 Series
        // Xilinx HDL Libraries Guide, version 2012.2

        (* IODELAY_GROUP = "iodelay_group_$n_iodelay_group" *) // Specifies group name for associated IDELAYs/ODELAYs and IDELAYCTRL

        IDELAYCTRL IDELAYCTRL_inst_$inst_count (
            .RDY($ready),        // 1-bit output: Ready output
            .REFCLK($ref_clock), // 1-bit input: Reference clock input
            .RST($reset)         // 1-bit input: Active high reset input
        );

        // End of IDELAYCTRL_inst instantiation
    """

    # VHDL instantiation for conversion
    # =================================
    # Add the required VHDL libraries for conversion
    myhdl_to_vhdl_primitive_conversion_setup.update(
        library='UNISIM', use_clauses='UNISIM.vcomponents.all')
    xil_input_delay_control.vhdl_code = """
        -- IDELAYCTRL: IDELAYE2/ODELAYE2 Tap Delay Value Control
        --             7 Series
        -- Xilinx HDL Libraries Guide, version 2012.3

        IDELAYCTRL_inst_$inst_count : IDELAYCTRL
        port map (
            RDY => $ready,        -- 1-bit output: Ready output
            REFCLK => $ref_clock, -- 1-bit input: Reference clock input
            RST => $reset         -- 1-bit input: Active high reset input
            );

        -- End of IDELAYCTRL_inst instantiation
    """

    return behavioural_model
