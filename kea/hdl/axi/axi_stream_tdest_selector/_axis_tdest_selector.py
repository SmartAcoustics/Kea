from myhdl import block, always, enum, Signal

from kea.hdl.axi import AxiStreamInterface
from kea.hdl.axi.axi_stream_utils import check_axi_stream_interface_attributes
from kea.hdl.signal_handling import signal_assigner

@block
def axis_tdest_selector(
    clock, reset, axis_source, axis_sink, tdest_select):
    ''' This block sets the axis sink TDEST signal to tdest_select.

    It will not update axis_sink.TDEST in the middle of a packet.
    '''

    if not isinstance(axis_source, AxiStreamInterface):
        raise TypeError(
            'axis_tdest_selector: axis_source should be an instance of '
            'AxiStreamInterface.')

    if not isinstance(axis_sink, AxiStreamInterface):
        raise TypeError(
            'axis_tdest_selector: axis_sink should be an instance of '
            'AxiStreamInterface.')

    # This block sets TDEST on the sink interface. At the moment it will not
    # allow a TDEST on the source interface. This can be allowed if necessary
    # but it seems odd to allow a TDEST on the source and then set TDEST to
    # something different on the sink.
    if axis_source.TDEST_width is not None:
        raise ValueError(
            'The axis_tdest_selector does not support TDEST on axis_source.')

    # This block requires a TDEST on the axis_sink
    if axis_sink.TDEST_width is None:
        raise ValueError(
            'The axis_tdest_selector requires a TDEST on axis_sink.')

    if len(tdest_select) > axis_sink.TDEST_width:
        raise ValueError(
            'axis_tdest_selector: tdest_select is too wide for '
            'axis_sink.TDEST.')

    # Check the other axis_source and axis_sink signals match. Note, TDEST is
    # excluded from this dict as it it checked above. This block does not
    # support all of the optional AXI stream signals as they are not currently
    # required. It should be simple to add them if required.
    expected_axis_attributes = {
        'bus_width': axis_source.bus_width,
        'TID_width': None,
        'TUSER_width': None,
        'TVALID_init': False,
        'TREADY_init': False,
        'use_TLAST': True,
        'use_TSTRB': False,
        'use_TKEEP': False,
    }
    check_axi_stream_interface_attributes(
        expected_axis_attributes, axis_source)
    check_axi_stream_interface_attributes(
        expected_axis_attributes, axis_sink)

    return_objects = []

    # Connect the axis source signals to the axis sink signals
    return_objects.append(
        signal_assigner(axis_source.TVALID, axis_sink.TVALID))
    return_objects.append(
        signal_assigner(axis_source.TDATA, axis_sink.TDATA))
    return_objects.append(
        signal_assigner(axis_sink.TREADY, axis_source.TREADY))
    return_objects.append(
        signal_assigner(axis_source.TLAST, axis_sink.TLAST))

    t_state = enum('NO_PACKET_IN_PROGRESS', 'PACKET_IN_PROGRESS')
    state = Signal(t_state.NO_PACKET_IN_PROGRESS)

    @always(clock.posedge)
    def sink_tdest_control():

        if state == t_state.NO_PACKET_IN_PROGRESS:

            if axis_source.TVALID and axis_sink.TREADY and axis_source.TLAST:
                # Packet has commenced and completed this cycle so we can
                # update TDEST.
                axis_sink.TDEST.next = tdest_select

            elif axis_source.TVALID:
                # There is a packet in progress on the axis sink
                state.next = t_state.PACKET_IN_PROGRESS

            else:
                # No packet in progress so update TDEST
                axis_sink.TDEST.next = tdest_select

        elif state == t_state.PACKET_IN_PROGRESS:
            if axis_source.TVALID and axis_sink.TREADY and axis_source.TLAST:
                # Packet has completed
                axis_sink.TDEST.next = tdest_select
                state.next = t_state.NO_PACKET_IN_PROGRESS

        if reset:
            axis_sink.TDEST.next = tdest_select
            state.next = t_state.NO_PACKET_IN_PROGRESS

    return_objects.append(sink_tdest_control)

    return return_objects
