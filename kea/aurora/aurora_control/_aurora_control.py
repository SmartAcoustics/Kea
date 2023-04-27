from myhdl import block, Signal, intbv, enum, always

from kea.utils import double_buffer

@block
def aurora_control(
    clock, enable, ready, reset_pb, pma_init, channel_up, clock_frequency):
    ''' This block controls the aurora power up and reset flow.

    channel_up, reset_pb and pma_init should be connected to the corresponding
    io on the aurora block.

    clock_frequency should be the clock frequency of the the clock.
    '''

    if clock_frequency <= 0:
        raise ValueError(
            'aurora_control: clock_frequency should be greater than 0.')

    if ready.val is not False:
        raise ValueError('aurora_control: ready should initialise False.')

    if reset_pb.val is not True:
        raise ValueError('aurora_control: reset_pb should initialise True.')

    if pma_init.val is not True:
        raise ValueError('aurora_control: pma_init should initialise True.')

    return_objects = []

    reset_pb_n_cycles = 128
    reset_pb_count_threshold = reset_pb_n_cycles-1
    reset_pb_count = Signal(intbv(0, 0, reset_pb_n_cycles))

    pma_init_n_cycles = clock_frequency
    pma_init_count_threshold = pma_init_n_cycles-1
    pma_init_count = Signal(intbv(0, 0, pma_init_n_cycles))

    buffered_enable = Signal(False)
    return_objects.append(double_buffer(clock, enable, buffered_enable))

    t_state = enum('RESET', 'INIT', 'HOLD', 'AWAIT_CH_UP', 'RUNNING')
    state = Signal(t_state.RESET)

    @always(clock.posedge)
    def control():

        if state == t_state.RESET:
            if reset_pb_count >= reset_pb_count_threshold:
                # reset_pb has been high long enough for the pma_init to be
                # set high
                pma_init.next = True
                pma_init_count.next = 0
                state.next = t_state.INIT

            else:
                # Count the reset_pb period before setting pma_init
                reset_pb_count.next = reset_pb_count + 1

        elif state == t_state.INIT:
            if pma_init_count >= pma_init_count_threshold:
                # pma_init has been high for the required period
                pma_init.next = False
                reset_pb_count.next = 0
                state.next = t_state.HOLD

            else:
                # Count the pma_init high period
                pma_init_count.next = pma_init_count + 1

        elif state == t_state.HOLD:
            if reset_pb_count >= reset_pb_count_threshold:
                # reset_pb has been high for the required period
                reset_pb.next = False
                state.next = t_state.AWAIT_CH_UP

            else:
                # Count the reset_pb period after resetting pma_init
                reset_pb_count.next = reset_pb_count + 1

        elif state == t_state.AWAIT_CH_UP:
            if channel_up:
                # The aurora block has set channel up
                ready.next = True
                state.next = t_state.RUNNING

        elif state == t_state.RUNNING:
            if not channel_up:
                # Channel has gone down
                ready.next = False
                reset_pb.next = True
                reset_pb_count.next = 0
                state.next = t_state.RESET

        if not buffered_enable:
            # Enable has gone low
            ready.next = False
            reset_pb.next = True
            reset_pb_count.next = 0
            state.next = t_state.RESET

    return_objects.append(control)

    return return_objects
