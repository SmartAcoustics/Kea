import random

from myhdl import block, Signal, always, intbv

from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._vector_not import vector_not

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    clock = Signal(False)
    result = Signal(False)

    bitwidth = random.randrange(1, 256)

    input_signal = Signal(intbv(0)[bitwidth:])
    output = Signal(intbv(0)[bitwidth:])

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

class TestVectorNotInterface(KeaTestCase):

    def setUp(self):

        self.args, _arg_types = test_args_setup()

    def test_mismatched_bitwidth(self):
        ''' The `vector_not` block should raise an error if the `output` and
        `input_signal` are not the same bitwidth.
        '''

        mismatched_bitwidths = random.sample(range(1, 256), 2)

        del self.args['clock']

        self.args['input_signal'] = Signal(intbv(0)[mismatched_bitwidths[0]:])
        self.args['output'] = Signal(intbv(0)[mismatched_bitwidths[1]:])

        self.assertRaisesRegex(
            ValueError,
            'vector_not: output must be the same width as the input',
            vector_not,
            **self.args,
        )

@block
def vector_not_wrapper(clock, output, input_signal):

    return vector_not(output, input_signal)

class TestVectorNot(KeaTestCase):

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
    def check_not(self, clock, output, input_signal):

        return_objects = []

        # Create a random signal driver for the input
        return_objects.append(
            self.random_signal_driver(clock, input_signal))

        bitwidth = len(output)

        @always(clock.posedge)
        def stim_check():

            if bitwidth == 1:
                assert(output != input_signal)

            else:
                assert(output == ~input_signal)

        return_objects.append(stim_check)

        return return_objects

    def test_random_bitwidths(self):
        ''' The `vector_not` block should be able to NOT an input signal of
        any width.
        '''

        cycles = 2000

        @block
        def test(clock, output, input_signal):

            return_objects = []

            return_objects.append(
                self.check_not(clock, output, input_signal))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_not_wrapper, vector_not_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_bitwidth_of_1(self):
        ''' The `vector_not` block should be able to handle `input_signal` and
        `output` which are both a single bit wide.
        '''

        cycles = 2000

        self.args['input_signal'] = Signal(intbv(0)[1:])
        self.args['output'] = Signal(intbv(0)[1:])

        @block
        def test(clock, output, input_signal):

            return_objects = []

            return_objects.append(
                self.check_not(clock, output, input_signal))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_not_wrapper, vector_not_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_boolean(self):
        ''' The `vector_not` block should be able to handle `input_signal` and
        `output` which are both boolean signals.
        '''

        cycles = 2000

        self.args['input_signal'] = Signal(False)
        self.args['output'] = Signal(False)

        @block
        def test(clock, output, input_signal):

            return_objects = []

            return_objects.append(
                self.check_not(clock, output, input_signal))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_not_wrapper, vector_not_wrapper,
            self.args, self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestVectorNotVivadoVhdl(
    KeaVivadoVHDLTestCase, TestVectorNot):
    pass

class TestVectorNotVivadoVerilog(
    KeaVivadoVerilogTestCase, TestVectorNot):
    pass
