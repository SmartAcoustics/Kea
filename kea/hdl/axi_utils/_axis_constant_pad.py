
from myhdl import *
from kea.hdl.axi import AxiStreamInterface

@block
def axis_constant_pad(clock, enable, axis_in, axis_out, constant=0):
    '''A block that will wait on a valid input transaction whenever enable
    goes high. Once a valid input transaction occurs, the output is always
    valid until enable goes low again.

    If enable goes low and then high again, the output is invalid until
    the next valid input transaction, at which point the output is always
    valid again.

    If the input is not valid and the output is (as per the rules above),
    the output TDATA is set to ``constant'', otherwise the output TDATA is the
    input TDATA.

    The block incurs one cycle delay.

    TREADY on the output is never propagated to the input (so is ignored).

    TLAST, if present, is ignored.
    '''

    if not isinstance(axis_in, AxiStreamInterface):
        raise ValueError('Invalid axis_in port: The '
                         'axis_in port should be an instance of '
                         'AxiStreamInterface.')

    if not isinstance(axis_out, AxiStreamInterface):
        raise ValueError('Invalid axis_out port: The '
                         'axis_out port should be an instance of '
                         'AxiStreamInterface.')

    # axis_out TREADY is ignored
    axis_out.TREADY.read = True

    valid_transaction_happened = Signal(False)
    internal_axis_out_TVALID = Signal(False)

    @always_comb
    def gate_axis_signals():

        axis_in.TREADY.next = enable
        axis_out.TVALID.next = enable and internal_axis_out_TVALID

    @always(clock.posedge)
    def assignments():

        if enable:
            if axis_in.TVALID:
                axis_out.TDATA.next = axis_in.TDATA
                internal_axis_out_TVALID.next = True

                valid_transaction_happened.next = True

            elif valid_transaction_happened:
                axis_out.TDATA.next = constant
                internal_axis_out_TVALID.next = True

            else:
                internal_axis_out_TVALID.next = False

        else:
            internal_axis_out_TVALID.next = False
            valid_transaction_happened.next = False

    return assignments, gate_axis_signals
