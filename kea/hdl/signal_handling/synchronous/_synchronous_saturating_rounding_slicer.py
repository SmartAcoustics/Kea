from math import ceil
from myhdl import block, Signal, intbv, always

from kea.hdl.signal_handling import signal_slicer, integer_constant_signal

def intbv_signal_bounds(signal):
    ''' This function will get the exclusive upper and inclusive lower bounds
    of `signal`.
    '''

    assert(isinstance(signal.val, intbv))

    signal_bitwidth = len(signal)

    if signal.min is None:
        # Assume unsigned signal

        # If signal.min is None then we make sure signal.max is also None.
        assert(signal.max is None)

        lower_bound = 0

        # signal.max is not set so calculate the upper bound based on the
        # signal bitwidth.
        upper_bound = 2**signal_bitwidth

    elif signal.min < 0:
        # Signed signal

        # If signal.min has been set then we make sure signal.max has also
        # been set.
        assert(signal.max is not None)

        # Check that signal.min includes all possible negative values for a
        # signed signal with this bitwidth.
        assert(signal.min == -2**(signal_bitwidth-1))

        # Check that signal.max includes all possible positive values for a
        # signed signal with this bitwidth.
        assert(signal.max == 2**(signal_bitwidth-1))

        lower_bound = signal.min
        upper_bound = signal.max

    else:
        # Unsigned signal

        # If signal.min has been set then we make sure signal.max has also
        # been set.
        assert(signal.max is not None)

        # Check that signal.min is 0.
        assert(signal.min == 0)

        # Check that signal.max includes all possible positive values for an
        # unsigned signal with this bitwidth.
        assert(signal.max == 2**signal_bitwidth)

        lower_bound = signal.min
        upper_bound = signal.max

    return lower_bound, upper_bound

