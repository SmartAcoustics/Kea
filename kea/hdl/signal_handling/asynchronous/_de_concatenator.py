from myhdl import block

from ._signal_slicer import signal_slicer

@block
def de_concatenator(signal_in, output_signals):
    ''' `output_signals` should be a list of signals. All `output_signals`
    should be the same bit width (output signal bit width).

    This block will slice the `signal_in` into slices of output signal bit
    width. It will then assign those slices to the corresponding signal in the
    `output_signals` list
    '''

    n_output_signals = len(output_signals)

    if n_output_signals < 1:
        raise ValueError('de_concatenator: the output_signals list is empty.')

    output_signal_bitwidth = len(output_signals[0])

    if n_output_signals > 1:
        for n in range(n_output_signals):
            if len(output_signals[n]) != output_signal_bitwidth:
                raise ValueError(
                    'de_concatenator: all signals in the output_signals list '
                    'should be the same bitwidth.')

    total_output_bitwidth = n_output_signals*output_signal_bitwidth

    if total_output_bitwidth > len(signal_in):
        raise ValueError(
            'de_concatenator: the total output bitwidth should be less than '
            'or equal to the signal_in bitwidth.')

    return_objects = []

    for n in range(n_output_signals):
        slice_offset = n*output_signal_bitwidth

        return_objects.append(
            signal_slicer(
                signal_in, slice_offset, output_signal_bitwidth,
                output_signals[n]))

    return return_objects
