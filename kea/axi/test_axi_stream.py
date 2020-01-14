from .axi_stream import (
    AxiStreamInterface, AxiStreamMasterBFM, AxiStreamSlaveBFM,
    axi_stream_buffer, axi_master_playback)
from unittest import TestCase
from veriutils import myhdl_cosimulation
from myhdl import *
import myhdl

from ovenbird import vivado_verilog_cosimulation, vivado_vhdl_cosimulation

from collections import deque
import random

import os
import tempfile
import shutil
import copy
import itertools

class TestAxiStreamInterface(TestCase):
    '''There should be an AXI4 Stream object that encapsulates all the AXI
    stream signals.
    '''
    def test_bus_width_property(self):
        '''There should be a bus width property which is an integer set
        by the first position ``bus_width`` keyword argument, defaulting to 4.
        '''
        interface = AxiStreamInterface()
        self.assertEqual(interface.bus_width, 4)

        interface = AxiStreamInterface(8)
        self.assertEqual(interface.bus_width, 8)

        interface = AxiStreamInterface('6')
        self.assertEqual(interface.bus_width, 6)

        interface = AxiStreamInterface(bus_width=16)
        self.assertEqual(interface.bus_width, 16)

    def test_TDATA(self):
        '''There should be a TDATA attribute that is an unsigned intbv Signal
        that is 8*bus_width bits wide.
        '''
        interface = AxiStreamInterface()
        self.assertTrue(isinstance(interface.TDATA, myhdl._Signal._Signal))
        self.assertTrue(isinstance(interface.TDATA._val, intbv))
        self.assertEqual(len(interface.TDATA._val), interface.bus_width*8)

        interface = AxiStreamInterface(bus_width='5')
        self.assertEqual(len(interface.TDATA._val), interface.bus_width*8)

    def test_TSTRB(self):
        '''There should be an optional TSTRB attribute that is an unsigned
        intbv Signal that is bus_width bits wide and is full range.
        '''
        # The default case is not to include it
        interface = AxiStreamInterface()
        self.assertFalse(hasattr(interface, 'TSTRB'))

        interface = AxiStreamInterface(use_TSTRB=True)
        self.assertTrue(isinstance(interface.TSTRB, myhdl._Signal._Signal))
        self.assertTrue(isinstance(interface.TSTRB._val, intbv))
        self.assertEqual(len(interface.TSTRB._val), interface.bus_width)
        self.assertEqual(interface.TSTRB.min, 0)
        self.assertEqual(interface.TSTRB.max, 2**(interface.bus_width))

        interface = AxiStreamInterface(bus_width='6', use_TSTRB=True)
        self.assertEqual(len(interface.TSTRB._val), interface.bus_width)

    def test_TKEEP(self):
        '''There should be an optional TKEEP attribute that is an unsigned
        intbv Signal that is bus_width bits wide and is full range.
        '''
        # The default case is not to include it
        interface = AxiStreamInterface()
        self.assertFalse(hasattr(interface, 'TKEEP'))

        interface = AxiStreamInterface(use_TKEEP=True)
        self.assertTrue(isinstance(interface.TKEEP, myhdl._Signal._Signal))
        self.assertTrue(isinstance(interface.TKEEP._val, intbv))
        self.assertEqual(len(interface.TKEEP._val), interface.bus_width)
        self.assertEqual(interface.TKEEP.min, 0)
        self.assertEqual(interface.TKEEP.max, 2**(interface.bus_width))

        interface = AxiStreamInterface(bus_width=8, use_TKEEP=True)
        self.assertEqual(len(interface.TKEEP._val), interface.bus_width)

    def test_TVALID(self):
        '''There should be a TVALID attribute that is a boolean Signal.
        '''
        interface = AxiStreamInterface()
        self.assertTrue(isinstance(interface.TVALID, myhdl._Signal._Signal))
        self.assertTrue(isinstance(interface.TVALID._val, (intbv, bool)))
        self.assertEqual(len(interface.TVALID), 1)

    def test_TREADY(self):
        '''There should be a TREADY attribute that is a boolean Signal.
        '''
        interface = AxiStreamInterface()
        self.assertTrue(isinstance(interface.TREADY, myhdl._Signal._Signal))
        self.assertTrue(isinstance(interface.TREADY._val, (intbv, bool)))
        self.assertEqual(len(interface.TREADY), 1)

    def test_TLAST(self):
        '''There should be a TLAST attribute that is a boolean Signal.

        It should be disabled by setting ``use_TLAST`` to False.
        '''
        interface = AxiStreamInterface()
        self.assertTrue(isinstance(interface.TLAST, myhdl._Signal._Signal))
        self.assertTrue(isinstance(interface.TLAST._val, (intbv, bool)))
        self.assertEqual(len(interface.TLAST), 1)

        interface = AxiStreamInterface(use_TLAST=False)
        self.assertFalse(hasattr(interface, 'TLAST'))


    def test_TID_width_property(self):
        '''There should be a TID_width property which is set by the
        ``TID_width`` keyword argument, the default of which is ``None``.
        '''
        interface = AxiStreamInterface()
        self.assertIs(interface.TID_width, None)

        interface = AxiStreamInterface(TID_width=10)
        self.assertEqual(interface.TID_width, 10)

        interface = AxiStreamInterface(TID_width='6')
        self.assertEqual(interface.TID_width, 6)

    def test_TID(self):
        '''There should be an optional TID attribute that is an intbv Signal
        of width set by the ``TID_width`` argument. If ``TID_width`` is
        ``None`` or not set then the attribute should not exist.
        '''
        interface = AxiStreamInterface()
        with self.assertRaises(AttributeError):
            interface.TID

        interface = AxiStreamInterface(TID_width=None)
        with self.assertRaises(AttributeError):
            interface.TID

        interface = AxiStreamInterface(TID_width=10)
        self.assertTrue(isinstance(interface.TID, myhdl._Signal._Signal))
        self.assertTrue(isinstance(interface.TID._val, intbv))
        self.assertEqual(len(interface.TID._val), interface.TID_width)

    def test_TDEST_width_property(self):
        '''There should be a TDEST_width property which is set by the
        ``TDEST_width`` keyword argument, the default of which is ``None``.
        '''
        interface = AxiStreamInterface()
        self.assertIs(interface.TDEST_width, None)

        interface = AxiStreamInterface(TDEST_width=10)
        self.assertEqual(interface.TDEST_width, 10)

        interface = AxiStreamInterface(TDEST_width='6')
        self.assertEqual(interface.TDEST_width, 6)

    def test_TDEST(self):
        '''There should be an optional TDEST attribute that is an intbv Signal
        of width set by the ``TDEST_width`` argument. If ``TDEST_width`` is
        ``None`` or not set then the attribute should not exist.
        '''
        interface = AxiStreamInterface()
        with self.assertRaises(AttributeError):
            interface.TDEST

        interface = AxiStreamInterface(TDEST_width=None)
        with self.assertRaises(AttributeError):
            interface.TDEST

        interface = AxiStreamInterface(TDEST_width=10)
        self.assertTrue(isinstance(interface.TDEST, myhdl._Signal._Signal))
        self.assertTrue(isinstance(interface.TDEST._val, intbv))
        self.assertEqual(len(interface.TDEST._val), interface.TDEST_width)

    def test_TUSER_width_property(self):
        '''There should be a TUSER_width property which is set by the
        ``TUSER_width`` keyword argument, the default of which is ``None``.
        '''
        interface = AxiStreamInterface()
        self.assertIs(interface.TUSER_width, None)

        interface = AxiStreamInterface(TUSER_width=10)
        self.assertEqual(interface.TUSER_width, 10)

        interface = AxiStreamInterface(TUSER_width='6')
        self.assertEqual(interface.TUSER_width, 6)

    def test_TUSER(self):
        '''There should be an optional TUSER attribute that is an intbv Signal
        of width set by the ``TUSER_width`` argument. If ``TUSER_width`` is
        ``None`` or not set then the attribute should not exist.
        '''
        interface = AxiStreamInterface()
        with self.assertRaises(AttributeError):
            interface.TUSER

        interface = AxiStreamInterface(TUSER_width=None)
        with self.assertRaises(AttributeError):
            interface.TUSER

        interface = AxiStreamInterface(TUSER_width=10)
        self.assertTrue(isinstance(interface.TUSER, myhdl._Signal._Signal))
        self.assertTrue(isinstance(interface.TUSER._val, intbv))
        self.assertEqual(len(interface.TUSER._val), interface.TUSER_width)

    def test_TVALID_init(self):
        '''It should be possible to set an initial value for TVALID through
        an __init__ argument, TVALID_init.
        '''
        interface = AxiStreamInterface()
        self.assertEqual(interface.TVALID, 0)

        interface = AxiStreamInterface(TVALID_init=True)
        self.assertEqual(interface.TVALID, 1)

        interface = AxiStreamInterface(TVALID_init=1)
        self.assertEqual(interface.TVALID, 1)

        interface = AxiStreamInterface(TVALID_init=False)
        self.assertEqual(interface.TVALID, 0)

    def test_TREADY_init(self):
        '''It should be possible to set an initial value for TREADY through
        an __init__ argument, TREADY_init.
        '''
        interface = AxiStreamInterface()
        self.assertEqual(interface.TREADY, 0)

        interface = AxiStreamInterface(TREADY_init=True)
        self.assertEqual(interface.TREADY, 1)

        interface = AxiStreamInterface(TREADY_init=1)
        self.assertEqual(interface.TREADY, 1)

        interface = AxiStreamInterface(TREADY_init=False)
        self.assertEqual(interface.TREADY, 0)

def _get_next_val(packet_list, instance_data):

    try:
        try:
            assert isinstance(instance_data['packet'], deque)
            next_val = instance_data['packet'].popleft()
        except KeyError:
            raise IndexError

    except IndexError:
        instance_data['packet'] = []
        while len(instance_data['packet']) == 0:
            if len(packet_list) == 0:
                return None

            else:
                instance_data['packet'] = packet_list.popleft()

        next_val = instance_data['packet'].popleft()

    return next_val

def _add_packets_to_stream(stream, packet_list, **kwargs):
    '''Adds the supplied packets to the stream and returns them.
    '''
    packet_list = deque(deque(packet) for packet in packet_list)
    stream.add_data(packet_list, **kwargs)
    return packet_list

def _add_random_packets_to_stream(
    stream, max_packet_length, max_new_packets, max_val, **kwargs):
    '''Adds a load of random data to the stream and returns
    the list of added packets.

    Each packet is of random length between 0 and max_packet_length
    and there are a random number between 0 and max_new_packets of
    them.
    '''
    packet_list = deque(
        [deque([random.randrange(0, max_val) for m
                in range(random.randrange(0, max_packet_length))]) for n
         in range(random.randrange(0, max_new_packets))])

    return _add_packets_to_stream(stream, packet_list, **kwargs)

def _generate_random_packets_with_Nones(
    data_byte_width, max_packet_length, max_new_packets):

    def val_gen(data_byte_width):
        # Generates Nones about half the time probability
        val = random.randrange(0, 2**(8 * data_byte_width))
        if val > 2**(8 * data_byte_width - 1):
            return None
        else:
            return val

    packet_list = deque(
        [deque([
            val_gen(data_byte_width) for m
            in range(random.randrange(0, max_packet_length))]) for n
            in range(random.randrange(0, max_new_packets))])

    total_data_len = sum(len(each) for each in packet_list)

    None_trimmed_packet_list = deque([
        deque([val for val in packet if val is not None]) for packet in
        packet_list])

    trimmed_packets = deque([
        packet for packet in None_trimmed_packet_list if len(packet) > 0])

    return packet_list, trimmed_packets, total_data_len

def generate_unique_streams(
    n_streams, max_id_value, max_dest_value, min_id_value=0,
    min_dest_value=0):
    ''' This block will return a list of length ``n_streams`` of random and
    unique stream identifiers (TID and TDEST). Each element in the list will
    be a tuple of the form (TID, TDEST).
    '''

    streams = set()

    for n in range(n_streams):
        stream = (
            random.randrange(min_id_value, max_id_value),
            random.randrange(min_dest_value, max_dest_value))

        while stream in streams:
            stream = (
                random.randrange(min_id_value, max_id_value),
                random.randrange(min_dest_value, max_dest_value))

        streams.add(stream)

    return list(streams)

def trim_empty_packets_and_streams(data):
    ''' This function takes in dict of streams containing the packet data and
    removes any empy packets and streams with no data.
    '''

    streams = data.keys()

    trimmed_data = copy.deepcopy(data)

    for stream in streams:
        while deque([]) in trimmed_data[(stream[0], stream[1])]:
            # Remove any empty packets from the stream as these will
            # not feature in recorded data.
            trimmed_data[(stream[0], stream[1])].remove(deque([]))

        if len(trimmed_data[(stream[0], stream[1])]) == 0:
            # Remove any streams which do not contain any packets as
            # these will not feature in the recorded data
            del(trimmed_data[(stream[0], stream[1])])

    return trimmed_data

def packetise_signal_record(signal_record):
    ''' This function takes a signal_record as produced by the
    AxiStreamSlaveBFM and converts it into a completed_packets
    dictionary of the same form as the completed_packets property on
    AxiStreamSlaveBFM.

    The signal record dictionary should contain these keys:

        TDATA
        TID
        TDEST
        TLAST

    Each of theses keys refers to a list of values received on their
    corresponding signal. A none in TDATA means the validity was low.
    '''

    packetised_signal_record = {}

    for n in range(len(signal_record['TDATA'])):
        if signal_record['TDATA'][n] is not None:

            # Determine the stream
            stream_id = signal_record['TID'][n]
            stream_dest = signal_record['TDEST'][n]
            stream = (stream_id, stream_dest)

            if stream in packetised_signal_record.keys():
                # We have already seen packets on this stream so append the
                # data
                packetised_signal_record[stream][-1].append(
                    signal_record['TDATA'][n])

            else:
                # This is the first packet on this stream so add the stream
                # to the record.
                packetised_signal_record[stream] = deque(
                    [deque([signal_record['TDATA'][n]])])

            if signal_record['TLAST'][n]:
                # This is the last word in the packet so add another
                packetised_signal_record[stream].append(deque([]))

    packetised_signal_record = trim_empty_packets_and_streams(
        packetised_signal_record)

    return packetised_signal_record

