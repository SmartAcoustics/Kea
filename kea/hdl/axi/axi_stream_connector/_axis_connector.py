from myhdl import block

from kea.hdl.axi import AxiStreamInterface
from kea.hdl.signal_handling import signal_assigner

@block
def axis_connector(clock, axis_source, axis_sink):

    if not isinstance(axis_source, AxiStreamInterface):
        raise TypeError(
            'axis_connector: axis_source should be an instance of '
            'AxiStreamInterface.')

    if not isinstance(axis_sink, AxiStreamInterface):
        raise TypeError(
            'axis_connector: axis_sink should be an instance of '
            'AxiStreamInterface.')

    assert(axis_source.bus_width == axis_sink.bus_width)
    assert(axis_source.TDEST_width == axis_sink.TDEST_width)
    assert(axis_source.TID_width == axis_sink.TID_width)
    assert(axis_source.TUSER_width == axis_sink.TUSER_width)
    assert(hasattr(axis_source, 'TLAST') == hasattr(axis_sink, 'TLAST'))
    assert(hasattr(axis_source, 'TSTRB') == hasattr(axis_sink, 'TSTRB'))
    assert(hasattr(axis_source, 'TKEEP') == hasattr(axis_sink, 'TKEEP'))

    return_objects = []

    # Connect the axis source signals to the axis sink signals
    return_objects.append(
        signal_assigner(axis_source.TVALID, axis_sink.TVALID))
    return_objects.append(
        signal_assigner(axis_source.TDATA, axis_sink.TDATA))
    return_objects.append(
        signal_assigner(axis_sink.TREADY, axis_source.TREADY))

    if axis_source.TDEST_width is not None:
        return_objects.append(
            signal_assigner(axis_source.TDEST, axis_sink.TDEST))

    if axis_source.TID_width is not None:
        return_objects.append(
            signal_assigner(axis_source.TID, axis_sink.TID))

    if axis_source.TUSER_width is not None:
        return_objects.append(
            signal_assigner(axis_source.TUSER, axis_sink.TUSER))

    if hasattr(axis_source, 'TLAST'):
        return_objects.append(
            signal_assigner(axis_source.TLAST, axis_sink.TLAST))

    if hasattr(axis_source, 'TSTRB'):
        return_objects.append(
            signal_assigner(axis_source.TSTRB, axis_sink.TSTRB))

    if hasattr(axis_source, 'TKEEP'):
        return_objects.append(
            signal_assigner(axis_source.TKEEP, axis_sink.TKEEP))

    return return_objects
