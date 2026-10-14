import copy

from math import ceil

from myhdl import block, Signal, intbv, enum, always, always_comb, concat

from kea.hdl.axi.axi_stream_utils import check_axi_stream_interface_attributes
from kea.hdl.ethernet.definitions import (
    DEST_MAC_N_OCTETS, SRC_MAC_N_OCTETS, DEST_MAC_BITWIDTH, SRC_MAC_BITWIDTH,
    ETHERTYPE_BITWIDTH)
from kea.hdl.signal_handling.asynchronous import (
    sig_assigner, combined_signal_assigner)
from kea.utils.interface_checks import check_bool_signal

from .definitions import ETHERNET_HEADER_N_BITS
from .interfaces import EthernetHeaderValuesInterface

@block
def single_beat_framer(
    clock, reset, ethernet_header_values_interface, axis_source, axis_sink):
    ''' The block prepends ethernet data to the data packets on the
    `axis_source` before forwarding them on `axis_sink`.
    '''

    check_bool_signal(clock, 'clock')
    check_bool_signal(reset, 'reset')

    expected_axis_source_attributes = {
        'TID_width': None,
        'TDEST_width': None,
        'TUSER_width': None,
        'TVALID_init': False,
        'TREADY_init': False,
        'use_TLAST': True,
        'use_TSTRB': False,
        'use_TKEEP': False,
    }

    check_axi_stream_interface_attributes(
        expected_axis_source_attributes, axis_source)

    # The axis_sink should have the same attributes as the axis_source. We
    # also make sure the bitwidth of axis_sink.TDATA is equal to the bitwidth
    # of the axis_source.TDATA and that the axis_sink includes TKEEP
    expected_axis_sink_attributes = copy.copy(expected_axis_source_attributes)
    expected_axis_sink_attributes['bus_width'] = axis_source.bus_width
    expected_axis_sink_attributes['use_TKEEP'] = True

    check_axi_stream_interface_attributes(
        expected_axis_sink_attributes, axis_sink)

    if not isinstance(
        ethernet_header_values_interface, EthernetHeaderValuesInterface):
        raise TypeError(
            'single_beat_framer: ethernet_header_values_interface should be '
            'an instance of EthernetHeaderValuesInterface.')

    axis_data_bitwidth = axis_source.bus_width*8

    if axis_data_bitwidth < ETHERNET_HEADER_N_BITS:
        raise TypeError(
            'single_beat_framer: this block should only be used for AXI '
            'stream interfaces with a data bitwidth which are greater than ' +
            str(ETHERNET_HEADER_N_BITS) + '. The multi_beat_framer should be '
            'used when the AXI stream data bitwdith is less than ' +
            str(ETHERNET_HEADER_N_BITS) + '.')

    if axis_data_bitwidth & (axis_data_bitwidth - 1) != 0:
        raise TypeError(
            'single_beat_framer: the bitwidth of the AXI stream data should '
            'be a power of 2.')

    return_objects = []

    current_header = Signal(intbv(0)[ETHERNET_HEADER_N_BITS:])

    # The header buffer packing is:
    #
    # header[112:104] = EtherType high byte (0x20)
    # header[104:96]  = EtherType low byte (0x21)
    #
    # header[96:88]   = Src MAC byte 5 (0x15)
    # header[88:80]   = Src MAC byte 4 (0x14)
    # header[80:72]   = Src MAC byte 3 (0x13)
    # header[72:64]   = Src MAC byte 2 (0x12)
    # header[64:56]   = Src MAC byte 1 (0x11)
    # header[56:48]   = Src MAC byte 0 (0x10)
    #
    # header[48:40]   = Dest MAC byte 5 (0x05)
    # header[40:32]   = Dest MAC byte 4 (0x04)
    # header[32:24]   = Dest MAC byte 3 (0x03)
    # header[24:16]   = Dest MAC byte 2 (0x02)
    # header[16:8]    = Dest MAC byte 1 (0x01)
    # header[8:0]     = Dest MAC byte 0 (0x00)

    # Extract the destination MAC octets and combine them onto one signal
    dest_mac_octets = [
        ethernet_header_values_interface.dest_mac_octet(n)
        for n in range(DEST_MAC_N_OCTETS)]
    dest_mac = Signal(intbv(0)[DEST_MAC_BITWIDTH:])
    return_objects.append(combined_signal_assigner(dest_mac_octets, dest_mac))

    # Extract the source MAC octets and combine them onto one signal
    src_mac_octets = [
        ethernet_header_values_interface.src_mac_octet(n)
        for n in range(SRC_MAC_N_OCTETS)]
    src_mac = Signal(intbv(0)[SRC_MAC_BITWIDTH:])
    return_objects.append(combined_signal_assigner(src_mac_octets, src_mac))

    # Extract the ethertype
    ethertype = ethernet_header_values_interface.ethertype

    # Calculate the index in the header of the uppermost bit in the source MAC
    src_mac_upper = DEST_MAC_BITWIDTH + SRC_MAC_BITWIDTH

    # The header will not completely fill an axis_sink word. The remainder of
    # the axis_sink word will be filled with data. This misalignment
    # propagates through all the data so each source word will be split
    # between two sink words. Here we calculate how many bits will be sent in
    # the leading word and how many bits will be sent in trailing word.
    n_leading_bits = axis_data_bitwidth - ETHERNET_HEADER_N_BITS
    n_trailing_bits = ETHERNET_HEADER_N_BITS

    # Sanity check to make sure n_trailing_bits is multiple of 8. Calculate
    # the number of trailing bytes
    assert(n_trailing_bits % 8 == 0)
    n_trailing_bytes = int(n_trailing_bits/8)

    # Create a signal to store the trailing bits
    trailing_data = Signal(intbv(0)[n_trailing_bits:])

    # Calculate the values to use when driving the axis_sink.TKEEP
    keep_all_bytes = 2**len(axis_sink.TKEEP) - 1
    keep_trailing_bytes = 2**n_trailing_bytes - 1

    disable_source_tready = Signal(False)

    # Create an internal_sink_tvalid and connect it to the axis_sink.TVALID
    internal_sink_tvalid = Signal(False)
    return_objects.append(
        sig_assigner(internal_sink_tvalid, axis_sink.TVALID))

    # Create an internal_source_tready and connect it to the
    # axis_source.TREADY
    internal_source_tready = Signal(False)
    return_objects.append(
        sig_assigner(internal_source_tready, axis_source.TREADY))

    t_state = enum('IDLE', 'FORWARD_DATA', 'SETUP_LAST_WORD')
    state = Signal(t_state.IDLE)

    @always(clock.posedge)
    def control():

        ########################
        # Load Ethernet Values #
        ########################

        if ethernet_header_values_interface.load_values:
            # Load the new ethernet header values
            current_header.next[DEST_MAC_BITWIDTH:] = dest_mac
            current_header.next[src_mac_upper:DEST_MAC_BITWIDTH] = src_mac
            current_header.next[:src_mac_upper] = ethertype

        ##################
        # Packet framing #
        ##################

        if internal_sink_tvalid and axis_sink.TREADY:
            # The downstream block has accepted the data
            internal_sink_tvalid.next = False

        if state == t_state.IDLE:

            if axis_source.TVALID and internal_source_tready:
                # We have accepted data on the source

                # Output the header
                internal_sink_tvalid.next = True
                axis_sink.TLAST.next = False
                axis_sink.TKEEP.next = keep_all_bytes

                # Output the first word of the header
                axis_sink.TDATA.next[ETHERNET_HEADER_N_BITS:] = current_header

                # Drive the rest of the axis_sink.TDATA (all the bits above
                # the header) with the leading data
                axis_sink.TDATA.next[:ETHERNET_HEADER_N_BITS] = (
                    axis_source.TDATA[n_leading_bits:])

                # Keep the trailing data (all data above the leading bits) for
                # the next word
                trailing_data.next = axis_source.TDATA[:n_leading_bits]

                if axis_source.TLAST:
                    # We have accepted the last word of the packet
                    disable_source_tready.next = True

                    state.next = t_state.SETUP_LAST_WORD

                else:
                    state.next = t_state.FORWARD_DATA

        elif state == t_state.FORWARD_DATA:
            if axis_source.TVALID and internal_source_tready:

                internal_sink_tvalid.next = True

                # Set up the next word with the trailing data
                axis_sink.TDATA.next[n_trailing_bits:] = trailing_data

                # Drive the rest of the axis_sink.TDATA (all the bits above
                # the trailing bits) with the leading data
                axis_sink.TDATA.next[:n_trailing_bits] = (
                    axis_source.TDATA[n_leading_bits:])

                # Keep the trailing data (all data above the leading bits) for
                # the next word
                trailing_data.next = axis_source.TDATA[:n_leading_bits]

                if axis_source.TLAST:
                    # We have accepted the last word of the packet
                    disable_source_tready.next = True

                    state.next = t_state.SETUP_LAST_WORD

        elif state == t_state.SETUP_LAST_WORD:
            if internal_sink_tvalid and axis_sink.TREADY:
                # The downstream block has accepted the data

                # Set up the the trailing data
                internal_sink_tvalid.next = True
                axis_sink.TLAST.next = True
                axis_sink.TKEEP.next = keep_trailing_bytes
                axis_sink.TDATA.next[:n_trailing_bits] = 0
                axis_sink.TDATA.next[n_trailing_bits:] = trailing_data

                # Enable source TREADY again so we can accept the next source
                # word as soon as it is available
                disable_source_tready.next = False

                state.next = t_state.IDLE

        if reset:
            internal_sink_tvalid.next = False
            disable_source_tready.next = False

            state.next = t_state.IDLE

    return_objects.append(control)

    @always_comb
    def ready_connector():

        if not disable_source_tready:
            if internal_sink_tvalid:
                # There is data on the output so we can receive data if the
                # receiver has set TREADY.
                internal_source_tready.next = axis_sink.TREADY

            else:
                # No data on the output so we can receive data
                internal_source_tready.next = True

        else:
            # disable_source_tready is high so the source TREADY signal should
            # be held low.
            internal_source_tready.next = False

        if reset:
            # Reset the internal_source_tready.
            internal_source_tready.next = False

    return_objects.append(ready_connector)

    return return_objects
