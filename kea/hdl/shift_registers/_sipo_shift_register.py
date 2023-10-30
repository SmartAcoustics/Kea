from myhdl import *

@block
def sipo_shift_register(
    clock, initialisation_authorised, read, parallel_data_out, serial_data_in,
    data_clock_out, parallel_load_out, read_complete_toggle,
    serial_clock_period):
    '''Implements a serial to parallel (deserialising) shift register to drive
    an external serialising shift register.

    On ``read`` going high, ``parallel_load_out`` goes low for one
    ``serial_clock_period`` to instruct the external shift register to load
    the parallel word, and then the ``data_clock_out`` reads the data in,
    one bit at a time with a period of ``serial_clock_period``, beginning
    with the MSB.

    Once the data has been read in, ``read_complete_toggle`` flips its value.
    The purpose of this is to report to upstream blocks when the data has been
    read in without handshaking being required.
    '''

    if serial_clock_period < 2:
        raise ValueError(
            'Clock period error: serial_clock_period must be at least 2')

    t_shift_reg_state = enum(
        'INIT', 'IDLE', 'PARALLEL_LOAD', 'CLOCK_OUT_LOW', 'CLOCK_OUT_HIGH')
    shift_reg_state = Signal(t_shift_reg_state.INIT)

    last_read_state = Signal(False)

    serial_clock_high_period = serial_clock_period//2
    serial_clock_low_period = serial_clock_period - serial_clock_high_period

    # Defensive getting of the max clock count period
    max_clock_count_period = max(
        serial_clock_high_period, serial_clock_low_period,
        serial_clock_period)

    cycle_counter = Signal(intbv(0, min=0, max=max_clock_count_period+1))

    bitwidth = len(parallel_data_out)
    bit_count = Signal(intbv(0, min=0, max=bitwidth))

    parallel_store = Signal(
        intbv(0, min=parallel_data_out.min, max=parallel_data_out.max))

    @always(clock.posedge)
    def shift_reg():

        last_read_state.next = read

        if shift_reg_state == t_shift_reg_state.INIT:
            if initialisation_authorised:
                # Give the system time to power up
                bit_count.next = 0
                parallel_load_out.next = False
                shift_reg_state.next = t_shift_reg_state.PARALLEL_LOAD
                cycle_counter.next = 1 # at least one cycle

        elif shift_reg_state == t_shift_reg_state.IDLE:

            data_clock_out.next = False

            if not last_read_state and read:
                bit_count.next = 0
                parallel_load_out.next = False
                shift_reg_state.next = t_shift_reg_state.PARALLEL_LOAD
                cycle_counter.next = 1 # at least one cycle

        elif shift_reg_state == t_shift_reg_state.PARALLEL_LOAD:

            if cycle_counter < serial_clock_period:
                cycle_counter.next = cycle_counter + 1

            else:
                cycle_counter.next = 1
                data_clock_out.next = False
                parallel_load_out.next = True

                shift_reg_state.next = t_shift_reg_state.CLOCK_OUT_LOW

        elif shift_reg_state == t_shift_reg_state.CLOCK_OUT_LOW:

            data_clock_out.next = 0

            if cycle_counter < serial_clock_low_period:
                cycle_counter.next = cycle_counter + 1

            else:
                cycle_counter.next = 1

                if (bit_count == bitwidth - 1):
                    # All data acquired
                    data_clock_out.next = False

                    parallel_data_out.next[0] = serial_data_in
                    parallel_data_out.next[bitwidth:1] = (
                        parallel_store[bitwidth-1:0])

                    read_complete_toggle.next = not read_complete_toggle
                    shift_reg_state.next = t_shift_reg_state.IDLE
                else:
                    # Need more data
                    data_clock_out.next = True

                    parallel_store.next[0] = serial_data_in
                    parallel_store.next[bitwidth:1] = (
                        parallel_store[bitwidth-1:0])

                    bit_count.next = bit_count + 1
                    shift_reg_state.next = t_shift_reg_state.CLOCK_OUT_HIGH

        elif shift_reg_state == t_shift_reg_state.CLOCK_OUT_HIGH:

            if cycle_counter < serial_clock_high_period:
                cycle_counter.next = cycle_counter + 1

            else:
                cycle_counter.next = 1
                data_clock_out.next = False
                shift_reg_state.next = t_shift_reg_state.CLOCK_OUT_LOW

    return shift_reg
