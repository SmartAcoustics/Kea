import random

from myhdl import block, Signal, always, intbv

from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._vector_or import vector_or

@block
def vector_or_wrapper(clock, output, input_signals):

    return vector_or(output, input_signals)

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    clock = Signal(False)

    bitwidth = 8
    n_input_signals = 8

    output = Signal(intbv(0)[bitwidth:])
    input_signals = [
        Signal(intbv(0)[bitwidth:]) for n in range(n_input_signals)]

    args = {
        'clock': clock,
        'output': output,
        'input_signals': input_signals,
    }

    arg_types = {
        'clock': 'clock',
        'output': 'output',
        'input_signals': 'custom',
    }

    return args, arg_types

class TestVectorOrInterface(KeaTestCase):

    def setUp(self):

        self.args, _arg_types = test_args_setup()

    def test_zero_input_signals(self):
        ''' The `vector_or` should raise an error if the `input_signals` list
        is empty.
        '''

        # Overwrite the chosen signal with an empty list
        self.args['input_signals'] = []

        self.assertRaisesRegex(
            ValueError,
            ('vector_or: There should be at least one input signal.'),
            vector_or_wrapper,
            **self.args
        )

    def test_invalid_input_signal_bitwidth(self):
        ''' The `vector_or` should raise an error if any signal in the
        `input_signals` list is not the same bitwidth as the others.
        '''
        # Pick a random input signal to set to an invalid bitwidth
        index = random.choice(range(len(self.args['input_signals'])))

        # Pick a random invalid bitwidth
        valid_bitwidth = len(self.args['input_signals'][0])
        invalid_bitwidths = [n for n in range(1, 32) if n != valid_bitwidth]
        invalid_bitwidth = random.choice(invalid_bitwidths)

        # Overwrite the chosen signal with an invalid bitwidth
        self.args['input_signals'][index] = (
            Signal(intbv(0)[invalid_bitwidth:]))

        self.assertRaisesRegex(
            TypeError,
            ('vector_or: All input signals should be the same bitwidth.'),
            vector_or_wrapper,
            **self.args
        )

    def test_boolean_input_signal(self):
        ''' The `vector_or` should raise an error if any signal in the
        `input_signals` list is a boolean.
        '''

        # Overwrite the input and output signals with 1 bit wide signals
        n_input_signals = 8
        self.args['input_signals'] = [
            Signal(intbv(0)[1:]) for n in range(n_input_signals)]
        self.args['output'] = Signal(intbv(0)[1:])

        # Pick a random input signal to set to an invalid bitwidth
        index = random.choice(range(len(self.args['input_signals'])))

        # Overwrite the chosen signal with a boolean
        self.args['input_signals'][index] = Signal(False)

        self.assertRaisesRegex(
            TypeError,
            ('vector_or: All input signals should be an intbv.'),
            vector_or_wrapper,
            **self.args
        )

    def test_invalid_output_signal_bitwidth(self):
        ''' The `vector_or` should raise an error if the `output` is not the
        same bitwidth as the signals in the `input_signals` list.
        '''

        # Pick a random invalid bitwidth
        valid_bitwidth = len(self.args['output'])
        invalid_bitwidths = [n for n in range(1, 32) if n != valid_bitwidth]
        invalid_bitwidth = random.choice(invalid_bitwidths)

        # Overwrite the output with an invalid bitwidth
        self.args['output'] = Signal(intbv(0)[invalid_bitwidth:])

        self.assertRaisesRegex(
            TypeError,
            ('vector_or: The output signal should be the same bitwidth as '
             'the input signals.'),
            vector_or_wrapper,
            **self.args
        )

    def test_boolean_output(self):
        ''' The `vector_or` should raise an error if the `output` is a
        boolean.
        '''

        # Overwrite the input signals with 1 bit wide signals
        n_input_signals = 8
        self.args['input_signals'] = [
            Signal(intbv(0)[1:]) for n in range(n_input_signals)]

        # Overwrite the output with a bool
        self.args['output'] = Signal(False)

        self.assertRaisesRegex(
            TypeError,
            ('vector_or: The output signal should be an intbv.'),
            vector_or_wrapper,
            **self.args
        )

