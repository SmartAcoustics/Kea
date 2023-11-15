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
                 use_TLAST=True, use_TSTRB=False, use_TKEEP=False):
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

        if use_TLAST:
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

def check_axi_stream_interfaces_identical(axis_0, axis_1):
    ''' Raises an error if the axis interfaces do not match.
    '''

    mismatches = []

    if axis_0.bus_width != axis_1.bus_width:
        mismatches.append('bus_width')

    if axis_0.TID_width != axis_1.TID_width:
        mismatches.append('TID_width')

    if axis_0.TDEST_width != axis_1.TDEST_width:
        mismatches.append('TDEST_width')

    if axis_0.TUSER_width != axis_1.TUSER_width:
        mismatches.append('TUSER_width')

    if axis_0.TVALID._init != axis_1.TVALID._init:
        mismatches.append('TVALID_init')

    if axis_0.TREADY._init != axis_1.TREADY._init:
        mismatches.append('TREADY_init')

    if hasattr(axis_0, 'TLAST') != hasattr(axis_1, 'TLAST'):
        mismatches.append('use_TLAST')

    if hasattr(axis_0, 'TSTRB') != hasattr(axis_1, 'TSTRB'):
        mismatches.append('use_TSTRB')

    if hasattr(axis_0, 'TKEEP') != hasattr(axis_1, 'TKEEP'):
        mismatches.append('use_TKEEP')

    mismatches.sort()

    if len(mismatches) != 0:
        raise ValueError(
            'The following mismatches were detected on the AXI stream '
            'interfaces:' + ', '.join(mismatches))

