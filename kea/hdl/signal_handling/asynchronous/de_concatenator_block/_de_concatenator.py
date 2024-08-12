from myhdl import block

from .._signal_slicer import signal_slicer
from .interfaces import DeConcatenatorOutputInterface

@block
def de_concatenator(signal_in, output_interface):
    ''' This block will slice the `signal_in` into slices of
    `output_interface.signal_bitwidth`. It will then assign those slices to
    the corresponding signal on the `output_inteface`.
    '''

    if not isinstance(output_interface, DeConcatenatorOutputInterface):
        raise TypeError(
            'de_concatenator: the output_interface should be an instance of '
            'DeConcatenatorOutputInterface.')

    n_output_signals = output_interface.n_signals

    # This is checked on the output_interface, we include a sanity check here
    assert(n_output_signals > 0)

    output_signal_bitwidth = output_interface.signal_bitwidth
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
                output_interface.signal_n(n)))

    return return_objects
