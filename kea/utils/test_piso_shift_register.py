from ._piso_shift_register import piso_shift_register

from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

import random

from myhdl import *

class TestPISOShiftRegisterInterfaceSimulation(KeaTestCase):

    def setUp(self):

        self.data_in_bitwidth = 15

        self.clock = Signal(False)
        self.reset = Signal(False)
        self.data_in = Signal(intbv(0)[self.data_in_bitwidth:0])
        self.data_out = Signal(False)
        self.data_out_clock = Signal(False)
        self.data_out_nreset = Signal(True)
        self.data_out_latch = Signal(False)
        self.data_out_nframe_sync = Signal(True)
        self.external_register_value = (
            Signal(intbv(0)[self.data_in_bitwidth:0]))
        self.clock_out_period = 10
        self.post_frame_delay = 0

        self.args = {
            'clock': self.clock,
            'reset': self.reset,
            'data_in': self.data_in,
            'data_out': self.data_out,
            'data_out_clock': self.data_out_clock,
            'data_out_nreset': self.data_out_nreset,
            'data_out_latch': self.data_out_latch,
            'data_out_nframe_sync': self.data_out_nframe_sync,
            'external_register_value': self.external_register_value,
            'clock_out_period': self.clock_out_period,
            'post_frame_delay': self.post_frame_delay,
            'ready': None,
        }

    def test_clock_out_period_of_one(self):
        '''The ``clock_out_period`` should be 2 or greater.
        '''
        self.args['clock_out_period'] = 1

        self.assertRaisesRegex(
            ValueError,
            'Clock period error',
            piso_shift_register,
            **self.args,
        )

    def test_clock_out_period_of_zero(self):
        '''The ``clock_out_period`` should be 2 or greater.
        '''
        self.args['clock_out_period'] = 0

        self.assertRaisesRegex(
            ValueError,
            'Clock period error',
            piso_shift_register,
            **self.args,
        )

    def test_negative_clock_out_period(self):
        '''The ``clock_out_period`` should be 2 or greater.
        '''
        self.args['clock_out_period'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            'Clock period error',
            piso_shift_register,
            **self.args,
        )

    def test_negative_post_frame_delay(self):
        '''The ``post_frame_delay`` should be 0 or greater.
        '''
        self.args['post_frame_delay'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            'post frame delay error',
            piso_shift_register,
            **self.args,
        )

    def test_mismatched_lengths(self):
        '''The length of ``external_register_value`` must equal the length of
        ``data_in``.
        '''
        lengths = random.sample(range(1, 32), 2)

        self.args['data_in'] = Signal(intbv(0)[lengths[0]:0])
        self.args['external_register_value'] = Signal(intbv(0)[lengths[1]:0])

        self.assertRaisesRegex(
            ValueError,
            'length error',
            piso_shift_register,
            **self.args,
        )

    def test_ready_initialised_false(self):
        ''' The ``piso_shift_register`` should raise an error if a ready
        signal is passed in and is not initialised True.
        '''

        self.args['ready'] = Signal(False)

        self.assertRaisesRegex(
            ValueError,
            'ready should be initialised true',
            piso_shift_register,
            **self.args,
        )

@block
def sipo_model(
    serial_clock, shift_reg_nreset, parallel_out_nreset, serial_data,
    serial_latch, parallel_data):
    ''' This block models a simple SIPO shift register.
    '''

    parallel_data_bitwidth = len(parallel_data)
    shift_reg = Signal(intbv(0)[parallel_data_bitwidth:0])

    @always(serial_clock.posedge, shift_reg_nreset.negedge)
    def shift():
        shift_reg.next[0] = serial_data
        shift_reg.next[parallel_data_bitwidth:1] = (
            shift_reg[parallel_data_bitwidth-1:0])

        if not shift_reg_nreset:
            shift_reg.next = 0

    @always(serial_latch.posedge, parallel_out_nreset.negedge)
    def latch():
        parallel_data.next = shift_reg

        if not parallel_out_nreset:
            parallel_data.next = 0

    return shift, latch

