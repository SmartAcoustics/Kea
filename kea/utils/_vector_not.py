from myhdl import block, always_comb

from jackdaw.utils.logic import not_gate

@block
def vector_not(output, input_signal):
    ''' This block will NOT all of the bits in the input signal onto the
    output.

    The `output` arg should be the same width as the input.

    The `input_signal` arg should be a signal which is at least one bit wide.
    '''

    if len(output) != len(input_signal):
        raise ValueError(
            'vector_not: output must be the same width as the input')

    return_objects = []

    if len(output) == 1:

        return_objects.append(not_gate(input_signal, output))

    else:
        @always_comb
        def logic():

            output.next = ~input_signal

        return_objects.append(logic)

    return return_objects
