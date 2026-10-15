import copy
import random

from collections import deque
from itertools import islice

from myhdl import Signal, block, always, intbv, enum, StopSimulation

from kea.hdl.axi import (
    AxiStreamInterface, AxiStreamMasterBFM, AxiStreamSlaveBFM)
from kea.hdl.axi.axi_stream_utils import check_axi_stream_interface_attributes
from kea.hdl.ethernet.definitions import (
    DEST_MAC_N_OCTETS, SRC_MAC_N_OCTETS, ETHERTYPE_N_OCTETS,
    ETHERTYPE_BITWIDTH)
from kea.testing.test_utils import (
    axi_stream_types_generator, generate_value_with_preferences)
from kea.utils.interface_checks import (
    check_bool_signal,
    get_dut_function_call_arguments,
    verify_dut_called_function)

from .definitions import ETHERNET_HEADER_N_BITS
from .interfaces import EthernetHeaderValuesInterface

def ethernet_header_values_interface_types_generator():
    ''' Generates the types for the `ethernet_header_values_interface`.
    '''

    types = {
        'load_values': 'custom',
        'ethertype': 'custom',
    }

    for n in range(DEST_MAC_N_OCTETS):
        types['dest_mac_octet_'+str(n)] = 'custom'

    for n in range(SRC_MAC_N_OCTETS):
        types['src_mac_octet_'+str(n)] = 'custom'

    return types

