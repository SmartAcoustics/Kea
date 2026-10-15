from myhdl import block

from kea.hdl.axi import AxiStreamInterface

from .definitions import ETHERNET_HEADER_N_BITS
from ._multi_beat_framer import multi_beat_framer
from ._single_beat_framer import single_beat_framer

@block
def ethernet_framer(
    clock, reset, ethernet_header_values_interface, axis_source, axis_sink):

    if not isinstance(axis_sink, AxiStreamInterface):
        raise TypeError(
            'ethernet_framer: axis_sink should be an instance of '
            'AxiStreamInterface')

    return_objects = []

    data_bitwidth = axis_sink.bus_width*8

    if data_bitwidth < ETHERNET_HEADER_N_BITS:
        return_objects.append(
            multi_beat_framer(
                clock, reset, ethernet_header_values_interface, axis_source,
                axis_sink))

    else:
        return_objects.append(
            single_beat_framer(
                clock, reset, ethernet_header_values_interface, axis_source,
                axis_sink))

    return return_objects
