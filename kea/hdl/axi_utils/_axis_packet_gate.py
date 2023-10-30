
from myhdl import *
from kea.hdl.axi import AxiStreamInterface

@block
def axis_packet_gate(clock, reset, axis_in, axis_out, go):
    '''A block that by default blocks the transactions on ``axis_in`` and
    ``axis_out`` by setting ``axis_in.TREADY = False`` and ``axis_out.TVALID =
    False`` until a synchronous pulse is received on the
    go signal.

    A this point the ``axis_in.TREADY`` signal will be routed to the
    ``axis_out.TREADY`` signal and the ``axis_out.TVALID`` signal will be
    routed to the ``axis_in.TVALID``.

    When ``axis_in.TLAST`` is encountered, the transactions will once again
    be blocked until a new ``go`` pulse is received.

    If a ``go`` happens at the same time as a ``TLAST``, then the gate will
    remain open (to allow clock contiguous packets).

    ``axis_out.TDATA`` is always connected to ``axis_in.TDATA``.
    '''

    if not isinstance(axis_in, AxiStreamInterface):
        raise ValueError('Invalid axis_in port: The '
                         'axis_in port should be an instance of '
                         'AxiStreamInterface.')

    if not isinstance(axis_out, AxiStreamInterface):
        raise ValueError('Invalid axis_out port: The '
                         'axis_out port should be an instance of '
                         'AxiStreamInterface.')

    try:
        axis_in.TLAST
    except AttributeError:
        raise ValueError('Missing axis_in TLAST signal: The axis_in port is '
                         'expected to have the TLAST signal enabled.')

    try:
        axis_out.TLAST
    except AttributeError:
        raise ValueError('Missing axis_out TLAST signal: The axis_out port '
                         'is expected to have the TLAST signal enabled.')

    t_gate_state = enum('GATE_OPEN', 'GATE_CLOSED')
    gate_state = Signal(t_gate_state.GATE_CLOSED)

    @always_comb
    def signal_assignments():
        axis_out.TDATA.next = axis_in.TDATA

        if gate_state == t_gate_state.GATE_CLOSED:
            axis_out.TVALID.next = False
            axis_out.TLAST.next = False
            axis_in.TREADY.next = False

        else:
            axis_out.TVALID.next = axis_in.TVALID
            axis_out.TLAST.next = axis_in.TLAST
            axis_in.TREADY.next = axis_out.TREADY

    @always(clock.posedge)
    def gate_state_walker():

        if reset:
            gate_state.next = t_gate_state.GATE_CLOSED

        else:
            if gate_state == t_gate_state.GATE_CLOSED:
                if go:
                    gate_state.next = t_gate_state.GATE_OPEN

            elif gate_state == t_gate_state.GATE_OPEN:
                if axis_in.TREADY and axis_in.TVALID and axis_in.TLAST:

                    if not go:
                        # We stay open if a go happens at the same time as a
                        # TLAST
                        gate_state.next = t_gate_state.GATE_CLOSED
                    else:
                        gate_state.next = t_gate_state.GATE_OPEN

            else:
                # Default defensive catch
                gate_state.next = t_gate_state.GATE_CLOSED

    return gate_state_walker, signal_assignments

