import random

from myhdl import block, Signal, always, intbv

from jackdaw.test_utils.base_test import (
    JackdawTestCase, JackdawVivadoVHDLTestCase, JackdawVivadoVerilogTestCase)

from ._vector_and import vector_and

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    clock = Signal(False)
    result = Signal(False)

    bitwidth = random.randrange(1, 256)

    input_signal = Signal(intbv(0)[bitwidth:])
    output = Signal(False)

    args = {
        'clock': clock,
        'output': output,
        'input_signal': input_signal,
    }

    arg_types = {
        'clock': 'clock',
        'output': 'output',
        'input_signal': 'custom',
    }

    return args, arg_types

class TestVectorAndInterface(JackdawTestCase):

    def setUp(self):

        self.args, _arg_types = test_args_setup()

        del self.args['clock']

    def test_invalid_output(self):
        ''' The `vector_and` block should raise an error if the output is not
        a boolean signal.
        '''

        self.args['output'] = Signal(intbv(0)[5:0])

        self.assertRaisesRegex(
            ValueError,
            'vector_and: output must be a boolean signal',
            vector_and,
            **self.args,
        )

@block
def vector_and_wrapper(clock, output, input_signal):

    return vector_and(output, input_signal)

class TestVectorAnd(JackdawTestCase):

    def setUp(self):

        self.args, self.arg_types = test_args_setup()

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
    def check_and(self, clock, output, input_signal):

        return_objects = []

        # Create a random signal driver for the input
        return_objects.append(
            self.random_signal_driver(clock, input_signal))

        bitwidth = len(input_signal)
        all_true = 2**bitwidth - 1

        @always(clock.posedge)
        def stim_check():

            if input_signal == all_true:
                self.assertTrue(output)

            else:
                self.assertFalse(output)

        return_objects.append(stim_check)

        return return_objects

    def test_random_input_bitwidths(self):
        ''' The `vector_and` block should be able to AND an input signal of
        any width.
        '''

        cycles = 2000

        @block
        def test(clock, output, input_signal):

            return_objects = []

            return_objects.append(
                self.check_and(clock, output, input_signal))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_and_wrapper, vector_and_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_input_bitwidth_of_1(self):
        ''' The `vector_and` block should be able to handle `input_signal`
        which is a single bit wide.
        '''

        cycles = 2000

        self.args['input_signal'] = Signal(intbv(0)[1:])

        @block
        def test(clock, output, input_signal):

            return_objects = []

            return_objects.append(
                self.check_and(clock, output, input_signal))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_and_wrapper, vector_and_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_input_boolean(self):
        ''' The `vector_and` block should be able to handle an `input_signal`
        which is a boolean signals.
        '''

        cycles = 2000

        self.args['input_signal'] = Signal(False)

        @block
        def test(clock, output, input_signal):

            return_objects = []

            return_objects.append(
                self.check_and(clock, output, input_signal))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_and_wrapper, vector_and_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestVectorAndVivadoVhdl(
    JackdawVivadoVHDLTestCase, TestVectorAnd):
    pass

class TestVectorAndVivadoVerilog(
    JackdawVivadoVerilogTestCase, TestVectorAnd):
    pass
