import random

from myhdl import *

from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._synchronous_signal_slicer import synchronous_signal_slicer

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    clock = Signal(False)

    # Choose a random signal in width
    signal_in_width = random.randrange(1, 32)
    signal_in = Signal(intbv(0)[signal_in_width: 0])

    # Choose random slice offset and bitwidth
    slice_offset = random.randrange(0, signal_in_width)
    slice_bitwidth = (
        random.randrange(1, signal_in_width-slice_offset+1))

    # Create a valid signal_out
    signal_out_width = slice_bitwidth
    signal_out = Signal(intbv(0)[signal_out_width: 0])

    # Define the default arguments for the DUT
    args = {
        'clock': clock,
        'signal_in': signal_in,
        'slice_offset': slice_offset,
        'slice_bitwidth': slice_bitwidth,
        'signal_out': signal_out,
    }

    arg_types = {
        'clock': 'clock',
        'signal_in': 'custom',
        'slice_offset': 'non-signal',
        'slice_bitwidth': 'non-signal',
        'signal_out': 'output',
    }

    return args, arg_types

class TestSignalSlicerInterface(KeaTestCase):
    ''' The synchronous_signal_slicer should reject incompatible interfaces
    and arguments.
    '''

    def setUp(self):

        self.args, _arg_types = test_args_setup()

    def test_negative_slice_offset(self):
        ''' The `synchronous_signal_slicer` should raise an error if the
        `slice_offset` is less than 0.
        '''

        # Generate a negative slice offset
        self.args['slice_offset'] = random.randrange(-100, 0)

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('synchronous_signal_slicer: slice_offset must not be negative'),
            synchronous_signal_slicer,
            **self.args,)

    def test_invalid_slice_offset(self):
        ''' The `synchronous_signal_slicer` should raise an error if the
        `slice_offset` is greater than the `signal_in` bit width.
        '''

        # Generate an invalid slice offset
        signal_in_bitwidth = len(self.args['signal_in'])
        self.args['slice_offset'] = (
            random.randrange(signal_in_bitwidth, 2*(signal_in_bitwidth+1)))

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('synchronous_signal_slicer: slice_offset must be less than the '
            'signal_in width'),
            synchronous_signal_slicer,
            **self.args,)

    def test_invalid_bitfield(self):
        ''' The `synchronous_signal_slicer` should raise an error if the
        combination of `slice_offset` and `slice_bitwidth` result in any bits
        of the slice exceeding the bit width of the `signal_in`.
        '''

        # Generate an invalid bitwidth
        min_invalid_bitwidth = (
            len(self.args['signal_in']) - self.args['slice_offset'] + 1)
        self.args['slice_bitwidth'] = (
            random.randrange(
                min_invalid_bitwidth, 2*(min_invalid_bitwidth+1)))

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('synchronous_signal_slicer: Slice bitfield must fit within '
             'signal_in'),
            synchronous_signal_slicer,
            **self.args,)

    def test_invalid_slice_bitwidth(self):
        ''' The `synchronous_signal_slicer` should raise an error if the
        `slice_bitwidth` is less than or equal to 0.
        '''

        # Generate an invalid bitwidth of 0
        self.args['slice_bitwidth'] = 0

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('synchronous_signal_slicer: slice_bitwidth must be greater than '
             '0'),
            synchronous_signal_slicer,
            **self.args,)

        # Generate a negaative bitwidth
        self.args['slice_bitwidth'] = random.randrange(-32, 0)

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('synchronous_signal_slicer: slice_bitwidth must be greater than '
             '0'),
            synchronous_signal_slicer,
            **self.args,)

    def test_invalid_signal_out_width(self):
        ''' The `synchronous_signal_slicer` should raise an error if the
        `signal_out` is not the same bitwidth as `slice_bitwidth`.
        '''

        # Generate an invalid signal_out width
        available_invalid_bitwidths = [
            n for n in range(1, 32) if n != self.args['slice_bitwidth']]
        invalid_bitwidth = random.choice(available_invalid_bitwidths)

        self.args['signal_out'] = Signal(intbv(0)[invalid_bitwidth:])

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('synchronous_signal_slicer: slice_bitwidth must be equal to the '
             'signal_out width'),
            synchronous_signal_slicer,
            **self.args,)

