from ._pulse_generator import pulse_generator

from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

import random

from myhdl import *

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    clock = Signal(False)
    reset = Signal(False)
    trigger = Signal(False)
    elongated_pulse_output = Signal(False)
    pulse_n_cycles = 10
    buffer_output = False

    args = {
        'clock': clock,
        'reset': reset,
        'trigger': trigger,
        'output': elongated_pulse_output,
        'pulse_n_cycles': pulse_n_cycles,
    }

    arg_types = {
        'clock': 'clock',
        'reset': 'custom',
        'trigger': 'custom',
        'output': 'output',
        'pulse_n_cycles': 'non-signal',
    }

    return args, arg_types

class TestPulseGeneratorInterface(KeaTestCase):
    ''' The block should reject incompatible interfaces.
    '''

    def setUp(self):

        self.args, _arg_types = test_args_setup()

    def test_zero_pulse_n_cycles(self):
        ''' The system should raise a ValueError if the
        ``pulse_n_cycles`` is zero.
        '''

        self.args['pulse_n_cycles'] = 0

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            'pulse_generator: pulse_n_cycles must be greater than zero.',
            pulse_generator,
            **self.args,
        )

    def test_negative_pulse_n_cycles(self):
        ''' The system should raise a ValueError if the
        ``pulse_n_cycles`` negative.
        '''

        self.args['pulse_n_cycles'] = random.randrange(-10, 0)

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            'pulse_generator: pulse_n_cycles must be greater than zero.',
            pulse_generator,
            **self.args,
        )

class TestPulseGenerator(KeaTestCase):

    def setUp(self):

        self.args, self.arg_types = test_args_setup()

    @block
    def stimulus(self, clock, reset, trigger):
        ''' This block will randomly drive the reset and trigger signals.
        '''

        return_objects = []

        @always(clock.posedge)
        def stim():

            # Randomly drive the reset signal
            if not reset:
                if random.random() < 0.05:
                    reset.next = True

            else:
                if random.random() < 0.2:
                    reset.next = False

            # Drive the trigger signal with pulses of random lengths
            if not trigger:
                if random.random() < 0.05:
                    trigger.next = True

            else:
                if random.random() < 0.2:
                    trigger.next = False

        return_objects.append(stim)

        return return_objects

    @block
    def pulse_generator_check(self, **kwargs):

        clock = kwargs['clock']
        reset = kwargs['reset']
        trigger = kwargs['trigger']
        output = kwargs['output']
        pulse_n_cycles = kwargs['pulse_n_cycles']

        return_objects = []

        return_objects.append(self.stimulus(clock, reset, trigger))

        pulse_period_count = Signal(intbv(0, 0, pulse_n_cycles+1))
        expected_output = Signal(False)

        @always(clock.posedge)
        def check():

            assert(output == expected_output)

            if trigger and not expected_output:
                expected_output.next = True
                pulse_period_count.next = 1

            if expected_output:
                if pulse_period_count == pulse_n_cycles:
                    pulse_period_count.next = 0
                    expected_output.next = False

                else:
                    pulse_period_count.next = pulse_period_count + 1

            if reset:
                pulse_period_count.next = 0
                expected_output.next = False

        return_objects.append(check)

        return return_objects

    def test_pulse_output(self):
        ''' When trigger is set high the system should output a pulse of
        length ``self.pulse_n_cycles``. Any subsequent high values on the
        trigger input should be ignored until ``self.pulse_n_cycles`` has
        lapsed and the output has returned low. The output should always go
        low in between pulses.

        This block should set the output low and ignore any trigger pulses
        while reset is high.
        '''

        cycles = 1000

        max_pulse_length = 16
        self.args['pulse_n_cycles'] = random.randrange(1, max_pulse_length+1)

        @block
        def stimulate_and_check(**kwargs):

            return_objects = []

            return_objects.append(self.pulse_generator_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, pulse_generator, pulse_generator,
            self.args, self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestPulseGeneratorVivadoVhdl(
    KeaVivadoVHDLTestCase, TestPulseGenerator):
    pass

class TestPulseGeneratorVivadoVerilog(
    KeaVivadoVerilogTestCase, TestPulseGenerator):
    pass