@block
def timing_checks(
    clock, serial_data_clock, serial_data_latch, serial_data_nframe_sync,
    serial_data_nreset, serial_data_clock_period, post_frame_delay,
    parallel_data_width):
    ''' This block checks that the system adheres to the timing requirements.
    '''

    return_objects = []

    serial_data_clock_d0 = Signal(False)
    serial_data_nreset_d0 = Signal(False)

    reset_period = serial_data_clock_period

    bit_count = Signal(intbv(0, 0, parallel_data_width+1))
    clock_period_count = Signal(intbv(0, 0, serial_data_clock_period+1))
    latch_period_count = Signal(intbv(0, 0, serial_data_clock_period+1))
    reset_period_count = Signal(intbv(reset_period, 0, reset_period+1))

    t_model_state = enum(
        'IDLE', 'AWAITING_FIRST_BIT', 'RECEIVING_DATA', 'LATCHING',
        'POST_FRAME_DELAY', 'RESET', 'POST_RESET_UPDATE')
    model_state = Signal(t_model_state.IDLE)

    expected_clock_high_period = serial_data_clock_period//2
    clock_high_count = Signal(intbv(0, 0, expected_clock_high_period+1))

    t_clock_state = enum('LOW', 'HIGH')
    clock_state = Signal(t_clock_state.LOW)

    @always(clock.posedge)
    def model():

        #########
        # Reset #
        #########
        # Keep a record of the nreset so we can detect changes
        serial_data_nreset_d0.next = serial_data_nreset

        if serial_data_nreset and not serial_data_nreset_d0:
            # Rising edge on nreset so check the reset is held low for the
            # required period
            assert(reset_period_count == reset_period)

        if not serial_data_nreset:
            # Check the serial signals return to default
            assert(serial_data_nframe_sync)
            assert(not serial_data_clock)
            assert(not serial_data_latch)

            if serial_data_nreset_d0:
                # Falling edge on nreset so start the period count
                reset_period_count.next = 1

            elif reset_period_count < reset_period:
                # Count the reset period
                reset_period_count.next = reset_period_count + 1

            clock_state.next = t_clock_state.LOW
            model_state.next = t_model_state.IDLE

        else:

            #############################
            # Shift register sequencing #
            #############################

            serial_data_clock_d0.next = serial_data_clock

            if model_state == t_model_state.IDLE:
                assert(not serial_data_clock)
                assert(not serial_data_latch)

                if not serial_data_nframe_sync:
                    model_state.next = t_model_state.AWAITING_FIRST_BIT

            elif model_state == t_model_state.AWAITING_FIRST_BIT:
                assert(not serial_data_nframe_sync)
                assert(not serial_data_latch)

                if serial_data_clock and not serial_data_clock_d0:
                    # Rising edge on serial_clock
                    bit_count.next = 1
                    clock_period_count.next = 1

                    model_state.next = t_model_state.RECEIVING_DATA

            elif model_state == t_model_state.RECEIVING_DATA:

                if not serial_data_nframe_sync:
                    # serial_data_nframe_sync should be kept low whilst data
                    # is being written.
                    assert(not serial_data_latch)

                    if serial_data_clock and not serial_data_clock_d0:
                        # Check that the clock period is correct
                        assert(clock_period_count == serial_data_clock_period)
                        clock_period_count.next = 1

                        bit_count.next = bit_count + 1

                    else:
                        # Count the clock period
                        clock_period_count.next = clock_period_count + 1

                else:
                    # Once all the data has arrived the PISO shift register
                    # should set serial_data_latch high.
                    assert(serial_data_latch)
                    assert(not serial_data_clock)
                    assert(bit_count == parallel_data_width)

                    latch_period_count.next = 1
                    model_state.next = t_model_state.LATCHING

            elif model_state == t_model_state.LATCHING:
                assert(serial_data_nframe_sync)
                assert(not serial_data_clock)

                if not serial_data_latch:
                    assert(latch_period_count == serial_data_clock_period)
                    model_state.next = t_model_state.IDLE

                else:
                    latch_period_count.next = latch_period_count + 1

            ################
            # Clock checks #
            ################
            # The total clock period is checked above so by checking the high
            # period we implicitly confirm the low period is correct.

            if clock_state == t_clock_state.LOW:
                if serial_data_clock:
                    # Serial data clock is high
                    clock_high_count.next = 1
                    clock_state.next = t_clock_state.HIGH

            elif clock_state == t_clock_state.HIGH:
                if not serial_data_clock:
                    # Serial data clock has gone low again
                    assert(clock_high_count == expected_clock_high_period)
                    clock_state.next = t_clock_state.LOW

                else:
                    clock_high_count.next = clock_high_count + 1

    return_objects.append(model)

    return return_objects

