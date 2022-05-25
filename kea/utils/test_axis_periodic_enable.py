from myhdl import *
import myhdl
from collections import deque

import random
import warnings

from jackdaw.test_utils.base_test import (
    JackdawTestCase, JackdawVivadoVHDLTestCase, JackdawVivadoVerilogTestCase)
from kea.axi import (
    AxiStreamInterface, AxiStreamMasterBFM, AxiStreamSlaveBFM)

from .axis_periodic_enable import axis_periodic_enable

'''There should be a block that enables periodic transactions between a
pair of axi stream interfaces.

Outside of the periodic cycles, transactions should be disabled.
'''

class TestAxisPeriodicEnableInterface(JackdawTestCase):

    def setUp(self):

        self.clock = Signal(False)
        self.reset = Signal(False)
        self.axis_in = AxiStreamInterface(4, use_TLAST=True)
        self.axis_out = AxiStreamInterface(4, use_TLAST=True)
        self.period = Signal(intbv(1, min=1, max=10))

        self.default_args = {
            'clock': self.clock,
            'reset': self.reset,
            'axis_in': self.axis_in,
            'axis_out': self.axis_out,
            'period': self.period}

    def test_clock_port_checked(self):
        '''The clock port should be a boolean signal.

        Anything else should raise a ValueError.
        '''
        self.do_port_check_bool_test(axis_periodic_enable, 'clock')

    def test_reset_port_checked(self):
        '''The reset port should be a boolean signal.

        Anything else should raise a ValueError.
        '''
        self.do_port_check_bool_test(axis_periodic_enable, 'reset')

    def test_axis_in_interface(self):
        '''The axis_in port should be an instance of
        ``kea.axi.AxiStreamInterface``.

        Anything else should raise a ValueError.
        '''

        args = self.default_args.copy()
        args['axis_in'] = 'not a valid interface'

        self.assertRaisesRegex(
            ValueError, 'Invalid axis_in port',
            axis_periodic_enable, **args)


    def test_axis_out_interface(self):
        '''The axis_out port should be an instance of
        ``kea.axi.AxiStreamInterface``.

        Anything else should raise a ValueError.
        '''

        args = self.default_args.copy()
        args['axis_out'] = 'not a valid interface'

        self.assertRaisesRegex(
            ValueError, 'Invalid axis_out port',
            axis_periodic_enable, **args)

    def test_period_port(self):
        '''The ``period`` port should be an unsigned intbv or a positive
        constant integer (or something that ``int`` will meaningfully
        convert to an integer).

        Anything else should raise a ValueError.
        '''

        # In the case of a signal (set in default args), it should run the
        # port test
        self.do_port_check_intbv_test(
            axis_periodic_enable, 'period',
            val_range=(1, 2**len(self.period)-1))

        # Non-signals
        # Works
        self.default_args['period'] = 10
        axis_periodic_enable(**self.default_args)

        self.default_args['period'] = '10'
        axis_periodic_enable(**self.default_args)

        # Fails
        self.default_args['period'] = -1
        self.assertRaisesRegex(
            ValueError, 'Period not a signal or an integer',
            axis_periodic_enable, **self.default_args)

        self.default_args['period'] = 0
        self.assertRaisesRegex(
            ValueError, 'Period not a signal or an integer',
            axis_periodic_enable, **self.default_args)

        self.default_args['period'] = 'something else'
        self.assertRaisesRegex(
            ValueError, 'Period not a signal or an integer',
            axis_periodic_enable, **self.default_args)


