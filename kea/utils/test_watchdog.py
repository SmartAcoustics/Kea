import random

from math import ceil

from myhdl import Signal, block, always, intbv, StopSimulation

from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._rising_edge_detector import rising_edge_detector
from ._constant_assigner import constant_assigner
from ._watchdog import watchdog

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    args = {
        'clock': Signal(False),
        'restart': Signal(False),
        'timed_out': Signal(True),
        'clock_frequency': 125e6,
        'timeout_period_seconds': 1e-6,
    }

    arg_types = {
        'clock': 'clock',
        'restart': 'custom',
        'timed_out': 'output',
        'clock_frequency': 'non-signal',
        'timeout_period_seconds': 'non-signal',
    }

    return args, arg_types

class TestWatchdogInterface(KeaTestCase):
    ''' The watchdog block should reject incompatible interfaces and
    arguments.
    '''

    def setUp(self):

        self.args, _arg_types = test_args_setup()

    def test_zero_clock_frequency(self):
        ''' The `watchdog` block should raise an error if the
        `clock_frequency` is 0.
        '''

        self.args['clock_frequency'] = 0

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('watchdog: clock_frequency should be greater than 0'),
            watchdog,
            **self.args,
        )

    def test_negative_clock_frequency(self):
        ''' The `watchdog` block should raise an error if the
        `clock_frequency` is less than 0.
        '''

        self.args['clock_frequency'] = random.randrange(-100, 0)

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('watchdog: clock_frequency should be greater than 0'),
            watchdog,
            **self.args,
        )

    def test_zero_timeout_period_seconds(self):
        ''' The `watchdog` block should raise an error if the
        `timeout_period_seconds` is 0.
        '''

        self.args['timeout_period_seconds'] = 0

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('watchdog: timeout_period_seconds should be greater than 0'),
            watchdog,
            **self.args,
        )

    def test_negative_timeout_period_seconds(self):
        ''' The `watchdog` block should raise an error if the
        `timeout_period_seconds` is less than 0.
        '''

        self.args['timeout_period_seconds'] = random.randrange(-100, 0)

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('watchdog: timeout_period_seconds should be greater than 0'),
            watchdog,
            **self.args,
        )

    def test_timed_out_initialised_low(self):
        ''' The `watchdog` block should raise an error if the
        `timed_out` is initialised low.
        '''

        self.args['timed_out'] = Signal(False)

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('watchdog: timed_out should be initialised high'),
            watchdog,
            **self.args,
        )