def gen_random_signal_record(
    max_n_streams, max_packet_length, max_n_packets_per_stream,
    max_data_value, max_id_value, max_dest_value, include_nones=False,
    min_n_streams=0, min_packet_length=0, min_n_packets_per_stream=0):
    ''' This function creates a signal record of the form produced by the
    AxiStreamSlaveBFMrequired and required by the axi_master_playback block.

    If include_nones is true, this function will included Nones in the data
    stream with approximately 50 per cent probability that an entry will be
    None.
    '''

    # Randomly determine the number of streams
    n_streams = random.randrange(min_n_streams, max_n_streams)

    streams = generate_unique_streams(n_streams, max_id_value, max_dest_value)

    # Create and populate a packet list with streams and packetised data.
    packet_list = {}
    for stream in streams:
        packet_list[stream] = deque([
            deque([random.randrange(0, max_data_value) for m
             in range(random.randrange(min_packet_length, max_packet_length))]) for n
            in range(random.randrange(min_n_packets_per_stream, max_n_packets_per_stream))])

    # Trim any empty packets and streams
    trimmed_packet_list = trim_empty_packets_and_streams(packet_list)

    signal_record = {}
    signal_record['TDATA'] = deque([])
    signal_record['TLAST'] = deque([])
    signal_record['TID'] = deque([])
    signal_record['TDEST'] = deque([])

    while len(trimmed_packet_list) > 0:

        if include_nones and random.random() < 0.5:
            # With about 50 per cent probability add Nones to the data stream
            # and randomise the values on the other signals
            signal_record['TDATA'].append(None)
            stream = random.choice(list(trimmed_packet_list.keys()))
            signal_record['TID'].append(stream[0])
            signal_record['TDEST'].append(stream[1])
            signal_record['TLAST'].append(random.randrange(2))

        else:
            # Randomly pick a stream from which to take the next data word
            stream = random.choice(list(trimmed_packet_list.keys()))

            # Append that data word to the data stream along with the
            # corresponding TID and TDEST
            signal_record['TDATA'].append(
                trimmed_packet_list[stream][0].popleft())
            signal_record['TID'].append(stream[0])
            signal_record['TDEST'].append(stream[1])

            if len(trimmed_packet_list[stream][0]) == 0:
                # If we're at the end of a packet add a TLAST
                signal_record['TLAST'].append(1)
                trimmed_packet_list[stream].popleft()

            else:
                signal_record['TLAST'].append(0)

            if len(trimmed_packet_list[stream]) == 0:
                # No more data in the stream
                del(trimmed_packet_list[stream])

    return signal_record, trim_empty_packets_and_streams(packet_list)

class AxiStreamRecorder(object):

    def __init__(self):
        ''' This block will record the data received over the axis interface.

        It maintains a record of the current packets in a packets_in_progress
        dict. Each individual stream (as indicated by the combination of TID
        and TDEST) has its own entry in the dict. The data is stored in a
        deque within the dict.

        When a packet completes (as indicated by TLAST going high) the deque
        in the packets_in_progress dict will be added to the recorded_data
        dict. Each stream has its own entry in the dict. Each stream is a
        deque of deques where the sub deque is a complete packet.
        '''
        self.packets_in_progress = {}
        self.recorded_data = {}

    def get_packets_in_progress(self):
        return copy.deepcopy(self.packets_in_progress)

    def get_recorded_data(self):
        return copy.deepcopy(self.recorded_data)

    def clear_data(self):
        self.packets_in_progress.clear()
        self.recorded_data.clear()

    @block
    def axis_recorder(self, clock, axis):

        inst_data = {
            'stream_id': 0,
            'stream_dest': 0,
            'stream': (0, 0)}

        TLAST = Signal(False)

        if hasattr(axis, 'TLAST'):
            @always_comb
            def assign_TLAST():
                TLAST.next = axis.TLAST

        else:
            @always(clock.posedge)
            def assign_TLAST():
                TLAST.next = False

        @always(clock.posedge)
        def inst():

            if axis.TREADY and axis.TVALID:

                # Extract the TID and TDEST of the stream
                inst_data['stream_id'] = copy.copy(axis.TID.val)
                inst_data['stream_dest'] = copy.copy(axis.TDEST.val)

                # Combine them into a stream identifier
                inst_data['stream'] = (
                    int(inst_data['stream_id']),
                    int(inst_data['stream_dest']))

                if inst_data['stream'] not in self.packets_in_progress.keys():
                    # If we don't have any data from this stream recorded so
                    # create the record and add the data.
                    self.packets_in_progress[inst_data['stream']] = deque()
                    self.packets_in_progress[inst_data['stream']].append(
                        copy.copy(axis.TDATA.val))

                else:
                    # We have already received data on this stream so add it
                    # to the recorded data for that stream
                    self.packets_in_progress[inst_data['stream']].append(
                        copy.copy(axis.TDATA.val))

                if TLAST:
                    # Packet has completed so add it to the recorded_data
                    if inst_data['stream'] not in self.recorded_data.keys():
                        # If the recorded_data doesn't contain any data from
                        # this stream then create the stream in the record and
                        # add the packet
                        self.recorded_data[inst_data['stream']] = deque()
                        self.recorded_data[inst_data['stream']].append(
                            copy.copy(
                                self.packets_in_progress[inst_data['stream']]))

                    else:
                        # Add the packet to the record
                        self.recorded_data[inst_data['stream']].append(
                            copy.copy(
                                self.packets_in_progress[inst_data['stream']]))

                    # Packet has completed and been recorded so remove it from
                    # packets_in_progress
                    del self.packets_in_progress[inst_data['stream']]

        return inst, assign_TLAST

