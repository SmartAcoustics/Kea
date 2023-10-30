from myhdl import *

@block
def constant_assigner(constant, signal):
    ''' This block assigns a constant to a signal.
    '''

    if constant >= 2**len(signal):
        raise ValueError('Constant is too large for the signal')

    if constant < 0:
        raise ValueError('Constant must not be negative')

    # This hack is necessary because @always_comb blocks needs a signal in the
    # sensitivity list. We then need to set constant_sig.driven to suppress
    # warnings on conversion that constant_sig is not driven.
    constant_sig = Signal(intbv(constant)[len(signal):])
    constant_sig.driven = 'reg'

    @always_comb
    def assigner():

        signal.next = constant_sig

    return assigner
