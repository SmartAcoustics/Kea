import random
import copy

from myhdl import Signal, block, always

from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from .interfaces import DoubleBufferArrayInterface
from ._double_buffer_array import double_buffer_array

def double_buffer_array_interface_types_generator(n_signals):
    ''' Generates the types for the double_buffer_array_interface.
    '''

    double_buffer_array_interface_types = {}

    for n in range(n_signals):
        double_buffer_array_interface_types['input_signal_'+str(n)] = 'custom'
        double_buffer_array_interface_types['output_signal_'+str(n)] = (
            'output')

    return double_buffer_array_interface_types

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    n_signals = 16
    init_val = False

    clock = Signal(False)
    double_buffer_array_interface = (
        DoubleBufferArrayInterface(n_signals, init_val))

    args = {
        'clock': clock,
        'double_buffer_array_interface': double_buffer_array_interface,
    }

    double_buffer_array_interface_types = (
        double_buffer_array_interface_types_generator(n_signals))

    arg_types = {
        'clock': 'clock',
        'double_buffer_array_interface': double_buffer_array_interface_types,
    }

    return args, arg_types

class TestDoubleBufferArrayInterface(KeaTestCase):
    ''' The `double_buffer_array` block should reject incompatible interfaces
    and arguments.
    '''

    def setUp(self):

        self.args, _arg_types = test_args_setup()

    def test_invalid_double_buffer_array_interface(self):
        ''' The `double_buffer_array` should raise an error if
        `double_buffer_array_interface` is not an instance of
        `DoubleBufferArrayInterface`.
        '''

        self.args['double_buffer_array_interface'] = random.randrange(0, 100)

        self.assertRaisesRegex(
            TypeError,
            ('double_buffer_array: double_buffer_array_interface should be an '
             'instance of DoubleBufferArrayInterface.'),
            double_buffer_array,
            **self.args,
        )

class TestDoubleBufferArray(KeaTestCase):

    def setUp(self):

        self.args, self.arg_types = test_args_setup()

    @block
    def signal_stim(self, clock, signal_to_drive):
        ''' Randomly drives a boolean signal.
        '''

        assert(len(signal_to_drive) == 1)

        return_objects = []

        @always(clock.posedge)
        def stim():

            signal_to_drive.next = bool(random.randrange(2))

        return_objects.append(stim)

        return return_objects

    @block
    def double_buffer_array_check(self, **kwargs):

        clock = kwargs['clock']
        double_buffer_array_interface = (
            kwargs['double_buffer_array_interface'])

        return_objects = []

        n_signals = double_buffer_array_interface.n_signals
        init_val = double_buffer_array_interface.init_val

        dut_input_signals = [
            double_buffer_array_interface.input_signal(n)
            for n in range(n_signals)]
        dut_output_signals = [
            double_buffer_array_interface.output_signal(n)
            for n in range(n_signals)]

        intermediate_signals = [
            Signal(init_val) for n in range(n_signals)]
        expected_output_signals = [
            Signal(init_val) for n in range(n_signals)]

        for n in range(n_signals):
            return_objects.append(
                self.signal_stim(clock, dut_input_signals[n]))

        @always(clock.posedge)
        def check():

            for n in range(n_signals):

                assert(dut_output_signals[n] == expected_output_signals[n])

                intermediate_signals[n].next = dut_input_signals[n]
                expected_output_signals[n].next = intermediate_signals[n]

        return_objects.append(check)

        return return_objects

    def test_double_buffer_array(self):
        ''' Every `double_buffer_array_interface.input_signal` should
        connected via a double buffer to the corresponding
        `double_buffer_array_interface.output_signal`.

        ie. A bit on `double_buffer_array_interface.input_signal(n)` should
        appear on `double_buffer_array_interface.output_signal(n)` two cycles
        later.
        '''

        cycles = 2000

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(self.double_buffer_array_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, double_buffer_array, double_buffer_array, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertTrue(dut_outputs == ref_outputs)

    def test_one_signal(self):
        ''' The `double_buffer_array` should function correctly when
        `double_buffer_array_interface.n_signals` is one.
        '''

        cycles = 2000

        n_signals = 1
        self.args['double_buffer_array_interface'] = (
            DoubleBufferArrayInterface(n_signals))
        self.arg_types['double_buffer_array_interface'] = (
            double_buffer_array_interface_types_generator(n_signals))

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(self.double_buffer_array_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, double_buffer_array, double_buffer_array, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertTrue(dut_outputs == ref_outputs)

    def test_random_n_signals(self):
        ''' The `double_buffer_array` should function correctly for any value
        of  `double_buffer_array_interface.n_signals`.
        '''

        cycles = 2000

        n_signals = random.randrange(2, 16)
        self.args['double_buffer_array_interface'] = (
            DoubleBufferArrayInterface(n_signals))
        self.arg_types['double_buffer_array_interface'] = (
            double_buffer_array_interface_types_generator(n_signals))

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(self.double_buffer_array_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, double_buffer_array, double_buffer_array, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertTrue(dut_outputs == ref_outputs)

    def test_init_val_true(self):
        ''' The `double_buffer_array` should function correctly when
        `double_buffer_array_interface.init_val` is True.
        '''

        cycles = 2000

        n_signals = 16
        init_val = True
        self.args['double_buffer_array_interface'] = (
            DoubleBufferArrayInterface(n_signals, init_val))
        self.arg_types['double_buffer_array_interface'] = (
            double_buffer_array_interface_types_generator(n_signals))

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(self.double_buffer_array_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, double_buffer_array, double_buffer_array, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertTrue(dut_outputs == ref_outputs)

class TestDoubleBufferArrayVivadoVhdl(
    KeaVivadoVHDLTestCase, TestDoubleBufferArray):
    pass

class TestDoubleBufferArrayVivadoVerilog(
    KeaVivadoVerilogTestCase, TestDoubleBufferArray):
    pass