class TestAxiStreamMasterBFM(TestCase):
    '''There should be an AXI Stream Bus Functional Model that implements
    a programmable AXI4 Stream protocol from the master side.
    '''

    def setUp(self):

        self.data_byte_width = 8
        self.max_packet_length = 10
        self.max_new_packets = 5
        self.max_rand_val = 2**(8 * self.data_byte_width)

        self.stream = AxiStreamMasterBFM()
        self.interface = AxiStreamInterface(self.data_byte_width)
        clock = Signal(bool(0))

        self.args = {'clock': clock}
        self.arg_types = {'clock': 'clock'}

    def test_single_stream_data(self):
        '''It should be possible to set the data for a single stream.

        When data is available, TVALID should be set. When TVALID is not set
        it should indicate the data is to be ignored.
        '''

        @block
        def testbench(clock):

            bfm = self.stream.model(clock, self.interface)
            inst_data = {}
            @always(clock.posedge)
            def inst():
                self.interface.TREADY.next = True

                if self.interface.TVALID:
                    next_expected_val = _get_next_val(packet_list, inst_data)

                    assert self.interface.TDATA == next_expected_val
                    cycle_count[0] += 1

                else:
                    # Stop if there is nothing left to process
                    if len(packet_list) == 0:
                        raise StopSimulation

                    elif all(len(each) == 0 for each in packet_list):
                        raise StopSimulation


            return inst, bfm

        for n in range(30):
            packet_list = _add_random_packets_to_stream(
                self.stream, self.max_packet_length, self.max_new_packets,
                self.max_rand_val)

            total_data_len = sum(len(each) for each in packet_list)
            cycle_count = [0]

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

            self.assertEqual(total_data_len, cycle_count[0])

    def test_alternative_ID_and_destinations(self):
        '''It should be possible to set the ID and destination with the
        ``add_data`` method.

        All the data set for each pairing of ID and destination should
        exist on a separate FIFO and the data should be interleaved
        randomly.
        '''

        interface = AxiStreamInterface(
            self.data_byte_width, TID_width=4, TDEST_width=4)

        @block
        def testbench(clock):

            bfm = self.stream.model(clock, interface)
            inst_data = {}
            @always(clock.posedge)
            def inst():
                interface.TREADY.next = True

                if interface.TVALID:
                    next_expected_val = _get_next_val(
                        packet_list[stream_ID, stream_destination], inst_data)

                    assert interface.TID == stream_ID
                    assert interface.TDEST == stream_destination
                    assert interface.TDATA == next_expected_val
                    cycle_count[0] += 1

                else:
                    # Stop if there is nothing left to process
                    if len(packet_list[stream_ID, stream_destination]) == 0:
                        raise StopSimulation

                    elif all(
                        len(each) == 0 for each in
                        packet_list[stream_ID, stream_destination]):

                        raise StopSimulation

            return inst, bfm

        for n in range(30):
            packet_list = {}

            stream_ID = random.randrange(0, 2**len(interface.TID))
            stream_destination = random.randrange(0, 2**len(interface.TDEST))

            packet_list[(stream_ID, stream_destination)] = (
                _add_random_packets_to_stream(
                    self.stream, self.max_packet_length, self.max_new_packets,
                    self.max_rand_val, stream_ID=stream_ID,
                    stream_destination=stream_destination))

            total_data_len = sum(
                len(each) for each in
                packet_list[(stream_ID, stream_destination)])
            cycle_count = [0]

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

            self.assertEqual(total_data_len, cycle_count[0])

    def test_multiple_stream_data(self):
        '''It should be possible to set the data for multiple streams by
        defining the ``stream_ID`` and ``stream_destination`` in the arguments
        to the ``add_data`` function.

        When data is available, TVALID should be set. When TVALID is not set
        it should indicate the data is to be ignored.

        The DUT should randomly select a stream to output. Each stream should
        be identifiable by TDEST and TID.
        '''

        interface = AxiStreamInterface(
            self.data_byte_width, TID_width=4, TDEST_width=4)
        recorder = AxiStreamRecorder()

        @block
        def testbench(clock):

            bfm = self.stream.model(clock, interface)
            axis_recorder = recorder.axis_recorder(clock, interface)

            reset_when_tvalid_low = Signal(False)

            @always(clock.posedge)
            def inst():
                interface.TREADY.next = True

                # Need to give the system one cycle to set TVALID.
                reset_when_tvalid_low.next = True

                if not interface.TVALID and reset_when_tvalid_low:
                    raise StopSimulation

            return inst, bfm, axis_recorder

        for n in range(30):
            packet_list = {}

            max_stream_id = 2**len(interface.TID)
            max_stream_dest = 2**len(interface.TDEST)

            min_n_streams = 2
            max_n_streams = 20
            n_streams = random.randrange(min_n_streams, max_n_streams)

            # Generate a list of random and unique combinations of TID and
            # TDEST
            streams = generate_unique_streams(
                n_streams, max_stream_id, max_stream_dest)

            for stream in streams:
                # Create a list of packets to send
                packet_list[stream] = (
                    _add_random_packets_to_stream(
                        self.stream, self.max_packet_length,
                        self.max_new_packets, self.max_rand_val,
                        stream_ID=stream[0],
                        stream_destination=stream[1]))

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

            # Get the data out of the axis recorder
            packets_in_progress = recorder.get_packets_in_progress()
            recorded_data = recorder.get_recorded_data()
            recorder.clear_data()

            trimmed_packet_list = trim_empty_packets_and_streams(packet_list)

            # As we have enabled TLAST packets in progress should be empty
            self.assertTrue(len(packets_in_progress)==0)
            self.assertTrue(trimmed_packet_list == recorded_data)

    def test_add_multi_stream_data(self):
        '''It should be possible to set the data for multiple streams using
        the ``add_multi_stream_data`` function.

        When data is available, TVALID should be set. When TVALID is not set
        it should indicate the data is to be ignored.

        The DUT should randomly select a stream to output. Each stream should
        be identifiable by TDEST and TID.
        '''

        interface = AxiStreamInterface(
            self.data_byte_width, TID_width=4, TDEST_width=4)
        recorder = AxiStreamRecorder()

        @block
        def testbench(clock):

            bfm = self.stream.model(clock, interface)
            axis_recorder = recorder.axis_recorder(clock, interface)

            reset_when_tvalid_low = Signal(False)

            @always(clock.posedge)
            def inst():
                interface.TREADY.next = True

                # Need to give the system one cycle to set TVALID.
                reset_when_tvalid_low.next = True

                if not interface.TVALID and reset_when_tvalid_low:
                    raise StopSimulation

            return inst, bfm, axis_recorder

        for n in range(30):
            packet_list = {}

            max_stream_id = 2**len(interface.TID)
            max_stream_dest = 2**len(interface.TDEST)

            min_n_streams = 2
            max_n_streams = 20
            n_streams = random.randrange(min_n_streams, max_n_streams)

            # Generate a list of random and unique combinations of TID and
            # TDEST
            streams = generate_unique_streams(
                n_streams, max_stream_id, max_stream_dest)

            for stream in streams:
                # Create a list of packets to send
                packet_list[stream] = deque([deque([
                    random.randrange(0, self.max_rand_val) for m
                    in range(random.randrange(0, self.max_packet_length))]) for n
                    in range(random.randrange(0, self.max_new_packets))])

            self.stream.add_multi_stream_data(packet_list)

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

            # Get the data out of the axis recorder
            packets_in_progress = recorder.get_packets_in_progress()
            recorded_data = recorder.get_recorded_data()
            recorder.clear_data()

            trimmed_packet_list = trim_empty_packets_and_streams(packet_list)

            # As we have enabled TLAST packets in progress should be empty
            self.assertTrue(len(packets_in_progress)==0)
            self.assertTrue(trimmed_packet_list == recorded_data)

    def test_TLAST_asserted_correctly(self):
        '''TLAST should be raised for the last word in a packet and must
        be deasserted before the beginning of the next packet.

        When data is available, TVALID should be set. When TVALID is not set
        it should indicate the data is to be ignored.
        '''

        @block
        def testbench(clock):

            bfm = self.stream.model(clock, self.interface)
            inst_data = {}
            @always(clock.posedge)
            def inst():
                self.interface.TREADY.next = True

                if self.interface.TVALID:
                    next_expected_val = _get_next_val(packet_list, inst_data)

                    if len(inst_data['packet']) == 0:
                        # The last word in the packet
                        assert self.interface.TLAST
                    else:
                        assert not self.interface.TLAST

                    cycle_count[0] += 1

                else:
                    # TVALID being false is a condition of the test
                    assert not self.interface.TVALID

                    # Stop if there is nothing left to process
                    if len(packet_list) == 0:
                        raise StopSimulation

                    elif all(len(each) == 0 for each in packet_list):
                        raise StopSimulation

            return inst, bfm

        #run the test several times to better sample the test space
        for n in range(30):
            packet_list = _add_random_packets_to_stream(
                self.stream, self.max_packet_length, self.max_new_packets,
                self.max_rand_val)
            total_data_len = sum(len(each) for each in packet_list)
            cycle_count = [0]

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

            self.assertEqual(total_data_len, cycle_count[0])

    def test_missing_TLAST(self):
        '''If the interface is missing TLAST, it should simply be ignored.

        In effect, the packets lose their boundary information.
        '''

        interface = AxiStreamInterface(self.data_byte_width, use_TLAST=False)

        @block
        def testbench(clock):

            bfm = self.stream.model(clock, interface)
            inst_data = {}
            @always(clock.posedge)
            def inst():
                interface.TREADY.next = True

                if interface.TVALID:
                    next_expected_val = _get_next_val(packet_list, inst_data)

                    assert interface.TDATA == next_expected_val
                    cycle_count[0] += 1

                else:
                    # Stop if there is nothing left to process
                    if len(packet_list) == 0:
                        raise StopSimulation

                    elif all(len(each) == 0 for each in packet_list):
                        raise StopSimulation


            return inst, bfm

        for n in range(30):
            packet_list = _add_random_packets_to_stream(
                self.stream, self.max_packet_length, self.max_new_packets,
                self.max_rand_val)

            total_data_len = sum(len(each) for each in packet_list)
            cycle_count = [0]

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

            self.assertEqual(total_data_len, cycle_count[0])

    def test_incomplete_last_packet_argument(self):
        '''It should be possible to set an argument when adding packets so
        that the completion of the last packet does not set the TLAST flag.

        This means it should be possible to add one continuous packet without
        TLAST being asserted.
        '''

        @block
        def testbench(clock):

            bfm = self.stream.model(clock, self.interface)
            inst_data = {}
            @always(clock.posedge)
            def inst():
                self.interface.TREADY.next = True

                if self.interface.TVALID:
                    next_expected_val = _get_next_val(packet_list, inst_data)

                    if (len(inst_data['packet']) == 0 and
                        len(packet_list) != 0):

                        # The last word in the packet
                        assert self.interface.TLAST
                    else:
                        assert not self.interface.TLAST

                    cycle_count[0] += 1

                else:
                    # TVALID being false is a condition of the test
                    assert not self.interface.TVALID

                    # Stop if there is nothing left to process
                    if len(packet_list) == 0:
                        raise StopSimulation

                    elif all(len(each) == 0 for each in packet_list):
                        raise StopSimulation

            return inst, bfm

        #run the test several times to better sample the test space
        for n in range(30):
            packet_list = _add_random_packets_to_stream(
                self.stream, self.max_packet_length, self.max_new_packets,
                self.max_rand_val, incomplete_last_packet=True)
            total_data_len = sum(len(each) for each in packet_list)
            cycle_count = [0]

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

            self.assertEqual(total_data_len, cycle_count[0])

    def test_add_new_packets_during_simulation(self):
        '''It should be possible to add packets whilst a simulation is running
        '''

        @block
        def testbench(clock):

            bfm = self.stream.model(clock, self.interface)
            inst_data = {
                'available_delay': random.randrange(0, 10),
                'tried_adding_during_run': False}

            @always(clock.posedge)
            def inst():
                self.interface.TREADY.next = True
                if self.interface.TVALID:
                    next_expected_val = _get_next_val(packet_list, inst_data)

                    assert self.interface.TDATA == next_expected_val
                    if len(inst_data['packet']) == 0:
                        assert self.interface.TLAST
                    else:
                        assert not self.interface.TLAST

                    if not inst_data['tried_adding_during_run']:
                        if inst_data['available_delay'] == 0:
                            new_packets = add_packets_to_stream()

                            packet_list.extend(new_packets)
                            total_data_len[0] += (
                                sum(len(each) for each in new_packets))

                            inst_data['tried_adding_during_run'] = True

                        else:
                            inst_data['available_delay'] -= 1

                    cycle_count[0] += 1

                else:

                    if len(packet_list) == 0:
                        raise StopSimulation

                    elif all(len(each) == 0 for each in packet_list):
                        raise StopSimulation


            return inst, bfm

        def checks():
            max_cycles = self.max_packet_length * self.max_new_packets * 50
            myhdl_cosimulation(
                max_cycles, None, testbench, self.args, self.arg_types)

            # A few test sanity checks.
            self.assertEqual(sum(len(packet) for packet in packet_list), 0)
            self.assertTrue(cycle_count[0] >= total_data_len[0])

        # A few explicit cases
        explicit_cases = (
            [[],[],[]],
            [[10], [], [10]],
            [[], [], [10]],
            [[10], [], []])

        for _packet_list in explicit_cases:
            add_packets_to_stream = lambda: _add_packets_to_stream(
                self.stream, _packet_list)
            packet_list = add_packets_to_stream()
            total_data_len = [0]
            cycle_count = [0]
            checks()

        #run the test several times to better sample test space
        add_packets_to_stream = lambda: _add_random_packets_to_stream(
            self.stream, self.max_packet_length, self.max_new_packets,
            self.max_rand_val)

        for n in range(30):
            packet_list = add_packets_to_stream()
            total_data_len = [sum(len(each) for each in packet_list)]
            cycle_count = [0]
            checks()

    def test_add_new_packets_after_data_exhausted(self):
        '''It should be possible to add packets when the existing data is
        exhausted.
        '''

        @block
        def testbench(clock):

            bfm = self.stream.model(clock, self.interface)
            inst_data = {
                'empty_delay': random.randrange(0, 10),
                'tried_adding_when_empty': False}

            @always(clock.posedge)
            def inst():
                self.interface.TREADY.next = True
                if self.interface.TVALID:
                    next_expected_val = _get_next_val(packet_list, inst_data)

                    assert self.interface.TDATA == next_expected_val
                    if len(inst_data['packet']) == 0:
                        assert self.interface.TLAST
                    else:
                        assert not self.interface.TLAST

                    cycle_count[0] += 1

                else:
                    if not inst_data['tried_adding_when_empty']:
                        if inst_data['empty_delay'] == 0:
                            new_packets = add_packets_to_stream()

                            packet_list.extend(new_packets)

                            total_data_len[0] += (
                                sum(len(each) for each in new_packets))

                            inst_data['tried_adding_when_empty'] = True

                        else:
                            inst_data['empty_delay'] -= 1

                    elif len(packet_list) == 0:
                        raise StopSimulation

                    elif all(len(each) == 0 for each in packet_list):
                        raise StopSimulation


            return inst, bfm

        def checks():
            max_cycles = self.max_packet_length * self.max_new_packets * 50
            myhdl_cosimulation(
                max_cycles, None, testbench, self.args, self.arg_types)

            # A few test sanity checks.
            self.assertEqual(sum(len(packet) for packet in packet_list), 0)
            self.assertTrue(cycle_count[0] >= total_data_len[0])

        # A few explicit edge cases
        explicit_cases = (
            [[],[],[]],
            [[10], [], [10]],
            [[], [], [10]],
            [[10], [], []],
            [[10], [20], [30]])

        for _packet_list in (explicit_cases):
            add_packets_to_stream = lambda: _add_packets_to_stream(
                self.stream, _packet_list)
            packet_list = add_packets_to_stream()
            total_data_len = [0]
            cycle_count = [0]
            checks()

        #run the test several times to better sample test space
        add_packets_to_stream = lambda: _add_random_packets_to_stream(
            self.stream, self.max_packet_length, self.max_new_packets,
            self.max_rand_val)

        for n in range(30):
            packet_list = add_packets_to_stream()
            total_data_len = [sum(len(each) for each in packet_list)]
            cycle_count = [0]
            checks()

    def test_run_new_uninitialised_model(self):
        '''It should be possible run the simulation without first adding any
        data to the model'''

        @block
        def testbench(clock):

            bfm = self.stream.model(clock, self.interface)
            @always(clock.posedge)
            def inst():
                self.interface.TREADY.next = True

                # Nothing should be available
                assert not self.interface.TVALID

            return inst, bfm

        # Make sure we have a new stream
        self.stream = AxiStreamMasterBFM()
        myhdl_cosimulation(
            10, None, testbench, self.args, self.arg_types)

    def test_TREADY_False_pauses_valid_transfer(self):
        '''When the slave sets TREADY to False, no data should be sent, but
        the data should not be lost. Transfers should continue again as soon
        as TREADY is True.
        '''

        @block
        def testbench(clock):

            bfm = self.stream.model(clock, self.interface)
            inst_data = {'packet': deque([])}
            @always(clock.posedge)
            def inst():

                if random.random() < ready_probability:
                    # Set TREADY True
                    self.interface.TREADY.next = True
                else:
                    # Set TREADY False
                    self.interface.TREADY.next = False


                if self.interface.TVALID and self.interface.TREADY:
                    next_expected_val = _get_next_val(packet_list, inst_data)

                    assert self.interface.TDATA == next_expected_val
                    cycle_count[0] += 1

                else:
                    # Stop if there is nothing left to process
                    if len(inst_data['packet']) == 0:
                        if (len(packet_list) == 0):
                            raise StopSimulation

                        elif all(len(each) == 0 for each in packet_list):
                            raise StopSimulation



            return inst, bfm

        for n in range(5):
            ready_probability = 0.2 * (n + 1)

            packet_list = _add_random_packets_to_stream(
                self.stream, self.max_packet_length, self.max_new_packets,
                self.max_rand_val)

            total_data_len = sum(len(each) for each in packet_list)
            cycle_count = [0]

            dut_output, ref_output = myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

            self.assertTrue(cycle_count[0] == total_data_len)

    def test_None_in_packets_sets_TVALID_False(self):
        '''Inserting a ``None`` into a packet should cause a cycle in which
        the ``TVALID`` flag is set ``False``.
        '''
        @block
        def testbench(clock):

            bfm = self.stream.model(clock, self.interface)
            inst_data = {'first_run': True,
                         'packet': deque([])}

            @always(clock.posedge)
            def inst():
                self.interface.TREADY.next = True

                if inst_data['first_run']:
                    assert not self.interface.TVALID
                    inst_data['first_run'] = False

                else:
                    next_expected_val = _get_next_val(packet_list, inst_data)

                    if next_expected_val is None:
                        assert not self.interface.TVALID
                        cycle_count[0] += 1

                    else:
                        assert self.interface.TVALID
                        assert self.interface.TDATA == next_expected_val
                        cycle_count[0] += 1

                # Stop if there is nothing left to process
                if len(inst_data['packet']) == 0:
                    if (len(packet_list) == 0):
                        raise StopSimulation

                    elif all(len(each) == 0 for each in packet_list):
                        raise StopSimulation

            return inst, bfm

        max_packet_length = self.max_packet_length
        max_new_packets = self.max_new_packets

        def val_gen(data_byte_width):
            # Generates Nones about half the time probability
            val = random.randrange(0, 2**(8 * data_byte_width))
            if val > 2**(8 * data_byte_width - 1):
                return None
            else:
                return val

        for n in range(30):

            packet_list = deque(
                [deque([
                    val_gen(self.data_byte_width) for m
                    in range(random.randrange(0, max_packet_length))]) for n
                    in range(random.randrange(0, max_new_packets))])

            _add_packets_to_stream(self.stream, packet_list)

            total_data_len = sum(len(each) for each in packet_list)
            cycle_count = [0]

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

            self.assertEqual(total_data_len, cycle_count[0])

    def test_None_at_end_of_packets_moves_TLAST(self):
        '''If one or several Nones are set at the end of a packet, TLAST
        should be asserted for the last valid value.
        '''
        @block
        def testbench(clock):

            bfm = self.stream.model(clock, self.interface)
            inst_data = {'first_run': True,
                         'packet': deque([])}

            @always(clock.posedge)
            def inst():
                self.interface.TREADY.next = True

                if inst_data['first_run']:
                    inst_data['first_run'] = False

                else:
                    next_expected_val = _get_next_val(packet_list, inst_data)

                    if all([each is None for each in inst_data['packet']]):
                        assert self.interface.TLAST

                    cycle_count[0] += 1

                # Stop if there is nothing left to process
                if len(inst_data['packet']) == 0:
                    if (len(packet_list) == 0):
                        raise StopSimulation

                    elif all(len(each) == 0 for each in packet_list):
                        raise StopSimulation

            return inst, bfm

        max_packet_length = self.max_packet_length
        max_new_packets = self.max_new_packets

        def val_gen(data_byte_width):
            # Generates Nones about half the time probability
            val = random.randrange(0, 2**(8 * data_byte_width))
            if val > 2**(8 * data_byte_width - 1):
                return None
            else:
                return val

        for n in range(30):

            # Use fixed packet lengths
            packet_list = deque(
                [deque([
                    val_gen(self.data_byte_width) for m
                    in range(10)]) for n in range(10)])

            # Add a random number of Nones to the packet (at least 1).
            for each_packet in packet_list:
                each_packet.extend([None] * random.randrange(1, 5))

            _add_packets_to_stream(self.stream, packet_list)

            total_data_len = sum(len(each) for each in packet_list)
            cycle_count = [0]

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

            self.assertEqual(total_data_len, cycle_count[0])

    def test_None_in_packets_for_one_cycle_only(self):
        '''If the data was ``None``, corresponding to setting
        ``TVALID = False``, it should always only last for a single clock
        cycle before it is discarded.
        '''

        @block
        def testbench(clock):

            bfm = self.stream.model(clock, self.interface)
            inst_data = {'first_run': True,
                         'packet': deque([]),
                         'stored_val': None}

            @always(clock.posedge)
            def inst():

                if random.random() < ready_probability:
                    # Set TREADY True
                    self.interface.TREADY.next = True
                else:
                    # Set TREADY False
                    self.interface.TREADY.next = False

                if inst_data['first_run']:
                    assert not self.interface.TVALID
                    inst_data['first_run'] = False

                else:
                    if inst_data['stored_val'] is None:
                        next_expected_val = (
                            _get_next_val(packet_list, inst_data))

                    else:
                        next_expected_val = inst_data['stored_val']

                    if next_expected_val is None:
                        assert not self.interface.TVALID
                        cycle_count[0] += 1

                    else:
                        if not self.interface.TREADY:
                            inst_data['stored_val'] = next_expected_val

                        else:
                            inst_data['stored_val'] = None
                            assert self.interface.TVALID
                            assert self.interface.TDATA == next_expected_val
                            cycle_count[0] += 1

                # Stop if there is nothing left to process
                if (inst_data['stored_val'] is None and
                    len(inst_data['packet']) == 0):

                    if (len(packet_list) == 0):
                        raise StopSimulation

                    elif all(len(each) == 0 for each in packet_list):
                        raise StopSimulation

            return inst, bfm

        max_packet_length = self.max_packet_length
        max_new_packets = self.max_new_packets

        def val_gen(data_byte_width):
            # Generates Nones about half the time probability
            val = random.randrange(0, 2**(8 * self.data_byte_width))
            if val > 2**(8 * self.data_byte_width - 1):
                return None
            else:
                return val

        for n in range(5):
            ready_probability = 0.2 * (n + 1)

            packet_list = deque(
                [deque([
                    val_gen(self.data_byte_width) for m
                    in range(random.randrange(0, max_packet_length))]) for n
                    in range(random.randrange(0, max_new_packets))])

            _add_packets_to_stream(self.stream, packet_list)

            total_data_len = sum(len(each) for each in packet_list)
            cycle_count = [0]

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

            self.assertEqual(total_data_len, cycle_count[0])

    def test_reset(self):
        '''
        On receipt of a reset the axi_stream should cease sending the current
        packet, clear the backlog of packets and remain idle until the next
        packet is added to the BFM.
        '''

        cycles = 4000

        @block
        def testbench(clock):

            reset = Signal(False)

            bfm = self.stream.model(clock, self.interface, reset=reset)

            t_stim_state = enum(
                'INIT', 'SETUP_DATA', 'DELAY_AND_RESET', 'PROPAGATION_DELAY',
                'CHECK')
            stim_state = Signal(t_stim_state.INIT)

            n_words = 100

            inst_data = {
                'delay_before_reset': random.randrange(1, n_words),
                'delay_count': 0,
                'data_count': 0,
                'packet': [],
                'packet_list': [],}

            @always(clock.posedge)
            def inst():
                self.interface.TREADY.next = True

                if stim_state == t_stim_state.INIT:
                    # Check that the control signals are low
                    self.assertFalse(self.interface.TVALID)
                    self.assertFalse(self.interface.TLAST)

                    if random.random() < 0.1:
                        # Randomise the start of the test
                        stim_state.next = t_stim_state.SETUP_DATA

                elif stim_state == t_stim_state.SETUP_DATA:
                    for n in range(n_words):
                        # Generate a random packet with a length of n_words
                        inst_data['packet'].append(random.randrange(
                            0, 2**(8 * self.data_byte_width)))

                    # Add the newly created packet to the packet list and add
                    # it to the stream
                    inst_data['packet_list'].append(inst_data['packet'])
                    _add_packets_to_stream(
                        self.stream, inst_data['packet_list'])

                    # Set a random delay for the test to wait before sending
                    # the reset
                    inst_data['delay_before_reset'] = (
                        random.randrange(1, n_words))
                    stim_state.next = t_stim_state.DELAY_AND_RESET

                elif stim_state == t_stim_state.DELAY_AND_RESET:
                    if self.interface.TVALID:
                        # Check that the system is sending the new packet.
                        # This is necessary to make sure that the previous
                        # reset removed the old packet.
                        self.assertTrue(
                            inst_data['packet'][inst_data['data_count']] ==
                            self.interface.TDATA)

                        if inst_data['delay_count'] == (
                            inst_data['delay_before_reset']):
                            # When the delay period has lapsed send the reset
                            reset.next = True
                            inst_data['delay_count'] = 0
                            inst_data['data_count'] = 0
                            stim_state.next = t_stim_state.PROPAGATION_DELAY
                        else:
                            inst_data['delay_count'] += 1
                            inst_data['data_count'] += 1

                elif stim_state == t_stim_state.PROPAGATION_DELAY:
                    reset.next = False
                    # Insert a one cycle delay to allow the reset to propagate
                    stim_state.next = t_stim_state.CHECK

                elif stim_state == t_stim_state.CHECK:
                    # Reset the stim packets ready for the next run
                    inst_data['packet'] = []
                    inst_data['packet_list'] = []
                    # Check that the control signals have been set low
                    self.assertFalse(self.interface.TVALID)
                    self.assertFalse(self.interface.TLAST)
                    stim_state.next = t_stim_state.INIT

            return inst, bfm

        myhdl_cosimulation(
            cycles, None, testbench, self.args, self.arg_types)

