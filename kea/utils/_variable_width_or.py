from myhdl import ConcatSignal, block, always_comb, Signal

from ._reducing_or import reducing_or

@block
def variable_width_or(output, input_signals):
    ''' This block will OR all of the input signals onto the output.

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

    if len(input_signals) == 1:
        # Only one input signal
        combined_input_signals = input_signals[0]

    else:
        # Combine all of the input signals into one signal
        combined_input_signals = ConcatSignal(*reversed(input_signals))

    return_objects.append(reducing_or(output, combined_input_signals))

    return return_objects
