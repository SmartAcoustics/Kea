from myhdl import block, Signal

from kea.hdl.signal_handling import (
    de_concatenator, DeConcatenatorOutputInterface, combined_signal_assigner)
from kea.xilinx.primitives.seven_series import xil_iobuf

from .interfaces import NBitsTriStateBuffersIOInterface

@block
def n_bit_tri_state_buffers(
    tri_state_write, tri_state_read, tri_state_control,
    tri_state_io_interface):

    if len(tri_state_control) != 1:
        raise ValueError(
            'n_bit_tri_state_buffers: tri_state_control should be one bit '
            'wide.')

    if not isinstance(
        tri_state_io_interface, NBitsTriStateBuffersIOInterface):
        raise TypeError(
            'n_bit_tri_state_buffers: tri_state_io_interface should be an '
            'instance of NBitsTriStateBuffersIOInterface')

    n_bits = tri_state_io_interface.n_bits

    if len(tri_state_write) != n_bits:
        raise ValueError(
            'n_bit_tri_state_buffers: tri_state_write should have the same '
            'number of bits as tri_state_io_interface.')

    if len(tri_state_read) != n_bits:
        raise ValueError(
            'n_bit_tri_state_buffers: tri_state_read should have the same '
            'number of bits as tri_state_io_interface.')

    return_objects = []

    # De-concatenate the tri_state_write onto one bit tri state write signals
    tri_state_writes_interface = DeConcatenatorOutputInterface(n_bits, 1)
    return_objects.append(
        de_concatenator(tri_state_write, tri_state_writes_interface))

    tri_state_reads = [Signal(False) for n in range(n_bits)]

    for n in range(n_bits):
        return_objects.append(
            xil_iobuf(
                tri_state_writes_interface.signal_n(n),
                tri_state_reads[n],
                tri_state_control,
                tri_state_io_interface.io_bit_n(n)))

    # Combine the tri_state_reads on to the tri_state_read
    return_objects.append(
        combined_signal_assigner(tri_state_reads, tri_state_read))

    return return_objects