class TestAxiStreamSlaveBFM(TestCase):
    '''There should be an AXI Stream Bus Functional Model that implements
    a programmable AXI4 Stream protocol from the slave side.
    '''

    def setUp(self):

        self.data_byte_width = 8
        self.max_packet_length = 20
        self.max_new_packets = 10
        self.max_rand_val = 2**(8 * self.data_byte_width)

        self.source_stream = AxiStreamMasterBFM()
        self.test_sink = AxiStreamSlaveBFM()

        self.interface = AxiStreamInterface(self.data_byte_width)
        clock = Signal(bool(0))

        self.args = {'clock': clock}
        self.arg_types = {'clock': 'clock'}

    def test_completed_packets_property(self):
        '''There should be a ``completed_packets`` property that records all
        the complete packets that have been received.

        This property should not contain not yet completed packets.
        '''
        @block
        def testbench(clock):

            test_sink = self.test_sink

            master = self.source_stream.model(clock, self.interface)
            slave = test_sink.model(clock, self.interface)

            enable_check = Signal(False)
            checker_data = {'packets_received': 0,}

            @always(clock.posedge)
            def checker():

                if len(test_sink.completed_packets) > 0:
                    # Wait for the first word to arrive.

                    # Check that the completed packets updates after receving
                    # a high on TLAST. Depending on whether this has run first
                    # or the dut has run first, we might be one value
                    # difference in length.
                    self.assertTrue(
                        (checker_data['packets_received'] ==
                         len(test_sink.completed_packets[stream])) or
                        (checker_data['packets_received'] ==
                         len(test_sink.completed_packets[stream]) - 1))

                if self.interface.TVALID and self.interface.TREADY:
                    # Wait for test to start before enabling the checks
                    enable_check.next = True

                    if self.interface.TLAST:
                        checker_data['packets_received'] += 1

                if enable_check and not self.interface.TVALID:
                    # All packets have been sent
                    self.assertTrue(
                        trimmed_packet_list == test_sink.completed_packets)

                    raise StopSimulation

                if len(trimmed_packet_list) == 0:
                    # The no data case
                    raise StopSimulation

            return master, slave, checker

        for n in range(30):
            # lots of test cases

            # We need new BFMs for every run
            self.source_stream = AxiStreamMasterBFM()
            self.test_sink = AxiStreamSlaveBFM()

            # Interface does not have TID or TDEST therefore the DUT should
            # set the stream_ID and stream_dest to 0 in the returned packet
            # list
            stream_ID = 0
            stream_destination = 0
            stream = (stream_ID, stream_destination)

            packet_list = {}
            packet_list[stream] = (
                _add_random_packets_to_stream(
                    self.source_stream, self.max_packet_length,
                    self.max_new_packets, self.max_rand_val))

            trimmed_packet_list = trim_empty_packets_and_streams(packet_list)

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

            self.test_sink.reset()

    def test_signal_record_property(self):
        '''There should be a ``signal_record`` property that records all
        the ``TDATA``, ``TID``, ``TDEST`` and ``TLAST`` signals on every cycle
        regardless of ``TVALID`` and ``TREADY``. If ``TVALID`` is low then the
        block should place a ``None`` in the ``TDATA`` record. The property
        should return a dictionary with each of the signal names as the key.

        The ``signal_record`` property gives us all of the signals with the
        validity.
        '''
        @block
        def testbench(clock):

            test_sink = self.test_sink

            master = self.source_stream.model(clock, interface)
            slave = test_sink.model(clock, interface)

            enable_check = Signal(False)
            checker_data = {'packets_received': 0,}

            @always(clock.posedge)
            def checker():

                if interface.TVALID and interface.TREADY:
                    # Wait for test to start before enabling the checks
                    enable_check.next = True

                if enable_check and not interface.TVALID:

                    # All packets have been sent
                    self.assertTrue(
                        trimmed_packet_list ==
                        packetise_signal_record(test_sink.signal_record))

                    raise StopSimulation

                if len(trimmed_packet_list) == 0:
                    # The no data case
                    raise StopSimulation

            return master, slave, checker

        for n in range(30):
            # lots of test cases

            # We need new BFMs for every run
            self.source_stream = AxiStreamMasterBFM()
            self.test_sink = AxiStreamSlaveBFM()

            interface = AxiStreamInterface(
                self.data_byte_width, TID_width=4, TDEST_width=4)

            max_stream_id = 2**len(interface.TID)
            max_stream_dest = 2**len(interface.TDEST)

            min_n_streams = 2
            max_n_streams = 20
            n_streams = random.randrange(min_n_streams, max_n_streams)

            # Generate a list of random and unique combinations of TID and
            # TDEST
            streams = generate_unique_streams(
                n_streams, max_stream_id, max_stream_dest)

            packet_list = {}
            for stream in streams:
                # Create a list of packets to send for each stream
                packet_list[stream] = (
                    _add_random_packets_to_stream(
                        self.source_stream, self.max_packet_length,
                        self.max_new_packets, self.max_rand_val,
                        stream_ID=stream[0],
                        stream_destination=stream[1]))

            trimmed_packet_list = trim_empty_packets_and_streams(packet_list)

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

            self.test_sink.reset()

    def test_TREADY_probability(self):
        '''There should be a TREADY_probability argument to the model
        that dictates the probability of TREADY being True.
        '''
        @block
        def testbench(clock):

            test_sink = self.test_sink

            master = self.source_stream.model(clock, self.interface)
            slave = test_sink.model(
                clock, self.interface, TREADY_probability=TREADY_probability)

            check_packet_next_time = Signal(False)
            checker_data = {'packets_to_check': 0,
                            'current_sent_packet_list': {},
                            'TREADY_False_count': 0,}

            @always(clock.posedge)
            def checker():

                if self.interface.TVALID and self.interface.TREADY:
                    if self.interface.TLAST:
                        check_packet_next_time.next = True
                        checker_data['packets_to_check'] += 1

                if not self.interface.TREADY:
                    checker_data['TREADY_False_count'] += 1

                if check_packet_next_time:
                    check_packet_next_time.next = False
                    packets_to_check = checker_data['packets_to_check']

                    checker_data['current_sent_packet_list'][stream] = (
                        deque(list(itertools.islice(
                            trimmed_packet_list[stream], 0,
                            packets_to_check))))

                    self.assertTrue(
                        checker_data['current_sent_packet_list'] ==
                        test_sink.completed_packets)

                    if packets_to_check >= len(trimmed_packet_list[stream]):
                        # The chance of this being false should be very very
                        # low
                        self.assertTrue(
                            checker_data['TREADY_False_count'] > 3)
                        raise StopSimulation

                if len(trimmed_packet_list) == 0:
                    # The no data case
                    raise StopSimulation


            return master, slave, checker

        for TREADY_percentage_probability in range(10, 90, 10):

            TREADY_probability = TREADY_percentage_probability/100.0
            # We need new BFMs for every run
            self.source_stream = AxiStreamMasterBFM()
            self.test_sink = AxiStreamSlaveBFM()

            # Interface does not have TID or TDEST therefore the DUT should
            # set the stream_ID and stream_dest to 0 in the returned packet
            # list
            stream_ID = 0
            stream_destination = 0
            stream = (stream_ID, stream_destination)

            packet_list = {}
            # Use fixed length packets so it is very likely to be
            packet_list[stream] = deque(
                [deque([random.randrange(0, self.max_rand_val) for m
                        in range(20)]) for n in range(10)])

            packet_list[stream] = _add_packets_to_stream(
                self.source_stream, packet_list[stream])

            trimmed_packet_list = trim_empty_packets_and_streams(packet_list)

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

    def test_TREADY_None(self):
        '''There should be possible to set TREADY_probability to None which
        prevents TREADY being driven.
        '''
        @block
        def testbench(clock, use_slave=True):

            test_sink = self.test_sink

            master = self.source_stream.model(clock, self.interface)
            test_sniffer = test_sink.model(
                clock, self.interface, TREADY_probability=None)

            slave = alt_test_sink.model(
                clock, self.interface, TREADY_probability=0.5)

            @always(clock.posedge)
            def stopper():
                if len(alt_test_sink.completed_packets) > 0:
                    if (len(trimmed_packet_list[stream]) ==
                        len(alt_test_sink.completed_packets[stream])):
                        raise StopSimulation

            if use_slave:
                return master, slave, test_sniffer, stopper
            else:
                return master, test_sniffer, stopper

        # We need new BFMs for every run
        self.source_stream = AxiStreamMasterBFM()
        self.test_sink = AxiStreamSlaveBFM()

        # We create another sink that actually does twiddle TREADY
        alt_test_sink = AxiStreamSlaveBFM()

        # Interface does not have TID or TDEST therefore the DUT should
        # set the stream_ID and stream_dest to 0 in the returned packet
        # list
        stream_ID = 0
        stream_destination = 0
        stream = (stream_ID, stream_destination)

        packet_list = {}
        # Use fixed length packets so it is very likely to be
        packet_list[stream] = deque(
            [deque([random.randrange(0, self.max_rand_val) for m
                    in range(random.randrange(0, 20))]) for n in range(10)])

        packet_list[stream] = _add_packets_to_stream(
            self.source_stream, packet_list[stream])

        trimmed_packet_list = trim_empty_packets_and_streams(packet_list)

        myhdl_cosimulation(
            None, None, testbench, self.args, self.arg_types)

        self.assertTrue(
            alt_test_sink.completed_packets==self.test_sink.completed_packets)
        self.assertTrue(
            trimmed_packet_list==self.test_sink.completed_packets)

        # Also check TREADY is not being driven.
        self.args['use_slave'] = False
        self.arg_types['use_slave'] = 'non-signal'
        self.test_sink = AxiStreamSlaveBFM()
        myhdl_cosimulation(
            100, None, testbench, self.args, self.arg_types)

        self.assertTrue(len(self.test_sink.completed_packets) == 0)
        self.assertTrue(len(self.test_sink.current_packets) == 0)

    def test_current_packets_property(self):
        ''' There should be a ``current_packets`` property that returns the
        packets that are currently being recorded and have not yet completed.
        '''
        @block
        def testbench(clock):

            test_sink = self.test_sink

            master = self.source_stream.model(clock, self.interface)
            slave = test_sink.model(clock, self.interface)

            check_packet_next_time = Signal(False)
            checker_data = {
                'data_in_packet': 0,
                'current_packet_idx': 0}

            @always(clock.posedge)
            def checker():
                if (len(test_sink.completed_packets) ==
                    len(trimmed_packet_list)):
                    raise StopSimulation

                if (self.interface.TVALID and self.interface.TREADY
                    and not self.interface.TLAST):

                    checker_data['data_in_packet'] += 1

                    if check_packet_next_time:

                        expected_length = checker_data['data_in_packet']
                        packet_length = len(test_sink.current_packets[stream])

                        # depending on whether this has run first or the dut
                        # has run first, we might be one value difference in
                        # length
                        self.assertTrue(
                            packet_length == expected_length
                            or packet_length == (expected_length - 1))

                        packet_idx = checker_data['current_packet_idx']
                        expected_packet = (
                            deque(list(itertools.islice(
                                trimmed_packet_list[stream][packet_idx], 0,
                                packet_length))))

                        self.assertTrue(
                            expected_packet==
                            test_sink.current_packets[stream])

                    else:
                        check_packet_next_time.next = True

                elif self.interface.TLAST:
                    checker_data['data_in_packet'] = 0
                    checker_data['current_packet_idx'] += 1

            return master, slave, checker

        for n in range(30):
            # lots of test cases

            # We need new BFMs for every run
            self.source_stream = AxiStreamMasterBFM()
            self.test_sink = AxiStreamSlaveBFM()

            # Interface does not have TID or TDEST therefore the DUT should
            # set the stream_ID and stream_dest to 0 in the returned packet
            # list
            stream_ID = 0
            stream_destination = 0
            stream = (stream_ID, stream_destination)

            packet_list = {}
            packet_list[stream] = _add_random_packets_to_stream(
                self.source_stream, self.max_packet_length,
                self.max_new_packets, self.max_rand_val)

            trimmed_packet_list = trim_empty_packets_and_streams(packet_list)

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

    def test_TVALID_low_default_not_recorded(self):
        '''If TVALID is unset on the master interface the values on the line
        should not be recorded.
        '''
        @block
        def testbench(clock):

            test_sink = self.test_sink

            master = self.source_stream.model(clock, self.interface)
            slave = test_sink.model(
                clock, self.interface, TREADY_probability=TREADY_probability)

            @always(clock.posedge)
            def stopper():

                if len(test_sink.completed_packets) > 0:
                    if len(test_sink.completed_packets[stream]) == (
                        len(packet_list[stream])):
                        raise StopSimulation

            return master, slave, stopper

        for TREADY_percentage_probability in (90,):#range(10, 90, 10):

            TREADY_probability = TREADY_percentage_probability/100.0
            # We need new BFMs for every run
            self.source_stream = AxiStreamMasterBFM()
            self.test_sink = AxiStreamSlaveBFM()

            # Interface does not have TID or TDEST therefore the DUT should
            # set the stream_ID and stream_dest to 0 in the returned packet
            # list
            stream_ID = 0
            stream_destination = 0
            stream = (stream_ID, stream_destination)

            packet_list = {}
            trimmed_packet_list = {}

            packet_list[stream] = deque([])
            trimmed_packet_list[stream] = deque([])
            for n in range(10):
                packet = deque([])
                trimmed_packet = deque([])
                for m in range(20):
                    val = random.randrange(0, self.max_rand_val * 2)
                    if val > self.max_rand_val:
                        val = None

                    else:
                        trimmed_packet.append(val)

                    packet.append(val)

                packet_list[stream].append(packet)
                trimmed_packet_list[stream].append(trimmed_packet)

            _add_packets_to_stream(self.source_stream, packet_list[stream])

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

            self.assertTrue(
                trimmed_packet_list==self.test_sink.completed_packets)

    def test_missing_TLAST(self):
        '''If TLAST is missing from the interface, then the effect should be
        that no packets are completed.
        '''

        interface = AxiStreamInterface(self.data_byte_width, use_TLAST=False)

        @block
        def testbench(clock):

            test_sink = self.test_sink

            master = self.source_stream.model(clock, interface)
            slave = test_sink.model(clock, interface)

            check_packet_next_time = Signal(False)
            checker_data = {'data_in_packet': 0}

            @always(clock.posedge)
            def checker():

                if len(test_sink.current_packets) > 0:
                    if (len(test_sink.current_packets[stream]) ==
                        len(trimmed_data_list)):
                        raise StopSimulation

                if (interface.TVALID and interface.TREADY):

                    checker_data['data_in_packet'] += 1

                    if len(test_sink.current_packets) > 0:

                        expected_length = checker_data['data_in_packet']
                        packet_length = len(test_sink.current_packets[stream])

                        # depending on whether this has run first or the dut
                        # has run first, we might be one value difference in
                        # length
                        self.assertTrue(
                            packet_length == expected_length
                            or packet_length == (expected_length - 1))

                        expected_packet = deque(
                            trimmed_data_list[:packet_length])

                        self.assertTrue(
                            expected_packet==
                            test_sink.current_packets[stream])

            return master, slave, checker

        for n in range(30):
            # lots of test cases

            # We need new BFMs for every run
            self.source_stream = AxiStreamMasterBFM()
            self.test_sink = AxiStreamSlaveBFM()

            # Interface does not have TID or TDEST therefore the DUT should
            # set the stream_ID and stream_dest to 0 in the returned packet
            # list
            stream_ID = 0
            stream_destination = 0
            stream = (stream_ID, stream_destination)

            packet_list = {}
            packet_list[stream] = _add_random_packets_to_stream(
                self.source_stream, self.max_packet_length,
                self.max_new_packets, self.max_rand_val)

            trimmed_packet_list = trim_empty_packets_and_streams(packet_list)

            while(len(trimmed_packet_list) == 0):
                packet_list[stream] = _add_random_packets_to_stream(
                    self.source_stream, self.max_packet_length,
                    self.max_new_packets, self.max_rand_val)

                trimmed_packet_list = (
                    trim_empty_packets_and_streams(packet_list))

            trimmed_data_list = [
                val for packet in trimmed_packet_list[stream] for val in packet]

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)


    def test_reset_method(self):
        '''There should be a reset method that when called clears all the
        recorded packets.
        '''
        @block
        def testbench(clock):

            test_sink = self.test_sink

            master = self.source_stream.model(clock, self.interface)
            slave = test_sink.model(clock, self.interface)

            return master, slave

        self.source_stream = AxiStreamMasterBFM()
        self.test_sink = AxiStreamSlaveBFM()

        # Interface does not have TID or TDEST therefore the DUT should
        # set the stream_ID and stream_dest to 0 in the returned packet
        # list
        stream_ID = 0
        stream_destination = 0
        stream = (stream_ID, stream_destination)

        # Create and send the packets
        packet_list = {}
        packet_list[stream] = _add_random_packets_to_stream(
            self.source_stream, self.max_packet_length,
            self.max_new_packets, self.max_rand_val)

        trimmed_packet_list = trim_empty_packets_and_streams(packet_list)

        # Work out how many cycles to run the first simulation for
        cycles = sum(len(packet) for packet in packet_list[stream]) + 1

        myhdl_cosimulation(
            cycles, None, testbench, self.args, self.arg_types)

        # Check that the system has received the data correctly
        assert self.test_sink.completed_packets == trimmed_packet_list

        # Create and send new data
        packet_list.clear()
        packet_list[stream] = _add_random_packets_to_stream(
            self.source_stream, self.max_packet_length,
            self.max_new_packets, self.max_rand_val)

        added_trimmed_packet_list = (
            trim_empty_packets_and_streams(packet_list))

        cycles = sum(len(packet) for packet in packet_list[stream]) + 1

        # Clear the old data
        self.test_sink.reset()

        myhdl_cosimulation(
            cycles, None, testbench, self.args, self.arg_types)

        # Check that the system does not contain the original data and only
        # contains the new
        self.assertEqual(self.test_sink.completed_packets,
                         added_trimmed_packet_list)

    def test_multiple_stream_data(self):
        ''' It should be possible to receive data for multiple streams as
        defined by the ``TID`` and ``TDEST`` signals in the AXI stream
        interface.

        The ``completed_packets`` property should record all the complete
        packets that have been received in a dictionary where the key is a
        tuple of the form:

            (TID, TDEST)

        The ``current_packets`` property should be of the same form and should
        contain all packets that have not yet completed.
        '''
        @block
        def testbench(clock):

            test_sink = self.test_sink

            master = self.source_stream.model(clock, interface)
            slave = self.test_sink.model(clock, interface)

            enable_check = Signal(False)

            @always(clock.posedge)
            def checker():

                # Wait for the transmission to start
                enable_check.next = True

                if enable_check:
                    if not interface.TVALID:
                        # Wait for the transmission to finish then check the
                        # recieved data matches the sent data
                        self.assertTrue(
                            trimmed_packet_list ==
                            self.test_sink.completed_packets)

                        raise StopSimulation

                if len(trimmed_packet_list) == 0:
                    # The no data case
                    raise StopSimulation


            return master, slave, checker

        for n in range(30):
            # lots of test cases

            # We need new BFMs for every run
            self.source_stream = AxiStreamMasterBFM()
            self.test_sink = AxiStreamSlaveBFM()

            interface = AxiStreamInterface(
                self.data_byte_width, TID_width=4, TDEST_width=4)

            max_stream_id = 2**len(interface.TID)
            max_stream_dest = 2**len(interface.TDEST)

            min_n_streams = 2
            max_n_streams = 20
            n_streams = random.randrange(min_n_streams, max_n_streams)

            # Generate a list of random and unique combinations of TID and
            # TDEST
            streams = generate_unique_streams(
                n_streams, max_stream_id, max_stream_dest)

            packet_list = {}
            for stream in streams:
                # Create a list of packets to send for each stream
                packet_list[stream] = (
                    _add_random_packets_to_stream(
                        self.source_stream, self.max_packet_length,
                        self.max_new_packets, self.max_rand_val,
                        stream_ID=stream[0],
                        stream_destination=stream[1]))

            trimmed_packet_list = trim_empty_packets_and_streams(packet_list)

            myhdl_cosimulation(
                None, None, testbench, self.args, self.arg_types)

