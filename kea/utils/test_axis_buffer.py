import random
import copy
from collections import deque

from myhdl import (
    Signal, block, intbv, always, always_comb, enum, StopSimulation)

from kea.axi import (
    AxiStreamInterface, AxiStreamMasterBFM, AxiStreamSlaveBFM)
from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from .logic import or_gate
from ._axis_buffer import axis_buffer

class TestAxisBufferInterface(KeaTestCase):

    def setUp(self):

        bitwidth = 32
        self.bytewidth = bitwidth//8

        self.clock = Signal(False)
        self.reset = Signal(False)
        self.axis_source = AxiStreamInterface(self.bytewidth, use_TLAST=True)
        self.axis_sink = AxiStreamInterface(self.bytewidth, use_TLAST=True)

        self.args = {
            'clock': self.clock,
            'reset': self.reset,
            'axis_source': self.axis_source,
            'axis_sink': self.axis_sink,}

    def test_invalid_axis_source(self):
        ''' The `axis_buffer` should raise a ValueError if the `axis_source`
        interface is not an instance of `AxiStreamInterface`.
        '''

        self.args['axis_source'] = 'not a valid interface'

        self.assertRaisesRegex(
            ValueError,
            'axis_source should be an instance of AxiStreamInterface.',
            axis_buffer,
            **self.args)

    def test_invalid_axis_sink(self):
        ''' The `axis_buffer` should raise a ValueError if the `axis_sink`
        interface is not an instance of `AxiStreamInterface`.
        '''

        self.args['axis_sink'] = 'not a valid interface'

        self.assertRaisesRegex(
            ValueError,
            'axis_sink should be an instance of AxiStreamInterface.',
            axis_buffer,
            **self.args)

    def test_tid_rejection(self):
        ''' The `axis_buffer` should raise a ValueError if the AXI stream
        interfaces include TID.
        '''

        tid_width = random.randrange(1, 10)

        self.args['axis_source'] = (
            AxiStreamInterface(self.bytewidth, TID_width=tid_width))
        self.args['axis_sink'] = (
            AxiStreamInterface(self.bytewidth, TID_width=tid_width))

        self.assertRaisesRegex(
            ValueError,
            'The axis_buffer does not support TID.',
            axis_buffer,
            **self.args)

    def test_tdest_rejection(self):
        ''' The `axis_buffer` should raise a ValueError if the AXI stream
        interfaces include TDEST.
        '''

        tdest_width = random.randrange(1, 10)

        self.args['axis_source'] = (
            AxiStreamInterface(self.bytewidth, TDEST_width=tdest_width))
        self.args['axis_sink'] = (
            AxiStreamInterface(self.bytewidth, TDEST_width=tdest_width))

        self.assertRaisesRegex(
            ValueError,
            'The axis_buffer does not support TDEST.',
            axis_buffer,
            **self.args)

    def test_tuser_rejection(self):
        ''' The `axis_buffer` should raise a ValueError if the AXI stream
        interfaces include TUSER.
        '''

        tuser_width = random.randrange(1, 10)

        self.args['axis_source'] = (
            AxiStreamInterface(self.bytewidth, TUSER_width=tuser_width))
        self.args['axis_sink'] = (
            AxiStreamInterface(self.bytewidth, TUSER_width=tuser_width))

        self.assertRaisesRegex(
            ValueError,
            'The axis_buffer does not support TUSER.',
            axis_buffer,
            **self.args)

    def test_tstrb_rejection(self):
        ''' The `axis_buffer` should raise a ValueError if the AXI stream
        interfaces include TSTRB.
        '''

        self.args['axis_source'] = (
            AxiStreamInterface(self.bytewidth, use_TSTRB=True))
        self.args['axis_sink'] = (
            AxiStreamInterface(self.bytewidth, use_TSTRB=True))

        self.assertRaisesRegex(
            ValueError,
            'The axis_buffer does not support TSTRB.',
            axis_buffer,
            **self.args)

    def test_tkeep_rejection(self):
        ''' The `axis_buffer` should raise a ValueError if the AXI stream
        interfaces include TKEEP.
        '''

        self.args['axis_source'] = (
            AxiStreamInterface(self.bytewidth, use_TKEEP=True))
        self.args['axis_sink'] = (
            AxiStreamInterface(self.bytewidth, use_TKEEP=True))

        self.assertRaisesRegex(
            ValueError,
            'The axis_buffer does not support TKEEP.',
            axis_buffer,
            **self.args)

