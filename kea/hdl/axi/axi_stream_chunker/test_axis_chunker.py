import copy
import random

from collections import deque
from itertools import islice

from myhdl import block, Signal, intbv, always, enum, StopSimulation

from kea.hdl.axi import (
    AxiStreamInterface, AxiStreamMasterBFM, AxiStreamSlaveBFM)
from kea.hdl.axi.axi_stream_utils import check_axi_stream_interface_attributes
from kea.testing.test_utils import (
    axi_stream_types_generator, generate_value_with_preferences)
from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)
from kea.utils.interface_checks import (
    check_bool_signal,
    check_intbv_signal,
    get_dut_function_call_arguments,
    verify_dut_called_function)

from ._axis_chunker import axis_chunker

def dut_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    axis_args = {
        'bus_width': 4,
        'TID_width': None,
        'TDEST_width': None,
        'TUSER_width': None,
        'TVALID_init': False,
        'TREADY_init': False,
        'use_TLAST': True,
        'use_TSTRB': False,
        'use_TKEEP': False
    }

    dut_args = {
        'clock': Signal(False),
        'reset': Signal(False),
        'n_words_per_chunk': Signal(intbv(0)[8:]),
        'axis_source': AxiStreamInterface(**axis_args),
        'axis_sink': AxiStreamInterface(**axis_args),
    }

    axis_source_types = (
        axi_stream_types_generator(
            sink=False,
            TID_width=axis_args['TID_width'],
            TDEST_width=axis_args['TDEST_width'],
            TUSER_width=axis_args['TUSER_width'],
            use_TLAST=axis_args['use_TLAST'],
            use_TSTRB=axis_args['use_TSTRB'],
            use_TKEEP=axis_args['use_TKEEP']))

    axis_sink_types = (
        axi_stream_types_generator(
            sink=True,
            TID_width=axis_args['TID_width'],
            TDEST_width=axis_args['TDEST_width'],
            TUSER_width=axis_args['TUSER_width'],
            use_TLAST=axis_args['use_TLAST'],
            use_TSTRB=axis_args['use_TSTRB'],
            use_TKEEP=axis_args['use_TKEEP']))

    dut_arg_types = {
        'clock': 'clock',
        'reset': 'custom',
        'n_words_per_chunk': 'custom',
        'axis_source': axis_source_types,
        'axis_sink': axis_sink_types,
    }

    return dut_args, dut_arg_types

def add_runs_of_none(
    packet, probability_of_run=0.2, min_length_of_run=0,
    max_length_of_run=5):
    ''' Given a list of words (data_packet) this function will insert runs of
    `None` values of random length at random intervals in the data.
    '''

    manipulated_packet = copy.copy(packet)

    for n in reversed(range(len(packet))):
        # Run through every index in the packet. If we don't reverse
        # the order of n here we increment up through the Nones we may
        # have just inserted into the list and may add more Nones in
        # the middle.
        if random.random() < probability_of_run:
            # At random indexes create a run of nones of random length
            # and insert them into the data
            none_run = [None]*random.randrange(
                min_length_of_run, max_length_of_run)

            for each in none_run:
                manipulated_packet.insert(n, each)

    return manipulated_packet

def generate_expected_chunks(data, n_words_per_chunk):
    '''`data` should be a list containing the data which will be used to
    stimulate the `axis_source`.

    `n_words_per_chunk` should be an integer and should be the
    `n_words_per_chunk` used to stimulate the DUT.
    '''

    expected_chunks = []

    # Split the data into chunks
    for i in range(0, len(data), n_words_per_chunk):
        expected_chunks.append(deque(data[i:i + n_words_per_chunk]))

    return expected_chunks

