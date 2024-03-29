import random

from myhdl import Signal, intbv, block, always

from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)
from kea.hdl.logic.asynchronous import vector_xor, reducing_or

from ._equality_detector import equality_detector

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    bitwidth = 8

    clock = Signal(False)
    enable = Signal(False)
    equal = Signal(False)
    input_0 = Signal(intbv(0)[bitwidth:])
    input_1 = Signal(intbv(0)[bitwidth:])

    args = {
        'clock': clock,
        'enable': enable,
        'equal': equal,
        'input_0': input_0,
        'input_1': input_1,
    }

    arg_types = {
        'clock': 'clock',
        'enable': 'custom',
        'equal': 'output',
        'input_0': 'custom',
        'input_1': 'custom',
    }

    return args, arg_types

class TestEqualityDetectorInterface(KeaTestCase):

    def setUp(self):

        self.args, _arg_types = test_args_setup()

    def test_invalid_output_type(self):
        ''' The `equality_detector` should raise an error if `output` is not a
        bool.
        '''

        self.args['equal'] = Signal(intbv(0)[random.randrange(1, 8):])

        self.assertRaisesRegex(
            TypeError,
            ('equality_detector: The equal signal should be a bool'),
            equality_detector,
            **self.args
        )

    def test_mismatched_input_bitwidths(self):
        ''' The `equality_detector` should raise an error if `input_0` is not
        the same width as `input_1`.
        '''

        bitwidths = random.sample([n for n in range(1, 17)], 2)

        self.args['input_0'] = Signal(intbv(0)[bitwidths[0]:])
        self.args['input_1'] = Signal(intbv(0)[bitwidths[1]:])

        self.assertRaisesRegex(
            ValueError,
            ('equality_detector: Both inputs should be the same width'),
            equality_detector,
            **self.args
        )

class TestEqualityDetector(KeaTestCase):

    def setUp(self):

        self.args, self.arg_types = test_args_setup()

    @block
    def stim(self, clock, enable, input_0, input_1):

        return_objects = []

        assert(len(input_0) == len(input_1))

        bitwidth = len(input_0)
        val_upper_bound = 2**bitwidth
        max_val = val_upper_bound-1

        @always(clock.posedge)
        def driver():

            if not enable:
                if random.random() < 0.1:
                    enable.next = True
            else:
                if random.random() < 0.05:
                    enable.next = False

            # Generate random stim values for the two inputs
            stim_values = (
                random.sample([n for n in range(val_upper_bound)], 2))

            random_val = random.random()

            if random_val < 0.05:
                # Set both input signals to be 0
                stim_values[0] = 0
                stim_values[1] = 0

            elif random_val < 0.1:
                # Set both input signals to max_val
                stim_values[0] = max_val
                stim_values[1] = max_val

            elif random_val < 0.5:
                # Set both inputs to the same value
                stim_values[0] = stim_values[1]

            elif random_val < 0.55:
                # Set one stim value to 0
                stim_values[random.randrange(2)] = 0

            elif random_val < 0.6:
                # Set one stim value to max_val
                stim_values[random.randrange(2)] = max_val

            input_0.next = stim_values[0]
            input_1.next = stim_values[1]

        return_objects.append(driver)

        return return_objects


    @block
    def check_equality_detector(self, **kwargs):

        clock = kwargs['clock']
        enable = kwargs['enable']
        equal = kwargs['equal']
        input_0 = kwargs['input_0']
        input_1 = kwargs['input_1']

        return_objects = []

        return_objects.append(
            self.stim(clock, enable, input_0, input_1))

        # XOR the two inputs
        assert(len(input_0) == len(input_1))
        xor_result = Signal(intbv(0)[len(input_0):])
        return_objects.append(vector_xor(xor_result, input_0, input_1))

        # reducing OR the XOR result
        or_result = Signal(False)
        return_objects.append(reducing_or(or_result, xor_result))

        expected_equal = Signal(False)

        @always(clock.posedge)
        def check():

            assert(equal == expected_equal)

            if enable:
                expected_equal.next = not or_result

            else:
                expected_equal.next = False

        return_objects.append(check)

        return return_objects

    def test_equality_detector(self):
        ''' When `enable` is high the `equality_detector` should set `equal`
        high when `input_0` and 'input_1' are equal. If they are not equal
        then the `equality_detector` should set `equal` low.

        When `enable` is low the `equality_detector` should set `equal` low.
        '''

        cycles = 4000

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(self.check_equality_detector(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, equality_detector, equality_detector, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_random_bitwidths(self):
        ''' The `equality_detector` should function correctly for any input
        bitwidths.
        '''

        cycles = 4000

        bitwidth = random.randrange(2, 17)
        self.args['input_0'] = Signal(intbv(0)[bitwidth:])
        self.args['input_1'] = Signal(intbv(0)[bitwidth:])

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(self.check_equality_detector(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, equality_detector, equality_detector, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_bitwidth_of_one(self):
        ''' The `equality_detector` should function correctly when the inputs
        are 1 bit wide.
        '''

        cycles = 4000

        bitwidth = 1
        self.args['input_0'] = Signal(intbv(0)[bitwidth:])
        self.args['input_1'] = Signal(intbv(0)[bitwidth:])

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(self.check_equality_detector(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, equality_detector, equality_detector, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestEqualityDetectorVivadoVhdl(
    KeaVivadoVHDLTestCase, TestEqualityDetector):
    pass

class TestEqualityDetectorVivadoVerilog(
    KeaVivadoVerilogTestCase, TestEqualityDetector):
    pass
