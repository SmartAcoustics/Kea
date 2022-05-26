from myhdl import *

@block
def detector(clock, reset, trigger, output):
    ''' Implements a falling edge detector. On receipt of a falling edge on
    the ``trigger`` input, this block will output a single cycle pulse.

    A high pulse on reset will set the output low and cause any recent falling
    edges that have not yet been reported to be ignored.
    '''

    return_objects = []

    trigger_d0 = Signal(False)
    trigger_d1 = Signal(False)

    @always(clock.posedge)
    def detector():

        # Double buffer the incoming trigger
        trigger_d0.next = trigger
        trigger_d1.next = trigger_d0

        if reset:
            trigger_d0.next = False
            trigger_d1.next = False

    return_objects.append(detector)

    @always_comb
    def output_driver():

        # Detect the falling edge
        output.next = not trigger_d0 and trigger_d1

        if reset:
            output.next = False

    return_objects.append(output_driver)

    return return_objects

@block
def falling_edge_detector(clock, reset, trigger, output, buffer_trigger=False):
    ''' Implements a falling edge detector. On receipt of a falling edge on
    the ``trigger`` input, this block will output a single cycle pulse.

    A high pulse on reset will set the output low and cause any recent falling
    edges that have not yet been reported to be ignored.

    If `buffer_trigger` is True then this block will add a register the trigger
    input before sending it to the detector. This is useful if the trigger is
    connected to an FPGA pin as it allows the tools to place the register
    close to the pin. It also means there is a double buffer on the input
    before and logic inside the detector.
    '''

    return_objects = []

    if buffer_trigger:
        # Create a signal to carry the buffered trigger
        buffered_trigger = Signal(False)

        @always(clock.posedge)
        def trigger_buffer():

            # Buffer the trigger
            buffered_trigger.next = trigger

        return_objects.append(trigger_buffer)

        # Detect falling edges on the buffered trigger
        return_objects.append(
            detector(clock, reset, buffered_trigger, output))

    else:
        # No buffering required on the trigger
        return_objects.append(detector(clock, reset, trigger, output))

    return return_objects
