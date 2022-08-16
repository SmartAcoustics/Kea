from myhdl import ConcatSignal, block, always_comb, Signal, intbv
from math import ceil

from kea.utils import signal_assigner
from kea.utils._reducing_and import reducing_and

@block
def variable_width_and(output, input_signals):
    ''' This block will AND all of the input signals onto the output.

    The `output` arg should be a boolean signal.

    The `input_signals` arg should be a list of boolean signals.
    '''

    if len(input_signals) < 1:
        raise ValueError('input_signals must contain at least one signal')

    if output._type != bool:
        raise ValueError('output must be a boolean signal')

    for input_signal in input_signals:
        if input_signal._type != bool:
            raise ValueError('All input_signals must be boolean signals')

    return_objects = []

    n_signals = len(input_signals)

    if n_signals == 1:
        # Only one input signal
        return_objects.append(signal_assigner(input_signals[0], output))

    else:
        # Combine all of the input signals into one signal
        combined_input = ConcatSignal(*reversed(input_signals))

        return_objects.append(reducing_and(output, combined_input))

    return return_objects