class AxiStreamMasterBFM(object):

    def __init__(self):
        '''Create an AXI4 Stream master bus functional model (BFM).

        Data is added to the stream using the ``add_data`` method, at
        which point all the parameters can be set up for a particular sequence
        of transfers.

        Currently ``TUSER`` is ignored.
        '''
        self._data = {}
        self._TLASTs = {}

    def add_data(
        self, data, incomplete_last_packet=False, stream_ID=0,
        stream_destination=0):
        '''Add data to this BFM. ``data`` is a list of lists, each sublist of
        which comprises a packet (terminated by ``TLAST`` being asserted).

        If ``incomplete_last_packet`` is set to ``True``, the last packet in
        ``data`` will not raise the ``TLAST`` flag.

        Values inside each packet (i.e. the inner lists) can be ``None``, in
        which case the value acts like a no-op, setting the ``TVALID`` flag to
        ``False`` for that data value. This allows the calling code to insert
        delays in the data output.

        The ``stream_ID`` and ``stream_destination`` parameters are used to
        set the ``TID`` and ``TDEST`` signals respectively for the data
        provided.
        '''

        new_TLASTs = deque([True for packet in data])
        if incomplete_last_packet:
            if len(new_TLASTs) > 0:
                new_TLASTs[-1] = False

        try:
            self._data[(stream_ID, stream_destination)].extend(
                deque([deque(packet) for packet in data]))
            self._TLASTs[(stream_ID, stream_destination)].extend(new_TLASTs)

        except KeyError:
            self._data[(stream_ID, stream_destination)] = deque(
                [deque(packet) for packet in data])

            self._TLASTs[(stream_ID, stream_destination)] = new_TLASTs

    def add_multi_stream_data(self, data):
        ''' Add multi stream data to this BFM. Multi stream data should be a
        dictionary with each entry into the dict a list of lists as required
        by add_data. The dictionary keys should be of the form:

            (stream ID, stream dest)
        '''

        for stream in data.keys():
            self.add_data(
                data[stream], stream_ID=stream[0],
                stream_destination=stream[1])

    @block
    def model(self, clock, interface, reset=None):

        packets = {}
        packets_TLASTs = {}
        model_rundata = {}

        None_data = Signal(False)

        use_TLAST = hasattr(interface, 'TLAST')

        return_instances = []

        if use_TLAST:
            internal_TLAST = Signal(interface.TLAST.val)

            @always_comb
            def assign_TLAST():
                interface.TLAST.next = internal_TLAST

            return_instances.append(assign_TLAST)

        else:
            internal_TLAST = Signal(False)

        if interface.TDEST_width is not None:
            internal_TDEST = Signal(intbv(0)[interface.TDEST_width:])

            @always_comb
            def assign_TDEST():
                interface.TDEST.next = internal_TDEST

            return_instances.append(assign_TDEST)

        else:
            internal_TDEST = Signal(intbv(0)[4:])

        if interface.TID_width is not None:
            internal_TID = Signal(intbv(0)[interface.TID_width:])

            @always_comb
            def assign_TID():
                interface.TID.next = internal_TID

            return_instances.append(assign_TID)

        else:
            internal_TID = Signal(intbv(0)[4:])

        if reset is None:
            reset = False

        @always(clock.posedge)
        def model_inst():
            if reset:
                self._data.clear()
                packets.clear()
                packets_TLASTs.clear()
                interface.TVALID.next = False
                internal_TLAST.next = False

            else:

                for k in self._data.keys():
                    if k not in packets.keys():
                        if len(self._data[k]) > 0:
                            # self._data contains an ID and destination
                            # combination that is not in packets therefore we
                            # should add a packet from this combination.
                            packets[k] = self._data[k].popleft()
                            packets_TLASTs[k] = self._TLASTs[k].popleft()

                    if k in packets.keys():
                        while len(packets[k]) == 0:
                            # Length of the packet is zero so add the next one
                            if len(self._data[k]) > 0:
                                packets[k] = self._data[k].popleft()
                                packets_TLASTs[k] = self._TLASTs[k].popleft()

                            else:
                                del packets[k]
                                # Nothing left to get, so we drop out.
                                break

                # We need to try to update either when a piece of data has
                # been propagated (TVALID and TREADY) or when we previously
                # didn't have any data, or the data was None (not TVALID)
                if ((interface.TVALID and interface.TREADY) or
                    not interface.TVALID):

                    if len(tuple(packets.keys())) > 0:
                        # Randomly pick a packet.
                        model_rundata['packet_key'] = (
                            random.choice(tuple(packets.keys())))

                        if len(packets[model_rundata['packet_key']]) > 0:

                            internal_TID.next = (
                                model_rundata['packet_key'][0])
                            internal_TDEST.next = (
                                model_rundata['packet_key'][1])

                            if len(packets[model_rundata['packet_key']]) == 1:

                                internal_TLAST.next = (packets_TLASTs[
                                    model_rundata['packet_key']])
                                value = (packets[
                                    model_rundata['packet_key']].popleft())

                                # Nothing left in the packet
                                del packets[model_rundata['packet_key']]

                            else:
                                value = (packets[
                                    model_rundata['packet_key']].popleft())

                                # We need to set TLAST if all the remaining
                                # values in the packet are None
                                if all(
                                    [val is None for val in
                                     packets[model_rundata['packet_key']]]):

                                    internal_TLAST.next = (packets_TLASTs[
                                        model_rundata['packet_key']])
                                else:
                                    internal_TLAST.next = False

                            if value is not None:
                                None_data.next = False
                                interface.TDATA.next = value
                                interface.TVALID.next = True
                            else:
                                None_data.next = True
                                interface.TVALID.next = False

                        else:
                            interface.TVALID.next = False
                            # no data, so simply remove the packet for
                            # initialisation next time
                            del packets[model_rundata['packet_key']]

                    else:
                        interface.TVALID.next = False

        return_instances.append(model_inst)

        return return_instances

