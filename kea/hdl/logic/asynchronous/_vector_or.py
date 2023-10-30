from myhdl import block, Signal, intbv

from kea.hdl.signal_handling import (
    signal_assigner, combined_signal_assigner, signal_slicer)

from ._variable_width_or import variable_width_or

@block
def vector_or(output, input_signals):
    '''This block will bitwise OR all of the signals in the input signals onto
    the output.

    The `output` arg should be a signal which is the same width as the signals
    in the `input_signals` list.

    The `input_signals` should be a list of signals all of which are the same
    width.
    '''

    if len(input_signals) <= 0:
        raise ValueError(
            'vector_or: There should be at least one input signal.')

    bitwidth = len(input_signals[0])
    n_input_signals = len(input_signals)

    for n in range(n_input_signals):
        if input_signals[n]._type != intbv:
            raise TypeError(
                'vector_or: All input signals should be an intbv.')

    for n in range(1, n_input_signals):
        if len(input_signals[n]) != bitwidth:
            raise TypeError(
                'vector_or: All input signals should be the same bitwidth.')

    if output._type != intbv:
        raise TypeError('vector_or: The output signal should be an intbv.')

    if len(output) != bitwidth:
        raise TypeError(
            'vector_or: The output signal should be the same bitwidth as the '
            'input signals.')

    return_objects = []

    if len(input_signals) == 1:
        # Only one input signal so connect it to the output
        return_objects.append(signal_assigner(input_signals[0], output))

    else:
        # Create a list of signals to carry the result of each bitwise OR
        or_out_bits = [Signal(False) for n in range(bitwidth)]

        for n in range(bitwidth):
            # Create a list of signals to connect the input_signals to the OR
            # gates
            or_bits = [Signal(False) for n in range(n_input_signals)]

            for input_sig, or_bit in zip(input_signals, or_bits):
                # Extract bit n from each input signal and connect it to the
                # OR input
                return_objects.append(signal_slicer(input_sig, n, 1, or_bit))

            # Bitwise OR bit n from the input signals
            return_objects.append(variable_width_or(or_out_bits[n], or_bits))

        # Combine the bits of the OR result and use them to drive the output
        return_objects.append(combined_signal_assigner(or_out_bits, output))

    return return_objects