class TestVectorOr(KeaTestCase):

    def setUp(self):

        self.args, self.arg_types = test_args_setup()

    @block
    def random_signal_driver(self, clock, reset, sig_to_drive):

        return_objects = []

        bitwidth = len(sig_to_drive)
        val_upper_bound = 2**bitwidth

        @always(clock.posedge)
        def driver():

            random_val = random.random()

            if random_val < 0.1:
                sig_to_drive.next = 0

            elif random_val < 0.15:
                sig_to_drive.next = random.randrange(val_upper_bound)

            else:
                sig_to_drive.next = 1 << random.randrange(bitwidth)

            if reset:
                sig_to_drive.next = 0

        return_objects.append(driver)

        return return_objects

    @block
    def check_or(self, **kwargs):

        clock = kwargs['clock']
        output = kwargs['output']
        input_signals = kwargs['input_signals']

        return_objects = []

        n_input_signals = len(input_signals)

        stim_reset = Signal(False)

        for input_sig in input_signals:
            # Create a block to drive all of the input signals
            return_objects.append(
                self.random_signal_driver(clock, stim_reset, input_sig))

        @always(clock.posedge)
        def check():

            # Pulse stim_reset
            stim_reset.next = False

            if random.random() < 0.05:
                # Randomly send a stim reset so that there are times when all
                # input signals are 0
                stim_reset.next = True

            expected_output = int(input_signals[0].val)
            for n in range(1, n_input_signals):
                expected_output |= int(input_signals[n].val)

            assert(output == expected_output)

        return_objects.append(check)

        return return_objects

    def test_vector_or(self):
        ''' The `vector_or` block should perform a bitwise OR of all the
        signals in the `input_signals` list and output the result on the
        `output` signal.
        '''

        cycles = 2000

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(self.check_or(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_or_wrapper, vector_or_wrapper, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_random_inputs(self):
        ''' The `vector_or` block should function correctly for any number of
        signals in the `input_signals` list.

        The `vector_or` block should function correctly for any bitwidths of
        input and output signals (as long as the inputs and output have the
        same bitwidth).
        '''

        cycles = 2000

        n_input_signals = random.randrange(2, 10)
        bitwidth = random.randrange(2, 17)

        self.args['input_signals'] = [
            Signal(intbv(0)[bitwidth:]) for n in range(n_input_signals)]
        self.args['output'] = Signal(intbv(0)[bitwidth:])

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(self.check_or(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_or_wrapper, vector_or_wrapper, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_random_n_one_bit_inputs(self):
        ''' The `vector_or` block should function correctly for any number of
        signals of one bit signals in the `input_signals` list. In this case
        it should act like a reducing or.
        '''

        cycles = 2000

        n_input_signals = random.randrange(2, 10)
        bitwidth = 1

        self.args['input_signals'] = [
            Signal(intbv(0)[bitwidth:]) for n in range(n_input_signals)]
        self.args['output'] = Signal(intbv(0)[bitwidth:])

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(self.check_or(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_or_wrapper, vector_or_wrapper, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_one_input_random_bitwidth(self):
        ''' The `vector_or` block should function correctly when there is a
        single signal in the `input_signals` list. In this case it should just
        pass the signal through.
        '''

        cycles = 2000

        n_input_signals = 1
        bitwidth = random.randrange(1, 17)

        self.args['input_signals'] = [
            Signal(intbv(0)[bitwidth:]) for n in range(n_input_signals)]
        self.args['output'] = Signal(intbv(0)[bitwidth:])

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(self.check_or(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_or_wrapper, vector_or_wrapper, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_one_input_bitwidth_one(self):
        ''' The `vector_or` block should function correctly when there is a
        single signal of bitwidth 1 in the `input_signals` list. In this case
        it should just pass the signal through.
        '''

        cycles = 2000

        n_input_signals = 1
        bitwidth = 1

        self.args['input_signals'] = [
            Signal(intbv(0)[bitwidth:]) for n in range(n_input_signals)]
        self.args['output'] = Signal(intbv(0)[bitwidth:])

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(self.check_or(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, vector_or_wrapper, vector_or_wrapper, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestVectorOrVivadoVhdl(KeaVivadoVHDLTestCase, TestVectorOr):
    pass

class TestVectorOrVivadoVerilog(KeaVivadoVerilogTestCase, TestVectorOr):
    pass
