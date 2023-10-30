import random

from math import log, ceil
from myhdl import Signal, intbv, block, always, StopSimulation

from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from .interfaces import MultiplexerInputInterface
from ._synchronous_multiplexer import synchronous_multiplexer

def multiplexer_input_interface_and_types(n_signals, signal_bit_width):
    ''' Generate the MultiplexerInputInterface and types.
    '''

    input_interface = MultiplexerInputInterface(n_signals, signal_bit_width)

    input_interface_types = {
        'signal_'+str(n): 'custom' for n in range(n_signals)}

    return input_interface, input_interface_types

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    clock = Signal(False)

    n_signals = 16
    signal_bit_width = 8
    select_bit_width = ceil(log(n_signals)/log(2))

    input_interface, input_interface_types = (
        multiplexer_input_interface_and_types(n_signals, signal_bit_width))
    output_signal = Signal(intbv(0)[signal_bit_width:])
    select = Signal(intbv(0)[select_bit_width:])

    # Define the default arguments for the DUT
    args = {
        'clock': clock,
        'input_interface': input_interface,
        'output_signal': output_signal,
        'select': select,
    }

    arg_types = {
        'clock': 'clock',
        'input_interface': input_interface_types,
        'output_signal': 'output',
        'select': 'custom',
    }

    return args, arg_types

class TestSynchronousMultiplexerInterface(KeaTestCase):
    ''' The synchronous_signal_slicer should reject incompatible interfaces
    and arguments.
    '''

    def setUp(self):

        self.args, _arg_types = test_args_setup()

    def test_interface_invalid_n_signals(self):
        ''' The `MultiplexerInputInterface` should raise an error if
        `n_signals` is less than or equal to 0.
        '''

        ##################
        # Zero n signals #
        ##################

        n_signals = 0
        signal_bit_width = 8

        self.assertRaisesRegex(
            ValueError,
            ('MultiplexerInputInterface: n_signals should be greater than '
             'zero.'),
            MultiplexerInputInterface,
            n_signals,
            signal_bit_width,)

        ######################
        # Negative n signals #
        ######################

        n_signals = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('MultiplexerInputInterface: n_signals should be greater than '
             'zero.'),
            MultiplexerInputInterface,
            n_signals,
            signal_bit_width,)

    def test_interface_invalid_signal_bit_width(self):
        ''' The `MultiplexerInputInterface` should raise an error if
        `signal_bit_width` is less than or equal to 0.
        '''

        ##################
        # Zero n signals #
        ##################

        n_signals = 2
        signal_bit_width = 0

        self.assertRaisesRegex(
            ValueError,
            ('MultiplexerInputInterface: signal_bit_width should be '
             'greater than zero.'),
            MultiplexerInputInterface,
            n_signals,
            signal_bit_width,)

        ######################
        # Negative n signals #
        ######################

        signal_bit_width = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('MultiplexerInputInterface: signal_bit_width should be '
             'greater than zero.'),
            MultiplexerInputInterface,
            n_signals,
            signal_bit_width,)

    def test_invalid_input_interface(self):
        ''' The `synchronous_multiplexer` should raise an error if
        `input_interface` is not an instance of MultiplexerInputInterface.
        '''

        self.args['input_interface'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            TypeError,
            ('synchronous_multiplexer: input_interface should be an instance '
             'of MultiplexerInputInterface.'),
            synchronous_multiplexer,
            **self.args,)

    def test_invalid_output_signal_bit_width(self):
        ''' The `synchronous_multiplexer` should raise an error if bit width
        of the `output_signal` is less than
        `input_interface.signal_bit_width`.
        '''

        invalid_upper_bound = self.args['input_interface'].signal_bit_width
        invalid_bit_width = random.randrange(1, invalid_upper_bound)

        self.args['output_signal'] = Signal(intbv(0)[invalid_bit_width:])

        self.assertRaisesRegex(
            ValueError,
            ('synchronous_multiplexer: The output_signal should be at least '
             'as wide as the signals on the input_interface.'),
            synchronous_multiplexer,
            **self.args,)

    def test_invalid_select_bit_width(self):
        ''' The `synchronous_multiplexer` should raise an error if `select` is
        not wide enough to select all signals on the `input_interface`.
        '''

        n_signals = 32
        signal_bit_width = self.args['input_interface'].signal_bit_width
        self.args['input_interface'] = (
            MultiplexerInputInterface(n_signals, signal_bit_width))

        invalid_upper_bound = ceil(log(signal_bit_width)/log(2))
        invalid_bit_width = random.randrange(1, invalid_upper_bound)

        self.args['select'] = Signal(intbv(0)[invalid_bit_width:])

        self.assertRaisesRegex(
            ValueError,
            ('synchronous_multiplexer: The select signal should be wide '
             'enough to select any input.'),
            synchronous_multiplexer,
            **self.args,)