@block
def synchronous_saturating_rounding_slicer(
    clock, enable, signal_in, signal_out, slice_offset):
    ''' This block will slice `signal_in` and assign it to `signal_out`. The
    offset of the slice is set by `slice_offset`. The length of the slice is
    set by the length of `signal_out`.

    Lets call the bits up to `slice_offset` the fractional bits.

    If, after slicing off the fractional bits, the `signal_in` is greater than
    or equal to the maximum value that `signal_out` can take, this block will
    saturate the `signal_out` at its maximum value.

    If, after slicing off the fractional bits, the `signal_in` is less than
    the minimum value that `signal_out` can take, this block will saturate the
    `signal_out` at its minimum value.

    If the output has not saturated, this block will round the slice according
    to the fractional bits. The slice will be rounded using a round half to
    even strategy. If the fractional bits are greater than half the range of
    the fractional bits, then this block will round up. If the fractional bits
    are less than half the range of the fractional bits, then this block will
    round down. If the fractional bits equal half the range of the fractional
    bits then this block will round to the closest even value.

    If `slice_offset` is 0 then this block will not perform any rounding.
    '''

    input_bitwidth = len(signal_in)
    output_bitwidth = len(signal_out)

    if not isinstance(signal_in.val, intbv):
        raise TypeError(
            'synchronous_saturating_rounding_slicer: signal_in should be an '
            'intbv signal')

    if not isinstance(signal_out.val, intbv):
        raise TypeError(
            'synchronous_saturating_rounding_slicer: signal_out should be an '
            'intbv signal')

    if slice_offset >= input_bitwidth:
        raise ValueError(
            'synchronous_saturating_rounding_slicer: slice_offset should be '
            'less than the bitwidth of signal_in')

    if slice_offset < 0:
        raise ValueError(
            'synchronous_saturating_rounding_slicer: slice_offset should be '
            'greater than or equal to 0.')

    return_objects = []

    # Get the inclusive lower bound and exclusive upper bound of signal_out
    signal_out_lower_bound, signal_out_upper_bound = (
        intbv_signal_bounds(signal_out))

    # Get the inclusive lower bound and exclusive upper bound of signal_in
    signal_in_lower_bound, signal_in_upper_bound = (
        intbv_signal_bounds(signal_in))

    if signal_out_lower_bound < 0:
        # signal_out is signed
        signed_signal_out = True
    else:
        # signal_out is unsigned
        assert(signal_out_lower_bound == 0)
        signed_signal_out = False

    if signal_in_lower_bound < 0:
        # signal_in is signed
        signed_signal_in = True
    else:
        # signal_in is unsigned
        assert(signal_in_lower_bound == 0)
        signed_signal_in = False

    if slice_offset == 0:

        if (signal_out_lower_bound <= signal_in_lower_bound and
            signal_out_upper_bound >= signal_in_upper_bound):
            # signal_out can take the full signal_in range. Therefore we don't
            # need to round or saturate

            @always(clock.posedge)
            def assigner():

                if enable:
                    signal_out.next = signal_in

            return_objects.append(assigner)

        else:
            # slice_offset is 0 so there are no fractional bits. Therefore we
            # need to saturate but not round

            signal_out_upper_saturation = signal_out_upper_bound - 1
            signal_out_lower_saturation = signal_out_lower_bound

            # Create integer constant signals so the conversion to VHDL works
            # correctly when signal_out_upper_bound is greater than 32 bits
            # (signed)
            signal_out_upper_bound_const = (
                integer_constant_signal(signal_out_upper_bound))
            signal_out_lower_bound_const = (
                integer_constant_signal(signal_out_lower_bound))

            @always(clock.posedge)
            def saturator():

                if enable:
                    if signal_in >= signal_out_upper_bound_const:
                        # signal_in is greater than or equal to the exclusive
                        # upper bound of signal_in so we saturate the output
                        # with the maximum value it can take.
                        signal_out.next = signal_out_upper_saturation

                    elif signal_in < signal_out_lower_bound_const:
                        # signal_in is less than the inclusive lower bound of
                        # signal_in so we saturate the output with the minimum
                        # value it can take.
                        signal_out.next = signal_out_lower_saturation

                    else:
                        signal_out.next = signal_in

            return_objects.append(saturator)

    else:
        fractional_slice_bitwidth = slice_offset
        fractional_slice_offset = 0
        half_fractional_range = ceil(2**(fractional_slice_bitwidth - 1))
        fractional_slice = Signal(intbv(0)[slice_offset:])
        return_objects.append(
            signal_slicer(
                signal_in, fractional_slice_offset, fractional_slice_bitwidth,
                fractional_slice))

        # The integer_slice is all the bits remaining after taking off the
        # fractional bits.
        integer_slice_bitwidth = input_bitwidth - slice_offset

        if signed_signal_in:
            # Signal in is signed so integer_slice needs to be signed
            integer_slice_lower_bound = -2**(integer_slice_bitwidth-1)
            integer_slice_upper_bound = 2**(integer_slice_bitwidth-1)

        else:
            assert(signal_in_lower_bound == 0)

            integer_slice_lower_bound = 0
            integer_slice_upper_bound = 2**integer_slice_bitwidth

        integer_slice = (
            Signal(intbv(
                0, min=integer_slice_lower_bound,
                max=integer_slice_upper_bound)))
        return_objects.append(
            signal_slicer(
                signal_in, slice_offset, integer_slice_bitwidth,
                integer_slice))

        signal_out_upper_saturation = signal_out_upper_bound - 1
        signal_out_lower_saturation = signal_out_lower_bound

        # Create integer constant signals so the conversion to VHDL works
        # correctly when the constants are greater than 32 bits (signed)
        half_fractional_range_const = (
            integer_constant_signal(half_fractional_range))
        signal_out_upper_saturation_const = (
            integer_constant_signal(signal_out_upper_saturation))
        signal_out_lower_bound_const = (
            integer_constant_signal(signal_out_lower_bound))

        @always(clock.posedge)
        def slicer():

            if enable:

                if integer_slice >= signal_out_upper_saturation_const:
                    # After removing the fractional bits, the signal_in is
                    # greater than or equal to the maximum value that
                    # signal_out can take so we saturate the output with the
                    # maximum value. Note: If signal_out is already at the
                    # signal_out_upper_saturation then it cannot be rounded up
                    # so we saturate and avoid any attempt to round up.
                    signal_out.next = signal_out_upper_saturation

                elif integer_slice < signal_out_lower_bound_const:
                    # After removing the fractional bits, signal_in is less
                    # than the inclusive lower bound of signal_in so we
                    # saturate the output with the minimum value it can take.
                    signal_out.next = signal_out_lower_saturation

                elif (fractional_slice == half_fractional_range_const and
                      integer_slice[0]):
                    # Round half up to even
                    signal_out.next = integer_slice + 1

                elif (fractional_slice == half_fractional_range_const and
                      not integer_slice[0]):
                    # Round half down to even
                    signal_out.next = integer_slice

                elif fractional_slice > half_fractional_range_const:
                    # Round up
                    signal_out.next = integer_slice + 1

                else:
                    # Round down
                    signal_out.next = integer_slice

        return_objects.append(slicer)

    return return_objects
