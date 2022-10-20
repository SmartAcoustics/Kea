from myhdl import block, intbv, always_comb

@block
def vector_xor(output, input_0, input_1):
    '''This block will bitwise XOR `input_0` and `input_1` onto the output.

    `input_0`, `input_1` and `output` should all be the same width.
    '''

    if input_0._type != intbv:
        raise TypeError('vector_xor: The input_0 signal should be an intbv.')

    if input_1._type != intbv:
        raise TypeError('vector_xor: The input_1 signal should be an intbv.')

    if output._type != intbv:
        raise TypeError('vector_xor: The output signal should be an intbv.')

    if len(input_0) != len(input_1):
        raise ValueError('vector_xor: Both inputs should be the same width')

    bitwidth = len(input_0)

    if len(output) != bitwidth:
        raise ValueError(
            'vector_xor: The output should be the same width as the inputs')

    return_objects = []

    @always_comb
    def logic():

        output.next = input_0 ^ input_1

    return_objects.append(logic)

    return return_objects
