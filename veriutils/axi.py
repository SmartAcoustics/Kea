from myhdl import *
from collections import deque
import copy
import random
from itertools import dropwhile

class AxiStreamInterface(object):
    '''The AXI stream interface definition'''

    @property
    def bus_width(self):
        return self._bus_width

    @property
    def TID_width(self):
        return self._TID_width

    @property
    def TDEST_width(self):
        return self._TDEST_width

    @property
    def TUSER_width(self):
        return self._TUSER_width

    def __init__(self, bus_width=4, TID_width=None, TDEST_width=None,
                 TUSER_width=None, TVALID_init=False, TREADY_init=False,
                 use_TSTRB=False, use_TKEEP=False):
        '''Creates an AXI4 Stream interface object. The signals and parameters
        are exactly as described in the AMBA 4 AXI4 Stream Protocol
        Specification.

        For a full understanding of the protocol, that document should be
        read (it is quite accessible and easy to read).

        ``bus_width`` gives the width of the data bus, ``TDATA``, in bytes.
        This by extension gives the width in bits of the byte qualifiers,
        ``TSTRB`` and ``TKEEP``.

        If ``TID_width`` is not ``None``, then the stream identifier signal,
        ``TID``, is enabled and has width ``TID_width`` bits. The AXI stream
        protocol specification recommends that ``TID_width`` not be larger than
        8.

        It ``TID_width`` is ``None``, then no ``TID`` signal is available.

        Similarly to ``TID_width``, ``TDEST_width`` and ``TUSER_width`` if not
        ``None`` set the width in bits of ``TDEST`` (providing routing
        information) and ``TUSER`` (providing user defined sideband
        information) respectively.

        If either are ``None``, then as with ``TID_width``, their respective
        signals are not available.

        The AXI stream protocol specification recommends that ``TDEST_width``
        not be larger than 4, and ``TUSER_width`` be an integer multiple of
        the interface width in bytes.

        None of the recommendations are enforced in the interface and can
        be implemented differently. There may be additional constraints on the
        size of the interfaces that need to be considered.

        Initial values of ``TVALID`` and ``TREADY`` can be set with the
        ``TVALID_init`` and ``TREADY_init`` arguments respectively. In both
        cases the argument is coerced to be a boolean type.

        By default, ``TSTRB`` and ``TKEEP`` are not included in the interface.
        They can be added by setting ``use_TSTRB`` or ``use_TKEEP`` to True.
        '''

        self._bus_width = int(bus_width)

        self.TVALID = Signal(bool(TVALID_init))
        self.TREADY = Signal(bool(TREADY_init))
        self.TDATA = Signal(intbv(0)[8*self.bus_width:])
        self.TLAST = Signal(bool(0))

        if use_TSTRB:
            self.TSTRB = Signal(intbv(0)[self.bus_width:])

        if use_TKEEP:
            self.TKEEP = Signal(intbv(0)[self.bus_width:])

        if TID_width is not None:
            self._TID_width = int(TID_width)
            self.TID = Signal(intbv(0)[self.TID_width:])
        else:
            self._TID_width = None

        if TDEST_width is not None:
            self._TDEST_width = int(TDEST_width)
            self.TDEST = Signal(intbv(0)[self.TDEST_width:])
        else:
            self._TDEST_width = None

        if TUSER_width is not None:
            self._TUSER_width = int(TUSER_width)
            self.TUSER = Signal(intbv(0)[self.TUSER_width:])
        else:
            self._TUSER_width = None

