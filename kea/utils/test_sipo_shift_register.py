from ._sipo_shift_register import sipo_shift_register

from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

import random

from myhdl import *

@block
def piso_model(data_clock, serial_data, parallel_load, parallel_value):
    ''' This block models a simple PISO shift register.
    '''

    parallel_buffer = Signal(
        intbv(0, min=parallel_value.min, max=parallel_value.max))

    msb = len(parallel_buffer) - 1

    @always_comb
    def set_serial_data():
        serial_data.next = parallel_buffer[msb]

    @always(parallel_load.posedge)
    def load_parallel_buffer():
        parallel_buffer.next = parallel_value

    @always(data_clock.posedge)
    def shift_buffer():
        parallel_buffer.next[msb+1:1] = parallel_buffer[msb:0]
        parallel_buffer.next[0] = 0

    return set_serial_data, load_parallel_buffer, shift_buffer

@block
def timing_checks(
    clock, serial_data_clock, parallel_load, serial_clock_period,
    parallel_data_bitwidth):
    ''' This block checks that the system adheres to the timing requirements.
    '''

    return_objects = []

    clock_high_period = serial_clock_period//2
    clock_low_period = serial_clock_period - clock_high_period
    clock_period_count = Signal(intbv(0, 0, serial_clock_period+1))

    load_count = Signal(intbv(0, 0, serial_clock_period+1))
    bit_count = Signal(intbv(0, 0, parallel_data_bitwidth+1))

    t_model_state = enum('IDLE', 'PARALLEL_LOAD', 'CLOCK_LOW', 'CLOCK_HIGH')
    model_state = Signal(t_model_state.IDLE)

    @always(clock.posedge)
    def model():

        if model_state == t_model_state.IDLE:
            assert(not serial_data_clock)

            if not parallel_load:
                # Each read should start with parallel_load being set low
                load_count.next = 1
                bit_count.next = 0
                model_state.next = t_model_state.PARALLEL_LOAD

        elif model_state == t_model_state.PARALLEL_LOAD:
            assert(not serial_data_clock)
            assert(not parallel_load)

            if load_count >= serial_clock_period-1:
                # parallel_load should be held low for serial_clock_period
                model_state.next = t_model_state.CLOCK_LOW

            else:
                load_count.next = load_count + 1

        elif model_state == t_model_state.CLOCK_LOW:
            assert(not serial_data_clock)
            assert(parallel_load)

            # Count the clock period
            clock_period_count.next = clock_period_count + 1

            if clock_period_count >= clock_low_period-1:
                # data_clock should be low for half the clock period
                model_state.next = t_model_state.CLOCK_HIGH

        elif model_state == t_model_state.CLOCK_HIGH:
            assert(serial_data_clock)
            assert(parallel_load)

            if clock_period_count >= serial_clock_period-1:
                # data_clock should be high for half the clock period
                clock_period_count.next = 0

                if bit_count >= parallel_data_bitwidth-2:
                    # All bits received
                    model_state.next = t_model_state.IDLE

                else:
                    # There are still bits to clock in
                    bit_count.next = bit_count + 1
                    model_state.next = t_model_state.CLOCK_LOW

            else:
                # Count the clock period
                clock_period_count.next = clock_period_count + 1

    return_objects.append(model)

    return return_objects