class TestAxiStreamBuffer(TestCase):
    '''There should be a block that interfaces with an AXI stream, buffering
    it as necessary if the output side is not ready. It should provide
    both a slave and a master interface.
    '''
    def setUp(self):
        self.data_byte_width = 8
        self.max_packet_length = 20
        self.max_new_packets = 10
        self.max_rand_val = 2**(8 * self.data_byte_width)

        self.source_stream = AxiStreamMasterBFM()
        self.test_sink = AxiStreamSlaveBFM()

        self.axi_stream_in = AxiStreamInterface(
            self.data_byte_width, TID_width=4, TDEST_width=4)
        self.axi_stream_out = AxiStreamInterface(
            self.data_byte_width, TID_width=4, TDEST_width=4)

        self.clock = Signal(bool(0))

        self.args = {'clock': self.clock}
        self.arg_types = {'clock': 'clock'}

    def test_zero_latency_non_passive_case(self):
        '''In the case where there is no need to buffer the signal (e.g.
        because the axi sink is always ready) there should be no latency
        in the outputs.

        This should happen when the buffer is not in passive mode (i.e. when
        TREADY is always set by the axi_stream_buffer block).
        '''

        @block
        def testbench(clock, axi_in, axi_out):

            buffer_block = axi_stream_buffer(
                clock, axi_in, axi_out, passive_sink_mode=False)

            @always(clock.posedge)
            def compare_sink():

                if axi_in.TVALID:
                    self.assertTrue(axi_out.TVALID)
                    self.assertEqual(axi_out.TDATA, axi_in.TDATA)
                    self.assertEqual(axi_out.TLAST, axi_in.TLAST)
                    self.assertEqual(axi_out.TID, axi_in.TID)
                    self.assertEqual(axi_out.TDEST, axi_in.TDEST)

            return buffer_block, compare_sink

        self.args['axi_in'] = self.axi_stream_in
        self.args['axi_out'] = self.axi_stream_out

        self.arg_types['axi_in'] = {
            'TDATA': 'custom', 'TLAST': 'custom', 'TVALID': 'custom',
            'TREADY': 'output', 'TID': 'custom', 'TDEST': 'custom',}

        self.arg_types['axi_out'] = {
            'TDATA': 'output', 'TLAST': 'output', 'TVALID': 'output',
            'TREADY': 'custom', 'TID': 'output', 'TDEST': 'output',}

        max_stream_id = 2**len(self.axi_stream_in.TID)
        max_stream_dest = 2**len(self.axi_stream_in.TDEST)

        min_n_streams = 2
        max_n_streams = 20
        n_streams = random.randrange(min_n_streams, max_n_streams)

        # Generate a list of random and unique combinations of TID and
        # TDEST
        streams = generate_unique_streams(
            n_streams, max_stream_id, max_stream_dest)

        packet_list = {}
        trimmed_packet_list = {}
        data_len = {}

        total_data_len = 0

        for stream in streams:
            packet_list[stream], trimmed_packet_list[stream], data_len[stream] = (
                _generate_random_packets_with_Nones(
                    self.data_byte_width, self.max_packet_length,
                    self.max_new_packets))

            self.source_stream.add_data(
                packet_list[stream], stream_ID=stream[0],
                stream_destination=stream[1])

            total_data_len = data_len[stream] + total_data_len

        # Clear empty streams from the trimmed packet list (which previously
        # had packets and Nones trimmed)
        trimmed_packet_list = (
            trim_empty_packets_and_streams(trimmed_packet_list))

        TREADY_probability = 1.0
        custom_sources = [
            (self.source_stream.model, (self.clock, self.axi_stream_in), {}),
            (self.test_sink.model,
             (self.clock, self.axi_stream_out, TREADY_probability), {})]

        cycles = total_data_len + 1

        myhdl_cosimulation(
            cycles, None, testbench, self.args, self.arg_types,
            custom_sources=custom_sources)

        self.assertTrue(
            trimmed_packet_list==self.test_sink.completed_packets)

    def test_zero_latency_passive_case(self):
        '''In the case where there is no need to buffer the signal (e.g.
        because the axi sink is always ready) there should be no latency
        in the outputs.

        This should happen when the buffer is in passive mode (i.e. when
        TREADY is set by a block other than that axi_stream_buffer block).
        '''

        @block
        def testbench(clock, axi_in, axi_out):

            buffer_block = axi_stream_buffer(
                clock, axi_in, axi_out, passive_sink_mode=True)

            @always(clock.posedge)
            def compare_sink():

                axi_out.TREADY.next = True

                if axi_in.TVALID:
                    self.assertTrue(axi_out.TVALID)
                    self.assertEqual(axi_out.TDATA, axi_in.TDATA)
                    self.assertEqual(axi_out.TLAST, axi_in.TLAST)
                    self.assertEqual(axi_out.TID, axi_in.TID)
                    self.assertEqual(axi_out.TDEST, axi_in.TDEST)

            return buffer_block, compare_sink

        self.args['axi_in'] = self.axi_stream_in
        self.args['axi_out'] = self.axi_stream_out

        self.arg_types['axi_in'] = {
            'TDATA': 'custom', 'TLAST': 'custom', 'TVALID': 'custom',
            'TREADY': 'output', 'TID': 'custom', 'TDEST': 'custom',}

        self.arg_types['axi_out'] = {
            'TDATA': 'output', 'TLAST': 'output', 'TVALID': 'output',
            'TREADY': 'custom', 'TID': 'output', 'TDEST': 'output',}

        max_stream_id = 2**len(self.axi_stream_in.TID)
        max_stream_dest = 2**len(self.axi_stream_in.TDEST)

        min_n_streams = 2
        max_n_streams = 20
        n_streams = random.randrange(min_n_streams, max_n_streams)

        # Generate a list of random and unique combinations of TID and
        # TDEST
        streams = generate_unique_streams(
            n_streams, max_stream_id, max_stream_dest)

        packet_list = {}
        trimmed_packet_list = {}
        data_len = {}

        total_data_len = 0

        for stream in streams:
            packet_list[stream], trimmed_packet_list[stream], data_len[stream] = (
                _generate_random_packets_with_Nones(
                    self.data_byte_width, self.max_packet_length,
                    self.max_new_packets))

            self.source_stream.add_data(
                packet_list[stream], stream_ID=stream[0],
                stream_destination=stream[1])

            total_data_len = data_len[stream] + total_data_len

        # Clear empty streams from the trimmed packet list (which previously
        # had packets and Nones trimmed)
        trimmed_packet_list = (
            trim_empty_packets_and_streams(trimmed_packet_list))

        # Create a slave channel to drive the AXI in interface to the buffer.
        # The test_sink on the other side of the buffer should receive the
        # same data as the ref_sink.
        ref_sink = AxiStreamSlaveBFM()

        TREADY_probability = 1.0
        custom_sources = [
            (self.source_stream.model, (self.clock, self.axi_stream_in), {}),
            (ref_sink.model,
             (self.clock, self.axi_stream_in, TREADY_probability), {}),
            (self.test_sink.model,
             (self.clock, self.axi_stream_out, TREADY_probability), {}),]

        cycles = total_data_len + 1

        myhdl_cosimulation(
            cycles, None, testbench, self.args, self.arg_types,
            custom_sources=custom_sources)

        self.assertTrue(
            ref_sink.completed_packets==self.test_sink.completed_packets)
        self.assertTrue(
            trimmed_packet_list==self.test_sink.completed_packets)


    def test_buffering_in_non_passive_case(self):
        '''In the case where the TREADY on the output bus is not the same
        as the TREADY on the input bus, the data should be buffered so
        it is not lost.

        This should happen when the buffer is in non passive mode (i.e. when
        TREADY is always set by the axi_stream_buffer block).
        '''

        @block
        def testbench(clock, axi_in, axi_out):

            buffer_block = axi_stream_buffer(
                clock, axi_in, axi_out, passive_sink_mode=False)

            return buffer_block

        self.args['axi_in'] = self.axi_stream_in
        self.args['axi_out'] = self.axi_stream_out

        self.arg_types['axi_in'] = {
            'TDATA': 'custom', 'TLAST': 'custom', 'TVALID': 'custom',
            'TREADY': 'output', 'TID': 'custom', 'TDEST': 'custom',}

        self.arg_types['axi_out'] = {
            'TDATA': 'output', 'TLAST': 'output', 'TVALID': 'output',
            'TREADY': 'custom', 'TID': 'output', 'TDEST': 'output',}

        max_stream_id = 2**len(self.axi_stream_in.TID)
        max_stream_dest = 2**len(self.axi_stream_in.TDEST)

        min_n_streams = 2
        max_n_streams = 20
        n_streams = random.randrange(min_n_streams, max_n_streams)

        # Generate a list of random and unique combinations of TID and
        # TDEST
        streams = generate_unique_streams(
            n_streams, max_stream_id, max_stream_dest)

        packet_list = {}
        trimmed_packet_list = {}
        data_len = {}

        total_data_len = 0

        for stream in streams:
            packet_list[stream], trimmed_packet_list[stream], data_len[stream] = (
                _generate_random_packets_with_Nones(
                    self.data_byte_width, self.max_packet_length,
                    self.max_new_packets))

            self.source_stream.add_data(
                packet_list[stream], stream_ID=stream[0],
                stream_destination=stream[1])

            total_data_len = data_len[stream] + total_data_len

        # Clear empty streams from the trimmed packet list (which previously
        # had packets and Nones trimmed)
        trimmed_packet_list = (
            trim_empty_packets_and_streams(trimmed_packet_list))

        TREADY_probability = 0.2
        custom_sources = [
            (self.source_stream.model, (self.clock, self.axi_stream_in), {}),
            (self.test_sink.model,
             (self.clock, self.axi_stream_out, TREADY_probability), {})]

        cycles = total_data_len * 20 + 1

        myhdl_cosimulation(
            cycles, None, testbench, self.args, self.arg_types,
            custom_sources=custom_sources)

        self.assertTrue(
            trimmed_packet_list==self.test_sink.completed_packets)


    def test_buffering_in_passive_case(self):
        '''In the case where the TREADY on the output bus is not the same
        as the TREADY on the input bus, the data should be buffered so
        it is not lost.

        This should happen when the buffer is in passive mode (i.e. when
        TREADY is set by a block other than that axi_stream_buffer block).
        '''

        @block
        def testbench(clock, axi_in, axi_out):

            buffer_block = axi_stream_buffer(
                clock, axi_in, axi_out, passive_sink_mode=True)

            return buffer_block

        self.args['axi_in'] = self.axi_stream_in
        self.args['axi_out'] = self.axi_stream_out

        self.arg_types['axi_in'] = {
            'TDATA': 'custom', 'TLAST': 'custom', 'TVALID': 'custom',
            'TREADY': 'output', 'TID': 'custom', 'TDEST': 'custom',}

        self.arg_types['axi_out'] = {
            'TDATA': 'output', 'TLAST': 'output', 'TVALID': 'output',
            'TREADY': 'custom', 'TID': 'output', 'TDEST': 'output',}

        max_stream_id = 2**len(self.axi_stream_in.TID)
        max_stream_dest = 2**len(self.axi_stream_in.TDEST)

        min_n_streams = 2
        max_n_streams = 20
        n_streams = random.randrange(min_n_streams, max_n_streams)

        # Generate a list of random and unique combinations of TID and
        # TDEST
        streams = generate_unique_streams(
            n_streams, max_stream_id, max_stream_dest)

        packet_list = {}
        trimmed_packet_list = {}
        data_len = {}

        total_data_len = 0

        for stream in streams:
            packet_list[stream], trimmed_packet_list[stream], data_len[stream] = (
                _generate_random_packets_with_Nones(
                    self.data_byte_width, self.max_packet_length,
                    self.max_new_packets))

            self.source_stream.add_data(
                packet_list[stream], stream_ID=stream[0],
                stream_destination=stream[1])

            total_data_len = data_len[stream] + total_data_len

        # Clear empty streams from the trimmed packet list (which previously
        # had packets and Nones trimmed)
        trimmed_packet_list = (
            trim_empty_packets_and_streams(trimmed_packet_list))

        # Create a slave channel to drive the AXI in interface to the buffer.
        # The test_sink on the other side of the buffer should receive the
        # same data as the ref_sink.
        ref_sink = AxiStreamSlaveBFM()

        test_TREADY_probability = 0.2
        ref_TREADY_probability = 0.5
        custom_sources = [
            (self.source_stream.model, (self.clock, self.axi_stream_in), {}),
            (ref_sink.model,
             (self.clock, self.axi_stream_in, ref_TREADY_probability), {}),
            (self.test_sink.model,
             (self.clock, self.axi_stream_out, test_TREADY_probability), {}),]

        cycles = total_data_len * 20 + 1

        myhdl_cosimulation(
            cycles, None, testbench, self.args, self.arg_types,
            custom_sources=custom_sources)

        self.assertTrue(
            ref_sink.completed_packets==self.test_sink.completed_packets)
        self.assertTrue(
            trimmed_packet_list==self.test_sink.completed_packets)

    def test_zero_latency_after_buffering_case(self):
        '''In the case where the signal is buffered but then has time to
        catch up (i.e. because no valid transactions are present on the input)
        there should be once again no latency in the outputs.
        '''

        dump_sink = AxiStreamSlaveBFM()

        @block
        def testbench(clock, axi_in, axi_out):

            buffer_block = axi_stream_buffer(
                clock, axi_in, axi_out, passive_sink_mode=True)

            states = enum('initial_data', 'catchup', 'zero_latency')
            state = Signal(states.initial_data)

            @always(clock.posedge)
            def compare_sink():

                if state == states.initial_data:
                    if ref_sink.completed_packets==trimmed_packet_list:

                        state.next = states.catchup
                        axi_out.TREADY.next = True

                    else:
                        axi_out.TREADY.next = False

                elif state == states.catchup:
                    axi_out.TREADY.next = True
                    if self.test_sink.completed_packets==trimmed_packet_list:
                        state.next = states.zero_latency

                else:
                    if axi_in.TVALID:
                        self.assertTrue(axi_out.TVALID)
                        self.assertEqual(axi_out.TDATA, axi_in.TDATA)
                        self.assertEqual(axi_out.TLAST, axi_in.TLAST)

            return buffer_block, compare_sink

        self.args['axi_in'] = self.axi_stream_in
        self.args['axi_out'] = self.axi_stream_out

        self.arg_types['axi_in'] = {
            'TDATA': 'custom', 'TLAST': 'custom', 'TVALID': 'custom',
            'TREADY': 'output', 'TID': 'custom', 'TDEST': 'custom',}

        self.arg_types['axi_out'] = {
            'TDATA': 'output', 'TLAST': 'output', 'TVALID': 'output',
            'TREADY': 'custom', 'TID': 'output', 'TDEST': 'output',}

        max_stream_id = 2**len(self.axi_stream_in.TID)
        max_stream_dest = 2**len(self.axi_stream_in.TDEST)

        min_n_streams = 2
        max_n_streams = 20
        n_streams = random.randrange(min_n_streams, max_n_streams)

        # Generate a list of random and unique combinations of TID and
        # TDEST
        streams = generate_unique_streams(
            n_streams, max_stream_id, max_stream_dest)

        packet_list = {}
        trimmed_packet_list = {}
        data_len = {}

        total_data_len = 0

        for stream in streams:
            packet_list[stream], trimmed_packet_list[stream], data_len[stream] = (
                _generate_random_packets_with_Nones(
                    self.data_byte_width, self.max_packet_length,
                    self.max_new_packets))

            self.source_stream.add_data(
                packet_list[stream], stream_ID=stream[0],
                stream_destination=stream[1])

            total_data_len = data_len[stream] + total_data_len

        # Clear empty streams from the trimmed packet list (which previously
        # had packets and Nones trimmed)
        trimmed_packet_list = (
            trim_empty_packets_and_streams(trimmed_packet_list))

        # Create a slave channel to drive the AXI in interface to the buffer.
        # The test_sink on the other side of the buffer should receive the
        # same data as the ref_sink.
        ref_sink = AxiStreamSlaveBFM()

        TREADY_probability = 1.0
        custom_sources = [
            (self.source_stream.model, (self.clock, self.axi_stream_in), {}),
            (ref_sink.model,
             (self.clock, self.axi_stream_in, TREADY_probability), {}),
            (self.test_sink.model,
             (self.clock, self.axi_stream_out, None), {}),]

        cycles = total_data_len * 3 + 1

        myhdl_cosimulation(
            cycles, None, testbench, self.args, self.arg_types,
            custom_sources=custom_sources)

        self.assertTrue(
            ref_sink.completed_packets==self.test_sink.completed_packets)
        self.assertTrue(
            trimmed_packet_list==self.test_sink.completed_packets)

    def test_no_TLAST_on_input(self):
        '''If TLAST is missing on the input, the TLAST should always be
        False on the output.
        '''

        @block
        def testbench(clock, axi_in, axi_out):

            buffer_block = axi_stream_buffer(
                clock, axi_in, axi_out, passive_sink_mode=False)

            return buffer_block

        axi_stream_in = AxiStreamInterface(
            self.data_byte_width, use_TLAST=False, TID_width=4, TDEST_width=4)

        self.args['axi_in'] = axi_stream_in
        self.args['axi_out'] = self.axi_stream_out

        self.arg_types['axi_in'] = {
            'TDATA': 'custom', 'TVALID': 'custom', 'TREADY': 'output',
            'TID': 'custom', 'TDEST': 'custom',}

        self.arg_types['axi_out'] = {
            'TDATA': 'output', 'TLAST': 'output', 'TVALID': 'output',
            'TREADY': 'custom', 'TID': 'output', 'TDEST': 'output',}

        max_stream_id = 2**len(axi_stream_in.TID)
        max_stream_dest = 2**len(self.axi_stream_in.TDEST)

        min_n_streams = 2
        max_n_streams = 20
        n_streams = random.randrange(min_n_streams, max_n_streams)

        # Generate a list of random and unique combinations of TID and
        # TDEST
        streams = generate_unique_streams(
            n_streams, max_stream_id, max_stream_dest)

        packet_list = {}
        trimmed_packet_list = {}
        data_len = {}

        total_data_len = 0

        for stream in streams:
            packet_list[stream], trimmed_packet_list[stream], data_len[stream] = (
                _generate_random_packets_with_Nones(
                    self.data_byte_width, self.max_packet_length,
                    self.max_new_packets))

            self.source_stream.add_data(
                packet_list[stream], stream_ID=stream[0],
                stream_destination=stream[1])

            total_data_len = data_len[stream] + total_data_len

        # Clear empty streams from the trimmed packet list (which previously
        # had packets and Nones trimmed)
        trimmed_packet_list = (
            trim_empty_packets_and_streams(trimmed_packet_list))

        trimmed_data_list = {}

        for stream in trimmed_packet_list.keys():
            trimmed_data_list[stream] = deque([
                val for packet in trimmed_packet_list[stream] for val in packet])

        TREADY_probability = 0.2
        custom_sources = [
            (self.source_stream.model, (self.clock, axi_stream_in), {}),
            (self.test_sink.model,
             (self.clock, self.axi_stream_out, TREADY_probability), {}),]

        cycles = total_data_len * 20 + 1

        myhdl_cosimulation(
            cycles, None, testbench, self.args, self.arg_types,
            custom_sources=custom_sources)

        self.assertTrue(self.test_sink.completed_packets=={})
        self.assertTrue(trimmed_data_list==self.test_sink.current_packets)

    def test_no_TLAST_on_output(self):
        '''If TLAST is missing on the output, this should be handled fine.
        '''

        @block
        def testbench(clock, axi_in, axi_out):

            buffer_block = axi_stream_buffer(
                clock, axi_in, axi_out, passive_sink_mode=False)

            return buffer_block

        axi_stream_out = AxiStreamInterface(
            self.data_byte_width, use_TLAST=False, TID_width=4, TDEST_width=4)

        self.args['axi_in'] = self.axi_stream_in
        self.args['axi_out'] = axi_stream_out

        self.arg_types['axi_in'] = {
            'TDATA': 'custom', 'TLAST': 'output', 'TVALID': 'custom',
            'TREADY': 'output', 'TID': 'custom', 'TDEST': 'custom',}

        self.arg_types['axi_out'] = {
            'TDATA': 'output', 'TVALID': 'output', 'TREADY': 'custom',
            'TID': 'output', 'TDEST': 'output',}

        max_stream_id = 2**len(self.axi_stream_in.TID)
        max_stream_dest = 2**len(self.axi_stream_in.TDEST)

        min_n_streams = 2
        max_n_streams = 20
        n_streams = random.randrange(min_n_streams, max_n_streams)

        # Generate a list of random and unique combinations of TID and
        # TDEST
        streams = generate_unique_streams(
            n_streams, max_stream_id, max_stream_dest)

        packet_list = {}
        trimmed_packet_list = {}
        data_len = {}

        total_data_len = 0

        for stream in streams:
            packet_list[stream], trimmed_packet_list[stream], data_len[stream] = (
                _generate_random_packets_with_Nones(
                    self.data_byte_width, self.max_packet_length,
                    self.max_new_packets))

            self.source_stream.add_data(
                packet_list[stream], stream_ID=stream[0],
                stream_destination=stream[1])

            total_data_len = data_len[stream] + total_data_len

        # Clear empty streams from the trimmed packet list (which previously
        # had packets and Nones trimmed)
        trimmed_packet_list = (
            trim_empty_packets_and_streams(trimmed_packet_list))

        trimmed_data_list = {}

        for stream in trimmed_packet_list.keys():
            trimmed_data_list[stream] = deque([
                val for packet in trimmed_packet_list[stream] for val in packet])

        TREADY_probability = 0.2
        custom_sources = [
            (self.source_stream.model, (self.clock, self.axi_stream_in), {}),
            (self.test_sink.model,
             (self.clock, axi_stream_out, TREADY_probability), {}),]

        cycles = total_data_len * 20 + 1

        myhdl_cosimulation(
            cycles, None, testbench, self.args, self.arg_types,
            custom_sources=custom_sources)

        self.assertTrue(self.test_sink.completed_packets=={})
        self.assertTrue(trimmed_data_list==self.test_sink.current_packets)

    def test_no_TID_and_TDEST_on_input(self):
        ''' If there is no TID or TDEST on the input the output TID and TDEST
        should be 0.
        '''

        @block
        def testbench(clock, axi_in, axi_out):

            buffer_block = axi_stream_buffer(
                clock, axi_in, axi_out, passive_sink_mode=True)

            @always(clock.posedge)
            def compare_sink():

                axi_out.TREADY.next = True

                self.assertEqual(axi_out.TID, 0)
                self.assertEqual(axi_out.TDEST, 0)

            return buffer_block, compare_sink

        axi_stream_in = AxiStreamInterface(self.data_byte_width)

        self.args['axi_in'] = axi_stream_in
        self.args['axi_out'] = self.axi_stream_out

        self.arg_types['axi_in'] = {
            'TDATA': 'custom', 'TLAST': 'custom', 'TVALID': 'custom',
            'TREADY': 'output',}

        self.arg_types['axi_out'] = {
            'TDATA': 'output', 'TLAST': 'output', 'TVALID': 'output',
            'TREADY': 'custom', 'TID': 'output', 'TDEST': 'output',}

        stream = (0, 0)

        packet_list = {}
        trimmed_packet_list = {}
        data_len = {}

        packet_list[stream], trimmed_packet_list[stream], data_len[stream] = (
            _generate_random_packets_with_Nones(
                self.data_byte_width, self.max_packet_length,
                self.max_new_packets))

        self.source_stream.add_data(
            packet_list[stream], stream_ID=stream[0],
            stream_destination=stream[1])

        # Clear empty streams from the trimmed packet list (which previously
        # had packets and Nones trimmed)
        trimmed_packet_list = (
            trim_empty_packets_and_streams(trimmed_packet_list))

        # Create a slave channel to drive the AXI in interface to the buffer.
        # The test_sink on the other side of the buffer should receive the
        # same data as the ref_sink.
        ref_sink = AxiStreamSlaveBFM()

        TREADY_probability = 1.0
        custom_sources = [
            (self.source_stream.model, (self.clock, axi_stream_in), {}),
            (ref_sink.model,
             (self.clock, axi_stream_in, TREADY_probability), {}),
            (self.test_sink.model,
             (self.clock, self.axi_stream_out, TREADY_probability), {}),]

        cycles = data_len[stream] + 1

        myhdl_cosimulation(
            cycles, None, testbench, self.args, self.arg_types,
            custom_sources=custom_sources)

        self.assertTrue(
            ref_sink.completed_packets==self.test_sink.completed_packets)
        self.assertTrue(
            trimmed_packet_list==self.test_sink.completed_packets)

    def test_no_TID_on_output(self):
        ''' If there is a TID on the input but no TID on the output then the
        system should error.
        '''
        axi_stream_out = AxiStreamInterface(
            self.data_byte_width, TDEST_width=len(self.axi_stream_in.TDEST))

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('There is a TID on the input and so there must be a TID on the '
             'output'),
            axi_stream_buffer, self.clock, self.axi_stream_in, axi_stream_out)

    def test_no_TDEST_on_output(self):
        ''' If there is a TDEST on the input but no TDEST on the output then
        the system should error.
        '''
        axi_stream_out = AxiStreamInterface(
            self.data_byte_width, TID_width=len(self.axi_stream_in.TID))

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('There is a TDEST on the input and so there must be a TDEST on '
             'the output'),
            axi_stream_buffer, self.clock, self.axi_stream_in, axi_stream_out)

    def test_TID_input_wider_than_output(self):
        ''' If the input TID is wider than the output TID then the system
        should error.
        '''

        axi_stream_in = AxiStreamInterface(
            self.data_byte_width,
            TID_width=(len(self.axi_stream_out.TID) + 2),
            TDEST_width=len(self.axi_stream_out.TDEST))

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('TID on the output must be as wide or wider than TID on the '
             'input'),
            axi_stream_buffer, self.clock, axi_stream_in, self.axi_stream_out)

    def test_TDEST_input_wider_than_output(self):
        ''' If the input TDEST is wider than the output TDEST then the system
        should error.
        '''

        axi_stream_in = AxiStreamInterface(
            self.data_byte_width, TID_width=len(self.axi_stream_out.TID),
            TDEST_width=(len(self.axi_stream_out.TDEST) + 2))

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('TDEST on the output must be as wide or wider than TDEST on the '
             'input'),
            axi_stream_buffer, self.clock, axi_stream_in, self.axi_stream_out)

    def test_TID_and_TDEST_outputs_wider_than_inputs(self):
        ''' If the output TID is wider than the input TID then the output TID
        should equal the input TID.

        If the output TDEST is wider than the input TDEST then the output
        TDEST should equal the input TDEST.
        '''

        @block
        def testbench(clock, axi_in, axi_out):

            buffer_block = axi_stream_buffer(
                clock, axi_in, axi_out, passive_sink_mode=True)

            @always(clock.posedge)
            def compare_sink():

                axi_out.TREADY.next = True

                self.assertEqual(axi_out.TID, self.axi_stream_in.TID)
                self.assertEqual(axi_out.TDEST, self.axi_stream_in.TDEST)

            return buffer_block, compare_sink

        axi_stream_out = AxiStreamInterface(
            self.data_byte_width,
            TID_width=(len(self.axi_stream_in.TID) + 2),
            TDEST_width=(len(self.axi_stream_in.TID) + 2))

        self.args['axi_in'] = self.axi_stream_in
        self.args['axi_out'] = axi_stream_out

        self.arg_types['axi_in'] = {
            'TDATA': 'custom', 'TLAST': 'custom', 'TVALID': 'custom',
            'TREADY': 'output', 'TID': 'output', 'TDEST': 'output',}

        self.arg_types['axi_out'] = {
            'TDATA': 'output', 'TLAST': 'output', 'TVALID': 'output',
            'TREADY': 'custom', 'TID': 'output', 'TDEST': 'output',}

        max_stream_id = 2**len(self.axi_stream_in.TID)
        max_stream_dest = 2**len(self.axi_stream_in.TDEST)

        min_n_streams = 2
        max_n_streams = 20
        n_streams = random.randrange(min_n_streams, max_n_streams)

        # Generate a list of random and unique combinations of TID and
        # TDEST
        streams = generate_unique_streams(
            n_streams, max_stream_id, max_stream_dest)

        packet_list = {}
        trimmed_packet_list = {}
        data_len = {}

        total_data_len = 0

        for stream in streams:
            packet_list[stream], trimmed_packet_list[stream], data_len[stream] = (
                _generate_random_packets_with_Nones(
                    self.data_byte_width, self.max_packet_length,
                    self.max_new_packets))

            self.source_stream.add_data(
                packet_list[stream], stream_ID=stream[0],
                stream_destination=stream[1])

            total_data_len = data_len[stream] + total_data_len

        # Clear empty streams from the trimmed packet list (which previously
        # had packets and Nones trimmed)
        trimmed_packet_list = (
            trim_empty_packets_and_streams(trimmed_packet_list))

        # Create a slave channel to drive the AXI in interface to the buffer.
        # The test_sink on the other side of the buffer should receive the
        # same data as the ref_sink.
        ref_sink = AxiStreamSlaveBFM()

        TREADY_probability = 1.0
        custom_sources = [
            (self.source_stream.model, (self.clock, self.axi_stream_in), {}),
            (ref_sink.model,
             (self.clock, self.axi_stream_in, TREADY_probability), {}),
            (self.test_sink.model,
             (self.clock, axi_stream_out, TREADY_probability), {}),]

        cycles = total_data_len + 1

        myhdl_cosimulation(
            cycles, None, testbench, self.args, self.arg_types,
            custom_sources=custom_sources)

        self.assertTrue(
            ref_sink.completed_packets==self.test_sink.completed_packets)
        self.assertTrue(
            trimmed_packet_list==self.test_sink.completed_packets)

