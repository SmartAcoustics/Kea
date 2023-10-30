
from .dsp import DSP, DSP_OPMODE_MULTIPLY, N_DSP_OPMODES

from myhdl import intbv, Signal, always_seq, instance, block

# A simple wrapper around the DSP, so all the tests for that
# object should work. The point is to test the DSP48 being not the top level
# in the hierarchy.

@block
def SimpleWrapper(A, B, P, clock_enable, reset, clock):
    '''A simple wrapper that implements the multiply function of the DSP
    block. The arguments are trivially passed through to that block.
    '''

    C = Signal(intbv(0, min=P.min, max=P.max))
    opmode = Signal(intbv(0, min=0, max=N_DSP_OPMODES))

    @always_seq(clock.posedge, reset)
    def constant_signal_driver():
        C.next = 0
        opmode.next = DSP_OPMODE_MULTIPLY

    multiply_wrapper = DSP(
        A, B, C, P, opmode, clock_enable, reset, clock)

    return multiply_wrapper, constant_signal_driver
