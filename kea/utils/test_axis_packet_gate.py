from myhdl import *
import random
from collections import deque

from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)
from kea.axi import (
    AxiStreamInterface, AxiStreamMasterBFM, AxiStreamSlaveBFM)

from .axis_packet_gate import axis_packet_gate

'''There should be a block that when a trigger signal is asserted, will
read data in from an input AXI stream interface and present it to an
output AXI stream interface. It should read data in until the `TLAST`
signal is encountered, and then it will block again until a new trigger
is asserted.
'''

class TestAxisPacketGateInterface(KeaTestCase):

    def setUp(self):

        self.clock = Signal(False)
        self.reset = Signal(False)
        self.axis_in = AxiStreamInterface(4, use_TLAST=True)
        self.axis_out = AxiStreamInterface(4, use_TLAST=True)
        self.go = Signal(False)

        self.default_args = {
            'clock': self.clock,
            'reset': self.reset,
            'axis_in': self.axis_in,
            'axis_out': self.axis_out,
            'go': self.go}

    def test_axis_in_interface(self):
        '''The axis_in port should be an instance of
        ``kea.axi.AxiStreamInterface``.

        Anything else should raise a ValueError.
        '''

        args = self.default_args.copy()
        args['axis_in'] = 'not a valid interface'

        self.assertRaisesRegex(
            ValueError, 'Invalid axis_in port',
            axis_packet_gate, **args)

    def test_axis_in_has_TLAST(self):
        '''The axis_in port should have the TLAST signal.

        If it does not, a ValueError should be raised.
        '''

        args = self.default_args.copy()
        args['axis_in'] = AxiStreamInterface(4, use_TLAST=False)

        self.assertRaisesRegex(
            ValueError, 'Missing axis_in TLAST signal',
            axis_packet_gate, **args)


    def test_axis_out_interface(self):
        '''The axis_out port should be an instance of
        ``kea.axi.AxiStreamInterface``.

        Anything else should raise a ValueError.
        '''

        args = self.default_args.copy()
        args['axis_out'] = 'not a valid interface'

        self.assertRaisesRegex(
            ValueError, 'Invalid axis_out port',
            axis_packet_gate, **args)

    def test_axis_out_has_TLAST(self):
        '''The axis_out port should have the TLAST signal.

        If it does not, a ValueError should be raised.
        '''

        args = self.default_args.copy()
        args['axis_out'] = AxiStreamInterface(4, use_TLAST=False)

        self.assertRaisesRegex(
            ValueError, 'Missing axis_out TLAST signal',
            axis_packet_gate, **args)

