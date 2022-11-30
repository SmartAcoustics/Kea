from math import ceil

from myhdl import block, Signal, intbv, always

from ._rising_edge_detector import rising_edge_detector
from ._constant_assigner import constant_assigner

@block
def watchdog(
    clock, restart, timed_out, clock_frequency, timeout_period_seconds):

    if clock_frequency <= 0:
        raise ValueError('watchdog: clock_frequency should be greater than 0')

    if timeout_period_seconds <= 0:
        raise ValueError(
            'watchdog: timeout_period_seconds should be greater than 0')

    if not timed_out:
        raise ValueError('watchdog: timed_out should be initialised high')

    return_objects = []

    # Detect rising edges on restart
    reset_counter = Signal(False)
    return_objects.append(
        rising_edge_detector(clock, False, restart, reset_counter))

    # Calculate the number of cycles to make up the timeout period
    timeout_period_n_cycles = ceil(clock_frequency*timeout_period_seconds)
    timeout_count = Signal(intbv(0, 0, timeout_period_n_cycles))

    # VHDL constants must be in the range:
    #     -2**31 <= VHDL constants < 2**31
    # To work around this restriction, we use a signal and drive it with a
    # constant value.
    timer_count_reset_val = Signal(intbv(0, 0, timeout_period_n_cycles))
    return_objects.append(
        constant_assigner(timeout_period_n_cycles-1, timer_count_reset_val))

    @always(clock.posedge)
    def control():

        if reset_counter:
            timeout_count.next = timer_count_reset_val
            timed_out.next = False

        elif timeout_count > 0:
            timeout_count.next = timeout_count - 1
            timed_out.next = False

        else:
            timeout_count.next = 0
            timed_out.next = True

    return_objects.append(control)

    return return_objects