class AxiStreamSlaveBFM(object):
    '''An AXI4 Stream Slave MyHDL bus functional model which supports multiple
    channels as defined by TID and TDEST.
    '''

    @property
    def current_packets(self):
        return copy.deepcopy(self._current_packets)

    @property
    def completed_packets(self):
        return copy.deepcopy(self._completed_packets)

    @property
    def signal_record(self):
        return copy.deepcopy(self._signal_record)

    def __init__(self):
        '''Create an AXI4 Stream slave bus functional model (BFM).

        Valid data that is received is recorded. Completed packets are
        available for inspection through the ``completed_packets``
        property. This will return a dictionary of the received packets
        on all the streams. The stream TID and TDEST form the dictionary keys:
            tuple(TID, TDEST)
        The dictionary entries are a deque of deques where each sub deque is a
        new packet.

        The packet currently being populated can be found on the
        ``current_packets`` attribute. This provides a snapshot and does
        not change with the underlying data structure. This will return a
        dictionary of the current packets on all the streams. The stream TID
        and TDEST form the dictionary keys:
            tuple(TID, TDEST)
        The dictionary entries are a deque which is the current packet for
        that stream.

        Currently ``TUSER`` is ignored.

        The MyHDL model is instantiated using the ``model`` method.
        '''
        self._completed_packets = {}
        self._current_packets = {}

        self._signal_record = {
            'TDATA': deque([]),
            'TID': deque([]),
            'TDEST': deque([]),
            'TLAST': deque([]),
        }

    def reset(self):
        '''Clears the current set of completed and current packets.
        '''
        self._completed_packets.clear()
        self._current_packets.clear()

        self._signal_record.clear()
        self._signal_record['TDATA'] = deque([])
        self._signal_record['TID'] = deque([])
        self._signal_record['TDEST'] = deque([])
        self._signal_record['TLAST'] = deque([])

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

        model_rundata = {'stream': (0, 0)}

        use_TLAST = hasattr(interface, 'TLAST')

        return_instances = []

        if use_TLAST:
            internal_TLAST = Signal(interface.TLAST.val)

            @always_comb
            def assign_TLAST():
                internal_TLAST.next = interface.TLAST

            return_instances.append(assign_TLAST)

        else:
            internal_TLAST = Signal(False)

        if interface.TDEST_width is not None:
            internal_TDEST = (
                Signal(intbv(interface.TDEST.val)[interface.TDEST_width:]))

            @always_comb
            def assign_TDEST():
                internal_TDEST.next = interface.TDEST

            return_instances.append(assign_TDEST)

        else:
            internal_TDEST = Signal(intbv(0)[4:])

        if interface.TID_width is not None:
            internal_TID = (
                Signal(intbv(interface.TID.val)[interface.TID_width:]))

            @always_comb
            def assign_TID():
                internal_TID.next = interface.TID

            return_instances.append(assign_TID)

        else:
            internal_TID = Signal(intbv(0)[4:])

        if TREADY_probability is not None:

            @always(clock.posedge)
            def TREADY_driver():
                if TREADY_probability > random.random():
                    interface.TREADY.next = True
                else:
                    interface.TREADY.next = False

            return_instances.append(TREADY_driver)

        @always(clock.posedge)
        def model_inst():

            if interface.TREADY:
                if interface.TVALID:
                    self._signal_record['TDATA'].append(
                        copy.copy(int(interface.TDATA.val)))
                else:
                    self._signal_record['TDATA'].append(None)

                self._signal_record['TID'].append(
                    copy.copy(int(internal_TID.val)))
                self._signal_record['TDEST'].append(
                    copy.copy(int(internal_TDEST.val)))
                self._signal_record['TLAST'].append(
                    copy.copy(int(internal_TLAST.val)))

            if interface.TVALID and interface.TREADY:
                model_rundata['stream'] = (
                    copy.copy(int(internal_TID.val)),
                    copy.copy(int(internal_TDEST.val)))

                if model_rundata['stream'] not in (
                    self._current_packets.keys()):

                    # Stream does not yet exist in current packet record so
                    # create it and add the data
                    self._current_packets[model_rundata['stream']] = deque(
                        [copy.copy(int(interface.TDATA.val))])

                else:
                    self._current_packets[model_rundata['stream']].append(
                        copy.copy(int(interface.TDATA.val)))

                if internal_TLAST:
                    # End of a packet, so copy the current packet into
                    # complete_packets.
                    if model_rundata['stream'] not in (
                        self._completed_packets.keys()):

                        # Stream does not yet exist in completed packet record
                        # so create it and add the packet
                        self._completed_packets[model_rundata['stream']] = (
                            deque([self._current_packets[
                                model_rundata['stream']]]))

                    else:
                        # Add the packet to completed packets
                        self._completed_packets[
                            model_rundata['stream']].append(
                                self._current_packets[
                                    model_rundata['stream']])

                    # Packet has completed and been added to the completed
                    # packets dict so delete it
                    del self._current_packets[model_rundata['stream']]

        return_instances.append(model_inst)

        return return_instances