def add_runs_of_none(
    data, probability_of_run=0.25, min_length_of_run=0, max_length_of_run=16):
    ''' Given a list of data, this function will insert a run of ``None``
    values of random length at random intervals in the data list.
    '''
    manipulated_data = copy.copy(data)

    for n in reversed(range(len(manipulated_data))):
        # Run through every index in the data. If we don't reverse the order
        # of n here we increment up through the Nones we may have just
        # inserted into the list and may add more Nones in the middle.
        if random.random() > probability_of_run:
            # At random indexes create a run of nones of random length and
            # insert them into the data list
            none_run = (
                [None]*random.randrange(min_length_of_run, max_length_of_run))
            for each in none_run:
                manipulated_data.insert(n, each)

    return manipulated_data

def generate_data(max_value, max_n_samples, randomise_tvalid):
    ''' This function will generate stimulus data.

    If randomise_tvalid is True then this funciton will add runs of None to
    the data so that the AXIS master BFM varies the TVALID signals during the
    data stream.
    '''

    # Randomly set n_samples
    n_samples = random.randrange(1, max_n_samples)

    # Generate data
    expected_data = [random.randrange(max_value) for n in range(n_samples)]

    if randomise_tvalid:
        # Add Nones so that TVALID varies
        stim_data = add_runs_of_none(expected_data)

    else:
        stim_data = copy.copy(expected_data)

    return stim_data, expected_data

def axis_types_generator(sink=False, use_TLAST=True):
    ''' Generates the types for the AXIS interface. If sink is False then it
    is assumed to be a source interface.
    '''

    if sink:
        types = {
            'TDATA': 'output',
            'TVALID': 'output',
            'TREADY': 'custom',}

        if use_TLAST:
            types['TLAST'] = 'output'

    else:
        types = {
            'TDATA': 'custom',
            'TVALID': 'custom',
            'TREADY': 'output',}

        if use_TLAST:
            types['TLAST'] = 'custom'

    return types

