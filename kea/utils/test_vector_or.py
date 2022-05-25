import random

from myhdl import block, Signal, always, intbv

from jackdaw.test_utils.base_test import (
    JackdawTestCase, JackdawVivadoVHDLTestCase, JackdawVivadoVerilogTestCase)

from ._vector_or import vector_or

class TestVectorOrInterfaceSimulation(JackdawTestCase):

    def setUp(self):
        self.result = Signal(False)

        self.source_signal_bitwidth = random.randrange(1, 256)

        self.source_signal = Signal(intbv(0)[self.source_signal_bitwidth:])

    def test_invalid_output(self):
        ''' The `vector_or` block should raise an error if the output is not a
        boolean signal.
        '''

        invalid_output = Signal(intbv(0)[5:0])

        self.assertRaisesRegex(
            ValueError,
            'output must be a boolean signal',
            vector_or,
            invalid_output,
            self.source_signal
        )

@block
def vector_or_wrapper(clock, output, input_signal):

    return vector_or(output, input_signal)

class TestVectorOrSimulation(JackdawTestCase):

    def setUp(self):
        self.clock = Signal(False)
        self.result = Signal(False)

        self.source_signal_bitwidth = random.randrange(1, 256)

        self.source_signal = Signal(intbv(0)[self.source_signal_bitwidth:])

        self.args = {
            'clock': self.clock,
            'output': self.result,
            'input_signal': self.source_signal,
        }

        self.arg_types = {
            'clock': 'clock',
            'output': 'output',
            'input_signal': 'custom',
        }

    @block
    def random_signal_driver(self, clock, sig_to_drive):

        @always(clock.posedge)
        def driver():

            random_val = random.random()

            if random_val < 0.3:
                # 30% of the time set to 0
                sig_to_drive.next = 0

            elif random_val < 0.5:
                # 20% of the time set a single bit
                shift = random.randrange(len(sig_to_drive))
                sig_to_drive.next = 1 << shift

            elif random_val < 0.7:
                # 20% of the time set all bits
                sig_to_drive.next = 2**len(sig_to_drive) - 1

            else:
                # 30% of the time set a random number
                sig_to_drive.next = random.randrange(2**len(sig_to_drive))

        return driver

    @block
    def check_or(self, clock, output, input_signal):

        return_objects = []

        # Create a random signal driver for the input
        return_objects.append(
            self.random_signal_driver(clock, input_signal))

        @always(clock.posedge)
        def stim_check():

            if input_signal != 0:
                # When the input is greater than 0 are high the output should
                # be high
                self.assertTrue(output)

            else:
                # When input is 0 the output should be low
                self.assertFalse(output)

        return_objects.append(stim_check)

        return return_objects

    def test_random_width_input_signal(self):
        ''' The `vector_or` block should be able to OR an input signal of any
        width.
        '''

        cycles = 2000

        @block
        def test(clock, output, input_signal):

            return_objects = []

            return_objects.append(
                self.check_or(clock, output, input_signal))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_or_wrapper, vector_or_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_one_bit_input_signal(self):
        ''' The `vector_or` block should be able to handle an input signal
        which is a single bit wide.
        '''

        cycles = 2000

        self.args['input_signal'] = Signal(intbv(0)[1:])

        @block
        def test(clock, output, input_signal):

            return_objects = []

            return_objects.append(
                self.check_or(clock, output, input_signal))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_or_wrapper, vector_or_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_boolean_input_signal(self):
        ''' The `vector_or` block should be able to handle an input signal
        which is a boolean signal.
        '''

        cycles = 2000

        self.args['input_signal'] = Signal(False)

        @block
        def test(clock, output, input_signal):

            return_objects = []

            return_objects.append(
                self.check_or(clock, output, input_signal))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_or_wrapper, vector_or_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestVectorOrVivadoVhdlSimulation(
    JackdawVivadoVHDLTestCase, TestVectorOrSimulation):
    pass

class TestVectorOrVivadoVerilogSimulation(
    JackdawVivadoVerilogTestCase, TestVectorOrSimulation):
    pass