class AxiStreamMasterBFM(object):

    def __init__(self):
        '''Create an AXI4 Stream master bus functional model (BFM).

        Data is added to the stream using the ``add_data`` method, at
        which point all the parameters can be set up for a particular sequence
        of transfers.

        Currently ``TUSER`` is ignored.
        '''
        self._data = {}

    def add_data(self, data):#, stream_ID=0, stream_destination=0):
        '''Add data to this BFM. ``data`` is a list of lists, each sublist of
        which comprises a packet (terminated by ``TKEEP`` being asserted).

        Values inside each packet (i.e. the inner lists) can be ``None``, in
        which case the value acts like a no-op, setting the ``TVALID`` flag to
        ``False`` for that data value. This allows the calling code to insert
        delays in the data output.
        '''
        #The ``stream_ID`` and ``stream_destination`` parameters are used to
        #set the ``TID`` and ``TDEST`` signals respectively for the data
        #provided.
        #'''

        stream_ID = 0
        stream_destination = 0

        try:
            self._data[(stream_ID, stream_destination)].extend(
                deque([deque(packet) for packet in data]))

        except KeyError:
            self._data[(stream_ID, stream_destination)] = deque(
                [deque(packet) for packet in data])


    @block
    def model(self, clock, interface):

        model_rundata = {}
        None_data = Signal(False)

        stream_ID = 0
        stream_destination = 0

        @always(clock.posedge)
        def model_inst():

            # We need to try to update either when a piece of data has been
            # propagated (TVALID and TREADY) or when we previously didn't
            # have any data, or the data was None (not TVALID)
            if ((interface.TVALID and interface.TREADY) or
                not interface.TVALID):

                if 'packet' not in model_rundata:
                    model_rundata['packet'] = []
                    while len(model_rundata['packet']) == 0:

                        try:
                            if len(self._data[
                                (stream_ID, stream_destination)]) > 0:

                                model_rundata['packet'] = self._data[
                                    (stream_ID, stream_destination)].popleft()

                            else:
                                # Nothing left to get, so we drop out.
                                break

                        except KeyError:
                            break

                if len(model_rundata['packet']) > 0:

                    if len(model_rundata['packet']) == 1:

                        interface.TLAST.next = True
                        value = model_rundata['packet'].popleft()

                        # Nothing left in the packet
                        del model_rundata['packet']

                    else:
                        value = model_rundata['packet'].popleft()

                        # We need to set TLAST if all the remaining values
                        # in the packet are None
                        if all(
                            [val is None for val in model_rundata['packet']]):
                            interface.TLAST.next = True
                        else:
                            interface.TLAST.next = False

                    if value is not None:
                        None_data.next = False
                        interface.TDATA.next = value
                        interface.TVALID.next = True
                    else:
                        None_data.next = True
                        interface.TVALID.next = False

                else:
                    interface.TVALID.next = False
                    # no data, so simply remove the packet for initialisation
                    # next time
                    del model_rundata['packet']


        return model_inst


class AxiStreamSlaveBFM(object):

    @property
    def current_packet(self):
        return [copy.copy(val) for val in self._current_packet]

    @property
    def completed_packets(self):
        copied_completed_packets = []
        for packet in self._completed_packets:
            copied_completed_packets.append(
                [copy.copy(val) for val in packet])

        return copied_completed_packets

    def __init__(self):
        '''Create an AXI4 Stream slave bus functional model (BFM).

        Valid data that is received is recorded. Completed packets are
        available for inspection through the ``completed_packets``
        property.

        The packet currently being populated can be found on the
        ``current_packet`` attribute. This provides a snapshot and does
        not change with the underlying data structure.

        Currently ``TUSER`` is ignored.

        The MyHDL model is instantiated using the ``model`` method.
        '''
        self._completed_packets = []
        self._current_packet = []

    @block
    def model(self, clock, interface, TREADY_probability=1.0):
        '''Instantiate a AXI stream slave MyHDL block that acts as the
        HDL front end to the class.

        ``clock`` and ``interface`` are the binary clock signal and valid
        AXI signal interface respectively.

        ``TREADY_probability`` gives the probability that on a given clock
        cycle the ``TREADY`` signal will be asserted. Changing it from
        the default of ``1.0`` allows the slave to not always be ready.

        If ``TREADY_probability`` is set to ``None``, then the model can be
        used in passive mode whereby it never sets ``TREADY``. It still acts
        as expected, recording the AXI transfers properly. This is useful
        if you want this block to sniff the lines and simply record the
        transactions (as an aside, this also happens when
        ``TREADY_probability`` is set to ``0.0``, but the driver code is
        still implemented in that case).
        '''

        @always(clock.posedge)
        def TREADY_driver():
            if TREADY_probability > random.random():
                interface.TREADY.next = True
            else:
                interface.TREADY.next = False

        @always(clock.posedge)
        def model_inst():

            if interface.TVALID and interface.TREADY:
                self._current_packet.append(copy.copy(interface.TDATA._val))

                if interface.TLAST:
                    # End of a packet, so copy the current packet into
                    # complete_packets and empty the current packet.
                    self._completed_packets.append(
                        copy.copy(self._current_packet))

                    del self._current_packet[:]

        if TREADY_probability is None:
            return model_inst

        else:
            return model_inst, TREADY_driver