class TestSynchronousMultiplexer(KeaTestCase):

    def setUp(self):

        self.test_count = 0
        self.tests_run = False

        self.args, self.arg_types = test_args_setup()

    @block
    def complete_tests(self, clock, n_tests):

        @always(clock.posedge)
        def control():

            if self.test_count >= n_tests:
                # Check that all the tests are run
                self.tests_run = True

                raise StopSimulation

        return control

    @block
    def synchronous_multiplexer_stim(self, **kwargs):
        ''' Stimulate the synchronous_multiplexer inputs.
        '''
        clock = kwargs['clock']
        input_interface = kwargs['input_interface']
        select = kwargs['select']

        return_objects = []

        n_inputs = input_interface.n_signals
        input_signals = [
            input_interface.signal(n) for n in range(n_inputs)]

        inputs_upper_bound = 2**input_interface.signal_bit_width
        select_upper_bound = 2**len(select)

        @always(clock.posedge)
        def stim():

            for n in range(n_inputs):
                # Randomly drive all inputs
                input_signals[n].next = random.randrange(inputs_upper_bound)

            # Randomly drive the select signal
            select.next = random.randrange(select_upper_bound)

        return_objects.append(stim)

        return return_objects

    @block
    def synchronous_multiplexer_check(self, **kwargs):
        ''' Check the synchronous_multiplexer output.
        '''
        clock = kwargs['clock']
        input_interface = kwargs['input_interface']
        output_signal = kwargs['output_signal']
        select = kwargs['select']

        return_objects = []

        return_objects.append(self.synchronous_multiplexer_stim(**kwargs))

        expected_output_signal = Signal(intbv(0)[len(output_signal):])

        n_inputs = input_interface.n_signals
        input_signals = [
            input_interface.signal(n) for n in range(n_inputs)]


        @always(clock.posedge)
        def check():

            self.test_count += 1

            assert(output_signal == expected_output_signal)

            try:
                # Update the expected signal with the specified input signal
                expected_output_signal.next = input_signals[select]

            except IndexError:
                # Select is pointing to an out of range input
                expected_output_signal.next = 0

        return_objects.append(check)

        return return_objects

    def test_synchronous_multiplexer(self):
        ''' The `synchronous_multiplexer` should select a signal on the
        `input_interface` and forward the selected input to the
        `output_signal'. The selection should be directed by the `select`
        signal.
        '''

        n_tests = 2000
        cycles = n_tests + 100

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            clock = kwargs['clock']

            return_objects.append(self.complete_tests(clock, n_tests))

            return_objects.append(
                self.synchronous_multiplexer_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_multiplexer, synchronous_multiplexer,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_select_outside_valid_range(self):
        ''' When `select` is set to a value which is greater than the number
        of signals on the `input_interface` the `synchronous_multiplexer`
        should set the `output_signal` to 0.
        '''

        n_tests = 1000
        cycles = n_tests + 100

        select_bit_width = len(self.args['select']) + 1
        self.args['select'] = Signal(intbv(0)[select_bit_width:])

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            clock = kwargs['clock']

            return_objects.append(self.complete_tests(clock, n_tests))

            return_objects.append(
                self.synchronous_multiplexer_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_multiplexer, synchronous_multiplexer,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_output_wider_than_input(self):
        ''' When the `output_signal` is wider than the
        `input_interface.signal_bit_width` the selected input signal should be
        forwarded to the least significant bits of the `output_signal`.
        '''

        n_tests = 1000
        cycles = n_tests + 100

        input_bit_width = self.args['input_interface'].signal_bit_width
        output_bit_width = input_bit_width + random.randrange(1, 8)
        self.args['output_signal'] = Signal(intbv(0)[output_bit_width:])

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            clock = kwargs['clock']

            return_objects.append(self.complete_tests(clock, n_tests))

            return_objects.append(
                self.synchronous_multiplexer_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_multiplexer, synchronous_multiplexer,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)


    def test_one_input(self):
        ''' The `synchronous_multiplexer` should function correctly when the
        `input_interface` contains a single signal.
        '''

        n_tests = 500
        cycles = n_tests + 100

        n_inputs = 1
        input_bit_width = self.args['input_interface'].signal_bit_width
        self.args['input_interface'], self.arg_types['input_interface'] = (
            multiplexer_input_interface_and_types(
                n_inputs, input_bit_width))

        self.args['select'] = Signal(intbv(0)[1:])

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            clock = kwargs['clock']

            return_objects.append(self.complete_tests(clock, n_tests))

            return_objects.append(
                self.synchronous_multiplexer_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_multiplexer, synchronous_multiplexer,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_two_inputs(self):
        ''' The `synchronous_multiplexer` should function correctly when the
        `input_interface` contains two signal.
        '''

        n_tests = 500
        cycles = n_tests + 100

        n_inputs = 2
        input_bit_width = self.args['input_interface'].signal_bit_width
        self.args['input_interface'], self.arg_types['input_interface'] = (
            multiplexer_input_interface_and_types(
                n_inputs, input_bit_width))

        self.args['select'] = Signal(intbv(0)[1:])

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            clock = kwargs['clock']

            return_objects.append(self.complete_tests(clock, n_tests))

            return_objects.append(
                self.synchronous_multiplexer_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_multiplexer, synchronous_multiplexer,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_boolean_select(self):
        ''' The `synchronous_multiplexer` should function correctly when
        `select` is a boolean signal.
        '''

        n_tests = 500
        cycles = n_tests + 100

        n_inputs = 2
        input_bit_width = self.args['input_interface'].signal_bit_width
        self.args['input_interface'], self.arg_types['input_interface'] = (
            multiplexer_input_interface_and_types(
                n_inputs, input_bit_width))

        self.args['select'] = Signal(False)

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            clock = kwargs['clock']

            return_objects.append(self.complete_tests(clock, n_tests))

            return_objects.append(
                self.synchronous_multiplexer_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_multiplexer, synchronous_multiplexer,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_one_bit_inputs(self):
        ''' The `synchronous_multiplexer` should function correctly when the
        `input_interface.signal_bit_width` is one.
        '''

        n_tests = 1000
        cycles = n_tests + 100

        n_inputs = self.args['input_interface'].n_signals
        input_bit_width = 1
        self.args['input_interface'], self.arg_types['input_interface'] = (
            multiplexer_input_interface_and_types(
                n_inputs, input_bit_width))

        self.args['output_signal'] = Signal(intbv(0)[1:])

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            clock = kwargs['clock']

            return_objects.append(self.complete_tests(clock, n_tests))

            return_objects.append(
                self.synchronous_multiplexer_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_multiplexer, synchronous_multiplexer,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_boolean_output(self):
        ''' The `synchronous_multiplexer` should function correctly when the
        `output_signal` is a boolean signal.
        '''

        n_tests = 1000
        cycles = n_tests + 100

        n_inputs = self.args['input_interface'].n_signals
        input_bit_width = 1
        self.args['input_interface'], self.arg_types['input_interface'] = (
            multiplexer_input_interface_and_types(
                n_inputs, input_bit_width))

        self.args['output_signal'] = Signal(False)

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            clock = kwargs['clock']

            return_objects.append(self.complete_tests(clock, n_tests))

            return_objects.append(
                self.synchronous_multiplexer_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_multiplexer, synchronous_multiplexer,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

class TestSynchronousMultiplexerVivadoVhdl(
    KeaVivadoVHDLTestCase, TestSynchronousMultiplexer):
    pass

class TestSynchronousMultiplexerVivadoVerilog(
    KeaVivadoVerilogTestCase, TestSynchronousMultiplexer):
    pass
