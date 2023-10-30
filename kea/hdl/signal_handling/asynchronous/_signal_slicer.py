from myhdl import *

@block
def signal_slicer(signal_in, slice_offset, slice_bitwidth, signal_out):
    ''' This block will slice signal_in and assign it to signal_out.

    The signal_in slice will start at slice_offset and finish at
    slice_offset + slice bitwidth.
    '''

    if slice_offset >= len(signal_in):
        raise ValueError('slice_offset must be less than the signal_in width')

    if (slice_bitwidth + slice_offset) > len(signal_in):
        raise ValueError('Slice bitfield must fit within signal_in')

    if slice_bitwidth <= 0:
        raise ValueError('slice_bitwidth must be greater than 0')

    if slice_bitwidth != len(signal_out):
        raise ValueError(
            'slice_bitwidth must be equal to the signal_out width')

    if slice_bitwidth == 1:
        @always_comb
        def assignment():
            signal_out.next = signal_in[slice_offset]

    else:
        @always_comb
        def assignment():
            signal_out.next = (
                signal_in[(slice_offset + slice_bitwidth): slice_offset])

    return assignment
