from myhdl import *

@block
def double_buffer(clock, signal_in, signal_out, init_val=False):

    signal_intermediate = Signal(init_val)

    @always(clock.posedge)
    def d_buf():

        signal_out.next = signal_intermediate
        signal_intermediate.next = signal_in

    return d_buf
