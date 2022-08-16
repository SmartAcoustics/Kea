from myhdl import block, always_comb, Signal, intbv

from kea.utils import signal_assigner
from kea.utils._vector_not import vector_not

@block
def reducing_and(output, input_signal):
    ''' This block will AND all of the bits in the input signal onto the
    output.

    The `output` arg should be a boolean signal.

    The `input_signal` arg should be a signal which is at least one bit wide.
    '''

    if output._type != bool:
        raise ValueError('reducing_and: output must be a boolean signal')

    return_objects = []

    input_bitwidth = len(input_signal)

    if input_bitwidth == 1:
        return_objects.append(signal_assigner(input_signal, output))

    else:
        # As we are ANDing signals we can simply not the input signal and
        # compare it to 0. The first iterations of this code did not use this
        # technique. Instead they compared the input signals to a constant
        # with all bits high. This was problematic as MyHdl does not convert
        # to VHDL correctly when the bitwidth of that constant is greater than
        # 31. The work around was:
        #
        #all_true_val = 2**len(input_signals) - 1
        #all_true = Signal(intbv(all_true_val, 0, all_true_val+1))
        #return_objects.append(constant_assigner(all_true_val, all_true))

        # Not the input signal
        inverted_input = Signal(intbv(0)[input_bitwidth:])
        return_objects.append(vector_not(inverted_input, input_signal))

        @always_comb
        def logic():

            if inverted_input == 0:
                # If the inverted input signals are all 0 then the non
                # inverted input signals are all 1.
                output.next = True

            else:
                output.next = False

        return_objects.append(logic)

    return return_objects
