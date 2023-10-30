from myhdl import Signal, block

from kea.hdl.cdc import double_buffer

from .interfaces import DoubleBufferArrayInterface

@block
def double_buffer_array(clock, double_buffer_array_interface):

    if not isinstance(
        double_buffer_array_interface, DoubleBufferArrayInterface):
        raise TypeError(
            'double_buffer_array: double_buffer_array_interface should be an '
            'instance of DoubleBufferArrayInterface.')

    return_objects = []

    for n in range(double_buffer_array_interface.n_signals):
        return_objects.append(
            double_buffer(
                clock,
                double_buffer_array_interface.input_signal(n),
                double_buffer_array_interface.output_signal(n),
                double_buffer_array_interface.init_val,))

    return return_objects