@block
def axi_stream_buffer(
    clock, axi_stream_in, axi_stream_out, passive_sink_mode=False):

    data_buffer = deque([])

    internal_TVALID = Signal(False)
    internal_TLAST = Signal(False)
    internal_TDATA = Signal(intbv(0)[len(axi_stream_out.TDATA):])

    data_in_buffer = Signal(False)
    use_internal_values = Signal(False)

    @always_comb
    def output_assignments():

        if use_internal_values:
            axi_stream_out.TVALID.next = internal_TVALID
            axi_stream_out.TDATA.next = internal_TDATA
            axi_stream_out.TLAST.next = internal_TLAST

        else:
            axi_stream_out.TVALID.next = axi_stream_in.TVALID
            axi_stream_out.TDATA.next = axi_stream_in.TDATA
            axi_stream_out.TLAST.next = axi_stream_in.TLAST

    @always(clock.posedge)
    def TREADY_driver():
        axi_stream_in.TREADY.next = True

    @always(clock.posedge)
    def model():
        transact_in = axi_stream_in.TREADY and axi_stream_in.TVALID
        transact_out = axi_stream_out.TREADY and axi_stream_out.TVALID

        if len(data_buffer) == 0:
            if (transact_in and not transact_out) or (
                transact_in and use_internal_values):

                data_buffer.append(
                    (int(axi_stream_in.TDATA.val),
                     bool(axi_stream_in.TLAST.val)))

            elif transact_out and not transact_in and use_internal_values:
                use_internal_values.next = False

        elif len(data_buffer) > 0 and transact_in:
            data_buffer.append(
                (int(axi_stream_in.TDATA.val), bool(axi_stream_in.TLAST.val)))

        # Data might have just been put into the buffer, so we always check it
        if len(data_buffer) > 0:
            if transact_out or (not transact_out and not use_internal_values):
                TDATA, TLAST = data_buffer.popleft()
                internal_TDATA.next = TDATA
                internal_TLAST.next = TLAST
                internal_TVALID.next = True
                use_internal_values.next = True

    if not passive_sink_mode:
        return model, output_assignments, TREADY_driver

    else:
        return model, output_assignments

@block
def axi_master_playback(clock, axi_interface, packets):

    # From the packets, we preload all the values that should be output.
    # This is TDATA, TVALID and TLAST

    TDATAs = tuple(val if val is not None else 0 for packet in packets
                   for val in packet)

    TVALIDs = tuple(1 if val is not None else 0 for packet in packets
                   for val in packet)

    # To find TLAST, we need both the length of the packet and the length
    # of the packet with the trailing Nones stripped away.
    packet_lengths = [len(packet) for packet in packets]
    None_stripped_packet_lengths = [
        len(tuple(dropwhile(lambda x: x is None, reversed(packet)))) for
        packet in packets]

    TLASTs = [0] * len(TDATAs)

    TLAST_offset = -1
    for length, stripped_length in zip(
        packet_lengths, None_stripped_packet_lengths):

        if length > 0:
            TLASTs[TLAST_offset + stripped_length] = 1
            TLAST_offset += length

        else:
            continue

    # TLASTs should be a tuple
    TLASTs = tuple(TLASTs)
    number_of_vals = len(TDATAs)
    value_index = Signal(intbv(0, min=0, max=number_of_vals + 1))

    internal_TVALID = Signal(False)

    @always(clock.posedge)
    def playback():

        if ((axi_interface.TREADY and internal_TVALID) or
            not internal_TVALID):

            if value_index < number_of_vals:
                # We don't actually need to set these when TVALID is low,
                # but there is no harm in doing so.
                axi_interface.TLAST.next = TLASTs[value_index]
                axi_interface.TDATA.next = TDATAs[value_index]

                internal_TVALID.next = TVALIDs[value_index]
                axi_interface.TVALID.next = TVALIDs[value_index]

                value_index.next = value_index + 1
            else:
                # The last output word
                if (axi_interface.TREADY and internal_TVALID):
                    internal_TVALID.next = False
                    axi_interface.TVALID.next = False

                value_index.next = value_index

    return playback