class TestAxiMasterPlaybackBlockMinimal(TestCase):
    '''There should be a convertible AXI master block that simply plays back
    the packets it is passed.

    This minimal specification should be testable under VHDL/Verilog
    simulation.
    '''

    def setUp(self):

        self.data_byte_width = 8
        self.max_rand_val = 2**(8 * self.data_byte_width)

        self.axi_slave = AxiStreamSlaveBFM()

        self.axi_interface = AxiStreamInterface(
            self.data_byte_width, TID_width=4, TDEST_width=4)
        self.clock = Signal(bool(0))

        self.args = {
            'clock': self.clock, 'axi_interface': self.axi_interface,
            'signal_record': None}

        self.arg_types = {
            'clock': 'clock',
            'axi_interface': {'TVALID': 'output', 'TREADY': 'custom',
                              'TDATA': 'output', 'TLAST': 'output',
                              'TID': 'output', 'TDEST': 'output'},
            'signal_record': 'non-signal'}

    def sim_wrapper(
        self, sim_cycles, dut_factory, ref_factory, args, arg_types,
        **kwargs):

        return myhdl_cosimulation(
            sim_cycles, dut_factory, ref_factory, args, arg_types, **kwargs)

    def test_playback_of_packets(self):
        ''' The signal_record should be a dictionary of lists and should be
        properly handleable by a valid AXI slave.
        '''

        max_n_streams = 10
        max_packet_length = 20
        max_n_packets_per_stream = 8
        max_data_value = self.max_rand_val
        max_id_value = 2**self.axi_interface._TID_width
        max_dest_value = 2**self.axi_interface._TDEST_width

        signal_record, trimmed_packet_list = gen_random_signal_record(
            max_n_streams, max_packet_length, max_n_packets_per_stream,
            max_data_value, max_id_value, max_dest_value)

        self.args['signal_record'] = signal_record

        max_cycles = (
            30 * max_n_streams * max_n_packets_per_stream * max_packet_length)

        n_words_expected = 0

        for key in trimmed_packet_list.keys():
            for packet in trimmed_packet_list[key]:
                # Count the number of expected words
                n_words_expected += len(packet)

        @block
        def exit_checker(clock):

            cycles = [0]
            checker_data = {'transfer_count': 0,
                            'end_simulation': False}

            @always(clock.posedge)
            def checker():
                # A sanity check to make sure we don't hang
                assert cycles[0] < max_cycles
                cycles[0] += 1

                if checker_data['end_simulation']:
                    raise StopSimulation

                if self.axi_interface.TVALID and self.axi_interface.TREADY:
                    # Count the number of transfers
                    checker_data['transfer_count'] += 1

                if checker_data['transfer_count'] >= n_words_expected:
                    # The expected number of transfers has been received
                    checker_data['end_simulation'] = True

                if len(signal_record['TDATA']) == 0:
                    # No data to send
                    raise StopSimulation

            return checker

        custom_sources = [
            (exit_checker, (self.clock,), {}),
            (self.axi_slave.model, (self.clock, self.axi_interface, 0.5), {})]

        dut_results, ref_results = self.sim_wrapper(
            None, axi_master_playback, axi_master_playback, self.args,
            self.arg_types, custom_sources=custom_sources)

        self.assertTrue(
            self.axi_slave.completed_packets == trimmed_packet_list)

    def test_empty_packets(self):
        ''' If the signal_record argument does not contain any data, it should
        simply have TVALID always false.
        '''

        signal_record = {
            'TDATA': deque([]),
            'TID': deque([]),
            'TDEST': deque([]),
            'TLAST': deque([]),}

        self.args['signal_record'] = signal_record

        cycles = 300

        @block
        def TVALID_checker(clock):

            @always(clock.posedge)
            def checker():
                assert self.axi_interface.TVALID == False

            return checker

        custom_sources = [
            (TVALID_checker, (self.clock,), {}),
            (self.axi_slave.model, (self.clock, self.axi_interface, 0.5), {})]

        dut_results, ref_results = self.sim_wrapper(
            cycles, axi_master_playback, axi_master_playback, self.args,
            self.arg_types, custom_sources=custom_sources)

        self.assertEqual(self.axi_slave.completed_packets, {})

        dut_packets = [[]]
        for axi_cycle in dut_results['axi_interface']:
            self.assertFalse(axi_cycle['TVALID'])

    def test_None_sets_TVALID_False(self):
        '''Values of None in the packets should set TVALID to False for a
        cycle.
        '''
        max_n_streams = 10
        max_packet_length = 20
        max_n_packets_per_stream = 8
        max_data_value = self.max_rand_val
        max_id_value = 2**self.axi_interface._TID_width
        max_dest_value = 2**self.axi_interface._TDEST_width

        signal_record, trimmed_packet_list = gen_random_signal_record(
            max_n_streams, max_packet_length, max_n_packets_per_stream,
            max_data_value, max_id_value, max_dest_value, include_nones=True)

        n_words_expected = 0

        for key in trimmed_packet_list.keys():
            for packet in trimmed_packet_list[key]:
                # Count the number of expected words
                n_words_expected += len(packet)

        self.args['signal_record'] = signal_record

        max_cycles = (
            30 * max_n_streams * max_n_packets_per_stream * max_packet_length)

        @block
        def exit_checker(clock):

            cycles = [0]
            checker_data = {'transfer_count': 0,
                            'end_simulation': False}

            @always(clock.posedge)
            def checker():
                # A sanity check to make sure we don't hang
                assert cycles[0] < max_cycles
                cycles[0] += 1

                if checker_data['end_simulation']:
                    raise StopSimulation

                if self.axi_interface.TVALID and self.axi_interface.TREADY:
                    # Count the number of transfers
                    checker_data['transfer_count'] += 1

                if checker_data['transfer_count'] >= n_words_expected:
                    # The expected number of transfers has been received
                    checker_data['end_simulation'] = True

                if len(signal_record['TDATA']) == 0:
                    # No data to send
                    raise StopSimulation

            return checker

        custom_sources = [
            (exit_checker, (self.clock,), {}),
            (self.axi_slave.model, (self.clock, self.axi_interface, 0.5), {})]

        dut_results, ref_results = self.sim_wrapper(
            None, axi_master_playback, axi_master_playback, self.args,
            self.arg_types, custom_sources=custom_sources)

        self.assertTrue(
            self.axi_slave.completed_packets == trimmed_packet_list)
        self.assertTrue(
            dut_results['axi_interface'] == ref_results['axi_interface'])

    def test_no_TLAST_on_interface(self):
        '''A missing TLAST on the interface should be handled with no problem.
        '''
        max_n_streams = 10
        max_packet_length = 20
        max_n_packets_per_stream = 8
        max_data_value = self.max_rand_val
        max_id_value = 2**self.axi_interface._TID_width
        max_dest_value = 2**self.axi_interface._TDEST_width

        signal_record, trimmed_packet_list = gen_random_signal_record(
            max_n_streams, max_packet_length, max_n_packets_per_stream,
            max_data_value, max_id_value, max_dest_value)

        n_words_expected = 0

        expected_data = {}

        for stream in trimmed_packet_list.keys():
            expected_data[stream] = deque([])

            for packet in trimmed_packet_list[stream]:
                # Count the number of expected words
                n_words_expected += len(packet)
                # Add the packet to the expected data
                expected_data[stream].extend(packet)

        self.args['signal_record'] = signal_record

        max_cycles = (
            30 * max_n_streams * max_n_packets_per_stream * max_packet_length)

        @block
        def exit_checker(clock):

            cycles = [0]
            checker_data = {'transfer_count': 0,
                            'end_simulation': False}

            @always(clock.posedge)
            def checker():
                # A sanity check to make sure we don't hang
                assert cycles[0] < max_cycles
                cycles[0] += 1

                if checker_data['end_simulation']:
                    raise StopSimulation

                if axi_interface.TVALID and axi_interface.TREADY:
                    # Count the number of transfers
                    checker_data['transfer_count'] += 1

                if checker_data['transfer_count'] >= n_words_expected:
                    # The expected number of transfers has been received
                    checker_data['end_simulation'] = True

                if len(signal_record['TDATA']) == 0:
                    # No data to send
                    raise StopSimulation

            return checker

        axi_interface = AxiStreamInterface(
            self.data_byte_width, use_TLAST=False, TID_width=4, TDEST_width=4)
        self.args['axi_interface'] = axi_interface
        self.arg_types['axi_interface'] = {
            'TVALID': 'output', 'TREADY': 'custom', 'TDATA': 'output',
            'TID': 'output', 'TDEST': 'output'}

        custom_sources = [
            (exit_checker, (self.clock,), {}),
            (self.axi_slave.model, (self.clock, axi_interface, 0.5), {})]

        dut_results, ref_results = self.sim_wrapper(
            None, axi_master_playback, axi_master_playback, self.args,
            self.arg_types, custom_sources=custom_sources)

        self.assertTrue(
            self.axi_slave.completed_packets == {})
        self.assertTrue(
            self.axi_slave.current_packets == expected_data)
        self.assertTrue(
            dut_results['axi_interface'] == ref_results['axi_interface'])

    def test_no_TID_or_TDEST_on_interface(self):
        ''' A missing TID and TDEST on the interface should be handled with no
        problem.
        '''

        max_n_streams = 2
        max_packet_length = 50
        max_n_packets_per_stream = 30
        max_data_value = self.max_rand_val
        max_id_value = 2**self.axi_interface._TID_width
        max_dest_value = 2**self.axi_interface._TDEST_width

        signal_record, trimmed_packet_list = gen_random_signal_record(
            max_n_streams, max_packet_length, max_n_packets_per_stream,
            max_data_value, max_id_value, max_dest_value, min_n_streams=1,
            min_packet_length=1, min_n_packets_per_stream=1)

        expected_output = {(0, 0): deque([])}

        for stream in trimmed_packet_list.keys():
            expected_output[(0, 0)].extend(trimmed_packet_list[stream])

        # Trim any empty streams and packets
        expected_output = trim_empty_packets_and_streams(expected_output)

        self.args['signal_record'] = signal_record

        max_cycles = (
            30 * max_n_streams * max_n_packets_per_stream * max_packet_length)

        n_words_expected = 0

        for key in trimmed_packet_list.keys():
            for packet in trimmed_packet_list[key]:
                # Count the number of expected words
                n_words_expected += len(packet)

        @block
        def exit_checker(clock):

            cycles = [0]
            checker_data = {'transfer_count': 0,
                            'end_simulation': False}

            @always(clock.posedge)
            def checker():
                # A sanity check to make sure we don't hang
                assert cycles[0] < max_cycles
                cycles[0] += 1

                if checker_data['end_simulation']:
                    raise StopSimulation

                if axi_interface.TVALID and axi_interface.TREADY:
                    # Count the number of transfers
                    checker_data['transfer_count'] += 1

                if checker_data['transfer_count'] >= n_words_expected:
                    # The expected number of transfers has been received
                    checker_data['end_simulation'] = True

                if len(signal_record['TDATA']) == 0:
                    # No data to send
                    raise StopSimulation

            return checker

        axi_interface = AxiStreamInterface(self.data_byte_width)
        self.args['axi_interface'] = axi_interface
        self.arg_types['axi_interface'] = {
            'TVALID': 'output', 'TREADY': 'custom', 'TDATA': 'output',
            'TLAST': 'output'}

        custom_sources = [
            (exit_checker, (self.clock,), {}),
            (self.axi_slave.model, (self.clock, axi_interface, 0.5), {})]

        dut_results, ref_results = self.sim_wrapper(
            None, axi_master_playback, axi_master_playback, self.args,
            self.arg_types, custom_sources=custom_sources)

        self.assertTrue(
            self.axi_slave.completed_packets == expected_output)

    def test_incomplete_last_packet_argument(self):
        '''If the ``incomplete_last_packet`` argument is set to ``True``,
        TLAST will not be asserted for the end of the last packet.

        If the last packet is empty, this effectively negates the
        ``incomplete_last_packet`` argument (since there is no data to not
        assert TLAST on).
        '''
        max_n_streams = 10
        max_packet_length = 50
        max_n_packets_per_stream = 20
        max_data_value = self.max_rand_val
        max_id_value = 2**self.axi_interface._TID_width
        max_dest_value = 2**self.axi_interface._TDEST_width

        signal_record, trimmed_packet_list = gen_random_signal_record(
            max_n_streams, max_packet_length, max_n_packets_per_stream,
            max_data_value, max_id_value, max_dest_value)

        n_words_expected = 0

        for key in trimmed_packet_list.keys():
            for packet in trimmed_packet_list[key]:
                # Count the number of expected words
                n_words_expected += len(packet)

        expected_packet_list = copy.deepcopy(trimmed_packet_list)

        if len(signal_record['TDATA']) > 0:
            for n, data_word in enumerate(reversed(signal_record['TDATA'])):
                if data_word is not None:
                    # Find the index of the last valid word in the signal
                    # record
                    index = len(signal_record['TDATA']) - n -1
                    # Find which stream that word is on
                    last_packet_stream = (
                        signal_record['TID'][index],
                        signal_record['TDEST'][index])

                    # Remove the last packet from the expected packet list
                    last_packet = {
                        last_packet_stream: expected_packet_list[
                            last_packet_stream].pop()}

                    break
        else:
            last_packet = {}

        # The removal of the last packet may have created an empty stream so
        # we try to trim it just in case
        expected_packet_list = (
            trim_empty_packets_and_streams(expected_packet_list))

        self.args['signal_record'] = signal_record

        max_cycles = (
            30 * max_n_streams * max_n_packets_per_stream * max_packet_length)

        @block
        def exit_checker(clock):

            cycles = [0]
            checker_data = {'transfer_count': 0,
                            'end_simulation': False}

            @always(clock.posedge)
            def checker():
                # A sanity check to make sure we don't hang
                assert cycles[0] < max_cycles
                cycles[0] += 1

                if checker_data['end_simulation']:
                    raise StopSimulation

                if self.axi_interface.TVALID and self.axi_interface.TREADY:
                    # Count the number of transfers
                    checker_data['transfer_count'] += 1

                if checker_data['transfer_count'] >= n_words_expected:
                    # The expected number of transfers has been received
                    checker_data['end_simulation'] = True

                if len(signal_record['TDATA']) == 0:
                    # No data to send
                    raise StopSimulation

            return checker

        self.args['incomplete_last_packet'] = True
        self.arg_types['incomplete_last_packet'] = 'non-signal'

        custom_sources = [
            (exit_checker, (self.clock,), {}),
            (self.axi_slave.model, (self.clock, self.axi_interface, 0.5), {})]

        dut_results, ref_results = self.sim_wrapper(
            None, axi_master_playback, axi_master_playback, self.args,
            self.arg_types, custom_sources=custom_sources)

        self.assertTrue(
            self.axi_slave.completed_packets == expected_packet_list)
        self.assertTrue(
            self.axi_slave.current_packets == last_packet)
        self.assertTrue(
            dut_results['axi_interface'] == ref_results['axi_interface'])

    def test_incorrect_TID_signal_record_length(self):
        ''' If the AXI interface has the TID signal then the length of the TID
        signal record must be equal to the length of the TDATA signal record
        or else the system should error.
        '''

        axi_stream_in = AxiStreamInterface(
            self.data_byte_width, TID_width=4, TDEST_width=4)

        max_n_streams = 10
        max_packet_length = 50
        max_n_packets_per_stream = 20
        max_data_value = self.max_rand_val
        max_id_value = 2**self.axi_interface._TID_width
        max_dest_value = 2**self.axi_interface._TDEST_width

        signal_record, trimmed_packet_list = gen_random_signal_record(
            max_n_streams, max_packet_length, max_n_packets_per_stream,
            max_data_value, max_id_value, max_dest_value, min_n_streams=1,
            min_packet_length=1, min_n_packets_per_stream=1)

        # Remove a single value from the TID signal record to trigger the
        # error
        signal_record['TID'].pop()

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('The length of the TID signal_record must be equal to the '
             'length of the TDATA signal_record'),
            axi_master_playback, self.clock, axi_stream_in, signal_record)

    def test_incorrect_TDEST_signal_record_length(self):
        ''' If the AXI interface has the TDEST signal then the length of the
        TDEST signal record must be equal to the length of the TDATA signal
        record or else the system should error.
        '''

        axi_stream_in = AxiStreamInterface(
            self.data_byte_width, TID_width=4, TDEST_width=4)

        max_n_streams = 10
        max_packet_length = 50
        max_n_packets_per_stream = 20
        max_data_value = self.max_rand_val
        max_id_value = 2**self.axi_interface._TID_width
        max_dest_value = 2**self.axi_interface._TDEST_width

        signal_record, trimmed_packet_list = gen_random_signal_record(
            max_n_streams, max_packet_length, max_n_packets_per_stream,
            max_data_value, max_id_value, max_dest_value, min_n_streams=1,
            min_packet_length=1, min_n_packets_per_stream=1)

        # Remove a single value from the TDEST signal record to trigger the
        # error
        signal_record['TDEST'].pop()

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('The length of the TDEST signal_record must be equal to the '
             'length of the TDATA signal_record'),
            axi_master_playback, self.clock, axi_stream_in, signal_record)

    def test_incorrect_TLAST_signal_record_length(self):
        ''' If the AXI interface has the TLAST signal then the length of the
        TLAST signal record must be equal to the length of the TDATA signal
        record or else the system should error.
        '''

        axi_stream_in = AxiStreamInterface(
            self.data_byte_width, TID_width=4, TDEST_width=4)

        max_n_streams = 10
        max_packet_length = 50
        max_n_packets_per_stream = 20
        max_data_value = self.max_rand_val
        max_id_value = 2**self.axi_interface._TID_width
        max_dest_value = 2**self.axi_interface._TDEST_width

        signal_record, trimmed_packet_list = gen_random_signal_record(
            max_n_streams, max_packet_length, max_n_packets_per_stream,
            max_data_value, max_id_value, max_dest_value, min_n_streams=1,
            min_packet_length=1, min_n_packets_per_stream=1)

        # Remove a single value from the TLAST signal record to trigger the
        # error
        signal_record['TLAST'].pop()

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('The length of the TLAST signal_record must be equal to the '
             'length of the TDATA signal_record'),
            axi_master_playback, self.clock, axi_stream_in, signal_record)

    def test_block_converts_to_vhdl(self):
        '''The axi_master_playback block should convert to VHDL
        '''
        max_n_streams = 10
        max_packet_length = 20
        max_n_packets_per_stream = 8
        max_data_value = self.max_rand_val
        max_id_value = 2**self.axi_interface._TID_width
        max_dest_value = 2**self.axi_interface._TDEST_width

        signal_record, trimmed_packet_list = gen_random_signal_record(
            max_n_streams, max_packet_length, max_n_packets_per_stream,
            max_data_value, max_id_value, max_dest_value, include_nones=True)

        n_words_expected = 0

        for key in trimmed_packet_list.keys():
            for packet in trimmed_packet_list[key]:
                # Count the number of expected words
                n_words_expected += len(packet)

        self.args['signal_record'] = signal_record

        tmp_dir = tempfile.mkdtemp()
        try:
            instance = axi_master_playback(**self.args)
            instance.convert('VHDL', path=tmp_dir)
            self.assertTrue(os.path.exists(
                os.path.join(tmp_dir, 'axi_master_playback.vhd')))
        finally:
            shutil.rmtree(tmp_dir)

    def test_block_converts_to_verilog(self):
        '''The axi_master_playback block should convert to Verilog.
        '''
        max_n_streams = 10
        max_packet_length = 20
        max_n_packets_per_stream = 8
        max_data_value = self.max_rand_val
        max_id_value = 2**self.axi_interface._TID_width
        max_dest_value = 2**self.axi_interface._TDEST_width

        signal_record, trimmed_packet_list = gen_random_signal_record(
            max_n_streams, max_packet_length, max_n_packets_per_stream,
            max_data_value, max_id_value, max_dest_value, include_nones=True)

        n_words_expected = 0

        for key in trimmed_packet_list.keys():
            for packet in trimmed_packet_list[key]:
                # Count the number of expected words
                n_words_expected += len(packet)

        self.args['signal_record'] = signal_record

        tmp_dir = tempfile.mkdtemp()
        try:
            instance = axi_master_playback(**self.args)
            instance.convert('Verilog', path=tmp_dir)
            self.assertTrue(os.path.exists(
                os.path.join(tmp_dir, 'axi_master_playback.v')))
        finally:
            shutil.rmtree(tmp_dir)

class TestAxiMasterPlaybackBlockMinimalVivadoVHDL(
    TestAxiMasterPlaybackBlockMinimal):
    def sim_wrapper(self, sim_cycles, dut_factory, ref_factory,
                           args, arg_types, **kwargs):

        return vivado_vhdl_cosimulation(
            sim_cycles, dut_factory, ref_factory, args, arg_types, **kwargs)

class TestAxiMasterPlaybackBlockMinimalVivadoVerilog(
    TestAxiMasterPlaybackBlockMinimal):
    def sim_wrapper(self, sim_cycles, dut_factory, ref_factory,
                           args, arg_types, **kwargs):

        return vivado_verilog_cosimulation(
            sim_cycles, dut_factory, ref_factory, args, arg_types, **kwargs)
