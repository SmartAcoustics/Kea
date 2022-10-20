import random

from myhdl import block, Signal, always, intbv

from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._vector_xor import vector_xor

@block
def vector_xor_wrapper(clock, output, input_0, input_1):

    return vector_xor(output, input_0, input_1)

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    clock = Signal(False)

    bitwidth = 8

    output = Signal(intbv(0)[bitwidth:])
    input_0 = Signal(intbv(0)[bitwidth:])
    input_1 = Signal(intbv(0)[bitwidth:])

    args = {
        'clock': clock,
        'output': output,
        'input_0': input_0,
        'input_1': input_1,
    }

    arg_types = {
        'clock': 'clock',
        'output': 'output',
        'input_0': 'custom',
        'input_1': 'custom',
    }

    return args, arg_types

class TestVectorXORInterface(KeaTestCase):

    def setUp(self):

        self.args, _arg_types = test_args_setup()

    def test_invalid_input_0_type(self):
        ''' The `vector_xor` should raise an error if `input_0` is not an
        intbv.
        '''

        self.args['input_0'] = Signal(False)

        self.assertRaisesRegex(
            TypeError,
            ('vector_xor: The input_0 signal should be an intbv.'),
            vector_xor_wrapper,
            **self.args
        )

    def test_invalid_input_1_type(self):
        ''' The `vector_xor` should raise an error if `input_1` is not an
        intbv.
        '''

        self.args['input_1'] = Signal(False)

        self.assertRaisesRegex(
            TypeError,
            ('vector_xor: The input_1 signal should be an intbv.'),
            vector_xor_wrapper,
            **self.args
        )

    def test_invalid_output_type(self):
        ''' The `vector_xor` should raise an error if `output` is not an
        intbv.
        '''

        self.args['output'] = Signal(False)

        self.assertRaisesRegex(
            TypeError,
            ('vector_xor: The output signal should be an intbv.'),
            vector_xor_wrapper,
            **self.args
        )

    def test_mismatched_input_bitwidths(self):
        ''' The `vector_xor` should raise an error if `input_0` is not the
        same width as `input_1`.
        '''

        bitwidths = random.sample([n for n in range(1, 17)], 2)

        self.args['input_0'] = Signal(intbv(0)[bitwidths[0]:])
        self.args['input_1'] = Signal(intbv(0)[bitwidths[1]:])

        self.assertRaisesRegex(
            ValueError,
            ('vector_xor: Both inputs should be the same width'),
            vector_xor_wrapper,
            **self.args
        )

    def test_mismatched_input_and_output_bitwidths(self):
        ''' The `vector_xor` should raise an error if the `output` is not the
        same width as the inputs.
        '''

        bitwidths = random.sample([n for n in range(1, 17)], 2)

        self.args['input_0'] = Signal(intbv(0)[bitwidths[0]:])
        self.args['input_1'] = Signal(intbv(0)[bitwidths[0]:])

        self.args['output'] = Signal(intbv(0)[bitwidths[1]:])

        self.assertRaisesRegex(
            ValueError,
            ('vector_xor: The output should be the same width as the inputs'),
            vector_xor_wrapper,
            **self.args
        )

class TestVectorXOR(KeaTestCase):

    def setUp(self):

        self.args, self.arg_types = test_args_setup()

    @block
    def random_signal_driver(self, clock, signal_0, signal_1):

        return_objects = []

        assert(len(signal_0) == len(signal_1))

        bitwidth = len(signal_0)
        val_upper_bound = 2**bitwidth
        max_val = val_upper_bound-1

        @always(clock.posedge)
        def driver():

            # Generate random stim values for the two inputs
            stim_values = (
                random.sample([n for n in range(val_upper_bound)], 2))

            random_val = random.random()

            if random_val < 0.1:
                # Set one stim value to 0
                stim_values[random.randrange(2)] = 0

            elif random_val < 0.2:
                # Set one stim value to all 1
                stim_values[random.randrange(2)] = max_val

            elif random_val < 0.3:
                # Set both inputs to the same value
                stim_values[0] = stim_values[1]

            signal_0.next = stim_values[0]
            signal_1.next = stim_values[1]

        return_objects.append(driver)

        return return_objects

    @block
    def check_xor(self, **kwargs):

        clock = kwargs['clock']
        output = kwargs['output']
        input_0 = kwargs['input_0']
        input_1 = kwargs['input_1']

        return_objects = []

        return_objects.append(
            self.random_signal_driver(clock, input_0, input_1))

        @always(clock.posedge)
        def check():

            # Check the output is correct
            expected_output = (input_0 & ~input_1) | (~input_0 & input_1)
            assert(output == expected_output)

        return_objects.append(check)

        return return_objects

    def test_vector_xor(self):
        ''' The `vector_xor` block should perform a bitwise XOR of `input_0`
        and 'input_1' and output the result on the `output` signal.
        '''

        cycles = 2000

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(self.check_xor(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_xor_wrapper, vector_xor_wrapper, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_random_bitwidth(self):
        ''' The `vector_xor` block should function correctly for any bitwidth
        of inputs and output.
        '''

        cycles = 2000

        bitwidth = random.randrange(2, 17)
        self.args['input_0'] = Signal(intbv(0)[bitwidth:])
        self.args['input_1'] = Signal(intbv(0)[bitwidth:])
        self.args['output'] = Signal(intbv(0)[bitwidth:])

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(self.check_xor(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_xor_wrapper, vector_xor_wrapper, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_bitwidth_of_one(self):
        ''' The `vector_xor` block should function correctly when the inputs
        and output are 1 bit wide.
        '''

        cycles = 2000

        bitwidth = 1
        self.args['input_0'] = Signal(intbv(0)[bitwidth:])
        self.args['input_1'] = Signal(intbv(0)[bitwidth:])
        self.args['output'] = Signal(intbv(0)[bitwidth:])

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(self.check_xor(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_xor_wrapper, vector_xor_wrapper, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestVectorXORVivadoVhdl(KeaVivadoVHDLTestCase, TestVectorXOR):
    pass

class TestVectorXORVivadoVerilog(KeaVivadoVerilogTestCase, TestVectorXOR):
    pass
