import random

from myhdl import block, Signal, always, intbv

from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._variable_width_and import variable_width_and

class TestVariableAndInterfaceSimulation(KeaTestCase):

    def setUp(self):
        self.result = Signal(False)

        self.n_source_signals = random.randrange(2, 256)

        self.source_signals = [
            Signal(False) for n in range(self.n_source_signals)]

    def test_no_input_signals(self):
        ''' The `variable_width_and` block should raise an error if the number
        of input signals is less than 1.
        '''

        source_signals = []

        self.assertRaisesRegex(
            ValueError,
            'input_signals must contain at least one signal',
            variable_width_and,
            self.result,
            source_signals,
        )

    def test_invalid_output(self):
        ''' The `variable_width_and` block should raise an error if the output
        is not a boolean signal.
        '''

        invalid_output = Signal(intbv(0)[5:0])

        self.assertRaisesRegex(
            ValueError,
            'output must be a boolean signal',
            variable_width_and,
            invalid_output,
            self.source_signals,
        )

    def test_invalid_input(self):
        ''' The `variable_width_and` block should raise an error if any of the
        input signals are not boolean signals.
        '''

        invalid_input_signals = [
            Signal(False) for n in range(self.n_source_signals)]

        invalid_index = random.randrange(len(invalid_input_signals))

        invalid_input_signals[invalid_index] = Signal(intbv(0)[5:0])

        self.assertRaisesRegex(
            ValueError,
            'All input_signals must be boolean signals',
            variable_width_and,
            self.result,
            invalid_input_signals,
        )

@block
def variable_width_and_wrapper(clock, output, input_signals):

    return variable_width_and(output, input_signals)

class TestVariableAndSimulation(KeaTestCase):

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

            if not sig_to_drive:
                if random.random() < 0.05:
                    # Randomly set the signal true
                    sig_to_drive.next = True

            if reset:
                sig_to_drive.next = False

        return driver

    @block
    def check_and(self, clock, output, input_signals):

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

            if all(input_signals):
                # When all the inputs are high the output should be high
                self.assertTrue(output)

                if random.random() < 0.05:
                    # Leave all signals high for a random period before
                    # setting them low with a reset
                    reset.next = True

            else:
                # When any inputs are low the output should be low
                self.assertFalse(output)

        return_objects.append(stim_check)

        return return_objects

    def test_random_n_source_signals(self):
        ''' The `variable_width_and` block should be able to AND a random
        number of input signals.
        '''

        cycles = 2000

        @block
        def test(clock, output, input_signals):

            return_objects = []

            return_objects.append(
                self.check_and(clock, output, input_signals))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, variable_width_and_wrapper, variable_width_and_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_large_n_signals(self):
        ''' The `variable_width_and` block should be able to handle 961 input
        signals
        '''

        if not self.testing_using_vivado:
            cycles = 500
            n_source_signals = random.randrange(900, 1000)
            source_signals = [Signal(False) for n in range(n_source_signals)]
        else:
            # To save simulation time
            cycles = 500
            n_source_signals = random.randrange(200, 300)
            source_signals = [Signal(False) for n in range(256)]

        self.args['input_signals'] = source_signals

        @block
        def test(clock, output, input_signals):

            return_objects = []

            return_objects.append(
                self.check_and(clock, output, input_signals))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, variable_width_and_wrapper, variable_width_and_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_two_source_signals(self):
        ''' The `variable_width_and` block should be able to handle 2 input
        signals
        '''

        cycles = 4000

        source_signals = [Signal(False) for n in range(2)]

        self.args['input_signals'] = source_signals

        @block
        def test(clock, output, input_signals):

            return_objects = []

            return_objects.append(
                self.check_and(clock, output, input_signals))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, variable_width_and_wrapper, variable_width_and_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_one_source_signals(self):
        ''' The `variable_width_and` block should be able to handle 1 input
        signal
        '''

        cycles = 4000

        source_signals = [Signal(False)]

        self.args['input_signals'] = source_signals

        @block
        def test(clock, output, input_signals):

            return_objects = []

            return_objects.append(
                self.check_and(clock, output, input_signals))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, variable_width_and_wrapper, variable_width_and_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_small_n_source_signals(self):
        ''' The `variable_width_and` block should be able to handle a small
        number of input signals
        '''

        cycles = 4000

        n_source_signals = random.randrange(3, 33)
        source_signals = [Signal(False) for n in range(n_source_signals)]

        self.args['input_signals'] = source_signals

        @block
        def test(clock, output, input_signals):

            return_objects = []

            return_objects.append(
                self.check_and(clock, output, input_signals))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, variable_width_and_wrapper, variable_width_and_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestVariableAndVivadoVhdlSimulation(
    KeaVivadoVHDLTestCase, TestVariableAndSimulation):
    pass

class TestVariableAndVivadoVerilogSimulation(
    KeaVivadoVerilogTestCase, TestVariableAndSimulation):
    pass
