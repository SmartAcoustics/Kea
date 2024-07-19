from myhdl import block, Signal, intbv, always_seq, ResetSignal

from kea.hdl.signal_handling import signal_assigner

@block
def sipo_follower_shift_register(
    serial_clock, shift_reg_nreset, parallel_out_nreset, serial_data,
    latch, parallel_data):
    ''' A SIPO follower shift register.

    Note: There should be a gap between shift_reg_nreset going high and any
    subsequent rising edges on serial_clock or latch.

    Note: There should be a gap between parallel_out_nreset going high and any
    subsequent rising edges on latch.
    '''

    parallel_data_bitwidth = len(parallel_data)

    # If we require a parallel_data_bitwidth of one in future then we will
    # need to write another shift block to handle this case.
    if parallel_data_bitwidth <= 1:
        raise ValueError(
            'sipo_follower_shift_register: parallel_data should be greater '
            'than 1 bit wide.')

    return_objects = []

    shift_reg = Signal(intbv(0)[parallel_data_bitwidth:0])

    sr_nreset = ResetSignal(0, active=0, isasync=True)
    return_objects.append(signal_assigner(shift_reg_nreset, sr_nreset))

    po_nreset = ResetSignal(0, active=0, isasync=True)
    return_objects.append(signal_assigner(parallel_out_nreset, po_nreset))

    @always_seq(serial_clock.posedge, reset=sr_nreset)
    def shift():
        shift_reg.next[0] = serial_data
        shift_reg.next[parallel_data_bitwidth:1] = (
            shift_reg[parallel_data_bitwidth-1:0])

    return_objects.append(shift)

    @always_seq(latch.posedge, reset=po_nreset)
    def latch():
        if not shift_reg_nreset:
            parallel_data.next = 0

        else:
            parallel_data.next = shift_reg

    return_objects.append(latch)

    return return_objects
