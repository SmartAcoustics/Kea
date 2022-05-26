import random

from myhdl import *

from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._signal_slicer import signal_slicer

class TestSignalSlicerInterfaceSimulation(KeaTestCase):
    ''' The signal_slicer should reject incompatible interfaces and arguments.
    '''

    def setUp(self):

        # Choose a random signal in width
        self.signal_in_width = random.randrange(1, 32)
        self.signal_in = Signal(intbv(0)[self.signal_in_width: 0])

        # Choose random slice offset and bitwidth
        self.slice_offset = random.randrange(0, self.signal_in_width)
        self.slice_bitwidth = (
            random.randrange(1, self.signal_in_width-self.slice_offset+1))

        # Create a valid signal_out
        self.signal_out_width = self.slice_bitwidth
        self.signal_out = Signal(intbv(0)[self.signal_out_width: 0])

    def test_invalid_slice_offset(self):
        # Generate an invalid slice offset
        invalid_slice_offset = random.randrange(
            self.signal_in_width, 2*(self.signal_in_width+1))

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            'slice_offset must be less than the signal_in width',
            signal_slicer,
            self.signal_in,
            invalid_slice_offset,
            self.slice_bitwidth,
            self.signal_out,)

    def test_invalid_bitfield(self):
        min_invalid_bitwidth = self.signal_in_width - self.slice_offset + 1
        # Generate an invalid bitwidth
        invalid_slice_bitwidth = random.randrange(
            min_invalid_bitwidth, 2*(min_invalid_bitwidth+1))

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            'Slice bitfield must fit within signal_in',
            signal_slicer,
            self.signal_in,
            self.slice_offset,
            invalid_slice_bitwidth,
            self.signal_out,)

    def test_zero_bitwidth(self):
        # Generate an invalid bitwidth of 0
        invalid_slice_bitwidth = 0

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            'slice_bitwidth must be greater than 0',
            signal_slicer,
            self.signal_in,
            self.slice_offset,
            invalid_slice_bitwidth,
            self.signal_out,)

    def test_negative_bitwidth(self):
        # Generate an invalid bitwidth of 0
        invalid_slice_bitwidth = random.randrange(-32, 0)

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            'slice_bitwidth must be greater than 0',
            signal_slicer,
            self.signal_in,
            self.slice_offset,
            invalid_slice_bitwidth,
            self.signal_out,)

    def test_invalid_signal_out_width(self):
        signal_in_width = 16
        signal_in = Signal(intbv(0)[self.signal_in_width: 0])

        slice_offset = 0
        slice_bitwidth = 1

        # Generate an invalid signal_out width
        invalid_signal_out_width = random.randrange(2, signal_in_width)
        invalid_signal_out = Signal(intbv(0)[invalid_signal_out_width: 0])

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            'slice_bitwidth must be equal to the signal_out width',
            signal_slicer,
            self.signal_in,
            slice_offset,
            slice_bitwidth,
            invalid_signal_out,)

@block
def signal_slicer_wrapper(
    clock, signal_in, slice_offset, slice_bitwidth, signal_out):

    return signal_slicer(signal_in, slice_offset, slice_bitwidth, signal_out)