class TestSignalSlicer(KeaTestCase):

    def setUp(self):

        self.args, self.arg_types = test_args_setup()

    @block
    def check_synchronous_signal_slicer(self, **kwargs):

        clock = kwargs['clock']
        signal_in = kwargs['signal_in']
        slice_offset = kwargs['slice_offset']
        slice_bitwidth = kwargs['slice_bitwidth']
        signal_out = kwargs['signal_out']

        expected_output_val = Signal(intbv(0)[slice_bitwidth:0])

        signal_in_upper_bound = 2**len(signal_in)

        slice_mask = 2**slice_bitwidth - 1

        @always(clock.posedge)
        def stim_check():

            # Randomly drive signal_in
            signal_in.next = random.randrange(0, signal_in_upper_bound)

            # Shift and mask the input value to get the expected output
            # value
            expected_output_val.next = (
                (signal_in >> slice_offset) & slice_mask)

            # Check that signal out always equals the expected output
            assert(signal_out == expected_output_val)

        return stim_check

    def test_random_bitfields(self):
        ''' The `synchronous_signal_slicer` should use `slice_offset` and
        `slice_bitwidth` to extract a slice out of `signal_in`. This slice
        should be synchronously assigned to `signal_out`.
        '''

        cycles = 2000

        @block
        def stimulate_check(**kwargs):

            return self.check_synchronous_signal_slicer(**kwargs)

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_signal_slicer, synchronous_signal_slicer,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_max_offset(self):
        ''' The `synchronous_signal_slicer` should work correctly with a
        `slice_offset` which is equal to the highest bit index in `signal_in`.
        '''

        slice_bitwidth = 1
        signal_out_width = slice_bitwidth

        # Modify the arguments to test the required behaviour
        self.args['slice_offset'] = len(self.args['signal_in']) - 1
        self.args['slice_bitwidth'] = slice_bitwidth
        self.args['signal_out'] = Signal(intbv(0)[signal_out_width: 0])

        cycles = 2000

        @block
        def stimulate_check(**kwargs):

            return self.check_synchronous_signal_slicer(**kwargs)

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_signal_slicer, synchronous_signal_slicer,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_max_bitwidth(self):
        ''' The `synchronous_signal_slicer` should work correctly with a
        `slice_offset` of 0 and a `slice_bitwidth` which is equal to the
        bitwidth of `signal_in`.
        '''

        slice_bitwidth = len(self.args['signal_in'])
        signal_out_width = slice_bitwidth

        # Modify the arguments to test the required behaviour
        self.args['slice_offset'] = 0
        self.args['slice_bitwidth'] = slice_bitwidth
        self.args['signal_out'] = Signal(intbv(0)[signal_out_width: 0])

        cycles = 2000

        @block
        def stimulate_check(**kwargs):

            return self.check_synchronous_signal_slicer(**kwargs)

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_signal_slicer, synchronous_signal_slicer,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_bool_output(self):
        ''' The `synchronous_signal_slicer` should work correctly with a
        `slice_bitwidth` of 1 and a boolean `signal_out`.
        '''

        # Modify the arguments to test the required behaviour
        self.args['slice_offset'] = (
            random.randrange(len(self.args['signal_in'])))
        self.args['slice_bitwidth'] = 1
        self.args['signal_out'] = Signal(False)

        cycles = 2000

        @block
        def stimulate_check(**kwargs):

            return self.check_synchronous_signal_slicer(**kwargs)

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_signal_slicer, synchronous_signal_slicer,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestSignalSlicerVivadoVhdl(KeaVivadoVHDLTestCase, TestSignalSlicer):
    pass

class TestSignalSlicerVivadoVerilog(
    KeaVivadoVerilogTestCase, TestSignalSlicer):
    pass
