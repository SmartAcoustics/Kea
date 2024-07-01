from myhdl import *

@block
def signal_slicer(signal_in, slice_offset, slice_bitwidth, signal_out):
    ''' This block will slice signal_in and assign it to signal_out.

    The signal_in slice will start at slice_offset and finish at
    slice_offset + slice bitwidth.
    '''

    if slice_offset >= len(signal_in):
        raise ValueError(
            'signal_slicer: slice_offset should be less than the signal_in '
            'width')

    if (slice_bitwidth + slice_offset) > len(signal_in):
        raise ValueError(
            'signal_slicer: Slice bitfield should fit within signal_in')

    if slice_bitwidth <= 0:
        raise ValueError(
            'signal_slicer: slice_bitwidth should be greater than 0')

    if slice_bitwidth != len(signal_out):
        raise ValueError(
            'signal_slicer: slice_bitwidth should be equal to the signal_out '
            'width')

    signal_out_min = signal_out.min

    if signal_out_min is None:
        # signal_out.min may return None (eg if signal_out is a bool signal).
        # In this case we assume signal_out is unsigned.
        signed_assignment = False

    elif signal_out.min < 0:
        signed_assignment = True

    else:
        signed_assignment = False

    slice_upper_bound = slice_offset + slice_bitwidth

    if signed_assignment:

        if 2**(slice_bitwidth-1) != signal_out.max:
            raise ValueError(
                'signal_slicer: signal_out.max should be equal to the '
                'exclusive upper bound for a signed signal of '
                'slice_bitwidth bits.')

        if -2**(slice_bitwidth-1) != signal_out.min:
            raise ValueError(
                'signal_slicer: signal_out.min should be equal to the '
                'inclusive lower bound for a signed signal of '
                'slice_bitwidth bits.')

        @always_comb
        def assignment():
            signal_out.next = (
                signal_in[slice_upper_bound: slice_offset]).signed()

    else:

        if isinstance(signal_out.val, bool):
            @always_comb
            def assignment():
                signal_out.next = signal_in[slice_offset]

        else:
            @always_comb
            def assignment():
                signal_out.next = signal_in[slice_upper_bound: slice_offset]

    return assignment