class TestAxisChunkerInterface(KeaTestCase):
    ''' The DUT should reject incompatible interfaces and arguments.
    '''

    def setUp(self):

        self.dut_args, _dut_arg_types = dut_args_setup()

    def test_bool_ports_checked(self):
        '''The `clock` and `reset` ports should be boolean signals.

        Anything else should raise an error.
        '''
        dut = axis_chunker
        bool_port_names = ['clock', 'reset']

        # Get all calls to check_bool_signal made by the DUT
        dut_function_call_arguments_list = (
            get_dut_function_call_arguments(
                check_bool_signal, dut, self.dut_args))

        for port_name in bool_port_names:
            expected_args_dict = {
                'test_signal': self.dut_args[port_name],
                'name': port_name,
            }

            # Check that the specified port was checked
            verify_dut_called_function(
                check_bool_signal, dut_function_call_arguments_list,
                expected_args_dict, 'test_signal', port_name)

    def test_intbv_ports_checked(self):
        '''The `n_words_per_chunk` port should be an unsigned intbv signal.

        Anything else should raise an error.
        '''
        dut = axis_chunker
        port_name = 'n_words_per_chunk'
        intbv_port_requirements = {
            port_name: {
                'signed': False,
            }
        }

        # Get all calls to check_intbv_signal made by the DUT
        dut_function_call_arguments_list = (
            get_dut_function_call_arguments(
                check_intbv_signal, dut, self.dut_args))

        # Assemble the args that should have been passed to
        # check_intbv_signal
        expected_args_dict = intbv_port_requirements[port_name]
        expected_args_dict['test_signal'] = self.dut_args[port_name]
        expected_args_dict['name'] =  port_name

        # Check that the specified port was checked
        verify_dut_called_function(
            check_intbv_signal, dut_function_call_arguments_list,
            expected_args_dict, 'test_signal', port_name)

    def test_axis_attributes_checked(self):
        '''The `axis_source` `AxiStreamInterface` should not have a `TID`,
        `TDEST`, `TUSER`, `TSTRB` or `TKEEP`. It should have a `TLAST`. The
        `TVALID` and `TREADY` signals should initialise low.

        Anything else should raise an error.

        The `axis_sink` `AxiStreamInterface` should have the same `bus_width`
        as `axis_source`. It should not have a `TID`, `TDEST`, `TUSER`,
        `TSTRB` or `TKEEP`. It should have a `TLAST`. The `TVALID` and
        `TREADY` signals should initialise low.

        Anything else should raise an error.
        '''
        axis_attributes = {
            'bus_width': self.dut_args['axis_source'].bus_width,
            'TID_width': None,
            'TDEST_width': None,
            'TUSER_width': None,
            'TVALID_init': False,
            'TREADY_init': False,
            'use_TLAST': True,
            'use_TSTRB': False,
            'use_TKEEP': False,
        }

        dut = axis_chunker
        axis_interface_expected_attributes = {
            'axis_source': axis_attributes,
            'axis_sink': axis_attributes,
        }

        # Get all calls to check_axi_stream_interface_attributes made by the
        # DUT
        dut_function_call_arguments_list = (
            get_dut_function_call_arguments(
                check_axi_stream_interface_attributes, dut, self.dut_args))

        for port_name in axis_interface_expected_attributes:
            # Assemble the args that should have been passed to
            # check_axi_stream_interface_attributes
            expected_args_dict = {
                'expected_attributes': (
                    axis_interface_expected_attributes[port_name]),
                'axis_interface': self.dut_args[port_name]
            }

            # Check that the specified port was checked
            verify_dut_called_function(
                check_axi_stream_interface_attributes,
                dut_function_call_arguments_list,
                expected_args_dict, 'axis_interface', port_name)