class TestWatchdog(KeaTestCase):

    def setUp(self):

        self.args, self.arg_types = test_args_setup()

        self.test_count = 0
        self.tests_run = False

    @block
    def stop_tests(self, clock, n_tests):

        return_objects = []

        @always(clock.posedge)
        def check():

            if self.test_count == n_tests:
                self.tests_run = True
                raise StopSimulation

        return_objects.append(check)
        return return_objects

    @block
    def watchdog_random_stim(self, restart_probability, **kwargs):
        ''' This block randomly drives restart based on restart probability.
        '''

        clock = kwargs['clock']
        restart = kwargs['restart']

        return_objects = []

        @always(clock.posedge)
        def stim():

            restart.next = False

            if random.random() < restart_probability:
                restart.next = True

        return_objects.append(stim)
        return return_objects

    @block
    def watchdog_defined_stim(
        self, restart_low_n_cycles, restart_high_n_cycles, **kwargs):
        ''' This block drives restart in a way defined by
        restart_high_n_cycles and restart_low_n_cycles.
        '''

        clock = kwargs['clock']
        restart = kwargs['restart']

        return_objects = []

        total_period = restart_low_n_cycles + restart_high_n_cycles
        count = Signal(intbv(0, 0, total_period))

        @always(clock.posedge)
        def stim():

            if count == total_period - 1:
                count.next = 0

            else:
                count.next = count + 1

            if count < restart_low_n_cycles:
                restart.next = False

            else:
                restart.next = True

        return_objects.append(stim)
        return return_objects

    @block
    def watchdog_check(self, **kwargs):

        clock = kwargs['clock']
        restart = kwargs['restart']
        timed_out = kwargs['timed_out']
        clock_frequency = kwargs['clock_frequency']
        timeout_period_seconds = kwargs['timeout_period_seconds']

        return_objects = []

        timeout_n_cycles = ceil(clock_frequency*timeout_period_seconds)
        timeout_count = Signal(intbv(timeout_n_cycles, 0, timeout_n_cycles+1))

        reset_count = Signal(False)
        return_objects.append(
            rising_edge_detector(clock, False, restart, reset_count))

        expected_timed_out = Signal(True)

        @always(clock.posedge)
        def check():

            assert(timed_out == expected_timed_out)

            if reset_count:
                timeout_count.next = 0
                expected_timed_out.next = False

                self.test_count += 1

            elif timeout_count < timeout_n_cycles-1:
                timeout_count.next = timeout_count + 1

            else:
                expected_timed_out.next = True

        return_objects.append(check)
        return return_objects

    def test_restart(self):
        ''' The `watchdog` block should monitor the `restart` signal. If the
        period between rising edges on the `restart` signal exceeds the
        `timeout_period_seconds` then the `watchdog` block should set
        `timed_out` high.

        When high, `timed_out` should remain high until the `watchdog`
        receives a rising edge on the `restart` signal, at which point it
        should go low again.

        The `watchdog` block should start up with `timed_out` set high. It
        should remain high until the `watchdog` receives the first rising edge
        on `restart`.
        '''

        if not self.testing_using_vivado:
            cycles = 10000
            n_tests = 30

        else:
            cycles = 4000
            n_tests = 10

        @block
        def stimulate_check(**kwargs):

            clock = kwargs['clock']

            return_objects = []

            restart_probability = 0.01

            return_objects.append(self.stop_tests(clock, n_tests))
            return_objects.append(
                self.watchdog_random_stim(restart_probability, **kwargs))
            return_objects.append(self.watchdog_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, watchdog, watchdog, self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_random_clock_frequency_and_timeout_period(self):
        ''' The `watchdog` block timeout period should be as close as possible
        to `timeout_period_seconds`. The `timed_out` signal can only change on
        a rising edge of the clock so the `clock_frequency` dictates how
        accurate the timeout period can be.

        The `watchdog` should be able to handle any random `clock_frequency`
        and `timeout_period_seconds`.
        '''

        if not self.testing_using_vivado:
            cycles = 10000
            n_tests = 30

        else:
            cycles = 4000
            n_tests = 10

        self.args['clock_frequency'] = 1e6*random.randrange(1, 10)
        self.args['timeout_period_seconds'] = 1e-6*random.randrange(1, 10)

        @block
        def stimulate_check(**kwargs):

            clock = kwargs['clock']
            clock_frequency = kwargs['clock_frequency']
            timeout_period_seconds = kwargs['timeout_period_seconds']

            return_objects = []

            restart_probability = (
                1/(1.5*clock_frequency*timeout_period_seconds))

            return_objects.append(self.stop_tests(clock, n_tests))
            return_objects.append(
                self.watchdog_random_stim(restart_probability, **kwargs))
            return_objects.append(self.watchdog_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, watchdog, watchdog, self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_timeout_period_of_one_cycle(self):
        ''' The `watchdog` block should function correctly if the
        `clock_frequency` and `timeout_period_seconds` combine such that the
        timeout period is a single cycle of the clock.

        Note: Under such circumstances it is impossible to drive restart in a
        way that avoids timeouts. This is because the `watchdog` looks for
        rising edges on `restart` so `restart` has to go low for at least one
        cycle and therefore misses the one cycle timeout.
        '''

        if not self.testing_using_vivado:
            cycles = 10000
            n_tests = 30

        else:
            cycles = 4000
            n_tests = 10

        self.args['clock_frequency'] = 1e6
        self.args['timeout_period_seconds'] = 1e-6

        @block
        def stimulate_check(**kwargs):

            clock = kwargs['clock']

            return_objects = []

            restart_probability = 0.01

            return_objects.append(self.stop_tests(clock, n_tests))
            return_objects.append(
                self.watchdog_random_stim(restart_probability, **kwargs))
            return_objects.append(self.watchdog_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, watchdog, watchdog, self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_large_timeout_period(self):
        ''' The `watchdog` block should function correctly if the
        `clock_frequency` and `timeout_period_seconds` combine such that the
        timeout period in cycles is large.

        We need to check that the `watchdog` functions correctly with a
        timeout period in cycles which is greater than or equal to 2**31 as
        VHDL imposes the following constraint:

            -2**31 <= VHDL constants < 2**31
        '''

        if not self.testing_using_vivado:
            cycles = 10000
            n_tests = 30

        else:
            cycles = 4000
            n_tests = 10

        self.args['clock_frequency'] = 125e6
        self.args['timeout_period_seconds'] = random.randrange(18, 30)

        timeout_period_n_cycles = (
            self.args['clock_frequency']*self.args['timeout_period_seconds'])
        assert(timeout_period_n_cycles >= 2**31)

        @block
        def stimulate_check(**kwargs):

            clock = kwargs['clock']

            return_objects = []

            restart_probability = 0.01

            return_objects.append(self.stop_tests(clock, n_tests))
            return_objects.append(
                self.watchdog_random_stim(restart_probability, **kwargs))
            return_objects.append(self.watchdog_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, watchdog, watchdog, self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_restart_on_timeout_cycle(self):
        ''' It should be possible to send a rising edge on `restart` exactly
        `timeout_period_seconds` apart. In these circumstances, `timed_out`
        should remain low.
        '''

        if not self.testing_using_vivado:
            cycles = 10000
            n_tests = 30

        else:
            cycles = 4000
            n_tests = 10

        @block
        def stimulate_check(**kwargs):

            clock = kwargs['clock']

            return_objects = []

            timeout_period_n_cycles = (
                kwargs['clock_frequency']*kwargs['timeout_period_seconds'])

            restart_low_n_cycles = timeout_period_n_cycles - 1
            restart_high_n_cycles = 1

            return_objects.append(self.stop_tests(clock, n_tests))
            return_objects.append(
                self.watchdog_defined_stim(
                    restart_low_n_cycles, restart_high_n_cycles, **kwargs))
            return_objects.append(self.watchdog_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, watchdog, watchdog, self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_restart_rising_edge_detection(self):
        ''' The `watchdog` should only restart the count on rising edges of
        `restart`. If `restart` is held high then it should not `restart` the
        timer.
        '''

        cycles = 2000

        @block
        def stimulate_check(**kwargs):

            clock = kwargs['clock']
            restart = kwargs['restart']

            return_objects = []

            return_objects.append(constant_assigner(True, restart))
            return_objects.append(self.watchdog_check(**kwargs))

            self.tests_run = True

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, watchdog, watchdog, self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

class TestWatchdogVivadoVhdl(KeaVivadoVHDLTestCase, TestWatchdog):
    pass

class TestWatchdogVivadoVerilog(KeaVivadoVerilogTestCase, TestWatchdog):
    pass