def dut_args_setup(axis_data_bytewidth):
    ''' Generate the arguments and argument types for the DUT.
    '''

    axis_source_args = {
        'bus_width': axis_data_bytewidth,
        'TID_width': None,
        'TDEST_width': None,
        'TUSER_width': None,
        'TVALID_init': False,
        'TREADY_init': False,
        'use_TLAST': True,
        'use_TSTRB': False,
        'use_TKEEP': False
    }

    axis_sink_args = copy.copy(axis_source_args)
    axis_sink_args['use_TKEEP'] = True

    dut_args = {
        'clock': Signal(False),
        'reset': Signal(False),
        'ethernet_header_values_interface': EthernetHeaderValuesInterface(),
        'axis_source': AxiStreamInterface(**axis_source_args),
        'axis_sink': AxiStreamInterface(**axis_sink_args),
    }

    ethernet_header_values_interface_types = (
        ethernet_header_values_interface_types_generator())

    axis_source_types = (
        axi_stream_types_generator(
            sink=False,
            TID_width=axis_source_args['TID_width'],
            TDEST_width=axis_source_args['TDEST_width'],
            TUSER_width=axis_source_args['TUSER_width'],
            use_TLAST=axis_source_args['use_TLAST'],
            use_TSTRB=axis_source_args['use_TSTRB'],
            use_TKEEP=axis_source_args['use_TKEEP']))

    axis_sink_types = (
        axi_stream_types_generator(
            sink=True,
            TID_width=axis_sink_args['TID_width'],
            TDEST_width=axis_sink_args['TDEST_width'],
            TUSER_width=axis_sink_args['TUSER_width'],
            use_TLAST=axis_sink_args['use_TLAST'],
            use_TSTRB=axis_sink_args['use_TSTRB'],
            use_TKEEP=axis_sink_args['use_TKEEP']))

    dut_arg_types = {
        'clock': 'clock',
        'reset': 'custom',
        'ethernet_header_values_interface': (
            ethernet_header_values_interface_types),
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

def generate_tkeep_trailing_bytes(axis_sink_bitwdith):
    ''' Generates the expected TKEEP for the last word of the packet.
    '''

    n_trailing_bits = ETHERNET_HEADER_N_BITS % axis_sink_bitwdith

    assert(n_trailing_bits % 8 == 0)
    n_trailing_bytes = n_trailing_bits//8

    tkeep_trailing_bytes = 2**n_trailing_bytes - 1

    return tkeep_trailing_bytes

def generate_expected_packet(
    dest_mac_octets, src_mac_octets, ethertype, data, bytes_per_word):
    ''' Generates the expected packet.

    `current_dest_mac_octets` should be a list containing the most recently
    loaded destination MAC octets.

    `current_src_mac_octets` should be a list containing the most recently
    loaded source MAC octets.

    `current_ethertype` should be an integer and should be the most recently
    loaded ethertype.

    `data` should be a list containing the data which will be used to
    stimulate the `axis_source`.

    `bytes_per_word` should be an integer and is the number of bytes in the
    AXI stream TDATA signals.
    '''

    # Convert all header values and data into bytes and combine into one
    # buffer
    buffer = (
        bytes(dest_mac_octets)
        + bytes(src_mac_octets)
        + ethertype.to_bytes(2, 'little')
        + b''.join(x.to_bytes(bytes_per_word, 'little') for x in data)
    )

    # Pad to next word boundary if needed
    remainder = len(buffer) % bytes_per_word
    if remainder:
        buffer += b'\x00' * (bytes_per_word - remainder)

    # Unpack the combined buffer into words of the correct size.
    expected_packet = deque([
        int.from_bytes(buffer[i:i + bytes_per_word], 'little')
        for i in range(0, len(buffer), bytes_per_word)
    ])

    return expected_packet

def extract_packet_fields(packet, bytes_per_word):
    ''' Extracts the header fields and data from a packet.

    `packet` should be a deque (or other iterable) of integer words, as
    produced by `generate_expected_packet`.

    `bytes_per_word` should be an integer and is the number of bytes in the
    AXI stream TDATA signals.

    Returns a tuple of:
        (dest_mac_octets, src_mac_octets, ethertype, data)

    The trailing zero padding added by `generate_expected_packet` is
    stripped, so `data` matches the original data words exactly.
    '''

    # Convert the words back into a single byte buffer
    buffer = b''.join(
        word.to_bytes(bytes_per_word, 'little') for word in packet)

    ethernet_header_n_octets = (
        DEST_MAC_N_OCTETS + SRC_MAC_N_OCTETS + ETHERTYPE_N_OCTETS)

    if len(buffer) < ethernet_header_n_octets:
        raise ValueError(
            'The packet is too short to contain a full ethernet header.')

    src_mac_upper = DEST_MAC_N_OCTETS + SRC_MAC_N_OCTETS

    # Slice out the header fields
    dest_mac_octets = list(buffer[:DEST_MAC_N_OCTETS])
    src_mac_octets = list(buffer[DEST_MAC_N_OCTETS:src_mac_upper])
    ethertype = int.from_bytes(
        buffer[src_mac_upper:ethernet_header_n_octets], 'little')

    # The padding added by the generator absorbs the misalignment caused
    # by the 14 byte header, so its length is the distance from 14 up to
    # the next word boundary.
    padding_len = bytes_per_word - (ethernet_header_n_octets % bytes_per_word)

    # Strip the header and the trailing padding
    if padding_len:
        payload = buffer[ethernet_header_n_octets:-padding_len]

    else:
        payload = buffer[ethernet_header_n_octets:]

    if len(payload) % bytes_per_word != 0:
        raise ValueError(
            'The payload length is not a whole number of words, so the '
            'packet was not generated with this word size.')

    data = [
        int.from_bytes(payload[i:i + bytes_per_word], 'little')
        for i in range(0, len(payload), bytes_per_word)
    ]

    return dest_mac_octets, src_mac_octets, ethertype, data

class BaseEthernetFramerInterfaceTests:
    ''' A base test class which defines the common interface tests for the
    ethernet framers
    '''

    # subclasses must override
    axis_data_bytewidth = None
    dut_func = None
    dut_name = None

    def setUp(self):
        if self.axis_data_bytewidth is None:
            raise NotImplementedError(
                f"{type(self).__name__} must define `axis_data_bytewidth`")

        if self.dut_func is None:
            raise NotImplementedError(
                f"{type(self).__name__} must define `dut_func`")

        if self.dut_name is None:
            raise NotImplementedError(
                f"{type(self).__name__} must define `dut_name`")

        self.dut_args, _dut_arg_types = (
            dut_args_setup(axis_data_bytewidth=self.axis_data_bytewidth))

    def test_bool_ports_checked(self):
        '''The `clock` and `reset` ports should be boolean signals.

        Anything else should raise an error.
        '''
        dut = self.dut_func
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

    def test_axis_attributes_checked(self):
        '''The `axis_source` `AxiStreamInterface` should not have a `TID`,
        `TDEST`, `TUSER`, `TSTRB` or `TKEEP`. It should have a `TLAST`. The
        `TVALID` and `TREADY` signals should initialise low.

        Anything else should raise an error.

        The `axis_sink` `AxiStreamInterface` should have the same `bus_width`
        as `axis_source`. It should not have a `TID`, `TDEST`, `TUSER` or
        `TSTRB`. It should have a `TKEEP` and `TLAST`. The `TVALID` and
        `TREADY` signals should initialise low.

        Anything else should raise an error.
        '''
        dut = self.dut_func
        axis_interface_expected_attributes = {
            'axis_source': {
                'TID_width': None,
                'TDEST_width': None,
                'TUSER_width': None,
                'TVALID_init': False,
                'TREADY_init': False,
                'use_TLAST': True,
                'use_TSTRB': False,
                'use_TKEEP': False,
            },
            'axis_sink': {
                'bus_width': self.dut_args['axis_source'].bus_width,
                'TID_width': None,
                'TDEST_width': None,
                'TUSER_width': None,
                'TVALID_init': False,
                'TREADY_init': False,
                'use_TLAST': True,
                'use_TSTRB': False,
                'use_TKEEP': True,
            },
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

    def test_invalid_ethernet_header_values_interface(self):
        ''' The ethernet framer block should raise an error if the
        `ethernet_header_values_interface` is not an instance of
        `EthernetHeaderValuesInterface`.
        '''

        self.dut_args['ethernet_header_values_interface'] = (
            random.randrange(0, 100))

        # Check that the system errors
        self.assertRaisesRegex(
            TypeError,
            (self.dut_name + ': ethernet_header_values_interface should be '
             'an instance of EthernetHeaderValuesInterface.'),
            self.dut_func,
            **self.dut_args,
        )

class BaseEthernetFramerTests:
    ''' The DUT should reject incompatible interfaces and arguments.
    '''

    dut_func = None

    def setUp(self):

        if self.dut_func is None:
            raise NotImplementedError(
                f"{type(self).__name__} must define `dut_func`")

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

    def generate_expected_packet_from_signals(
        self, current_dest_mac_octets, current_src_mac_octets,
        current_ethertype, data, bytes_per_word):
        ''' Generates the expected packet.

        `current_dest_mac_octets` should be a list of signals carrying
        the most recently loaded destination MAC octets.

        `current_src_mac_octets` should be a list of signals carrying
        the most recently loaded source MAC octets.

        `current_ethertype` should be a signal carrying the most
        recently loaded ethertype.

        `data` should be a list containing the data which will be use to
        stimulate the `axis_source`.

        `bytes_per_word` should be an integer and is the number of bytes
        in the AXI stream TDATA signals.
        '''

        # Extract the current header values from the signals
        dest_mac_octets = [
            copy.copy(int(dmo.val)) for dmo in current_dest_mac_octets]
        src_mac_octets = [
            copy.copy(int(smo.val)) for smo in current_src_mac_octets]
        ethertype = copy.copy(int(current_ethertype.val))

        expected_packet = (
            generate_expected_packet(
                dest_mac_octets, src_mac_octets, ethertype, data,
                bytes_per_word))

        return expected_packet

    @block
    def stim_ctrl(
        self, reset_toggle_p, reset_pulse_p, load_values_p, **dut_args):

        clock = dut_args['clock']
        reset = dut_args['reset']
        ethernet_header_values_interface = (
            dut_args['ethernet_header_values_interface'])

        return_objects = []

        hold_reset_high = Signal(False)

        octet_val_upper_bound = 2**8
        ethertype_val_upper_bound = (
            2**len(ethernet_header_values_interface.ethertype))

        dest_mac_octets = [
            ethernet_header_values_interface.dest_mac_octet(n)
            for n in range(DEST_MAC_N_OCTETS)]
        src_mac_octets = [
            ethernet_header_values_interface.src_mac_octet(n)
            for n in range(SRC_MAC_N_OCTETS)]

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

            ##########################
            # Ethernet header values #
            ##########################

            for dest_mac_octet in dest_mac_octets:
                dest_mac_octet.next = random.randrange(octet_val_upper_bound)

            for src_mac_octet in src_mac_octets:
                src_mac_octet.next = random.randrange(octet_val_upper_bound)

            ethernet_header_values_interface.ethertype.next = (
                random.randrange(ethertype_val_upper_bound))

            ethernet_header_values_interface.load_values.next = False

            if random.random() < load_values_p:
                ethernet_header_values_interface.load_values.next = True

        return_objects.append(stim)

        return return_objects

    @block
    def stim_check_data_packets(
        self, vary_axis_source_tvalid, axis_sink_tready_probability,
        **dut_args):
        ''' This block performs packet based checks on the DUT. It will send
        packets on `axis_source` and check that the packets are output on
        `axis_sink` with the correct header.
        '''

        clock = dut_args['clock']
        reset = dut_args['reset']
        ethernet_header_values_interface = (
            dut_args['ethernet_header_values_interface'])
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
            axis_sink_slave_bfm.model(
                clock, axis_sink, axis_sink_tready_probability))

        data_upper_bound = 2**len(axis_source.TDATA)

        dest_mac_octets = [
            ethernet_header_values_interface.dest_mac_octet(n)
            for n in range(DEST_MAC_N_OCTETS)]
        current_dest_mac_octets = [
            Signal(intbv(0)[8:]) for n in range(DEST_MAC_N_OCTETS)]

        src_mac_octets = [
            ethernet_header_values_interface.src_mac_octet(n)
            for n in range(SRC_MAC_N_OCTETS)]
        current_src_mac_octets = [
            Signal(intbv(0)[8:]) for n in range(SRC_MAC_N_OCTETS)]

        current_ethertype = Signal(intbv(0)[ETHERTYPE_BITWIDTH:])

        # Calclate the number of octets per data word
        bytes_per_word = len(axis_sink.TDATA)//8

        pending_packets = deque([])
        expected_packets = {}

        t_state = enum(
            'STIM', 'AWAIT_SOURCE_START', 'AWAIT_SINK_COMPLETE', 'CHECK',
            'RESET')
        state = Signal(t_state.STIM)

        @always(clock.posedge)
        def stim_check():

            if ethernet_header_values_interface.load_values:
                # Keep a record of the header values

                for n in range(DEST_MAC_N_OCTETS):
                    current_dest_mac_octets[n].next = dest_mac_octets[n]

                for n in range(SRC_MAC_N_OCTETS):
                    current_src_mac_octets[n].next = src_mac_octets[n]

                current_ethertype.next = (
                    ethernet_header_values_interface.ethertype)

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
                        generate_value_with_preferences(1, 33, [1, 2], 0.2)
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

                    state.next = t_state.AWAIT_SOURCE_START

            elif state == t_state.AWAIT_SOURCE_START:
                if axis_source.TVALID:

                    # Extract the first packet
                    data = pending_packets.popleft()

                    if len(expected_packets) <= 0:
                        # Set up the expected packets dict
                        expected_packets[(0, 0)] = deque([])

                    # Generate the expected packet
                    expected_packets[(0, 0)].append(
                        self.generate_expected_packet_from_signals(
                            current_dest_mac_octets, current_src_mac_octets,
                            current_ethertype, data, bytes_per_word))

                    state.next = t_state.AWAIT_SINK_COMPLETE

            elif state == t_state.AWAIT_SINK_COMPLETE:

                if (axis_sink.TVALID and
                    axis_sink.TREADY and
                    axis_sink.TLAST):
                    # The packet has completed

                    if len(pending_packets) > 0:
                        # There are more packets pending

                        if axis_source.TVALID:
                            # The next packet is arriving
                            data = pending_packets.popleft()

                            # Generate the expected packet
                            expected_packets[(0, 0)].append(
                                self.generate_expected_packet_from_signals(
                                    current_dest_mac_octets,
                                    current_src_mac_octets, current_ethertype,
                                    data, bytes_per_word))

                        else:
                            # There is more data pending but it hasn't started
                            # arriving yet
                            state.next = t_state.AWAIT_SOURCE_START

                    else:
                        # There are no more packets pending
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

    def base_test(
        self, axis_data_bytewidth, vary_axis_source_tvalid=False,
        axis_sink_tready_probability=1, load_values_p=0.007,
        reset_toggle_p=0, reset_pulse_p=0):

        dut_args, dut_arg_types = dut_args_setup(axis_data_bytewidth)

        if not self.testing_using_vivado:
            cycles = 100000
            n_tests = 40
        else:
            cycles = 50000
            n_tests = 15

        @block
        def stimulate_check(**dut_args):

            return_objects = []

            return_objects.append(self.monitor_tests(n_tests, **dut_args))
            return_objects.append(
                self.stim_ctrl(
                    reset_toggle_p, reset_pulse_p, load_values_p, **dut_args))
            return_objects.append(
                self.stim_check_data_packets(
                    vary_axis_source_tvalid, axis_sink_tready_probability,
                    **dut_args))
            return_objects.append(self.check_axis_control_signals(**dut_args))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, self.dut_func, self.dut_func, dut_args,
            dut_arg_types, custom_sources=[(stimulate_check, (), dut_args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)
