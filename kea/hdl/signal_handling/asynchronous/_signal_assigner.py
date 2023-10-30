from myhdl import *

@block
def boolean_signal_assigner(signal_in, signal_out):

    @always_comb
    def assigner():
        # Pass the signal straight through
        signal_out.next = signal_in

    return assigner

@block
def intbv_signal_assigner(signal_in, signal_out, offset):

    @always_comb
    def assigner():
        # Shift the signal as requested
        signal_out.next[:offset] = signal_in

    return assigner

@block
def intbv_to_signed_signal_assigner(signal_in, signal_out, offset):

    @always_comb
    def assigner():
        # Convert to signed and shift the signal as requested
        signal_out.next[:offset] = signal_in.signed()

    return assigner

@block
def signal_assigner(signal_in, signal_out, offset=0, convert_to_signed=False):
    ''' Assigns the signal_in to the signal_out shifted by the offset value.
    If convert_to_signed is true, then this block will convert the input to a
    signed value as part of the assignment.
    '''

    if len(signal_out) < len(signal_in) + offset:
        raise ValueError(
            'signal_out must be wide enough to accomodate the signal_in '
            'shifted by offset.')

    if len(signal_out) == 1:
        return boolean_signal_assigner(signal_in, signal_out)

    else:
        if convert_to_signed:
            return (
                intbv_to_signed_signal_assigner(
                    signal_in, signal_out, offset))

        else:
            return intbv_signal_assigner(signal_in, signal_out, offset)
