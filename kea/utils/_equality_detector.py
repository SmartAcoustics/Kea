from myhdl import block, intbv, always

from ._vector_xor import vector_xor
from ._reducing_or import reducing_or
from .logic import not_gate
from ._synchronous_signal_assigner import synchronous_signal_assigner

@block
def equality_detector(clock, enable, equal, input_0, input_1):
    ''' When `enable` is high, if `input_0` and `input_1` are the same,
    `equal` will be set high.
    '''

    return_objects = []

    if equal._type != bool:
        raise TypeError(
            'equality_detector: The equal signal should be a bool')

    if len(input_0) != len(input_1):
        raise ValueError(
            'equality_detector: Both inputs should be the same width')

    @always(clock.posedge)
    def detector():

        if enable and (input_0 == input_1):
            equal.next = True

        else:
            equal.next = False

    return_objects.append(detector)

    return return_objects
