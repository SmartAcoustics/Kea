from myhdl import *

@block
def piso_shift_register(
    clock, reset, data_in, data_out, data_out_clock, data_out_latch,
    data_out_nframe_sync, data_out_nreset, external_register_value,
    clock_out_period, post_frame_delay=0, ready=None):
    '''Implements a parallel to serial (serialising) shift register to drive
    an external deserialising shift register.

    ``external_register_value`` is an output signal that keeps track of the
    state of the external register that is being written to. It is updated on
    each latch going high (so might still be slightly earlier than actual
    hardware).

    The MSB is clocked onto the serial line first, the LSB last.

    ``clock_out_period`` gives the clock period of the data out clock in
    cycles of ``clock``.

    ``post_frame_delay``, if set, gives the delay after a full frame
    (including the latch) has completed. This is in cycles of ``clock``.

    If required, this block can take a ``ready`` signal. It will be set high
    when the piso_shift_register is ready for a change on ``data_in``. The
    ready signal does not change the behaviour of this block in any way.
    ``data_in`` can still be changed at any time. The ready can be used for
    timing so the external block knows when ``data_in`` was read.
    '''

    if clock_out_period < 2:
        raise ValueError(
            'Clock period error: clock_out_period must be at least 2')

    if post_frame_delay < 0:
        raise ValueError(
            'post frame delay error: post_frame_delay must be a positive '
            'integer. %s given' % str(post_frame_delay))

    if len(external_register_value) != len(data_in):
        raise ValueError(
            'length error: external_register_value should be the same length '
            'as the data_in')

    if ready is not None:
        if not ready._init:
            # Ready should be initialised true as this block will read data_in
            # on the first rising edge
            raise ValueError('ready should be initialised true')

    else:
        # Ready has not been passed in so create it and set read true to
        # suppress the conversion warning
        ready = Signal(True)
        ready.read = True

    t_shift_reg_state = enum(
        'IDLE', 'RESET_HOLD', 'CLOCK_OUT_LOW', 'CLOCK_OUT_HIGH', 'LATCHING',
        'POST_FRAME_DELAY')
    shift_reg_state = Signal(t_shift_reg_state.IDLE)

    clock_high_period = clock_out_period//2
    clock_low_period = clock_out_period - clock_high_period

    latch_period = clock_out_period

    max_clock_count_period = max(
        clock_high_period, clock_low_period, latch_period, post_frame_delay)

    input_data_width = len(data_in)

    msb_bit_index = input_data_width - 1
    bit_count = Signal(intbv(0, min=0, max=input_data_width+1))

    shift_reg_buffer = Signal(intbv(0, min=data_in.min, max=data_in.max))
    shift_reg_shifting_buffer = Signal(intbv(0)[len(data_in):])

    cycle_counter = Signal(intbv(0, min=0, max=max_clock_count_period+1))

    reset_period = clock_out_period
    reset_counter = Signal(intbv(reset_period, min=0, max=reset_period+1))

    force_update = Signal(True)

    @always_comb
    def set_data_bit():
        data_out.next = shift_reg_shifting_buffer[msb_bit_index]

    @always(clock.posedge)
    def shift_reg():

        if reset:
            data_out_nreset.next = False
            shift_reg_state.next = t_shift_reg_state.RESET_HOLD
            force_update.next = True

            data_out_clock.next = 0
            data_out_latch.next = False
            data_out_nframe_sync.next = True

            ready.next = False

            if reset_counter > 0:
                reset_counter.next = reset_counter - 1

        else:

            if shift_reg_state == t_shift_reg_state.IDLE:

                data_out_nreset.next = True
                data_out_latch.next = False

                if force_update or data_in != shift_reg_buffer:
                    shift_reg_buffer.next = data_in
                    shift_reg_shifting_buffer.next = (
                        data_in[input_data_width:])

                    force_update.next = False

                    ready.next = False

                    bit_count.next = 0
                    data_out_clock.next = 0
                    data_out_nframe_sync.next = False
                    cycle_counter.next = 1 # We'll get at least one cycle

                    shift_reg_state.next = t_shift_reg_state.CLOCK_OUT_LOW
                else:
                    data_out_nframe_sync.next = True

            elif shift_reg_state == t_shift_reg_state.CLOCK_OUT_LOW:

                if cycle_counter < clock_low_period:
                    cycle_counter.next = cycle_counter + 1

                else:
                    cycle_counter.next = 1 # We'll get at least one cycle
                    data_out_clock.next = 1
                    bit_count.next = bit_count + 1

                    shift_reg_state.next = t_shift_reg_state.CLOCK_OUT_HIGH

            elif shift_reg_state == t_shift_reg_state.CLOCK_OUT_HIGH:

                if cycle_counter < clock_high_period:
                    cycle_counter.next = cycle_counter + 1

                else:
                    # left shift the shifting buffer, filling with 0 from the
                    # right
                    shift_reg_shifting_buffer.next[:1] = (
                        shift_reg_shifting_buffer[msb_bit_index:0])

                    shift_reg_shifting_buffer.next[0] = 0

                    data_out_clock.next = 0
                    cycle_counter.next = 1 # We'll get at least one cycle

                    if bit_count < msb_bit_index + 1:
                        shift_reg_state.next = t_shift_reg_state.CLOCK_OUT_LOW

                    else:
                        data_out_latch.next = True
                        data_out_nframe_sync.next = True

                        external_register_value.next = shift_reg_buffer

                        shift_reg_state.next = t_shift_reg_state.LATCHING

            elif shift_reg_state == t_shift_reg_state.LATCHING:

                if cycle_counter < latch_period:
                    cycle_counter.next = cycle_counter + 1

                else:
                    cycle_counter.next = 1 # We'll get at least one cycle
                    data_out_latch.next = False

                    if post_frame_delay > 0:
                        shift_reg_state.next = (
                            t_shift_reg_state.POST_FRAME_DELAY)
                    else:
                        ready.next = True
                        shift_reg_state.next = t_shift_reg_state.IDLE

            elif shift_reg_state == t_shift_reg_state.POST_FRAME_DELAY:

                if cycle_counter < post_frame_delay:
                    cycle_counter.next = cycle_counter + 1

                else:
                    cycle_counter.next = 1 # We'll get at least one cycle
                    ready.next = True
                    shift_reg_state.next = t_shift_reg_state.IDLE

            elif  shift_reg_state == t_shift_reg_state.RESET_HOLD:

                if reset_counter > 0:
                    reset_counter.next = reset_counter - 1

                else:
                    reset_counter.next = reset_period
                    data_out_nreset.next = True

                    shift_reg_state.next = t_shift_reg_state.IDLE


    return shift_reg, set_data_bit