class TestSIPOShiftRegisterSimulation(KeaTestCase):
    '''
    The SIPO shift register should obey the following timing diagram
    (defined in Wavedrom):
        { "signal": [
      { "name": "system clock",
       "wave": "p.||||||||||||||||||.." },

      { "name": "read",
       "wave": "01x...................",
       "node": '............E',},
['External shift-reg signals',
      { "name": "To external PISO parallel_load_out",
       "wave": "1.0.1.................",
       "node": '..A.C..',},

      { "name": "From external PISO serial_data_in",
       "wave": "x..=..=.=.=.=.=.=.=.x.",
       "data": ["q7", "q6", "q5", "q4", "q3", "q2", "q1", "q0"],
       "node": '...R..X',},

      { "name": "To external PISO data_clock_out",
       "wave": "0....10101010101010...",
       "node": '.....E.G.I.......J.',}],

      { "name": "parallel_data_out",
       "wave": "x..................=..",
       "data": ["data word"],
       "node": '...................M',},
      { "name": "read_complete_toggle",
       "wave": "=..................=..",
       "data": ["toggle value", "not(toggle value)"],
       "node": '...................U',},
      { "node": '..PQ.YZ.',},

      { "node": '..B.DF.H.K.......L.N',},
      { "node": '..O..............T'},
      {"node": '..S'},],
      "edge": [
        'A|B', 'C|D', 'E|F', 'G|H', 'I|K', 'J|L', 'M|N', 'R|Q', 'X|Z',
        'B<->D tp',
        'D<->F tp/2',
        'F<->H tp',
        'H<->K tp',
        'L<->N tp',
      'Y<->Z td',
    'P<->Q td',
    'O td = time delay from clock edge to data ready',
    'S tp = period of data out clock. td must be less than tp.',
    'T The read_complete_toggle_flag will flip on completion of the read transaction',
    'T->U'],
    head:{
   text:"SIPO Shift Register timing behaviour for an example parallel " +
   "width of 8-bits",
 },
 foot:{
   text: ""},
}
    '''

    def setUp(self):

        clock = Signal(False)
        initialisation_authorised = Signal(False)
        read = Signal(False)
        parallel_data_out = Signal(intbv(0)[16:])
        serial_data_in = Signal(False)
        data_clock_out = Signal(False)
        parallel_load_out = Signal(True)
        read_complete_toggle = Signal(False)
        serial_clock_period = 8

        self.tests_complete = False
        self.n_tests_run = 0

        self.args = {
            'clock': clock,
            'initialisation_authorised': initialisation_authorised,
            'read': read,
            'parallel_data_out': parallel_data_out,
            'serial_data_in': serial_data_in,
            'data_clock_out': data_clock_out,
            'parallel_load_out': parallel_load_out,
            'read_complete_toggle': read_complete_toggle,
            'serial_clock_period': serial_clock_period,
        }

        self.arg_types = {
            'clock': 'clock',
            'initialisation_authorised': 'custom',
            'read': 'custom',
            'parallel_data_out': 'output',
            'serial_data_in': 'custom',
            'data_clock_out': 'output',
            'parallel_load_out': 'output',
            'read_complete_toggle': 'output',
            'serial_clock_period': 'non-signal'
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
    def sipo_stim(self, clock, initialisation_authorised, read):
        ''' This block randomly drives the stim signals.
        '''

        @always(clock.posedge)
        def driver():

            initialisation_authorised.next = False

            if random.random() < 0.01:
                # Randoly drive initialisation_authorised
                initialisation_authorised.next = True

            read.next = False

            if random.random() < 0.01:
                # Randomly drive the read signal
                read.next = True

        return driver

    @block
    def check_sipo_shift_register(self, **kwargs):

        clock = kwargs['clock']
        initialisation_authorised = kwargs['initialisation_authorised']
        read = kwargs['read']
        parallel_data_out = kwargs['parallel_data_out']
        serial_data_in = kwargs['serial_data_in']
        data_clock_out = kwargs['data_clock_out']
        parallel_load_out = kwargs['parallel_load_out']
        read_complete_toggle = kwargs['read_complete_toggle']
        serial_clock_period = kwargs['serial_clock_period']

        return_objects = []

        parallel_data_width = len(parallel_data_out)

        # Create a stim block to drive the stim signals
        parallel_stim_data = Signal(intbv(0)[parallel_data_width:])
        return_objects.append(
            self.sipo_stim(clock, initialisation_authorised, read))

        # Create a block to check the interface timing
        return_objects.append(
            timing_checks(
                clock, data_clock_out, parallel_load_out, serial_clock_period,
                parallel_data_width))

        # Create a PISO model
        return_objects.append(
            piso_model(
                data_clock_out, serial_data_in, parallel_load_out,
                parallel_stim_data))

        expected_parallel_data_out = Signal(intbv(0)[parallel_data_width:])

        read_complete_toggle_d0 = Signal(False)

        t_check_state = enum('INIT', 'IDLE', 'AWAIT_COMPLETE')
        check_state = Signal(t_check_state.INIT)

        @always(clock.posedge)
        def check():

            # Keep a record of the read complete toggle so we can transitions
            read_complete_toggle_d0.next = read_complete_toggle

            if check_state == t_check_state.INIT:
                # During the init pause the DUT should not perform a read
                assert(not data_clock_out)
                assert(parallel_load_out)
                assert(parallel_data_out == expected_parallel_data_out)
                assert(read_complete_toggle == read_complete_toggle_d0)

                if initialisation_authorised:
                    # Update the stim data
                    parallel_data = random.randrange(2**parallel_data_width)
                    parallel_stim_data.next = parallel_data

                    check_state.next = t_check_state.AWAIT_COMPLETE

            elif check_state == t_check_state.IDLE:
                # When Idle the system should not perform a read or update the
                # parallel_data_out.
                assert(not data_clock_out)
                assert(parallel_load_out)
                assert(parallel_data_out == expected_parallel_data_out)
                assert(read_complete_toggle == read_complete_toggle_d0)

                if read:
                    # Update the stim data
                    parallel_data = random.randrange(2**parallel_data_width)
                    parallel_stim_data.next = parallel_data

                    check_state.next = t_check_state.AWAIT_COMPLETE

            elif check_state == t_check_state.AWAIT_COMPLETE:
                if read_complete_toggle != read_complete_toggle_d0:
                    # Wait for the read_complete_toggle to change state then
                    # check that the parallel_data_out has updated correctly.
                    assert(parallel_data_out == parallel_stim_data)
                    expected_parallel_data_out.next = parallel_stim_data

                    self.n_tests_run += 1

                    if read:
                        # As we use the read_complete_toggle to detect
                        # completion, the DUT will have returned to idle so we
                        # need to detect read in this state.
                        parallel_data = (
                            random.randrange(2**parallel_data_width))
                        parallel_stim_data.next = parallel_data

                    else:
                        check_state.next = t_check_state.IDLE

                else:
                    assert(parallel_data_out == expected_parallel_data_out)

        return_objects.append(check)

        return return_objects

    ###################
    # Interface tests #
    ###################

    def test_serial_clock_period_of_one(self):
        '''The ``serial_clock_period`` should be 2 or greater.
        '''
        self.args['serial_clock_period'] = 1

        self.assertRaisesRegex(
            ValueError,
            'Clock period error: serial_clock_period must be at least 2',
            sipo_shift_register,
            **self.args,
        )

    def test_serial_clock_period_of_zero(self):
        '''The ``serial_clock_period`` should be 2 or greater.
        '''
        self.args['serial_clock_period'] = 0

        self.assertRaisesRegex(
            ValueError,
            'Clock period error: serial_clock_period must be at least 2',
            sipo_shift_register,
            **self.args,
        )

    def test_negative_serial_clock_period(self):
        '''The ``serial_clock_period`` should be 2 or greater.
        '''
        self.args['serial_clock_period'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            'Clock period error: serial_clock_period must be at least 2',
            sipo_shift_register,
            **self.args,
        )

    #######################
    # Functionality tests #
    #######################

    def test_read(self):
        ''' On a rising edge of ``read``, the block should firstly deassert
        ``parallel_load_out`` for ``serial_clock_period`` cycles, at which
        read the first (MSB) data bit should be available on
        ``serial_data_in``. The data should then be clocked out of the
        external shift register as per the timing diagram, with N-1 cycles
        of ``data_clock_out`` where N is the bitwidth of the parallel shift
        register and should be inferred from the width of
        ``parallel_load_out``.

        On completion of each read transaction, the ``read_complete_toggle``
        signal should flip.

        When the ``read_complete_toggle`` flips, the value in the
        ``parallel_data_out`` signal should be the correctly read value.

        The data on ``parallel_load_out`` should remain fixed until it is
        updated from a new read.
        '''

        if not self.testing_using_vivado:
            cycles = 15000
            n_tests = 15

        else:
            cycles = 5000
            n_tests = 4

        @block
        def stimulate_and_check(**kwargs):

            return_objects = []

            clock = kwargs['clock']

            return_objects.append(self.stop_when_complete(clock, n_tests))

            return_objects.append(self.check_sipo_shift_register(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, sipo_shift_register, sipo_shift_register,
            self.args, self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_initialisation_read(self):
        ''' On startup, the block should wait for `initialisation_authorised`
        to go high and then conduct an initial read without receiving the read
        command. The procedure for this read is identical to the normal read
        descrided above.
        '''

        cycles = 3000
        n_tests = 2

        @block
        def stimulate_and_check(**kwargs):

            return_objects = []

            clock = kwargs['clock']

            return_objects.append(self.stop_when_complete(clock, n_tests))

            return_objects.append(self.check_sipo_shift_register(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, sipo_shift_register, sipo_shift_register,
            self.args, self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_min_serial_clock_period(self):
        ''' The minimum ``serial_clock_period`` that the
        ``sipo_shift_register`` can handle is 2. The system should function
        correctly when passed a ``serial_clock_period`` of 2.
        '''

        if not self.testing_using_vivado:
            cycles = 15000
            n_tests = 15

        else:
            cycles = 5000
            n_tests = 4

        self.args['serial_clock_period'] = 2

        @block
        def stimulate_and_check(**kwargs):

            return_objects = []

            clock = kwargs['clock']

            return_objects.append(self.stop_when_complete(clock, n_tests))

            return_objects.append(self.check_sipo_shift_register(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, sipo_shift_register, sipo_shift_register,
            self.args, self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_large_serial_clock_period(self):
        ''' The ``sipo_shift_register`` should function correctly with a large
        ``serial_clock_period``.
        '''

        if not self.testing_using_vivado:
            cycles = 60000
            n_tests = 5

        else:
            cycles = 30000
            n_tests = 3

        self.args['serial_clock_period'] = 201

        @block
        def stimulate_and_check(**kwargs):

            return_objects = []

            clock = kwargs['clock']

            return_objects.append(self.stop_when_complete(clock, n_tests))

            return_objects.append(self.check_sipo_shift_register(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, sipo_shift_register, sipo_shift_register,
            self.args, self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_random_serial_clock_period(self):
        ''' The ``sipo_shift_register`` should function correctly with any
        ``serial_clock_period`` which is greater than 1.
        '''

        if not self.testing_using_vivado:
            cycles = 60000
            n_tests = 15

        else:
            cycles = 30000
            n_tests = 5

        self.args['serial_clock_period'] = random.randrange(3, 33)

        @block
        def stimulate_and_check(**kwargs):

            return_objects = []

            clock = kwargs['clock']

            return_objects.append(self.stop_when_complete(clock, n_tests))

            return_objects.append(self.check_sipo_shift_register(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, sipo_shift_register, sipo_shift_register,
            self.args, self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_min_bitwidth(self):
        ''' The ``sipo_shift_register`` should function correctly when
        ``parallel_data_out`` is 2 bits wide.
        '''

        if not self.testing_using_vivado:
            cycles = 15000
            n_tests = 20

        else:
            cycles = 5000
            n_tests = 10

        self.args['parallel_data_out'] = Signal(intbv(0)[2:])

        @block
        def stimulate_and_check(**kwargs):

            return_objects = []

            clock = kwargs['clock']

            return_objects.append(self.stop_when_complete(clock, n_tests))

            return_objects.append(self.check_sipo_shift_register(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, sipo_shift_register, sipo_shift_register,
            self.args, self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_large_bitwidth(self):
        ''' The ``sipo_shift_register`` should function correctly when
        ``parallel_data_out`` is a large number of bits wide.
        '''

        if not self.testing_using_vivado:
            cycles = 20000
            n_tests = 10

        else:
            cycles = 10000
            n_tests = 5

        self.args['parallel_data_out'] = Signal(intbv(0)[64:])

        @block
        def stimulate_and_check(**kwargs):

            return_objects = []

            clock = kwargs['clock']

            return_objects.append(self.stop_when_complete(clock, n_tests))

            return_objects.append(self.check_sipo_shift_register(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, sipo_shift_register, sipo_shift_register,
            self.args, self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_random_bitwidth(self):
        ''' The ``sipo_shift_register`` should function correctly when
        ``parallel_data_out`` is any random of bits wide.
        '''

        if not self.testing_using_vivado:
            cycles = 30000
            n_tests = 20

        else:
            cycles = 15000
            n_tests = 10

        bitwidth = random.randrange(2, 32)
        self.args['parallel_data_out'] = Signal(intbv(0)[bitwidth:])

        @block
        def stimulate_and_check(**kwargs):

            return_objects = []

            clock = kwargs['clock']

            return_objects.append(self.stop_when_complete(clock, n_tests))

            return_objects.append(self.check_sipo_shift_register(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, sipo_shift_register, sipo_shift_register,
            self.args, self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

class TestSIPOShiftRegisterVivadoVHDLSimulation(
    KeaVivadoVHDLTestCase, TestSIPOShiftRegisterSimulation):
    pass

class TestSIPOShiftRegisterVivadoVerilogSimulation(
    KeaVivadoVerilogTestCase, TestSIPOShiftRegisterSimulation):
    pass