class TestPISOShiftRegisterSimulation(KeaTestCase):

    def setUp(self):

        self.data_in_bitwidth = 15

        self.clock = Signal(False)
        self.reset = Signal(False)
        self.data_in = Signal(intbv(0)[self.data_in_bitwidth:0])
        self.data_out = Signal(False)
        self.data_out_clock = Signal(False)
        self.data_out_nreset = Signal(True)
        self.data_out_latch = Signal(False)
        self.data_out_nframe_sync = Signal(True)
        self.external_register_value = (
            Signal(intbv(0)[self.data_in_bitwidth:0]))
        self.clock_out_period = 10
        self.post_frame_delay = 0

        self.tests_complete = False
        self.n_tests_run = 0

        self.args = {
            'clock': self.clock,
            'reset': self.reset,
            'data_in': self.data_in,
            'data_out': self.data_out,
            'data_out_clock': self.data_out_clock,
            'data_out_nreset': self.data_out_nreset,
            'data_out_latch': self.data_out_latch,
            'data_out_nframe_sync': self.data_out_nframe_sync,
            'external_register_value': self.external_register_value,
            'clock_out_period': self.clock_out_period,
            'post_frame_delay': self.post_frame_delay,
        }

        self.arg_types = {
            'clock': 'clock',
            'reset': 'custom',
            'data_in': 'custom',
            'data_out': 'output',
            'data_out_clock': 'output',
            'data_out_nreset': 'output',
            'data_out_latch': 'output',
            'data_out_nframe_sync': 'output',
            'external_register_value': 'output',
            'clock_out_period': 'non-signal',
            'post_frame_delay': 'non-signal',
        }

    @block
    def stop_when_complete(self, clock, n_required_tests):

        @always(clock.posedge)
        def check():

            if self.n_tests_run >= n_required_tests:
                # Check that the checks are actually performed
                self.tests_complete = True
                raise StopSimulation

        return check

    @block
    def piso_stim(self, clock, reset, data, drive_reset=False):
        ''' This block randomly drives the control signals.
        '''

        @always(clock.posedge)
        def driver():

            if random.random() < 0.003:
                # Randomly drive the data signal
                data.next = random.randrange(2**len(data))

            if drive_reset:
                if reset:
                    if random.random() < 0.25:
                        # Keep reset high for a random period
                        reset.next = False

                else:
                    if random.random() < 0.003:
                        # Randomly set reset
                        reset.next = True

        return driver

    @block
    def check_piso_shift_register(
        self, clock, reset, data_in, data_out, data_out_clock, data_out_latch,
        data_out_nframe_sync, data_out_nreset, external_register_value,
        clock_out_period, post_frame_delay, dut_ready):

        return_objects = []

        expected_data = Signal(intbv(0)[self.data_in_bitwidth:0])
        written_data = Signal(intbv(0)[self.data_in_bitwidth:0])
        next_data = Signal(intbv(0)[self.data_in_bitwidth:0])

        expected_ready = Signal(True)

        post_frame_delay_count = Signal(intbv(0, 0, post_frame_delay+1))

        latch_period = clock_out_period
        latch_period_count = Signal(intbv(0, 0, latch_period+1))

        # Create buffers so we can detect edges on latch and nreset
        data_out_nreset_buffer = Signal(False)
        data_out_latch_buffer = Signal(False)

        return_objects.append(
            sipo_model(
                data_out_clock, data_out_nreset, data_out_nreset,
                data_out, data_out_latch, written_data))

        return_objects.append(
            timing_checks(
                clock, data_out_clock, data_out_latch,
                data_out_nframe_sync, data_out_nreset,
                clock_out_period, post_frame_delay, self.data_in_bitwidth))

        t_check_state = enum(
            'INIT', 'IDLE', 'AWAIT_LATCH', 'LATCHING', 'POST_FRAME_DELAY',
            'RESET')
        check_state = Signal(t_check_state.INIT)

        @always(clock.posedge)
        def check():

            # Keep a record of the data_out_nreset, data_out_latch so we can
            # detect edges
            data_out_nreset_buffer.next = data_out_nreset
            data_out_latch_buffer.next = data_out_latch

            if data_out_nreset_buffer and not data_out_nreset:
                # After falling edges on nreset, check written_data is 0
                assert(written_data == 0)
                expected_data.next = 0

            elif data_out_latch and not data_out_latch_buffer:
                # After rising edges on data_out_latch, data should update
                assert(written_data == next_data)
                expected_data.next = next_data

            else:
                assert(written_data == expected_data)

            if dut_ready is not None:
                assert(dut_ready == expected_ready)

            if check_state == t_check_state.INIT:
                # At start up the DUT should perform a write
                next_data.next = data_in
                expected_ready.next = False
                check_state.next = t_check_state.AWAIT_LATCH

            elif check_state == t_check_state.IDLE:
                if data_in != expected_data:
                    # Data in has changed so the DUT should write the data out
                    next_data.next = data_in
                    expected_ready.next = False
                    check_state.next = t_check_state.AWAIT_LATCH

            elif check_state == t_check_state.AWAIT_LATCH:
                if data_out_latch:
                    # Latching is in progress
                    check_state.next = t_check_state.LATCHING

            elif check_state == t_check_state.LATCHING:
                if latch_period_count >= latch_period - 2:
                    # We have to use minus 2 here because the source knows
                    # when it sets latch low and is consequently an extra
                    # cycle ahead
                    latch_period_count.next = 0

                    if post_frame_delay == 0:
                        # Count the number of tests run
                        self.n_tests_run += 1
                        expected_ready.next = True
                        check_state.next = t_check_state.IDLE

                    else:
                        post_frame_delay_count.next = 1
                        check_state.next = t_check_state.POST_FRAME_DELAY

                else:
                    latch_period_count.next = latch_period_count + 1

            elif check_state == t_check_state.POST_FRAME_DELAY:
                if post_frame_delay_count >= post_frame_delay:
                    # Post frame delay has passed
                    post_frame_delay_count.next = 0

                    # Count the number of tests run
                    self.n_tests_run += 1
                    expected_ready.next = True
                    check_state.next = t_check_state.IDLE

                else:
                    post_frame_delay_count.next = post_frame_delay_count + 1

            elif check_state == t_check_state.RESET:
                # After a reset the DUT should perform a write
                if data_out_nreset:
                    next_data.next = data_in
                    check_state.next = t_check_state.AWAIT_LATCH

            if reset:
                expected_ready.next = False
                post_frame_delay_count.next = 0
                latch_period_count.next = 0
                check_state.next = t_check_state.RESET

        return_objects.append(check)

        return return_objects

    def test_piso_shift_reg(self):
        ''' Whenever data is changed on data_in, the full width of data_in
        will be clocked out with a clock on data_out_clock (with a period
        specified by the ``clock_out_period`` argument), and then
        data_out_latch should deassert for a full period of
        ``data_out_clock``.

        Each transition on ``data_out`` should happen half way through the
        ``data_out_clock`` period to give equal setup and hold times on
        the external shift register.

        The data should be clocked out MSB first.

        The shift register should always complete a full transaction before
        reading in new data.

        After a full transaction, ``external_register_value`` should be
        updated to reflect what was clocked out.

        At startup, the shift register should output the initial value
        of ``data_in``.

        ``data_out_nframe_sync`` should go low for the full period of the
        serial out clock cycles.

        The above is encapsulated in the following timing diagram
        (defined in Wavedrom):

        { "signal": [
          { "name": "system clock",
           "wave": "p.|||||||||||||||||||" },

          { "name": "Data word data_in",
           "wave": "x=..........x........",
           "data": ["data word (q[7-0])"],
           "node": '............e',},

          { "name": "To external SIPO data_out_nframe_sync",
           "wave": "1.0...............1..",
           "node": '..a..',},

          { "name": "To external SIPO data_out",
           "wave": "x.=.=.=.=.=.=.=.=.x..",
           "data": ["q7", "q6", "q5", "q4", "q3", "q2", "q1", "q0"],
           "node": '......',},

          { "name": "To external SIPO data_out_clock",
           "wave": "0..1010101010101010..",
           "node": '...r.ex............',},

          { "name": "To external SIPO data_out_latch",
           "wave": "0.................1.0",
           "data": ["data word"],
           "node": '..................j.m',},


          { "node": '..pq.yz...........l.n',},],

          "edge": [
            'a|p', 'e|y', 'g|h', 'j|l', 'm|n', 'r|q', 'x|z',
            'l->n tp',
          'y->z tp/2',
          'q->y tp',
        'p->q tp/2'],
        head:{
       text:"PISO Shift Register timing behaviour for an example parallel " +
       "width of 8-bits",
     },
     foot:{
       text: "tp = period of data out clock"},
        }
        '''

        if not self.testing_using_vivado:
            cycles = 15000
            n_tests = 15

        else:
            cycles = 5000
            n_tests = 4

        @block
        def stimulate_and_check(
            clock, reset, data_in, data_out, data_out_clock, data_out_latch,
            data_out_nframe_sync, data_out_nreset, external_register_value,
            clock_out_period, post_frame_delay=0, ready=None):

            return_objects = []

            return_objects.append(self.piso_stim(clock, reset, data_in))

            return_objects.append(
                self.stop_when_complete(clock, n_tests))

            return_objects.append(
                self.check_piso_shift_register(
                    clock, reset, data_in, data_out, data_out_clock,
                    data_out_latch, data_out_nframe_sync, data_out_nreset,
                    external_register_value, clock_out_period,
                    post_frame_delay, ready))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, piso_shift_register, piso_shift_register,
            self.args, self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_min_clock_out_period(self):
        ''' The `piso_shift_register` should be able to handle a
        `clock_out_period` as low as 2.
        '''

        if not self.testing_using_vivado:
            cycles = 10000
            n_tests = 15

        else:
            cycles = 5000
            n_tests = 4

        self.args['clock_out_period'] = 2

        @block
        def stimulate_and_check(
            clock, reset, data_in, data_out, data_out_clock, data_out_latch,
            data_out_nframe_sync, data_out_nreset, external_register_value,
            clock_out_period, post_frame_delay=0, ready=None):

            return_objects = []

            return_objects.append(self.piso_stim(clock, reset, data_in))

            return_objects.append(
                self.stop_when_complete(clock, n_tests))

            return_objects.append(
                self.check_piso_shift_register(
                    clock, reset, data_in, data_out, data_out_clock,
                    data_out_latch, data_out_nframe_sync, data_out_nreset,
                    external_register_value, clock_out_period,
                    post_frame_delay, ready))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, piso_shift_register, piso_shift_register,
            self.args, self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_large_clock_out_period(self):
        ''' The `piso_shift_register` should be able to handle a large
        `clock_out_period`.
        '''

        if not self.testing_using_vivado:
            cycles = 40000
            n_tests = 5

        else:
            cycles = 20000
            n_tests = 2

        self.args['clock_out_period'] = random.randrange(200, 300)

        @block
        def stimulate_and_check(
            clock, reset, data_in, data_out, data_out_clock, data_out_latch,
            data_out_nframe_sync, data_out_nreset, external_register_value,
            clock_out_period, post_frame_delay=0, ready=None):

            return_objects = []

            return_objects.append(self.piso_stim(clock, reset, data_in))

            return_objects.append(
                self.stop_when_complete(clock, n_tests))

            return_objects.append(
                self.check_piso_shift_register(
                    clock, reset, data_in, data_out, data_out_clock,
                    data_out_latch, data_out_nframe_sync, data_out_nreset,
                    external_register_value, clock_out_period,
                    post_frame_delay, ready))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, piso_shift_register, piso_shift_register,
            self.args, self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_non_zero_post_frame_delay(self):
        ''' The `piso_shift_register` should delay for `post_frame_delay`
        cycles after completion of each frame (including the latch).
        '''

        if not self.testing_using_vivado:
            cycles = 15000
            n_tests = 15

        else:
            cycles = 5000
            n_tests = 4

        self.args['post_frame_delay'] = random.randrange(1, 200)

        @block
        def stimulate_and_check(
            clock, reset, data_in, data_out, data_out_clock, data_out_latch,
            data_out_nframe_sync, data_out_nreset, external_register_value,
            clock_out_period, post_frame_delay=0, ready=None):

            return_objects = []

            return_objects.append(self.piso_stim(clock, reset, data_in))

            return_objects.append(
                self.stop_when_complete(clock, n_tests))

            return_objects.append(
                self.check_piso_shift_register(
                    clock, reset, data_in, data_out, data_out_clock,
                    data_out_latch, data_out_nframe_sync, data_out_nreset,
                    external_register_value, clock_out_period,
                    post_frame_delay, ready))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, piso_shift_register, piso_shift_register,
            self.args, self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_reset(self):
        ''' On reset being asserted, the ``data_out_nreset`` line should be
        deasserted for one full clock out period or the full time reset
        is asserted, whichever is greater.

        Once reset goes low again and ``data_out_nreset`` has gone high again,
        the shift register should serial output whatever is on the ``data_in``
        line, even if it is all zeros. This is because the last data clocked
        out should always reflect the state of the ``piso_shift_register``
        block.
        '''

        if not self.testing_using_vivado:
            cycles = 30000
            n_tests = 15

        else:
            cycles = 10000
            n_tests = 4

        self.args['clock_out_period'] = random.randrange(2, 20)
        self.args['post_frame_delay'] = random.randrange(1, 200)

        @block
        def stimulate_and_check(
            clock, reset, data_in, data_out, data_out_clock, data_out_latch,
            data_out_nframe_sync, data_out_nreset, external_register_value,
            clock_out_period, post_frame_delay=0, ready=None):

            return_objects = []

            return_objects.append(
                self.piso_stim(clock, reset, data_in, drive_reset=True))

            return_objects.append(
                self.stop_when_complete(clock, n_tests))

            return_objects.append(
                self.check_piso_shift_register(
                    clock, reset, data_in, data_out, data_out_clock,
                    data_out_latch, data_out_nframe_sync, data_out_nreset,
                    external_register_value, clock_out_period,
                    post_frame_delay, ready))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, piso_shift_register, piso_shift_register,
            self.args, self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_ready(self):
        ''' When required, it should be possible to pass a ready signal to the
        ``piso_shift_register``. This ready signal should be a status signal
        that indicates the ``piso_shift_register`` is in a state to detect
        changes between ``data_in`` and ``external_register_value``. If
        ``data_in`` changed before ``ready`` was set high, then the
        ``piso_shift_register`` shoul set ready high for one cycle and then
        write the updated ``data_in`` value.

        ``ready`` can be used by external blocks for timing purposes.

        On reset, ``ready`` should be set low.
        '''

        if not self.testing_using_vivado:
            cycles = 30000
            n_tests = 15

        else:
            cycles = 10000
            n_tests = 4

        self.args['ready'] = Signal(True)
        self.arg_types['ready'] = 'output'

        self.args['clock_out_period'] = random.randrange(2, 20)
        if random.random() < 0.5:
            # Half the time give it a non zero post frame delay
            self.args['post_frame_delay'] = random.randrange(1, 50)

        @block
        def stimulate_and_check(
            clock, reset, data_in, data_out, data_out_clock, data_out_latch,
            data_out_nframe_sync, data_out_nreset, external_register_value,
            clock_out_period, post_frame_delay=0, ready=None):

            return_objects = []

            return_objects.append(
                self.piso_stim(clock, reset, data_in, drive_reset=True))

            return_objects.append(
                self.stop_when_complete(clock, n_tests))

            return_objects.append(
                self.check_piso_shift_register(
                    clock, reset, data_in, data_out, data_out_clock,
                    data_out_latch, data_out_nframe_sync, data_out_nreset,
                    external_register_value, clock_out_period,
                    post_frame_delay, ready))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, piso_shift_register, piso_shift_register,
            self.args, self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)


class TestPISOShiftRegisterVivadoVHDLSimulation(
    KeaVivadoVHDLTestCase, TestPISOShiftRegisterSimulation):
    pass

class TestPISOShiftRegisterVivadoVerilogSimulation(
    KeaVivadoVerilogTestCase, TestPISOShiftRegisterSimulation):
    pass