@block
def axi_stream_buffer(
    clock, axi_stream_in, axi_stream_out, passive_sink_mode=False):
    '''An AXI4 Stream MyHDL FIFO buffer with arbitrary depth.

    ``axi_stream_in`` is buffered until ``axi_stream_out`` is capable
    of handling the data.

    If ``passive_sink_mode`` is set to ``True``, this block will not touch
    the ``TREADY`` signal on ``axi_stream_in`` - it simply monitors the
    transactions and buffers them for ``axi_stream_out``.
    '''

    if ((axi_stream_in.TID_width is not None) and
        (axi_stream_out.TID_width is None)):
        raise ValueError(
            'There is a TID on the input and so there must be a TID on the '
            'output')

    if ((axi_stream_in.TDEST_width is not None) and
        (axi_stream_out.TDEST_width is None)):
        raise ValueError(
            'There is a TDEST on the input and so there must be a TDEST on '
            'the output')

    if ((axi_stream_in.TID_width is not None) and
        (axi_stream_out.TID_width is not None)):

        if axi_stream_in.TID_width > axi_stream_out.TID_width:
            raise ValueError(
                'TID on the output must be as wide or wider than TID on the '
                'input')

    if ((axi_stream_in.TDEST_width is not None) and
        (axi_stream_out.TDEST_width is not None)):

        if axi_stream_in.TDEST_width > axi_stream_out.TDEST_width:
            raise ValueError(
                'TDEST on the output must be as wide or wider than TDEST on '
                'the input')

    data_buffer = deque([])

    internal_input_TLAST = Signal(False)

    internal_TVALID = Signal(False)
    internal_TLAST = Signal(False)
    internal_TDATA = Signal(intbv(0)[len(axi_stream_out.TDATA):])

    data_in_buffer = Signal(False)
    use_internal_values = Signal(False)
    await_next_word_in = Signal(False)

    use_input_TLAST = hasattr(axi_stream_in, 'TLAST')
    use_output_TLAST = hasattr(axi_stream_out, 'TLAST')

    return_instances = []

    if use_input_TLAST:
        @always_comb
        def input_TLAST_assignment():
            internal_input_TLAST.next = axi_stream_in.TLAST

        return_instances.append(input_TLAST_assignment)

    if use_output_TLAST:
        @always_comb
        def output_TLAST_assignment():
            if use_internal_values:
                axi_stream_out.TLAST.next = internal_TLAST
            else:
                axi_stream_out.TLAST.next = internal_input_TLAST

        return_instances.append(output_TLAST_assignment)

    if axi_stream_in.TID_width is not None:

        internal_input_TID = (
            Signal(intbv(axi_stream_in.TID.val)[axi_stream_in.TID_width:]))
        internal_TID = (
            Signal(intbv(axi_stream_in.TID.val)[axi_stream_in.TID_width:]))

        @always_comb
        def input_TID_assignment():
            internal_input_TID.next = axi_stream_in.TID

        return_instances.append(input_TID_assignment)

    else:
        internal_input_TID = Signal(intbv(0)[4:])
        internal_TID = Signal(intbv(0)[4:])

    if axi_stream_out.TID_width is not None:

        @always_comb
        def output_TID_assignment():
            if use_internal_values:
                axi_stream_out.TID.next = internal_TID
            else:
                axi_stream_out.TID.next = internal_input_TID

        return_instances.append(output_TID_assignment)

    if axi_stream_in.TDEST_width is not None:

        internal_input_TDEST = (
            Signal(intbv(axi_stream_in.TDEST.val)[
                axi_stream_in.TDEST_width:]))
        internal_TDEST = (
            Signal(intbv(axi_stream_in.TDEST.val)[
                axi_stream_in.TDEST_width:]))

        @always_comb
        def input_TDEST_assignment():
            internal_input_TDEST.next = axi_stream_in.TDEST

        return_instances.append(input_TDEST_assignment)

    else:
        internal_input_TDEST = Signal(intbv(0)[4:])
        internal_TDEST = Signal(intbv(0)[4:])

    if axi_stream_out.TDEST_width is not None:

        @always_comb
        def output_TDEST_assignment():
            if use_internal_values:
                axi_stream_out.TDEST.next = internal_TDEST
            else:
                axi_stream_out.TDEST.next = internal_input_TDEST

        return_instances.append(output_TDEST_assignment)

    if not passive_sink_mode:

        @always(clock.posedge)
        def TREADY_driver():
            axi_stream_in.TREADY.next = True

        return_instances.append(TREADY_driver)

    @always_comb
    def output_assignments():

        if use_internal_values:
            axi_stream_out.TVALID.next = internal_TVALID
            axi_stream_out.TDATA.next = internal_TDATA

        elif await_next_word_in:
            axi_stream_out.TVALID.next = False
            axi_stream_out.TDATA.next = axi_stream_in.TDATA

        else:
            axi_stream_out.TVALID.next = axi_stream_in.TVALID
            axi_stream_out.TDATA.next = axi_stream_in.TDATA

    @always(clock.posedge)
    def model():
        transact_in = axi_stream_in.TREADY and axi_stream_in.TVALID
        transact_out = axi_stream_out.TREADY and axi_stream_out.TVALID

        if len(data_buffer) == 0:
            if (transact_in and not transact_out and not
                await_next_word_in) or (
                transact_in and use_internal_values):

                # There is no data in the buffer but the data has been read
                # in and the output is not ahead so add it to the data_buffer
                data_buffer.append(
                    (int(axi_stream_in.TDATA.val),
                     bool(internal_input_TLAST.val),
                     int(internal_input_TID.val),
                     int(internal_input_TDEST.val)))

            elif transact_out and not transact_in and use_internal_values:
                # No data in buffer and data has been read out so we should
                # stop using the internal values (ie the values stored in the
                # buffer
                use_internal_values.next = False

            if transact_out and not transact_in and not use_internal_values:
                # There has been a transaction out but no transaction in so we
                # need to wait for the input side to catch up
                await_next_word_in.next = True

            if await_next_word_in and transact_in:
                # The input side has caught up with the output side so we can
                # set await_next_word_in low
                await_next_word_in.next = False

        elif len(data_buffer) > 0 and transact_in:
            # If there is data in the buffer and a transaction in happens then
            # add it to the data buffer
            data_buffer.append(
                (int(axi_stream_in.TDATA.val), bool(internal_input_TLAST.val),
                 int(internal_input_TID.val), int(internal_input_TDEST.val)))

        # Data might have just been put into the buffer, so we always check it
        if len(data_buffer) > 0:
            if transact_out or (not transact_out and not use_internal_values):
                TDATA, TLAST, TID, TDEST = data_buffer.popleft()
                internal_TDATA.next = TDATA
                internal_TLAST.next = TLAST
                internal_TID.next = TID
                internal_TDEST.next = TDEST
                internal_TVALID.next = True
                use_internal_values.next = True

    return_instances.extend([model, output_assignments])

    return return_instances

