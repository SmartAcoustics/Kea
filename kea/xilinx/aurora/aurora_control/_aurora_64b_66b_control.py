from myhdl import block, Signal, intbv, enum, always

from kea.hdl.cdc import double_buffer
from kea.hdl.signal_handling import signal_assigner

@block
def aurora_64b_66b_control(
    clock, enable, ready, reset_pb, pma_init, clock_frequency):
    ''' This block controls the aurora power up and reset sequence.

    reset_pb and pma_init should be connected to the corresponding io on the
    aurora block.

    clock_frequency should be the clock frequency of the the clock.

    clock_frequency should be less than or equal to the frequency of the
    user_clock out from the Aurora block.
    '''

    if clock_frequency <= 0:
        raise ValueError(
            'aurora_64b_66b_control: clock_frequency should be greater than '
            '0.')

    if ready.val is not False:
        raise ValueError(
            'aurora_64b_66b_control: ready should initialise False.')

    if reset_pb.val is not True:
        raise ValueError(
            'aurora_64b_66b_control: reset_pb should initialise True.')

    if pma_init.val is not True:
        raise ValueError(
            'aurora_64b_66b_control: pma_init should initialise True.')

    return_objects = []

    # Set up internal signals so the signals are initialised with the correct
    # value.
    reset_pb_internal = Signal(True)
    pma_init_internal = Signal(True)
    ready_internal = Signal(False)

    return_objects.append(signal_assigner(reset_pb_internal, reset_pb))
    return_objects.append(signal_assigner(pma_init_internal, pma_init))
    return_objects.append(signal_assigner(ready_internal, ready))

    reset_pb_n_cycles = 128
    reset_pb_count_threshold = reset_pb_n_cycles-1
    reset_pb_count = Signal(intbv(0, 0, reset_pb_n_cycles))

    pma_init_n_cycles = clock_frequency
    pma_init_count_threshold = pma_init_n_cycles-1
    pma_init_count = Signal(intbv(0, 0, pma_init_n_cycles))

    buffered_enable = Signal(False)
    return_objects.append(double_buffer(clock, enable, buffered_enable))

    t_state = enum('RESET', 'INIT', 'HOLD', 'RUNNING')
    state = Signal(t_state.RESET)

    @always(clock.posedge)
    def control():

        if state == t_state.RESET:
            if reset_pb_count >= reset_pb_count_threshold:
                # reset_pb has been high long enough for the pma_init to be
                # set high
                pma_init_internal.next = True
                pma_init_count.next = 0
                state.next = t_state.INIT

            else:
                # Count the reset_pb period before setting pma_init
                reset_pb_count.next = reset_pb_count + 1

        elif state == t_state.INIT:
            if pma_init_count >= pma_init_count_threshold:
                # pma_init has been high for the required period
                pma_init_internal.next = False
                reset_pb_count.next = 0
                state.next = t_state.HOLD

            else:
                # Count the pma_init high period
                pma_init_count.next = pma_init_count + 1

        elif state == t_state.HOLD:
            if reset_pb_count >= reset_pb_count_threshold:
                # reset_pb has been high for the required period
                reset_pb_internal.next = False
                ready_internal.next = True
                state.next = t_state.RUNNING

            else:
                # Count the reset_pb period after resetting pma_init
                reset_pb_count.next = reset_pb_count + 1

        elif state == t_state.RUNNING:
            pass

        if not buffered_enable:
            # Enable has gone low
            ready_internal.next = False
            reset_pb_internal.next = True
            reset_pb_count.next = 0
            state.next = t_state.RESET

    return_objects.append(control)

    return return_objects