class TestAxisChunker(KeaTestCase):

    def setUp(self):

        self.test_count = 0
        self.tests_complete = False

    @block
    def monitor_tests(self, n_tests, **dut_args):

        clock = dut_args['clock']

        return_objects = []

        @always(clock.posedge)
        def monitor():

            if self.test_count >= n_tests:
                # Check that all the tests are run
                self.tests_complete = True

                raise StopSimulation

        return_objects.append(monitor)

        return return_objects

    @block
    def stim_ctrl(
        self, reset_toggle_p, reset_pulse_p, n_words_per_chunk_update_p,
        **dut_args):

        clock = dut_args['clock']
        reset = dut_args['reset']
        n_words_per_chunk = dut_args['n_words_per_chunk']

        return_objects = []

        hold_reset_high = Signal(False)

        @always(clock.posedge)
        def stim():

            #########
            # Reset #
            #########

            if random.random() < reset_toggle_p:
                # Hold reset high for extended period
                hold_reset_high.next = not hold_reset_high
                reset.next = not reset

            elif not hold_reset_high:

                reset.next = False

                if random.random() < reset_pulse_p:
                    # Randomly pulse reset
                    reset.next = True

            #####################
            # N words per chunk #
            #####################

            if random.random() < n_words_per_chunk_update_p:
                n_words_per_chunk.next = (
                    generate_value_with_preferences(0, 33, [0, 1, 2], 0.3))

        return_objects.append(stim)

        return return_objects

    @block
    def stim_check_data_packets(
        self, vary_axis_source_tvalid, axis_sink_tready_p, **dut_args):
        ''' This block performs packet based checks on the DUT. It will send
        packets on `axis_source` and check that the packets are chunked
        correctly and output on `axis_sink`.
        '''

        clock = dut_args['clock']
        reset = dut_args['reset']
        n_words_per_chunk = dut_args['n_words_per_chunk']
        axis_source = dut_args['axis_source']
        axis_sink = dut_args['axis_sink']

        return_objects = []

        # Create an AxiStreamMasterBFM to drive the axis_source
        axis_source_master_bfm = AxiStreamMasterBFM()
        return_objects.append(
            axis_source_master_bfm.model(clock, axis_source, reset))

        # Create an AxiStreamSlaveBFM to receive data from axis_sink
        axis_sink_slave_bfm = AxiStreamSlaveBFM()
        return_objects.append(
            axis_sink_slave_bfm.model(clock, axis_sink, axis_sink_tready_p))

        data_upper_bound = 2**len(axis_source.TDATA)

        packet_n_words_per_chunk = Signal(intbv(0)[len(n_words_per_chunk):])

        pending_packets = deque([])
        expected_packets = {}

        t_state = enum(
            'STIM', 'AWAIT_SOURCE_START', 'AWAIT_SOURCE_COMPLETE',
            'AWAIT_SINK_COMPLETE', 'CHECK', 'RESET')
        state = Signal(t_state.STIM)

        @always(clock.posedge)
        def stim_check():

            if state == t_state.STIM:
                if not reset and random.random() < 0.01:
                    # We check reset is low to avoid a race. If we attempt to
                    # load data into the AXIS master when reset is high, it
                    # can arrive after the AXIS master has acted upon the
                    # reset. This will result in a mismatch between the
                    # expected packets and the actual packets.

                    # Generate a random number of back to back packets to test
                    # the situation when axis_source.TVALID stays high after
                    # the TLAST of the preceding packet.
                    n_back_to_back_packets = random.randrange(1, 5)

                    # Generate random packet lengths for the packets. Give
                    # preference to 1 word and 2 word packets.
                    packet_lengths = [
                        generate_value_with_preferences(1, 129, [1, 2], 0.2)
                        for n in range(n_back_to_back_packets)]

                    stim_packets = []

                    for packet_length in packet_lengths:
                        # Generate the packets of data
                        packet = [
                            random.randrange(data_upper_bound)
                            for n in range(packet_length)]

                        # Keep a record of the stim packets
                        pending_packets.append(packet)

                        if vary_axis_source_tvalid:
                            # Add runs of None to the packet to vary TVALID
                            stim_packets.append(add_runs_of_none(packet))

                        else:
                            # Add the packet to the stim data
                            stim_packets.append(packet)

                    # Add the stim_packets to the axis_source_master_bfm
                    axis_source_master_bfm.add_data(stim_packets)

                    # Keep a record of n_words_per_chunk
                    packet_n_words_per_chunk.next = n_words_per_chunk

                    state.next = t_state.AWAIT_SOURCE_START

            elif state == t_state.AWAIT_SOURCE_START:
                if (axis_source.TVALID and axis_source.TREADY and
                    packet_n_words_per_chunk > 0):

                    # Extract the first packet
                    data = pending_packets.popleft()

                    if len(expected_packets) <= 0:
                        # Set up the expected packets dict
                        expected_packets[(0, 0)] = deque([])

                    # Generate the expected chunks
                    expected_packets[(0, 0)].extend(
                        generate_expected_chunks(
                            data, int(packet_n_words_per_chunk.val)))

                    if axis_source.TLAST:
                        if len(pending_packets) > 0:
                            # There are more packets pending

                            # Keep a record of n_words_per_chunk
                            packet_n_words_per_chunk.next = n_words_per_chunk

                            # There is more data pending but it hasn't started
                            # arriving yet
                            state.next = t_state.AWAIT_SOURCE_START

                        else:
                            # There are no more packets pending
                            state.next = t_state.AWAIT_SINK_COMPLETE

                    else:
                        state.next = t_state.AWAIT_SOURCE_COMPLETE

                else:
                    # Keep a record of n_words_per_chunk
                    packet_n_words_per_chunk.next = n_words_per_chunk

            elif state == t_state.AWAIT_SOURCE_COMPLETE:

                if (axis_source.TVALID and
                    axis_source.TREADY and
                    axis_source.TLAST):
                    # The packet has completed

                    if len(pending_packets) > 0:
                        # There are more packets pending

                        # Keep a record of n_words_per_chunk
                        packet_n_words_per_chunk.next = n_words_per_chunk

                        # There is more data pending but it hasn't started
                        # arriving yet
                        state.next = t_state.AWAIT_SOURCE_START

                    else:
                        # There are no more packets pending
                        state.next = t_state.AWAIT_SINK_COMPLETE

            elif state == t_state.AWAIT_SINK_COMPLETE:
                if (axis_sink.TVALID and
                    axis_sink.TREADY and
                    axis_sink.TLAST):
                    # The packet has finished on the output
                    state.next = t_state.CHECK

            elif state == t_state.CHECK:

                # Check that there are no partially received packets in the
                # sink BFM
                assert(not axis_sink_slave_bfm.current_packets)

                # Check that the received packets are correct
                assert(
                    axis_sink_slave_bfm.completed_packets == expected_packets)

                # Clear the completed packets
                axis_sink_slave_bfm.clear_completed_packets()

                # Clear the expected packets
                expected_packets.clear()

                self.test_count += 1

                state.next = t_state.STIM

            elif state == t_state.RESET:

                if len(axis_sink_slave_bfm.completed_packets) > 0:
                    # Some packets completed before the reset so extract them
                    completed_packets = (
                        axis_sink_slave_bfm.completed_packets[(0, 0)])

                    for n in range(len(completed_packets)):
                        # Check that the packets which completed before the
                        # reset are correct
                        expected_packet = expected_packets[(0, 0)].popleft()
                        received_packet = completed_packets.popleft()

                        assert(received_packet == expected_packet)

                if len(axis_sink_slave_bfm.current_packets):
                    # There is a packet in progress

                    expected_packet = expected_packets[(0, 0)].popleft()
                    received_data = (
                        axis_sink_slave_bfm.current_packets[(0, 0)])

                    # Check that the data received before the reset is correct
                    assert(all(a == b for a, b in zip(
                        islice(received_data, len(received_data)),
                        islice(expected_packet, len(received_data)))))

                # Reset the sink BFM
                axis_sink_slave_bfm.reset()

                # Clear the pending packets
                pending_packets.clear()

                # Clear the expected packets
                expected_packets.clear()

                state.next = t_state.STIM

            if reset:
                state.next = t_state.RESET

        return_objects.append(stim_check)

        return return_objects

    @block
    def check_axis_signals(self, **dut_args):
        ''' This block performs continuous checks on the AXI stream signals.
        '''

        clock = dut_args['clock']
        reset = dut_args['reset']
        n_words_per_chunk = dut_args['n_words_per_chunk']
        axis_source = dut_args['axis_source']
        axis_sink = dut_args['axis_sink']

        return_objects = []

        packet_n_words_per_chunk = Signal(intbv(0)[len(n_words_per_chunk):])
        word_count = Signal(intbv(0)[len(n_words_per_chunk):])

        expected_axis_sink_tvalid = Signal(False)
        expected_axis_sink_tlast = Signal(False)
        expected_axis_sink_tdata = Signal(intbv(0)[len(axis_sink.TDATA):])

        t_state = enum('IDLE', 'PACKET_IN_PROGRESS')
        state = Signal(t_state.IDLE)


        @always(clock.posedge)
        def check():

            #############################
            # axis_source.TREADY checks #
            #############################

            if reset or packet_n_words_per_chunk <= 0:
                # axis_source.TREADY should be set low in response to a reset
                assert(not axis_source.TREADY)

            else:
                # The DUT should be forwarding data to axis_sink

                if axis_sink.TVALID:
                    # There is data on the axis_sink so the DUT should only
                    # set axis_source.TREADY if axis_sink.TREADY is high.
                    assert(axis_source.TREADY == axis_sink.TREADY)

                else:
                    # There is no data on axis_sink so axis_source.TREADY
                    # should be high
                    assert(axis_source.TREADY)

            ####################
            # axis_sink checks #
            ####################

            assert(axis_sink.TVALID == expected_axis_sink_tvalid)
            assert(axis_sink.TLAST == expected_axis_sink_tlast)
            assert(axis_sink.TDATA == expected_axis_sink_tdata)

            if state == t_state.IDLE:

                if axis_sink.TVALID and axis_sink.TREADY:
                    # Downstream has received the word on the axis_sink
                    expected_axis_sink_tvalid.next = False

                if axis_source.TVALID and axis_source.TREADY:
                    # The DUT has accepted a word on the axis_source so it
                    # should update axis_sink.
                    expected_axis_sink_tvalid.next = True
                    expected_axis_sink_tdata.next = axis_source.TDATA

                    if axis_source.TLAST:
                        # The packet on the axis_source is a single word
                        expected_axis_sink_tlast.next = True

                        # Update the packet_n_words_per_chunk
                        packet_n_words_per_chunk.next = n_words_per_chunk

                        state.next = t_state.IDLE

                    elif packet_n_words_per_chunk <= 1:
                        # We need to set TLAST to chunk the packet into one
                        # word chunks
                        expected_axis_sink_tlast.next = True
                        word_count.next = 0
                        state.next = t_state.PACKET_IN_PROGRESS

                    else:
                        # The chunk is longer than a single word
                        expected_axis_sink_tlast.next = False
                        word_count.next = 1
                        state.next = t_state.PACKET_IN_PROGRESS

                else:
                    # Keep a record of the n_words_per_chunk
                    packet_n_words_per_chunk.next = n_words_per_chunk

            elif state == t_state.PACKET_IN_PROGRESS:

                if axis_sink.TVALID and axis_sink.TREADY:
                    # Downstream has received the word on the axis_sink
                    expected_axis_sink_tvalid.next = False

                if axis_source.TVALID and axis_source.TREADY:
                    # The DUT has accepted a word on the axis_source so it
                    # should update axis_sink.
                    expected_axis_sink_tvalid.next = True
                    expected_axis_sink_tdata.next = axis_source.TDATA

                    if axis_source.TLAST:
                        # The last word of the source packet has been received
                        expected_axis_sink_tlast.next = True

                        # Update the packet_n_words_per_chunk
                        packet_n_words_per_chunk.next = n_words_per_chunk

                        state.next = t_state.IDLE

                    elif word_count >= packet_n_words_per_chunk-1:
                        # The next word will be the last of the chunk.
                        expected_axis_sink_tlast.next = True
                        word_count.next = 0
                        state.next = t_state.PACKET_IN_PROGRESS

                    else:
                        # We have not yet forwarded a chunks worth of data
                        expected_axis_sink_tlast.next = False
                        word_count.next = word_count + 1
                        state.next = t_state.PACKET_IN_PROGRESS

            if reset:
                expected_axis_sink_tvalid.next = False

                # Update the packet_n_words_per_chunk
                packet_n_words_per_chunk.next = n_words_per_chunk

                state.next = t_state.IDLE

        return_objects.append(check)

        return return_objects

    def base_test(
        self, reset_toggle_p=0, reset_pulse_p=0,
        n_words_per_chunk_update_p=0.05, vary_axis_source_tvalid=False,
        axis_sink_tready_p=1):

        dut_args, dut_arg_types = dut_args_setup()

        if not self.testing_using_vivado:
            cycles = 100000
            n_tests = 40
        else:
            cycles = 50000
            n_tests = 16

        @block
        def stimulate_check(**dut_args):

            return_objects = []

            return_objects.append(self.monitor_tests(n_tests, **dut_args))
            return_objects.append(
                self.stim_ctrl(
                    reset_toggle_p, reset_pulse_p, n_words_per_chunk_update_p,
                    **dut_args))
            return_objects.append(
                self.stim_check_data_packets(
                    vary_axis_source_tvalid, axis_sink_tready_p, **dut_args))
            return_objects.append(self.check_axis_signals(**dut_args))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axis_chunker, axis_chunker, dut_args, dut_arg_types,
            custom_sources=[(stimulate_check, (), dut_args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_axis_chunker(self):
        ''' The `axis_chunker` should forward all data received on the
        `axis_source` to the `axis_sink`.

        The `axis_chunker` should use the same `n_words_per_chunk` for the
        entire `axis_source` packet. This means that a packet will be
        separated into chunks of the same size, even if `n_words_per_chunk`
        changes in the middle of the packet.

        To help specify the rest of the functionality we will call the value
        of `n_words_per_chunk` which is used for an entire packet
        `packet_n_words_per_chunk`.

        The `packet_n_words_per_chunk` should be updated to
        `n_words_per_chunk` whenever any of the following are true:

            - When there isn't a valid transaction on `axis_source`
            (`axis_source.TVALID` or `axis_source.TREADY` are low).
            - When a packet on the source completes (`axis_source.TVALID`,
            `axis_source.TREADY` and `axis_source.TLAST` are high).
            - `reset` is high.

        The `axis_chunker` should use the `axis_sink.TLAST` to separate the
        data into chunks of `packet_n_words_per_chunk`. Each of these chunks
        should be an AXI stream packet.

        If the number of words in a packet on `axis_source` is less than
        `packet_n_words_per_chunk` then the packet should be forwarded as is.

        If the number of words in a packet is not a multiple of
        `packet_n_words_per_chunk` then the last packet on `axis_sink` should
        include all remaining data. ie the last packet on `axis_sink` won't
        be `packet_n_words_per_chunk` words.

        If `packet_n_words_per_chunk` is 0, then the `axis_chunker` should
        hold `axis_source.TREADY` low (thereby blocking the data stream).
        '''
        self.base_test()

    def test_rapid_n_words_per_chunk_update(self):
        ''' The `axis_chunker` should function correctly when
        `n_words_per_chunk` is updating frequently.
        '''
        self.base_test(n_words_per_chunk_update_p=0.5)

    def test_varying_tvalid_and_tready(self):
        ''' The `axis_chunker` should function correctly when the
        `axis_source.TVALID` and `axis_sink.TREADY` signals are varying.
        '''
        self.base_test(
            vary_axis_source_tvalid=True,
            axis_sink_tready_p=0.5)

    def test_reset(self):
        ''' While `reset` is high, the `axis_chunker` should  asynchronously
        hold `axis_source.TREADY` and `axis_sink.TVALID` low.
        '''
        self.base_test(
            reset_toggle_p=0.001,
            reset_pulse_p=0.001)

    def test_reset_varying_tvalid_and_tready(self):
        ''' The `axis_chunker` should correctly handle `reset` when the
        `axis_source.TVALID` and `axis_sink.TREADY` are varying.
        '''
        self.base_test(
            vary_axis_source_tvalid=True,
            axis_sink_tready_p=0.5,
            reset_toggle_p=0.0005,
            reset_pulse_p=0.001)

class TestAxisChunkerVivadoVhdl(
    KeaVivadoVHDLTestCase, TestAxisChunker):
    pass

class TestAxisChunkerVivadoVerilog(
    KeaVivadoVerilogTestCase, TestAxisChunker):
    pass
