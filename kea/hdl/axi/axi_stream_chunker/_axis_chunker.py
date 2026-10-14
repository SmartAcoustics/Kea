from myhdl import block, Signal, intbv, always, always_comb, enum

from kea.hdl.axi.axi_stream_utils import check_axi_stream_interface_attributes
from kea.hdl.logic.asynchronous import and_gate
from kea.hdl.signal_handling.asynchronous import sig_assigner
from kea.utils.interface_checks import check_bool_signal, check_intbv_signal

@block
def axis_chunker(clock, reset, n_words_per_chunk, axis_source, axis_sink):
    ''' This block will chunk an AXI stream packet into smaller packets based
    on `n_words_per_chunk`.
    '''

    check_bool_signal(clock, 'clock')
    check_bool_signal(reset, 'reset')

    check_intbv_signal(n_words_per_chunk, 'n_words_per_chunk', signed=False)

    expected_axis_attributes = {
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
        expected_axis_attributes, axis_source)

    # Check the axis_sink has the same bus width as the axis_source
    expected_axis_attributes['bus_width'] = axis_source.bus_width

    check_axi_stream_interface_attributes(
        expected_axis_attributes, axis_sink)

    return_objects = []

    # Create an internal_source_tready and connect it to the
    # axis_source.TREADY
    internal_source_tready = Signal(False)
    return_objects.append(
        sig_assigner(internal_source_tready, axis_source.TREADY))

    internal_sink_tvalid = Signal(False)
    return_objects.append(
        sig_assigner(internal_sink_tvalid, axis_sink.TVALID))

    # Create a signal to record the number of words in each chunk for this
    # packet
    packet_n_words_per_chunk = Signal(intbv(0)[len(n_words_per_chunk):])

    # Create a signal so we can count the number of words per chunk
    word_count = Signal(intbv(0)[len(n_words_per_chunk):])

    packet_in_progress = Signal(False)

    @always(clock.posedge)
    def control():

        if axis_sink.TVALID and axis_sink.TREADY:
            # Downstream has accepted the word
            internal_sink_tvalid.next = False

        if axis_source.TVALID and internal_source_tready:
            # We have accepted a word on the source so we must update the
            # output. The internal_source_tready will only be set high if it
            # is safe to update axis_sink.

            internal_sink_tvalid.next = True
            axis_sink.TDATA.next = axis_source.TDATA

            if axis_source.TLAST:
                # Last word of the packet on the source
                axis_sink.TLAST.next = True
                word_count.next = 0
                packet_n_words_per_chunk.next = n_words_per_chunk
                packet_in_progress.next = False

            elif word_count >= packet_n_words_per_chunk-1:
                # This is the last word of the chunk
                axis_sink.TLAST.next = True
                word_count.next = 0
                packet_in_progress.next = True

            else:
                # Not the last word on the source or the last word of the
                # chunk
                axis_sink.TLAST.next = False
                word_count.next = word_count + 1
                packet_in_progress.next = True

        elif not packet_in_progress:
            # We haven't just accepted a word on axis_source and there isn't a
            # packet_in_progress so packet_n_words_per_chunk can track
            # n_words_per_chunk
            packet_n_words_per_chunk.next = n_words_per_chunk

        if reset:
            internal_sink_tvalid.next = False
            word_count.next = 0
            packet_n_words_per_chunk.next = n_words_per_chunk
            packet_in_progress.next = False

    return_objects.append(control)

    @always_comb
    def ready_driver():

        if internal_sink_tvalid:
            # There is data on the output so we can receive data if the
            # receiver has set TREADY.
            internal_source_tready.next = axis_sink.TREADY

        else:
            # No data on the output so we can receive data
            internal_source_tready.next = True

        if reset or packet_n_words_per_chunk < 1:
            # Set the internal_source_tready on reset or when the
            # packet_n_words_per_chunk is 0
            internal_source_tready.next = False

    return_objects.append(ready_driver)

    return return_objects
