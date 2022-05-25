import random

from myhdl import block, Signal, always, intbv

from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._variable_width_or import variable_width_or

class TestVariableOrInterfaceSimulation(KeaTestCase):

    def setUp(self):
        self.result = Signal(False)

        self.n_source_signals = random.randrange(2, 256)

        self.source_signals = [
            Signal(False) for n in range(self.n_source_signals)]

    def test_no_input_signals(self):
        ''' The `variable_width_or` block should raise an error if the number
        of input signals is less than 1.
        '''

        source_signals = []

        self.assertRaisesRegex(
            ValueError,
            'input_signals must contain at least one signal',
            variable_width_or,
            self.result,
            source_signals,
        )

    def test_invalid_output(self):
        ''' The `variable_width_or` block should raise an error if the output
        is not a boolean signal.
        '''

        invalid_output = Signal(intbv(0)[5:0])

        self.assertRaisesRegex(
            ValueError,
            'output must be a boolean signal',
            variable_width_or,
            invalid_output,
            self.source_signals,
        )

    def test_invalid_input(self):
        ''' The `variable_width_or` block should raise an error if any of the
        input signals are not boolean signals.
        '''

        invalid_input_signals = [
            Signal(False) for n in range(self.n_source_signals)]

        invalid_index = random.randrange(len(invalid_input_signals))

        invalid_input_signals[invalid_index] = Signal(intbv(0)[5:0])

        self.assertRaisesRegex(
            ValueError,
            'All input_signals must be boolean signals',
            variable_width_or,
            self.result,
            invalid_input_signals,
        )

@block
def variable_width_or_wrapper(clock, output, input_signals):

    return variable_width_or(output, input_signals)

class TestVariableOrSimulation(KeaTestCase):

    def setUp(self):
        self.clock = Signal(False)
        self.result = Signal(False)

        self.n_source_signals = random.randrange(2, 256)

        self.source_signals = [
            Signal(False) for n in range(self.n_source_signals)]

        self.args = {
            'clock': self.clock,
            'output': self.result,
            'input_signals': self.source_signals,
        }

        self.arg_types = {
            'clock': 'clock',
            'output': 'output',
            'input_signals': 'custom',
        }

    @block
    def random_signal_driver(self, clock, reset, sig_to_drive):

        @always(clock.posedge)
        def driver():

            if random.random() < 0.01:
                # Randomly set the signal true
                sig_to_drive.next = True

            else:
                sig_to_drive.next = False

            if reset:
                sig_to_drive.next = False

        return driver

    @block
    def check_or(self, clock, output, input_signals):

        return_objects = []

        reset = Signal(False)

        for sig in input_signals:
            # Create a random signal driver for each input
            return_objects.append(
                self.random_signal_driver(clock, reset, sig))

        @always(clock.posedge)
        def stim_check():

            if reset:
                # Pulse reset
                reset.next = False

            if random.random() < 0.05:
                # Randomly sent a reset to have times when all input signals
                # are low
                reset.next = True

            if any(input_signals):
                # When any of the inputs are high the output should be high
                self.assertTrue(output)

            else:
                # When any inputs are low the output should be low
                self.assertFalse(output)

        return_objects.append(stim_check)

        return return_objects

    def test_random_n_source_signals(self):
        ''' The `variable_width_or` block should be able to OR a random
        number of input signals.
        '''

        cycles = 2000

        @block
        def test(clock, output, input_signals):

            return_objects = []

            return_objects.append(
                self.check_or(clock, output, input_signals))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, variable_width_or_wrapper, variable_width_or_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_two_source_signals(self):
        ''' The `variable_width_or` block should be able to handle 2 input
        signals
        '''

        cycles = 4000

        source_signals = [Signal(False) for n in range(2)]

        self.args['input_signals'] = source_signals

        @block
        def test(clock, output, input_signals):

            return_objects = []

            return_objects.append(
                self.check_or(clock, output, input_signals))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, variable_width_or_wrapper, variable_width_or_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_one_source_signals(self):
        ''' The `variable_width_or` block should be able to handle 1 input
        signal
        '''

        cycles = 4000

        source_signals = [Signal(False)]

        self.args['input_signals'] = source_signals

        @block
        def test(clock, output, input_signals):

            return_objects = []

            return_objects.append(
                self.check_or(clock, output, input_signals))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, variable_width_or_wrapper, variable_width_or_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestVariableOrVivadoVhdlSimulation(
    KeaVivadoVHDLTestCase, TestVariableOrSimulation):
    pass

class TestVariableOrVivadoVerilogSimulation(
    KeaVivadoVerilogTestCase, TestVariableOrSimulation):
    pass