class TestAxisPacketGateSimulation(KeaTestCase):

    def setUp(self):

        self.clock = Signal(False)
        self.reset = Signal(False)
        self.axis_in = AxiStreamInterface(4, use_TLAST=True)
        self.axis_out = AxiStreamInterface(4, use_TLAST=True)
        self.go = Signal(False)

        self.default_args = {
            'clock': self.clock,
            'reset': self.reset,
            'axis_in': self.axis_in,
            'axis_out': self.axis_out,
            'go': self.go}

        axis_in_signal_types = {
            'TDATA': 'custom',
            'TVALID': 'custom',
            'TREADY': 'output',
            'TLAST': 'custom'}

        axis_out_signal_types = {
            'TDATA': 'output',
            'TVALID': 'output',
            'TREADY': 'custom',
            'TLAST': 'output'}

        self.default_arg_types = {
            'clock': 'clock',
            'reset': 'custom',
            'axis_in': axis_in_signal_types,
            'axis_out': axis_out_signal_types,
            'go': 'custom'}

    def test_packets(self):
        '''When a go is triggered, the gate is transparent to transactions
        until the TLAST signal is received on the ``axis_in`` interface
        '''
        # We should never reach this number of cycles as we can raise
        # StopSimulation once we've completed the tests
        max_cycles = 20000

        axis_write_bfm = AxiStreamMasterBFM()
        axis_read_bfm = AxiStreamSlaveBFM()

        max_packet_len = 1000
        min_packet_len = 500
        write_probability = 0.5
        read_probability = 0.5

        go_probability = 0.05
        go_clear_probability = 0.1

        max_input_val = self.axis_in.TDATA.max

        # Randomly determine the number of packets to write
        n_packets = random.randrange(5, 10)
        write_data = []

        for x in range(n_packets):
            packet = (
                [random.randrange(0, max_input_val)  if
                 random.random() < write_probability else None
                 for x in range(
                     random.randrange(min_packet_len, max_packet_len))])

            if(all([val is None for val in packet])):
                # Make sure the packet is not _all_ None
                packet.append(random.randrange(0, max_input_val))

            write_data.append(packet)

        # We create a stripped version of the write data without any
        # of the Nones. This is the expected read data.
        stripped_write_data = deque([
            deque([each for each in packet if each is not None])
            for packet in write_data])

        # TID and TDEST are not used therefore the stream value will be
        # interpreted and zeroes by the AxiSlaceBFM
        stream = (0, 0)

        # check data is stripped data reversed, so we can pop packets off it.
        stripped_write_data.reverse()
        check_data = stripped_write_data

        expected_output_data = {stream: deque([])}

        axis_write_bfm.add_data(write_data)

        test_checks = {'test_run': False}

        @block
        def stimulate_and_check(clock, reset, axis_in, axis_out, go):

            write_bfm_model = axis_write_bfm.model(clock, axis_in)

            read_bfm_model = axis_read_bfm.model(
                clock, axis_out, TREADY_probability=read_probability)

            t_go_state = enum('IDLE', 'TRIGGERED')
            go_state = Signal(t_go_state.IDLE)

            t_test_state = enum('GATE_OPEN', 'GATE_CLOSED', 'CHECK_PACKET')
            test_state = Signal(t_test_state.GATE_CLOSED)

            @always(clock.posedge)
            def go_driver():

                if go_state == t_go_state.IDLE:

                    if test_state == t_test_state.GATE_CLOSED:

                        if random.random() < go_probability:
                            go.next = True
                            go_state.next = t_go_state.TRIGGERED
                        else:
                            pass

                    else:
                        pass

                elif go_state == t_go_state.TRIGGERED:

                    if random.random() < go_clear_probability:
                        go.next = False
                        go_state.next = t_go_state.IDLE
                    else:
                        pass

                else:
                    raise RuntimeError('In an unknown state')

            @always(clock.posedge)
            def packet_checker():

                if test_state == t_test_state.GATE_CLOSED:
                    if go:
                        test_state.next = t_test_state.GATE_OPEN
                    else:
                        pass
                elif test_state == t_test_state.GATE_OPEN:
                    if axis_in.TVALID and axis_in.TREADY and axis_in.TLAST:
                        test_state.next = t_test_state.CHECK_PACKET

                    else:
                        pass

                elif test_state == t_test_state.CHECK_PACKET:

                    expected_output_data[stream].append(check_data.pop())

                    self.assertTrue(expected_output_data ==
                                    axis_read_bfm.completed_packets)

                    if len(check_data) == 0:
                        test_checks['test_run'] = True
                        raise StopSimulation

                    test_state.next = t_test_state.GATE_CLOSED


            @always(clock.posedge)
            def signal_checker():
                if test_state == t_test_state.GATE_CLOSED:
                    assert not axis_out.TVALID
                    assert not axis_in.TREADY

                elif test_state == t_test_state.GATE_OPEN:
                    assert axis_out.TVALID == axis_in.TVALID
                    assert axis_in.TREADY == axis_out.TREADY
                    assert axis_out.TDATA == axis_in.TDATA
                    assert axis_out.TLAST == axis_in.TLAST

            return (write_bfm_model, read_bfm_model, go_driver,
                    packet_checker, signal_checker)

        dut_outputs, ref_outputs = self.cosimulate(
            max_cycles, axis_packet_gate, axis_packet_gate,
            self.default_args, self.default_arg_types,
            custom_sources=[
                (stimulate_and_check, (), self.default_args)])

        assert(test_checks['test_run'])

        self.assertTrue(dut_outputs == ref_outputs)

    def test_constant_go(self):
        '''If go is held high, then the gate should stay open, without
        ever closing between packets.
        '''
        # We should never reach this number of cycles as we can raise
        # StopSimulation once we've completed the tests
        max_cycles = 20000

        axis_write_bfm = AxiStreamMasterBFM()
        axis_read_bfm = AxiStreamSlaveBFM()

        # Make go always true
        self.default_args['go'] = Signal(True)

        max_packet_len = 1000
        min_packet_len = 500

        max_input_val = self.axis_in.TDATA.max

        # Randomly determine the number of packets to write
        n_packets = random.randrange(5, 10)

        # TID and TDEST are not used therefore the stream value will be
        # interpreted and zeroes by the AxiSlaceBFM
        stream = (0, 0)
        write_data = {stream: deque([])}

        for x in range(n_packets):
            packet = deque(
                [random.randrange(0, max_input_val)  for x in range(
                    random.randrange(min_packet_len, max_packet_len))])

            if(all([val is None for val in packet])):
                # Make sure the packet is not _all_ None
                packet.append(random.randrange(0, max_input_val))

            write_data[stream].append(packet)

        axis_write_bfm.add_data(write_data[stream])

        test_checks = {'test_run': False}

        @block
        def stimulate_and_check(clock, reset, axis_in, axis_out, go):

            write_bfm_model = axis_write_bfm.model(clock, axis_in)

            read_bfm_model = axis_read_bfm.model(clock, axis_out)

            t_test_state = enum('INIT', 'RUNNING', 'CHECK_PACKET')
            test_state = Signal(t_test_state.INIT)

            @always(clock.posedge)
            def go_driver():
                go.next = True

            @always(clock.posedge)
            def packet_checker():

                if test_state == t_test_state.INIT:
                    test_state.next = t_test_state.RUNNING

                elif test_state == t_test_state.RUNNING:
                    assert axis_in.TREADY

                    if not axis_in.TVALID:
                        test_state.next = t_test_state.CHECK_PACKET

                elif test_state == t_test_state.CHECK_PACKET:
                    self.assertTrue(write_data ==
                                    axis_read_bfm.completed_packets)

                    test_checks['test_run'] = True
                    raise StopSimulation

            return (write_bfm_model, read_bfm_model, go_driver,
                    packet_checker)

        dut_outputs, ref_outputs = self.cosimulate(
            max_cycles, axis_packet_gate, axis_packet_gate,
            self.default_args, self.default_arg_types,
            custom_sources=[
                (stimulate_and_check, (), self.default_args)])

        assert(test_checks['test_run'])

        self.assertTrue(dut_outputs == ref_outputs)

    def test_reset(self):
        '''On a synchronous reset, the gate should close and return to its
        default state. No TLAST should be propagated.
        '''

        # We should never reach this number of cycles as we can raise
        # StopSimulation once we've completed the tests
        max_cycles = 20000

        axis_write_bfm = AxiStreamMasterBFM()
        axis_read_bfm = AxiStreamSlaveBFM()

        max_packet_len = 100
        min_packet_len = 50
        write_probability = 0.5
        read_probability = 0.5

        go_probability = 0.05
        go_clear_probability = 0.1

        reset_probability = 0.02
        reset_clear_probability = 0.05

        max_input_val = self.axis_in.TDATA.max

        # Randomly determine the number of packets to write
        n_packets = random.randrange(5, 10)

        # TID and TDEST are not used therefore the stream value will be
        # interpreted and zeroes by the AxiSlaceBFM
        stream = (0, 0)
        write_data = {stream: deque([])}

        for x in range(n_packets):
            packet = deque(
                [random.randrange(0, max_input_val)  if
                 random.random() < write_probability else None
                 for x in range(
                     random.randrange(min_packet_len, max_packet_len))])

            if(all([val is None for val in packet])):
                # Make sure the packet is not _all_ None
                packet.append(random.randrange(0, max_input_val))

            write_data[stream].append(packet)

        # We create a stripped version of the write data without any
        # of the Nones. This is the expected read data.
        stripped_write_data = {}
        stripped_write_data[stream] = deque([
            deque([each for each in packet if each is not None])
            for packet in write_data[stream]])

        axis_write_bfm.add_data(write_data[stream])

        test_checks = {'test_run': False}

        @block
        def stimulate_and_check(clock, reset, axis_in, axis_out, go):

            write_bfm_model = axis_write_bfm.model(clock, axis_in)

            read_bfm_model = axis_read_bfm.model(
                clock, axis_out, TREADY_probability=read_probability)

            t_go_state = enum('IDLE', 'TRIGGERED')
            go_state = Signal(t_go_state.IDLE)

            outputs_reset = Signal(False)

            @always(clock.posedge)
            def go_driver():
                if not go:
                    if random.random() < go_probability:
                        go.next = True

                else:
                    if random.random() < go_clear_probability:
                        go.next = False

            @always(clock.posedge)
            def reset_driver():
                if not reset:
                    if random.random() < reset_probability:
                        reset.next = True

                else:
                    if random.random() < reset_clear_probability:
                        reset.next = False

            @always(clock.posedge)
            def stopper():

                if stream in axis_read_bfm.completed_packets.keys():

                    if (len(axis_read_bfm.completed_packets[stream]) ==
                        len(stripped_write_data[stream])):

                        test_checks['test_run'] = True
                        raise StopSimulation

            @always(clock.posedge)
            def signal_checker():
                if reset:
                    outputs_reset.next = True
                else:
                    outputs_reset.next = False

                if outputs_reset:
                    assert not axis_out.TVALID
                    assert not axis_out.TLAST
                    assert not axis_in.TREADY

            return (write_bfm_model, read_bfm_model, go_driver, reset_driver,
                    stopper, signal_checker)

        dut_outputs, ref_outputs = self.cosimulate(
            max_cycles, axis_packet_gate, axis_packet_gate,
            self.default_args, self.default_arg_types,
            custom_sources=[
                (stimulate_and_check, (), self.default_args)])

        assert(test_checks['test_run'])

        self.assertTrue(
            axis_read_bfm.completed_packets == stripped_write_data)

        self.assertTrue(dut_outputs == ref_outputs)

class TestAxisPacketGateVivadoVhdlSimulation(
    KeaVivadoVHDLTestCase, TestAxisPacketGateSimulation):
    pass

class TestAxisPacketGateVivadoVerilogSimulation(
    KeaVivadoVerilogTestCase, TestAxisPacketGateSimulation):
    pass