@block
def axi_master_playback(
    clock, axi_interface, signal_record, incomplete_last_packet=False):
    '''A convertible block that plays back the signal_record over an AXI
    stream interface.

    If ``incomplete_last_packet`` is set to True, the final packet in the
    signal_record will not trigger the ``TLAST`` to be asserted. This means
    data streams for which ``TLAST`` is not meaningful can be modelled.
    '''

    if axi_interface.TID_width is not None:
        if len(signal_record['TDATA']) != len(signal_record['TID']):
            raise ValueError(
                'The length of the TID signal_record must be equal to the '
                'length of the TDATA signal_record')

    if axi_interface.TDEST_width is not None:
        if len(signal_record['TDATA']) != len(signal_record['TDEST']):
            raise ValueError(
                'The length of the TDEST signal_record must be equal to the '
                'length of the TDATA signal_record')

    use_TLAST = hasattr(axi_interface, 'TLAST')

    if use_TLAST:
        if len(signal_record['TDATA']) != len(signal_record['TLAST']):
            raise ValueError(
                'The length of the TLAST signal_record must be equal to the '
                'length of the TDATA signal_record')

    if len(signal_record['TDATA']) == 0:
        # We need a non-zero packet length to work around a myhdl conversion
        # bug with empty lists. The following satisfies everything. We have
        # already checked that these lists are the same length as TDATA so we
        # know they are also empty.
        signal_record['TDATA'] = [None]
        signal_record['TVALID'] = [0]
        signal_record['TID'] = [0]
        signal_record['TDEST'] = [0]
        signal_record['TLAST'] = [0]

    elif incomplete_last_packet:
        # incomplete last packet is true so determine the index of the final
        # TLAST.
        last_valid_value_index = 0
        for n, data_word in enumerate(reversed(signal_record['TDATA'])):
            if data_word is not None:
                last_valid_value_index = len(signal_record['TDATA']) - n - 1
                break

        # Set the final TLAST to False
        signal_record['TLAST'][last_valid_value_index] = 0

    # From the signal_record, we preload all the values that should be
    # output. This is TDATA, TVALID, TID, TDEST and TLAST
    TDATAs = tuple(
        val if val is not None else 0 for val in signal_record['TDATA'])

    TVALIDs = tuple(
        1 if val is not None else 0 for val in signal_record['TDATA'])

    TIDs = tuple(val for val in signal_record['TID'])
    TDESTs = tuple(val for val in signal_record['TDEST'])
    TLASTs = tuple(val for val in signal_record['TLAST'])

    number_of_vals = len(TDATAs)
    value_index = Signal(intbv(0, min=0, max=number_of_vals + 1))

    internal_TVALID = Signal(False)

    return_instances = []

    if use_TLAST:

        @always(clock.posedge)
        def playback_TLAST():
            # Replicates the logic of playback_core in terms of when to
            # playback the signals
            if ((axi_interface.TREADY and internal_TVALID) or
                not internal_TVALID):

                if value_index < number_of_vals:
                    axi_interface.TLAST.next = TLASTs[value_index]

        return_instances.append(playback_TLAST)

    else:
        playback_TLAST = None

    if axi_interface.TID_width is not None:
        @always(clock.posedge)
        def playback_TID():
            # Replicates the logic of playback_core in terms of when to
            # playback the signals
            if ((axi_interface.TREADY and internal_TVALID) or
                not internal_TVALID):

                if value_index < number_of_vals:
                    axi_interface.TID.next = TIDs[value_index]

        return_instances.append(playback_TID)

    else:
        playback_TID = None

    if axi_interface.TDEST_width is not None:
        @always(clock.posedge)
        def playback_TDEST():
            # Replicates the logic of playback_core in terms of when to
            # playback the signals
            if ((axi_interface.TREADY and internal_TVALID) or
                not internal_TVALID):

                if value_index < number_of_vals:
                    axi_interface.TDEST.next = TDESTs[value_index]

        return_instances.append(playback_TDEST)

    else:
        playback_TDEST = None

    @always(clock.posedge)
    def playback_core():

        if ((axi_interface.TREADY and internal_TVALID) or
            not internal_TVALID):

            if value_index < number_of_vals:
                # We don't actually need to set these when TVALID is low,
                # but there is no harm in doing so.
                axi_interface.TDATA.next = TDATAs[value_index]

                internal_TVALID.next = TVALIDs[value_index]
                axi_interface.TVALID.next = TVALIDs[value_index]

                value_index.next = value_index + 1
            else:
                # The last output word
                if (axi_interface.TREADY and internal_TVALID):
                    internal_TVALID.next = 0
                    axi_interface.TVALID.next = 0

                value_index.next = value_index

    return_instances.append(playback_core)

    return return_instances
