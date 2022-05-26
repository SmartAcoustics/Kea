from myhdl import block, ConcatSignal

from kea.utils import signal_assigner

@block
def combined_signal_assigner(input_signals, signal_out):
    ''' The `input_signals` argument should be a list of signals. This block
    combines these signals and uses them to drive signal_out.
    '''

    n_input_signals = len(input_signals)

    if n_input_signals < 1:
        raise ValueError(
            'combined_signal_assigner: input_signals should contain at least '
            'one signal.')

    if n_input_signals > 1:
        for n in range(1, n_input_signals):
            if len(input_signals[n]) != len(input_signals[0]):
                raise ValueError(
                    'combined_signal_assigner: All signals in the '
                    'input_signals list should be the same bitwidth.')

    # Calculate the total bitwidth of the signals in input_signals
    signal_in_bitwidth = n_input_signals*len(input_signals[0])

    signal_out_bitwidth = len(signal_out)

    if signal_in_bitwidth > signal_out_bitwidth:
        raise ValueError(
            'combined_signal_assigner: The signal_out is not wide enough '
            'for all of the input_signals.')

    return_objects = []

    if n_input_signals == 1:
        # Only one input_signal
        signal_in = input_signals[0]

    else:
        # Combine the input_signals onto a single signal
        signal_in = ConcatSignal(*reversed(input_signals))

    # Drive the signal_out with the combined input_signals
    return_objects.append(
        signal_assigner(
            signal_in, signal_out, offset=0, convert_to_signed=False))

    return return_objects
