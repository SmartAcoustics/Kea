from myhdl import block, Signal, intbv, always

from kea.hdl.signal_handling import synchronous_signal_assigner

@block
def synchronous_sipo_follower(
    clock, serial_clock, shift_reg_nreset, parallel_out_nreset, serial_data,
    latch, parallel_data):
    ''' A SIPO follower shift register. Being synchronous to a clock other
    than the serial_clock is unusual but necessary in certain circumstances.
    '''

    parallel_data_bitwidth = len(parallel_data)

    # If we require a parallel_data_bitwidth of one in future then we will
    # need to write another shift block to handle this case.
    if parallel_data_bitwidth <= 1:
        raise ValueError(
            'synchronous_sipo_follower: parallel_data should be greater '
            'than 1 bit wide.')

    return_objects = []

    # Keep a record of serial_clock so we can detect edges
    serial_clock_d0 = Signal(False)
    return_objects.append(
        synchronous_signal_assigner(clock, serial_clock, serial_clock_d0))

    # Keep a record of latch so we can detect edges
    latch_d0 = Signal(False)
    return_objects.append(synchronous_signal_assigner(clock, latch, latch_d0))

    shift_reg = Signal(intbv(0)[parallel_data_bitwidth:0])

    @always(clock.posedge)
    def shift():

        if serial_clock and not serial_clock_d0:
            # Rising edge on serial_clock
            shift_reg.next[0] = serial_data
            shift_reg.next[parallel_data_bitwidth:1] = (
                shift_reg[parallel_data_bitwidth-1:0])

        if not shift_reg_nreset:
            shift_reg.next = 0

    return_objects.append(shift)

    @always(clock.posedge)
    def latcher():
        if latch and not latch_d0:
            # Rising edge on latch
            parallel_data.next = shift_reg

        if not parallel_out_nreset:
            parallel_data.next = 0

    return_objects.append(latcher)

    return return_objects
