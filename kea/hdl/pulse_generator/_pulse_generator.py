from myhdl import *

from kea.hdl.signal_handling import (
    synchronous_signal_assigner, signal_assigner)

@block
def pulse_generator(clock, reset, trigger, output, pulse_n_cycles):
    ''' Implements a pulse generator. On receipt of a high on the trigger
    input this block will output a pulse of length ``pulse_n_cycles``. Any
    subsequent high values on the trigger input will be ignored until the end
    of the output pulse. The output will always go low in between pulses.

    This block will set the output low and ignore any trigger pulses while
    reset is high.
    '''

    if pulse_n_cycles <= 0:
        raise ValueError(
            'pulse_generator: pulse_n_cycles must be greater than zero.')

    return_objects = []

    pulse_length_count = Signal(intbv(0, 0, pulse_n_cycles+1))

    t_generator_state = enum('IDLE', 'PULSE')
    generator_state = Signal(t_generator_state.IDLE)

    @always(clock.posedge)
    def generator():

        if generator_state == t_generator_state.IDLE:

            if trigger:
                # On receipt of a trigger start the pulse
                output.next = True
                pulse_length_count.next = 1
                generator_state.next = t_generator_state.PULSE

        elif generator_state == t_generator_state.PULSE:

            if pulse_length_count == pulse_n_cycles:
                # Pulse has been high for the required period so set it low
                output.next = False
                pulse_length_count.next = 0
                generator_state.next = t_generator_state.IDLE

            else:
                # Count the pulse high period
                pulse_length_count.next = pulse_length_count + 1

        if reset:
            output.next = False
            pulse_length_count.next = 0
            generator_state.next = t_generator_state.IDLE

    return_objects.append(generator)

    return return_objects