class TestAxisPeriodicEnableSimulation(JackdawTestCase):

    def setUp(self):

        self.clock = Signal(False)
        self.reset = Signal(False)
        self.axis_in = AxiStreamInterface(4, use_TLAST=True)
        self.axis_out = AxiStreamInterface(4, use_TLAST=True)

        self.stream = (0, 0)

        # Give self.period an initial value of something typical
        self.period = Signal(intbv(11, min=1, max=20))

        self.default_args = {
            'clock': self.clock,
            'reset': self.reset,
            'axis_in': self.axis_in,
            'axis_out': self.axis_out,
            'period': self.period}

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
            'period': 'custom'}

        self.test_data = {'enable_count': 0}

    @block
    def periodic_model(self, clock, reset, period, enabled):

        if isinstance(period, myhdl._Signal._Signal):
            max_period = period.max
        else:
            max_period = period

        counter = Signal(intbv(0, min=0, max=max_period))

        @always_comb
        def set_enabled():

            # Remember, the output is _not_ enabled during the reset.
            if not reset and counter == 0:
                enabled.next = True

            else:
                enabled.next = False

        @always(clock.posedge)
        def set_counter():
            if reset:
                counter.next = 0

            else:
                if counter >= period - 1:
                    counter.next = 0
                else:
                    counter.next = counter + 1

        return set_enabled, set_counter

    @block
    def checker(
        self, clock, reset, axis_in, axis_out, period, write_bfm, read_bfm,
        n_expected_output_packets, TREADY_probability=1.0):

        enabled = Signal(False)

        write_bfm_model = write_bfm.model(clock, axis_in)
        read_bfm_model = read_bfm.model(
            clock, axis_out, TREADY_probability=TREADY_probability)

        periodic_enabler = self.periodic_model(clock, reset, period, enabled)

        last_valid_axis_out_TDATA = (
            Signal(intbv(0, min=axis_out.TDATA.min, max=axis_out.TDATA.max)))

        self.test_data['enable_count'] = 0

        if hasattr(axis_in, 'TLAST') and hasattr(axis_out, 'TLAST'):
            @always(clock.posedge)
            def TLAST_checker():
                assert axis_out.TLAST == axis_in.TLAST

        elif (not hasattr(axis_in, 'TLAST') and
              hasattr(axis_out, 'TLAST')):
            @always(clock.posedge)
            def TLAST_checker():
                assert axis_out.TLAST == False

        else:
            @always(clock.posedge)
            def TLAST_checker():
                pass

        @always(clock.posedge)
        def signal_checker():

            if enabled:
                assert axis_in.TREADY == axis_out.TREADY
                assert axis_out.TVALID == axis_in.TVALID
                assert axis_out.TDATA == axis_in.TDATA

                if axis_out.TREADY and axis_out.TVALID:
                    last_valid_axis_out_TDATA.next = axis_out.TDATA

                self.test_data['enable_count'] += 1
            else:
                assert axis_in.TREADY == False
                assert axis_out.TVALID == False

                assert axis_out.TDATA == last_valid_axis_out_TDATA

        @always(clock.posedge)
        def stopper():
            if self.stream in read_bfm.completed_packets.keys():
                if len(read_bfm.completed_packets[self.stream]) == (
                    n_expected_output_packets):
                    raise StopSimulation

        return (write_bfm_model, read_bfm_model, periodic_enabler,
                signal_checker, TLAST_checker, stopper)

    def test_constant_periodic_transactions(self):
        '''If data is always available on both the input and the output,
        data should propagate every ``period`` cycles when period is a
        constant.
        '''
        # We should never reach this number of cycles as we can raise
        # StopSimulation once we've completed the tests
        max_cycles = 20000

        self.period = random.randrange(2, 20)

        axis_write_bfm = AxiStreamMasterBFM()
        axis_read_bfm = AxiStreamSlaveBFM()

        max_packet_len = 100
        min_packet_len = 50

        max_input_val = self.axis_in.TDATA.max

        # Randomly determine the number of packets to write
        n_packets = random.randrange(5, 10)

        # TID and TDEST are not used therefore the stream value will be
        # interpreted and zeroes by the AxiSlaceBFM
        stream = self.stream
        write_data = {stream: deque([])}

        for x in range(n_packets):
            packet = deque(
                [random.randrange(0, max_input_val)  for x in range(
                    random.randrange(min_packet_len, max_packet_len))])

            write_data[stream].append(packet)

        n_samples = sum(len(packet) for packet in write_data[stream])

        axis_write_bfm.add_data(write_data[stream])

        self.default_args['period'] = self.period
        self.default_arg_types['period'] = 'non-signal'

        checker_args = self.default_args.copy()
        checker_args['read_bfm'] = axis_read_bfm
        checker_args['write_bfm'] = axis_write_bfm
        checker_args['n_expected_output_packets'] = len(write_data[stream])

        dut_outputs, ref_outputs = self.cosimulate(
            max_cycles, axis_periodic_enable, axis_periodic_enable,
            self.default_args, self.default_arg_types,
            custom_sources=[
                (self.checker, (), checker_args)])

        self.assertTrue(axis_read_bfm.completed_packets == write_data)
        self.assertTrue(dut_outputs == ref_outputs)

    def test_signal_set_periodic_transactions(self):
        '''If data is always available on both the input and the output,
        data should propagate every ``period`` cycles when period is a
        set by a signal.

        In this case, it should be possible to update the signal at any
        time and the output should respond accordingly.

        If the period is reduced from the previous value and more than the
        new period has elapsed already, then an output should be enabled on the
        next clock cycle and a new period should be begun (effectively, it
        should begin a new period on the next cycle).

        If the updated period has not yet elapsed, then the output should
        wait until the new period has elapsed before restarting.
        '''
        # We should never reach this number of cycles as we can raise
        # StopSimulation once we've completed the tests
        max_cycles = 20000

        axis_write_bfm = AxiStreamMasterBFM()
        axis_read_bfm = AxiStreamSlaveBFM()

        max_packet_len = 100
        min_packet_len = 50

        max_input_val = self.axis_in.TDATA.max

        # Randomly determine the number of packets to write
        n_packets = random.randrange(5, 10)

        # TID and TDEST are not used therefore the stream value will be
        # interpreted and zeroes by the AxiSlaceBFM
        stream = self.stream
        write_data = {stream: deque([])}

        for x in range(n_packets):
            packet = deque(
                [random.randrange(0, max_input_val)  for x in range(
                    random.randrange(min_packet_len, max_packet_len))])

            write_data[stream].append(packet)

        n_samples = sum(len(packet) for packet in write_data[stream])

        axis_write_bfm.add_data(write_data[stream])

        @block
        def period_driver(clock, period):

            period_change_probability = 0.01

            @always(clock.posedge)
            def driver():

                if random.random() < period_change_probability:
                    period.next = random.randrange(period.min, period.max)

            return driver

        checker_args = self.default_args.copy()
        checker_args['read_bfm'] = axis_read_bfm
        checker_args['write_bfm'] = axis_write_bfm
        checker_args['n_expected_output_packets'] = len(write_data[stream])

        dut_outputs, ref_outputs = self.cosimulate(
            max_cycles, axis_periodic_enable, axis_periodic_enable,
            self.default_args, self.default_arg_types,
            custom_sources=[
                (self.checker, (), checker_args),
                (period_driver, (self.clock, self.period), {})])

        self.assertTrue(axis_read_bfm.completed_packets == write_data)
        self.assertTrue(dut_outputs == ref_outputs)

    def test_reset(self):
        '''If synchronous reset is asserted high on any cycle, then the
        period counter should be set to zero.

        The output should be enabled on the first cycle in which reset is
        deasserted, and it should then output on every ``period`` cycles after
        _that_.
        '''
        # We should never reach this number of cycles as we can raise
        # StopSimulation once we've completed the tests
        max_cycles = 20000

        axis_write_bfm = AxiStreamMasterBFM()
        axis_read_bfm = AxiStreamSlaveBFM()

        max_packet_len = 100
        min_packet_len = 50

        max_input_val = self.axis_in.TDATA.max

        # Randomly determine the number of packets to write
        n_packets = random.randrange(5, 10)

        # TID and TDEST are not used therefore the stream value will be
        # interpreted and zeroes by the AxiSlaceBFM
        stream = self.stream
        write_data = {stream: deque([])}

        for x in range(n_packets):
            packet = deque(
                [random.randrange(0, max_input_val)  for x in range(
                    random.randrange(min_packet_len, max_packet_len))])

            write_data[stream].append(packet)

        n_samples = sum(len(packet) for packet in write_data[stream])

        axis_write_bfm.add_data(write_data[stream])

        @block
        def reset_driver(clock, reset):

            reset_set_probability = 0.02
            reset_unset_probability = 0.3

            @always(clock.posedge)
            def driver():

                if not reset:
                    if random.random() < reset_set_probability:
                        reset.next = True

                else:
                    if random.random() < reset_unset_probability:
                        reset.next = False

            return driver

        checker_args = self.default_args.copy()
        checker_args['read_bfm'] = axis_read_bfm
        checker_args['write_bfm'] = axis_write_bfm
        checker_args['n_expected_output_packets'] = len(write_data[stream])

        dut_outputs, ref_outputs = self.cosimulate(
            max_cycles, axis_periodic_enable, axis_periodic_enable,
            self.default_args, self.default_arg_types,
            custom_sources=[
                (self.checker, (), checker_args),
                (reset_driver, (self.clock, self.reset), {})])

        self.assertTrue(axis_read_bfm.completed_packets == write_data)
        self.assertTrue(dut_outputs == ref_outputs)

    def test_invalid_in_or_unready_out(self):
        '''If the input is invalid on a period or the output is not ready
        on a period, then that transaction should just not happen.
        '''
        # We should never reach this number of cycles as we can raise
        # StopSimulation once we've completed the tests
        max_cycles = 20000

        self.period = random.randrange(2, 20)

        axis_write_bfm = AxiStreamMasterBFM()
        axis_read_bfm = AxiStreamSlaveBFM()

        max_packet_len = 100
        min_packet_len = 50

        max_input_val = self.axis_in.TDATA.max

        # Randomly determine the number of packets to write
        n_packets = random.randrange(5, 10)

        # TID and TDEST are not used therefore the stream value will be
        # interpreted and zeroes by the AxiSlaceBFM
        stream = self.stream
        write_data = {stream: deque([])}

        read_probability = 0.5
        write_probability = 0.5

        for x in range(n_packets):
            packet = deque(
                [random.randrange(0, max_input_val) if
                 random.random() < write_probability else None
                 for x in range(
                     random.randrange(min_packet_len, max_packet_len))])

            write_data[stream].append(packet)

        # We create a stripped version of the write data without any
        # of the Nones, and with packets removed that are entirely
        # Nones. This is the expected read data.
        stripped_write_data = {}
        stripped_write_data[stream] = deque([
            deque([each for each in packet if each is not None])
            for packet in write_data[stream] if
            not all([val is None for val in packet])])

        n_samples = sum(len(packet) for packet in write_data[stream])

        axis_write_bfm.add_data(write_data[stream])

        self.default_args['period'] = self.period
        self.default_arg_types['period'] = 'non-signal'

        checker_args = self.default_args.copy()
        checker_args['read_bfm'] = axis_read_bfm
        checker_args['write_bfm'] = axis_write_bfm
        checker_args['n_expected_output_packets'] = len(write_data[stream])
        checker_args['TREADY_probability'] = read_probability

        dut_outputs, ref_outputs = self.cosimulate(
            max_cycles, axis_periodic_enable, axis_periodic_enable,
            self.default_args, self.default_arg_types,
            custom_sources=[
                (self.checker, (), checker_args)])

        self.assertTrue(
            axis_read_bfm.completed_packets == stripped_write_data)
        self.assertTrue(dut_outputs == ref_outputs)

    def test_no_output_TLAST(self):
        '''If the ``axis_out`` does not have a TLAST, then the input TLAST
        is simply ignored.
        '''
        # We should never reach this number of cycles as we can raise
        # StopSimulation once we've completed the tests
        max_cycles = 20000

        self.axis_out = AxiStreamInterface(4, use_TLAST=False)

        self.default_args['axis_out'] = self.axis_out
        del self.default_arg_types['axis_out']['TLAST']

        self.period = random.randrange(2, 20)

        axis_write_bfm = AxiStreamMasterBFM()
        axis_read_bfm = AxiStreamSlaveBFM()

        max_packet_len = 100
        min_packet_len = 50

        max_input_val = self.axis_in.TDATA.max

        # Randomly determine the number of packets to write
        n_packets = random.randrange(5, 10)

        # TID and TDEST are not used therefore the stream value will be
        # interpreted and zeroes by the AxiSlaceBFM
        stream = self.stream
        write_data = {stream: deque([])}

        for x in range(n_packets):
            packet = deque(
                [random.randrange(0, max_input_val)  for x in range(
                    random.randrange(min_packet_len, max_packet_len))])

            write_data[stream].append(packet)

        n_samples = sum(len(packet) for packet in write_data[stream])

        axis_write_bfm.add_data(write_data[stream])

        self.default_args['period'] = self.period
        self.default_arg_types['period'] = 'non-signal'

        checker_args = self.default_args.copy()
        checker_args['read_bfm'] = axis_read_bfm
        checker_args['write_bfm'] = axis_write_bfm
        checker_args['n_expected_output_packets'] = len(write_data[stream])

        with warnings.catch_warnings():
            warnings.filterwarnings(
                'ignore',
                message='Signal is driven but not read: axis_in_TLAST',
                category=myhdl.ToVHDLWarning)

            warnings.filterwarnings(
                'ignore',
                message='Signal is driven but not read: axis_in_TLAST',
                category=myhdl.ToVerilogWarning)

            dut_outputs, ref_outputs = self.cosimulate(
                max_cycles, axis_periodic_enable, axis_periodic_enable,
                self.default_args, self.default_arg_types,
                custom_sources=[
                    (self.checker, (), checker_args)])

        # Flatten the packet
        expected_output = {}
        expected_output[stream] = deque(
            [item for packet in write_data[stream] for item in packet])

        self.assertTrue(axis_read_bfm.current_packets == expected_output)
        self.assertTrue(dut_outputs == ref_outputs)

    def test_no_input_TLAST(self):
        '''If the ``axis_in`` does not have a TLAST, then the output TLAST
        if it exists is always ``False``.
        '''
        # We should never reach this number of cycles as we can raise
        # StopSimulation once we've completed the tests
        max_cycles = 20000

        self.axis_in = AxiStreamInterface(4, use_TLAST=False)

        self.default_args['axis_in'] = self.axis_in
        del self.default_arg_types['axis_in']['TLAST']

        self.period = random.randrange(2, 20)

        axis_write_bfm = AxiStreamMasterBFM()
        axis_read_bfm = AxiStreamSlaveBFM()

        max_packet_len = 100
        min_packet_len = 50

        max_input_val = self.axis_in.TDATA.max

        # Randomly determine the number of packets to write
        n_packets = random.randrange(5, 10)

        # TID and TDEST are not used therefore the stream value will be
        # interpreted as zeroes by the AxiSlaceBFM
        stream = self.stream
        write_data = {stream: deque([])}

        for x in range(n_packets):
            packet = deque(
                [random.randrange(0, max_input_val)  for x in range(
                    random.randrange(min_packet_len, max_packet_len))])

            write_data[stream].append(packet)

        n_samples = sum(len(packet) for packet in write_data[stream])

        axis_write_bfm.add_data(write_data[stream])

        self.default_args['period'] = self.period
        self.default_arg_types['period'] = 'non-signal'

        checker_args = self.default_args.copy()
        checker_args['read_bfm'] = axis_read_bfm
        checker_args['write_bfm'] = axis_write_bfm
        checker_args['n_expected_output_packets'] = len(write_data[stream])

        dut_outputs, ref_outputs = self.cosimulate(
            max_cycles, axis_periodic_enable, axis_periodic_enable,
            self.default_args, self.default_arg_types,
            custom_sources=[
                (self.checker, (), checker_args)])

        # Flatten the packet
        expected_output = {}
        expected_output[stream] = deque(
            [item for packet in write_data[stream] for item in packet])

        self.assertTrue(axis_read_bfm.current_packets == expected_output)
        self.assertTrue(dut_outputs == ref_outputs)

    def test_missing_TLASTs(self):
        '''If neither ``axis_in`` not ``axis_out`` have a TLAST, then the
        block should still work just without any TLAST signals.
        '''
        # We should never reach this number of cycles as we can raise
        # StopSimulation once we've completed the tests
        max_cycles = 20000

        self.axis_in = AxiStreamInterface(4, use_TLAST=False)
        self.axis_out = AxiStreamInterface(4, use_TLAST=False)

        self.default_args['axis_in'] = self.axis_in
        del self.default_arg_types['axis_in']['TLAST']

        self.default_args['axis_out'] = self.axis_out
        del self.default_arg_types['axis_out']['TLAST']

        self.period = random.randrange(2, 20)

        axis_write_bfm = AxiStreamMasterBFM()
        axis_read_bfm = AxiStreamSlaveBFM()

        max_packet_len = 100
        min_packet_len = 50

        max_input_val = self.axis_in.TDATA.max

        # Randomly determine the number of packets to write
        n_packets = random.randrange(5, 10)

        # TID and TDEST are not used therefore the stream value will be
        # interpreted as zeroes by the AxiSlaceBFM
        stream = self.stream
        write_data = {stream: deque([])}

        for x in range(n_packets):
            packet = deque(
                [random.randrange(0, max_input_val)  for x in range(
                    random.randrange(min_packet_len, max_packet_len))])

            write_data[stream].append(packet)

        n_samples = sum(len(packet) for packet in write_data[stream])

        axis_write_bfm.add_data(write_data[stream])

        self.default_args['period'] = self.period
        self.default_arg_types['period'] = 'non-signal'

        checker_args = self.default_args.copy()
        checker_args['read_bfm'] = axis_read_bfm
        checker_args['write_bfm'] = axis_write_bfm
        checker_args['n_expected_output_packets'] = len(write_data[stream])

        dut_outputs, ref_outputs = self.cosimulate(
            max_cycles, axis_periodic_enable, axis_periodic_enable,
            self.default_args, self.default_arg_types,
            custom_sources=[
                (self.checker, (), checker_args)])

        # Flatten the packet
        expected_output = {}
        expected_output[stream] = deque(
            [item for packet in write_data[stream] for item in packet])

        self.assertTrue(axis_read_bfm.current_packets == expected_output)
        self.assertTrue(dut_outputs == ref_outputs)

class TestAxisPeriodicEnableVivadoVhdlSimulation(
    JackdawVivadoVHDLTestCase, TestAxisPeriodicEnableSimulation):
    pass

class TestAxisPeriodicEnableVivadoVerilogSimulation(
    JackdawVivadoVerilogTestCase, TestAxisPeriodicEnableSimulation):
    pass
