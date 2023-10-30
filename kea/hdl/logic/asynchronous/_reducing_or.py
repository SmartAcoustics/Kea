from myhdl import block, always_comb, Signal

@block
def reducing_or(output, input_signal):
    ''' This block will OR all of the bits in the input signal onto the
    output.

    The `output` arg should be a boolean signal.

    The `input_signal` arg should be a signal which is at least one bit wide.
    '''

    if output._type != bool:
        raise ValueError('output must be a boolean signal')

    @always_comb
    def logic():
        if input_signal != 0:
            output.next = True

        else:
            output.next = False

    return logic