class TestSignalSlicerSimulation(KeaTestCase):

    def setUp(self):

        self.clock = Signal(False)

        # Choose a random signal in width
        self.signal_in_width = random.randrange(1, 32)
        self.signal_in = Signal(intbv(0)[self.signal_in_width: 0])

        # Choose random slice offset and bitwidth
        self.slice_offset = random.randrange(0, self.signal_in_width)
        self.slice_bitwidth = (
            random.randrange(1, self.signal_in_width-self.slice_offset+1))

        # Create a valid signal_out
        self.signal_out_width = self.slice_bitwidth
        self.signal_out = Signal(intbv(0)[self.signal_out_width: 0])

        # Define the default arguments for the DUT
        self.default_args = {
            'clock': self.clock,
            'signal_in': self.signal_in,
            'slice_offset': self.slice_offset,
            'slice_bitwidth': self.slice_bitwidth,
            'signal_out': self.signal_out,
        }

        self.default_arg_types = {
            'clock': 'clock',
            'signal_in': 'custom',
            'slice_offset': 'non-signal',
            'slice_bitwidth': 'non-signal',
            'signal_out': 'output',
        }

    @block
    def check_signal_slicer(
        self, clock, signal_in, slice_offset, slice_bitwidth, signal_out):

        expected_output_val = Signal(intbv(0)[slice_bitwidth:0])

        @always(clock.posedge)
        def stim_check():

            # Generate a random input value
            input_val = random.randrange(0, 2**self.signal_in_width)
            # Shift and mask the input value to get the expected output
            # value
            expected_output_val.next = (
                input_val >> slice_offset) & ((2**slice_bitwidth)-1)

            # Randomly drive signal_in
            signal_in.next = input_val

            # Check that signal out always equals the expected output
            assert(signal_out==expected_output_val)

        return stim_check

    def test_random_bitfields(self):
        ''' The signal_slicer should connect the correct slice of signal_in to
        signal_out so that signal_out always equals the signal_in slice.
        '''

        args = self.default_args.copy()
        arg_types = self.default_arg_types.copy()

        cycles = 2000

        @block
        def stimulate_check(
            clock, signal_in, slice_offset, slice_bitwidth, signal_out):

            return (
                self.check_signal_slicer(
                    clock, signal_in, slice_offset, slice_bitwidth,
                    signal_out))

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, signal_slicer_wrapper, signal_slicer_wrapper, args,
            arg_types, custom_sources=[(stimulate_check, (), args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_max_offset(self):
        ''' The signal_slicer should work correctly with an offset which is
        equal to the signal_in_width-1 and a bitwidth of 1.
        '''

        args = self.default_args.copy()
        arg_types = self.default_arg_types.copy()

        slice_bitwidth = 1
        signal_out_width = slice_bitwidth

        # Modify the arguments to test the required behaviour
        args['slice_offset'] = self.signal_in_width-1
        args['slice_bitwidth'] = slice_bitwidth
        args['signal_out'] = Signal(intbv(0)[signal_out_width: 0])

        cycles = 2000

        @block
        def stimulate_check(
            clock, signal_in, slice_offset, slice_bitwidth, signal_out):

            return (
                self.check_signal_slicer(
                    clock, signal_in, slice_offset, slice_bitwidth,
                    signal_out))

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, signal_slicer_wrapper, signal_slicer_wrapper, args,
            arg_types, custom_sources=[(stimulate_check, (), args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_max_bitwidth(self):
        ''' The signal_slicer should work correctly with an offset of 0 and a
        bitwidth of signal_in_width.
        '''

        args = self.default_args.copy()
        arg_types = self.default_arg_types.copy()

        slice_bitwidth = self.signal_in_width
        signal_out_width = slice_bitwidth

        # Modify the arguments to test the required behaviour
        args['slice_offset'] = 0
        args['slice_bitwidth'] = slice_bitwidth
        args['signal_out'] = Signal(intbv(0)[signal_out_width: 0])

        cycles = 2000

        @block
        def stimulate_check(
            clock, signal_in, slice_offset, slice_bitwidth, signal_out):

            return (
                self.check_signal_slicer(
                    clock, signal_in, slice_offset, slice_bitwidth,
                    signal_out))

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, signal_slicer_wrapper, signal_slicer_wrapper, args,
            arg_types, custom_sources=[(stimulate_check, (), args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestSignalSlicerVivadoVhdlSimulation(
    KeaVivadoVHDLTestCase, TestSignalSlicerSimulation):
    pass

class TestSignalSlicerVivadoVerilogSimulation(
    KeaVivadoVerilogTestCase, TestSignalSlicerSimulation):
    pass