class TestAxisBuffer(KeaTestCase):

    def setUp(self):

        bitwidth = 32
        self.bytewidth = bitwidth//8

        self.clock = Signal(False)
        self.reset = Signal(False)
        self.axis_source = AxiStreamInterface(self.bytewidth, use_TLAST=True)
        self.axis_sink = AxiStreamInterface(self.bytewidth, use_TLAST=True)

        self.test_count = 0
        self.tests_run = False

        self.args = {
            'clock': self.clock,
            'reset': self.reset,
            'axis_source': self.axis_source,
            'axis_sink': self.axis_sink,}

        self.axis_source_types = (
            axis_types_generator(sink=False, use_TLAST=True))

        self.axis_sink_types = (
            axis_types_generator(sink=True, use_TLAST=True))

        self.arg_types = {
            'clock': 'clock',
            'reset': 'custom',
            'axis_source': self.axis_source_types,
            'axis_sink': self.axis_sink_types,}

    @block
    def count_tests(self, clock, n_tests):

        @always(clock.posedge)
        def counter():

            if self.test_count >= n_tests:
                # Check that all the tests are run
                self.tests_run = True

                raise StopSimulation

        return counter

    @block
    def axis_expected_signal(
        self, clock, source_tvalid, source_tready, source_signal,
        expected_signal):
        ''' This block updates the expected signal on the basis of the
        source_tvalid and source_tready signals. This block should correctly
        update the TDATA signal and all the optional signals on an AXI stream
        interface.
        '''

        @always(clock.posedge)
        def bfm():

            if source_tvalid and source_tready:
                expected_signal.next = source_signal

        return bfm

    @block
    def signal_check(self, clock, signal, expected_signal):

        @always(clock.posedge)
        def check():

            assert(signal == expected_signal)

        return check

    @block
    def axis_buffer_check(
        self, clock, reset, axis_source, axis_sink, max_n_samples=128,
        randomise_axis_control_signals=False):
        ''' Checks the behaviour of the axis_buffer.
        '''

        # Check axis_source and axis_sink match
        assert(axis_source.bus_width == axis_sink.bus_width)
        assert(axis_source.TID_width == axis_sink.TID_width)
        assert(axis_source.TDEST_width == axis_sink.TDEST_width)
        assert(axis_source.TUSER_width == axis_sink.TUSER_width)
        assert(hasattr(axis_source, 'TLAST') == hasattr(axis_sink, 'TLAST'))
        assert(hasattr(axis_source, 'TSTRB') == hasattr(axis_sink, 'TSTRB'))
        assert(hasattr(axis_source, 'TKEEP') == hasattr(axis_sink, 'TKEEP'))

        return_objects = []

        if randomise_axis_control_signals:
            tready_probability = 0.5

        else:
            tready_probability = 1.0

        max_value = 2**(len(axis_source.TDATA))

        # Create the reset for the source BFM
        axis_source_reset = Signal(False)
        combined_axis_source_reset = Signal(False)
        return_objects.append(
            or_gate(reset, axis_source_reset, combined_axis_source_reset))

        # Create the source BFM
        axis_source_bfm = AxiStreamMasterBFM()
        return_objects.append(
            axis_source_bfm.model(
                clock, axis_source, reset=combined_axis_source_reset))

        # Create the sink BFM
        axis_sink_bfm = AxiStreamSlaveBFM()
        return_objects.append(
            axis_sink_bfm.model(
                clock, axis_sink, TREADY_probability=tready_probability))

        expected_source_tready = Signal(False)
        expected_sink_tvalid = Signal(False)
        expected_sink_tdata = Signal(intbv(0)[len(axis_sink.TDATA):])

        return_objects.append(
            self.axis_expected_signal(
                clock, axis_source.TVALID, axis_source.TREADY,
                axis_source.TDATA, expected_sink_tdata))

        if hasattr(axis_source, 'TLAST'):
            expected_sink_tlast = Signal(False)
            return_objects.append(
                self.axis_expected_signal(
                    clock, axis_source.TVALID, axis_source.TREADY,
                    axis_source.TLAST, expected_sink_tlast))

            # Check the axis sink TLAST is correct
            return_objects.append(
                self.signal_check(
                    clock, axis_sink.TLAST, expected_sink_tlast))

        expected_data = deque([])
        received_data = deque([])

        t_check_state = enum('IDLE', 'STIM', 'AWAIT_DATA', 'CHECK')
        check_state = Signal(t_check_state.IDLE)

        @always_comb
        def source_ready():

            expected_source_tready.next = (
                not reset and (axis_sink.TREADY or not axis_sink.TVALID))

        return_objects.append(source_ready)

        @always(clock.posedge)
        def stim_check():

            #################
            # Signal checks #
            #################

            assert(axis_source.TREADY == expected_source_tready)
            assert(axis_sink.TVALID == expected_sink_tvalid)
            assert(axis_sink.TDATA == expected_sink_tdata)

            if expected_sink_tvalid and axis_sink.TREADY:
                expected_sink_tvalid.next = axis_source.TVALID

            if not expected_sink_tvalid:
                expected_sink_tvalid.next = axis_source.TVALID

            ##############
            # Sequencing #
            ##############

            if check_state == t_check_state.IDLE:
                axis_source_reset.next = False

                if random.random() < 0.05:
                    check_state.next = t_check_state.STIM

            elif check_state == t_check_state.STIM:
                # Reset the receiving bfm
                axis_sink_bfm.reset()

                # Generate the stim data
                stim_data, expected_sink_data = (
                    generate_data(
                        max_value, max_n_samples,
                        randomise_axis_control_signals))

                expected_data.clear()
                expected_data.extend(expected_sink_data)

                axis_source_bfm.add_data([stim_data])

                check_state.next = t_check_state.AWAIT_DATA

            elif check_state == t_check_state.AWAIT_DATA:
                if hasattr(axis_source, 'TLAST'):
                    # The AXIS interfaces have TLAST so we can use completed
                    # packets
                    if len(axis_sink_bfm.completed_packets) > 0:
                        # All the packet has arrived
                        received_data.clear()
                        received_data.extend(
                            axis_sink_bfm.completed_packets[(0, 0)][0])

                        check_state.next = t_check_state.CHECK

                else:
                    # The AXIS interfaces don't have TLAST so we can't use the
                    # completed packets.
                    if len(axis_sink_bfm.current_packets) > 0:
                        if (len(axis_sink_bfm.current_packets[(0, 0)]) ==
                            len(expected_data)):
                            # All the expected data has arrived
                            received_data.clear()
                            received_data.extend(
                                axis_sink_bfm.current_packets[(0, 0)])

                            check_state.next = t_check_state.CHECK

            elif check_state == t_check_state.CHECK:

                # Check that the received data matches the expected data.
                self.assertTrue(received_data == expected_data)

                # Reset the receiving and source bfms
                axis_sink_bfm.reset()
                axis_source_reset.next = True

                self.test_count += 1

                check_state.next = t_check_state.IDLE

            if reset:
                expected_sink_tvalid.next = False
                axis_source_reset.next = True

                check_state.next = t_check_state.IDLE

        return_objects.append(stim_check)

        return return_objects

    def test_axis_buffer(self):
        ''' The `axis_buffer` should correctly buffer the `axis_source`
        interface whilst adhering to the AXI stream spec.
        '''

        if not self.testing_using_vivado:
            cycles = 20000
            max_n_samples = 512
            n_tests = 20
        else:
            cycles = 2000
            max_n_samples = 25
            n_tests = 10

        @block
        def test(clock, reset, axis_source, axis_sink):

            return_objects = []

            return_objects.append(
                self.axis_buffer_check(
                    clock, reset, axis_source, axis_sink,
                    max_n_samples=max_n_samples,
                    randomise_axis_control_signals=False))

            return_objects.append(self.count_tests(clock, n_tests))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axis_buffer, axis_buffer, self.args, self.arg_types,
            custom_sources=[(test, (), self.args)])

        self.assertTrue(self.tests_run)
        self.assertTrue(dut_outputs == ref_outputs)

    def test_randomised_axis_signals(self):
        ''' The `axis_buffer` should correctly buffer and forward the signals
        from the `axis_source` to the `axis_sink` when the axis control
        signals (`TVALID` and `TREADY`) vary.
        '''

        if not self.testing_using_vivado:
            cycles = 30000
            max_n_samples = 256
            n_tests = 20
        else:
            cycles = 4000
            max_n_samples = 25
            n_tests = 10

        @block
        def test(clock, reset, axis_source, axis_sink):

            return_objects = []

            return_objects.append(
                self.axis_buffer_check(
                    clock, reset, axis_source, axis_sink,
                    max_n_samples=max_n_samples,
                    randomise_axis_control_signals=True))

            return_objects.append(self.count_tests(clock, n_tests))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axis_buffer, axis_buffer, self.args, self.arg_types,
            custom_sources=[(test, (), self.args)])

        self.assertTrue(self.tests_run)
        self.assertTrue(dut_outputs == ref_outputs)

    def test_no_tlast(self):
        ''' The `axis_buffer` should function correctly even when the AXI
        stream interfaces don't include a `TLAST` signal.
        '''

        if not self.testing_using_vivado:
            cycles = 30000
            max_n_samples = 256
            n_tests = 20
        else:
            cycles = 4000
            max_n_samples = 25
            n_tests = 10

        self.args['axis_source'] = (
            AxiStreamInterface(self.bytewidth, use_TLAST=False))
        self.args['axis_sink'] = (
            AxiStreamInterface(self.bytewidth, use_TLAST=False))

        self.arg_types['axis_source'] = (
            axis_types_generator(sink=False, use_TLAST=False))
        self.arg_types['axis_sink'] = (
            axis_types_generator(sink=True, use_TLAST=False))

        @block
        def test(clock, reset, axis_source, axis_sink):

            return_objects = []

            return_objects.append(
                self.axis_buffer_check(
                    clock, reset, axis_source, axis_sink,
                    max_n_samples=max_n_samples,
                    randomise_axis_control_signals=True))

            return_objects.append(self.count_tests(clock, n_tests))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axis_buffer, axis_buffer, self.args, self.arg_types,
            custom_sources=[(test, (), self.args)])

        self.assertTrue(self.tests_run)
        self.assertTrue(dut_outputs == ref_outputs)

    def test_reset(self):
        ''' On receipt of a reset the `axis_buffer` should set
        `axis_source.TREADY` and `axis_sink.TVALID` low.

        The `axis_source.TREADY` signal should remain low until reset goes
        low.

        The `axis_sink.TVALID` signal should remain low until another word is
        written to the buffer.
        '''

        if not self.testing_using_vivado:
            cycles = 20000
            max_n_samples = 256
            n_tests = 10
        else:
            cycles = 2000
            max_n_samples = 25
            n_tests = 5

        @block
        def test(clock, reset, axis_source, axis_sink):

            return_objects = []

            return_objects.append(
                self.axis_buffer_check(
                    clock, reset, axis_source, axis_sink,
                    max_n_samples=max_n_samples,
                    randomise_axis_control_signals=True))

            return_objects.append(self.count_tests(clock, n_tests))

            t_stim_state = enum(
                'UNINTERRUPTED', 'AWAIT_DATA', 'RESET', 'HOLD')
            stim_state = Signal(t_stim_state.UNINTERRUPTED)

            @always(clock.posedge)
            def reset_stim():

                if stim_state == t_stim_state.UNINTERRUPTED:
                    # Allow an uninterrupted packet
                    if (axis_sink.TVALID and
                        axis_sink.TREADY and
                        axis_sink.TLAST):
                        # One full packet has gone through the buffer
                        stim_state.next = t_stim_state.AWAIT_DATA

                elif stim_state == t_stim_state.AWAIT_DATA:
                    # Await the next packet
                    if axis_sink.TVALID:
                        # The next packet has started
                        stim_state.next = t_stim_state.RESET

                elif stim_state == t_stim_state.RESET:
                    if random.random() < 0.1:
                        # Randomly send a reset
                        reset.next = True
                        stim_state.next = t_stim_state.HOLD

                elif stim_state == t_stim_state.HOLD:
                    if random.random() < 0.2:
                        # Keep reset high for a random period
                        reset.next = False
                        stim_state.next = t_stim_state.UNINTERRUPTED

            return_objects.append(reset_stim)

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axis_buffer, axis_buffer, self.args, self.arg_types,
            custom_sources=[(test, (), self.args)])

        self.assertTrue(self.tests_run)
        self.assertTrue(dut_outputs == ref_outputs)

class TestAxisBufferVivadoVhdl(
    KeaVivadoVHDLTestCase, TestAxisBuffer):
    pass

class TestAxisBufferVivadoVerilog(
    KeaVivadoVerilogTestCase, TestAxisBuffer):
    pass
