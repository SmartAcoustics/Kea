import random

from myhdl import block, always, Signal, intbv

from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._toggle_flip_flop import toggle_flip_flop

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    clock = Signal(True)
    toggle = Signal(False)
    output = Signal(False)

    args = {
        'clock': clock,
        'toggle': toggle,
        'output': output,
    }

    arg_types = {
        'clock': 'clock',
        'toggle': 'custom',
        'output': 'output',
    }

    return args, arg_types

class TestToggleFlipFlopInterface(KeaTestCase):
    ''' The DUT should reject incompatible interfaces and arguments.
    '''

    def setUp(self):
        self.args, _arg_types = test_args_setup()

    def test_non_boolean_signal_toggle(self):
        ''' The `toggle_flip_flop` should raise an error if the bit width of
        the `toggle` signal is not 1.
        '''

        self.args['toggle'] = Signal(intbv(0)[random.randrange(2, 33):])

        self.assertRaisesRegex(
            TypeError,
            ('toggle_flip_flop: toggle should be 1 bit wide.'),
            toggle_flip_flop,
            **self.args,
        )

    def test_non_boolean_signal_output(self):
        ''' The `toggle_flip_flop` should raise an error if the bit width of
        the `output` signal is not 1.
        '''

        self.args['output'] = Signal(intbv(0)[random.randrange(2, 33):])

        self.assertRaisesRegex(
            TypeError,
            ('toggle_flip_flop: output should be 1 bit wide.'),
            toggle_flip_flop,
            **self.args,
        )

class TestToggleFlipFlop(KeaTestCase):

    def setUp(self):
        self.args, self.arg_types = test_args_setup()

    @block
    def check_toggle_flip_flop(self, **kwargs):
        ''' Check the behaviour of the toggle_flip_flop.
        '''

        clock = kwargs['clock']
        toggle = kwargs['toggle']
        output = kwargs['output']

        return_objects = []

        expected_output = Signal(output.val)

        @always(clock.posedge)
        def stim_check():

            assert(output == expected_output)

            toggle.next = bool(random.randrange(2))

            if toggle:
                expected_output.next = not expected_output

        return_objects.append(stim_check)

        return return_objects

    def test_toggle_flop_flop(self):
        ''' When `toggle` is high the `toggle_flip_flop` should toggle the
        `output`. When `toggle` is low the `output` should hold its value.
        '''

        cycles = 1000

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            return_objects.append(self.check_toggle_flip_flop(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, toggle_flip_flop, toggle_flip_flop, self.args,
            self.arg_types, custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_output_initialised_true(self):
        ''' The `toggle_flip_flop` should function correctly when `output` is
        initialised true.
        '''

        cycles = 1000

        self.args['output'] = Signal(True)

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            return_objects.append(self.check_toggle_flip_flop(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, toggle_flip_flop, toggle_flip_flop, self.args,
            self.arg_types, custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_one_bit_intbv(self):
        ''' The `toggle_flip_flop` should function correctly when `toggle` and
        `output` are one bit intbv signals.
        '''

        cycles = 1000

        self.args['output'] = Signal(intbv(0)[1:])
        self.args['toggle'] = Signal(intbv(0)[1:])

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            return_objects.append(self.check_toggle_flip_flop(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, toggle_flip_flop, toggle_flip_flop, self.args,
            self.arg_types, custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestToggleFlipFlopVivadoVhdl(
    KeaVivadoVHDLTestCase, TestToggleFlipFlop):
    pass

class TestToggleFlipFlopVivadoVerilog(
    KeaVivadoVerilogTestCase, TestToggleFlipFlop):
    pass
