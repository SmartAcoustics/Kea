from myhdl import block, always_comb, always, Signal

from kea.axi import AxiStreamInterface

from ._signal_assigner import signal_assigner

@block
def axis_signal_buffer(
    clock, source_tvalid, source_tready, source_signal, sink_signal):
    ''' This block updates the sink signal with the source signal according
    to the source_tvalid and source_tready signals.

    If both `source_tvalid` and `source_tready` are high then `sink_signal`
    is updated to `source_signal`. If not, `sink_signal` retains its value.
    '''
    @always(clock.posedge)
    def buffer():

        if source_tvalid and source_tready:
            sink_signal.next = source_signal

    return buffer

@block
def axis_buffer(clock, reset, axis_source, axis_sink):
    ''' This block buffers the axis source.
    '''

    if not isinstance(axis_source, AxiStreamInterface):
        raise ValueError(
            'axis_source should be an instance of AxiStreamInterface.')

    if not isinstance(axis_sink, AxiStreamInterface):
        raise ValueError(
            'axis_sink should be an instance of AxiStreamInterface.')

    # Check axis_source and axis_sink match
    assert(axis_source.bus_width == axis_sink.bus_width)
    assert(axis_source.TID_width == axis_sink.TID_width)
    assert(axis_source.TDEST_width == axis_sink.TDEST_width)
    assert(axis_source.TUSER_width == axis_sink.TUSER_width)
    assert(hasattr(axis_source, 'TLAST') == hasattr(axis_sink, 'TLAST'))
    assert(hasattr(axis_source, 'TSTRB') == hasattr(axis_sink, 'TSTRB'))
    assert(hasattr(axis_source, 'TKEEP') == hasattr(axis_sink, 'TKEEP'))

    # This block does not support all of the optional AXI stream signals as
    # they are not currently required. It should be simple to add them in the
    # same way TLAST is buffered.

    if axis_source.TID_width is not None:
        raise ValueError('The axis_buffer does not support TID.')

    if axis_source.TDEST_width is not None:
        raise ValueError('The axis_buffer does not support TDEST.')

    if axis_source.TUSER_width is not None:
        raise ValueError('The axis_buffer does not support TUSER.')

    if hasattr(axis_source, 'TSTRB'):
        raise ValueError('The axis_buffer does not support TSTRB.')

    if hasattr(axis_source, 'TKEEP'):
        raise ValueError('The axis_buffer does not support TKEEP.')

    return_objects = []

    # Create internal versions of the source tready and sink tvalid
    axis_source_tready = Signal(False)
    axis_sink_tvalid = Signal(False)

    # Connect the internal source tready and sink tvalid signals to their
    # axis interface counterparts
    return_objects.append(
        signal_assigner(axis_source_tready, axis_source.TREADY))
    return_objects.append(
        signal_assigner(axis_sink_tvalid, axis_sink.TVALID))

    # Buffer TDATA
    return_objects.append(
        axis_signal_buffer(
            clock, axis_source.TVALID, axis_source_tready,
            axis_source.TDATA, axis_sink.TDATA))

    if hasattr(axis_source, 'TLAST'):
        # The interfaces have TLAST signals so buffer it
        return_objects.append(
            axis_signal_buffer(
                clock, axis_source.TVALID, axis_source_tready,
                axis_source.TLAST, axis_sink.TLAST))

    @always(clock.posedge)
    def sink_valid_control():

        if not axis_sink_tvalid or axis_sink.TREADY:
            # If there is no data in the buffer (axis_sink_tvalid is low) then
            # read in from the source. If there is data in the buffer then
            # read in when axis_sink.TREADY is high as this means the buffer
            # has been read.
            axis_sink_tvalid.next = axis_source.TVALID

        if reset:
            axis_sink_tvalid.next = False

    return_objects.append(sink_valid_control)

    @always_comb
    def source_ready_control():
        # The buffer is ready if the sink is reading or there is no data on
        # sink interface
        axis_source_tready.next = (
            not reset and (axis_sink.TREADY or not axis_sink_tvalid))

    return_objects.append(source_ready_control)

    return return_objects
