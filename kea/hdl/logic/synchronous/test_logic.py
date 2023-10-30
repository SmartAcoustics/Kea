import random

from myhdl import block, Signal, always, StopSimulation

from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from .logic import (
    synchronous_and_gate, synchronous_or_gate, synchronous_not_gate,
    synchronous_nand_gate, synchronous_nor_gate, synchronous_exor_gate,
    synchronous_exnor_gate)

class TestLogicSimulation(KeaTestCase):

    def setUp(self):

        clock = Signal(False)

        signal_in_0 = Signal(False)
        signal_in_1 = Signal(False)
        signal_out = Signal(False)

        self.test_count = 0
        self.tests_complete = False

        self.args = {
            'clock': clock,
            'signal_in_0': signal_in_0,
            'signal_in_1': signal_in_1,
            'signal_out': signal_out,
        }

        self.arg_types = {
            'clock': 'clock',
            'signal_in_0': 'custom',
            'signal_in_1': 'custom',
            'signal_out': 'output',
        }

    @block
    def random_signal_driver(self, clock, signal):
        ''' Randomly drives signal.
        '''

        @always(clock.posedge)
        def stim():

            signal.next = bool(random.randrange(2))

        return stim

    def test_synchronous_and_gate(self):
        ''' The AND gate should always output the AND of the two inputs.
        '''

        cycles = 2000

        if not self.testing_using_vivado:
            min_n_tests = 100

        else:
            min_n_tests = 25

        @block
        def stim_check(clock, signal_in_0, signal_in_1, signal_out):

            return_objects = []

            # Randomly drive signal_in_0 and signal_in_1
            return_objects.append(
                self.random_signal_driver(clock, signal_in_0))
            return_objects.append(
                self.random_signal_driver(clock, signal_in_1))

            expected_signal_out = Signal(False)

            @always(clock.posedge)
            def check():

                # Updated expected_signal_out with dissimilar logic
                expected_signal_out.next = not (
                    not signal_in_0 or not signal_in_1)

                assert(signal_out == expected_signal_out)

                if signal_out:
                    # Count the number of times signal_count is high
                    self.test_count += 1

                if self.test_count >= min_n_tests:
                    # The min number of tests has been exceeded
                    self.tests_complete = True
                    raise StopSimulation

            return_objects.append(check)

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_and_gate, synchronous_and_gate, self.args,
            self.arg_types, custom_sources=[(stim_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)
        self.assertTrue(self.tests_complete)

    def test_synchronous_or_gate(self):
        ''' The OR gate should always output the OR of the two inputs.
        '''

        cycles = 2000

        if not self.testing_using_vivado:
            min_n_tests = 100

        else:
            min_n_tests = 25

        @block
        def stim_check(clock, signal_in_0, signal_in_1, signal_out):

            return_objects = []

            # Randomly drive signal_in_0 and signal_in_1
            return_objects.append(
                self.random_signal_driver(clock, signal_in_0))
            return_objects.append(
                self.random_signal_driver(clock, signal_in_1))

            expected_signal_out = Signal(False)

            @always(clock.posedge)
            def check():

                # Updated expected_signal_out with dissimilar logic
                expected_signal_out.next = not (
                    not signal_in_0 and not signal_in_1)

                assert(signal_out == expected_signal_out)

                if not signal_out:
                    # Count the number of times signal_count is low
                    self.test_count += 1

                if self.test_count >= min_n_tests:
                    # The min number of tests has been exceeded
                    self.tests_complete = True
                    raise StopSimulation

            return_objects.append(check)

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_or_gate, synchronous_or_gate, self.args,
            self.arg_types, custom_sources=[(stim_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)
        self.assertTrue(self.tests_complete)

    def test_synchronous_not_gate(self):
        ''' The NOT gate should always invert the input.
        '''

        cycles = 2000

        if not self.testing_using_vivado:
            min_n_tests = 100

        else:
            min_n_tests = 25

        del self.args['signal_in_0']
        del self.args['signal_in_1']
        del self.arg_types['signal_in_0']
        del self.arg_types['signal_in_1']

        self.args['signal_in'] = Signal(False)
        self.arg_types['signal_in'] = 'custom'

        @block
        def stim_check(clock, signal_in, signal_out):

            return_objects = []

            # Randomly drive signal_in
            return_objects.append(
                self.random_signal_driver(clock, signal_in))

            expected_signal_out = Signal(False)

            @always(clock.posedge)
            def check():

                # Updated expected_signal_out with dissimilar logic
                expected_signal_out.next = not signal_in

                assert(signal_out == expected_signal_out)

                if signal_out:
                    # Count the number of times signal_count is high
                    self.test_count += 1

                if self.test_count >= min_n_tests:
                    # The min number of tests has been exceeded
                    self.tests_complete = True
                    raise StopSimulation

            return_objects.append(check)

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_not_gate, synchronous_not_gate, self.args,
            self.arg_types, custom_sources=[(stim_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)
        self.assertTrue(self.tests_complete)

    def test_synchronous_nand_gate(self):
        ''' The NAND gate should always output the NAND of the two inputs.
        '''

        cycles = 2000

        if not self.testing_using_vivado:
            min_n_tests = 100

        else:
            min_n_tests = 25

        @block
        def stim_check(clock, signal_in_0, signal_in_1, signal_out):

            return_objects = []

            # Randomly drive signal_in_0 and signal_in_1
            return_objects.append(
                self.random_signal_driver(clock, signal_in_0))
            return_objects.append(
                self.random_signal_driver(clock, signal_in_1))

            expected_signal_out = Signal(False)

            @always(clock.posedge)
            def check():

                # Updated expected_signal_out with dissimilar logic
                expected_signal_out.next = not signal_in_0 or not signal_in_1

                assert(signal_out == expected_signal_out)

                if not signal_out:
                    # Count the number of times signal_count is low
                    self.test_count += 1

                if self.test_count >= min_n_tests:
                    # The min number of tests has been exceeded
                    self.tests_complete = True
                    raise StopSimulation

            return_objects.append(check)

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_nand_gate, synchronous_nand_gate, self.args,
            self.arg_types, custom_sources=[(stim_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)
        self.assertTrue(self.tests_complete)

    def test_synchronous_nor_gate(self):
        ''' The NOR gate should always output the NOR of the two inputs.
        '''

        cycles = 2000

        if not self.testing_using_vivado:
            min_n_tests = 100

        else:
            min_n_tests = 25

        @block
        def stim_check(clock, signal_in_0, signal_in_1, signal_out):

            return_objects = []

            # Randomly drive signal_in_0 and signal_in_1
            return_objects.append(
                self.random_signal_driver(clock, signal_in_0))
            return_objects.append(
                self.random_signal_driver(clock, signal_in_1))

            expected_signal_out = Signal(False)

            @always(clock.posedge)
            def check():

                # Updated expected_signal_out with dissimilar logic
                expected_signal_out.next = not signal_in_0 and not signal_in_1

                assert(signal_out == expected_signal_out)

                if signal_out:
                    # Count the number of times signal_count is high
                    self.test_count += 1

                if self.test_count >= min_n_tests:
                    # The min number of tests has been exceeded
                    self.tests_complete = True
                    raise StopSimulation

            return_objects.append(check)

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_nor_gate, synchronous_nor_gate, self.args,
            self.arg_types, custom_sources=[(stim_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)
        self.assertTrue(self.tests_complete)

    def test_synchronous_exor_gate(self):
        ''' The EXOR gate should always output the EXOR of the two inputs.
        '''

        cycles = 2000

        if not self.testing_using_vivado:
            min_n_tests = 100

        else:
            min_n_tests = 25

        @block
        def stim_check(clock, signal_in_0, signal_in_1, signal_out):

            return_objects = []

            # Randomly drive signal_in_0 and signal_in_1
            return_objects.append(
                self.random_signal_driver(clock, signal_in_0))
            return_objects.append(
                self.random_signal_driver(clock, signal_in_1))

            expected_signal_out = Signal(False)

            @always(clock.posedge)
            def check():

                # Updated expected_signal_out with dissimilar logic
                expected_signal_out.next = not (
                    (signal_in_0 and signal_in_1) or
                    (not signal_in_0 and not signal_in_1))

                assert(signal_out == expected_signal_out)

                if signal_out:
                    # Count the number of times signal_count is high
                    self.test_count += 1

                if self.test_count >= min_n_tests:
                    # The min number of tests has been exceeded
                    self.tests_complete = True
                    raise StopSimulation

            return_objects.append(check)

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_exor_gate, synchronous_exor_gate, self.args,
            self.arg_types, custom_sources=[(stim_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)
        self.assertTrue(self.tests_complete)

    def test_synchronous_exnor_gate(self):
        ''' The EXNOR gate should always output the EXNOR of the two inputs.
        '''

        cycles = 2000

        if not self.testing_using_vivado:
            min_n_tests = 100

        else:
            min_n_tests = 25

        @block
        def stim_check(clock, signal_in_0, signal_in_1, signal_out):

            return_objects = []

            # Randomly drive signal_in_0 and signal_in_1
            return_objects.append(
                self.random_signal_driver(clock, signal_in_0))
            return_objects.append(
                self.random_signal_driver(clock, signal_in_1))

            expected_signal_out = Signal(False)

            @always(clock.posedge)
            def check():

                # Updated expected_signal_out with dissimilar logic
                expected_signal_out.next = not (
                    (signal_in_0 and not signal_in_1) or
                    (not signal_in_0 and signal_in_1))

                assert(signal_out == expected_signal_out)

                if signal_out:
                    # Count the number of times signal_count is high
                    self.test_count += 1

                if self.test_count >= min_n_tests:
                    # The min number of tests has been exceeded
                    self.tests_complete = True
                    raise StopSimulation

            return_objects.append(check)

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_exnor_gate, synchronous_exnor_gate, self.args,
            self.arg_types, custom_sources=[(stim_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)
        self.assertTrue(self.tests_complete)

class TestLogicVivadoVhdlSimulation(
    KeaVivadoVHDLTestCase, TestLogicSimulation):
    pass

class TestLogicVivadoVerilogSimulation(
    KeaVivadoVerilogTestCase, TestLogicSimulation):
    pass
