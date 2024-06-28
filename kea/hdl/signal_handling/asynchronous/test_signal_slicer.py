import random

from myhdl import *

from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._signal_slicer import signal_slicer

def test_args_setup(
    signal_in_bitwidth, slice_bitwidth, slice_offset, signed_output=False):
    ''' Generate the arguments and argument types for the DUT.
    '''

    if signed_output:
        signal_out_max = 2**(slice_bitwidth-1)
        signal_out_min = -2**(slice_bitwidth-1)
        signal_out = Signal(intbv(0, min=signal_out_min, max=signal_out_max))

    else:
        signal_out_bitwidth = slice_bitwidth
        signal_out = Signal(intbv(0)[signal_out_bitwidth:])

    args = {
        'clock': Signal(False),
        'signal_in': Signal(intbv(0)[signal_in_bitwidth:]),
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

@block
def signal_slicer_wrapper(**dut_wrapper_args):

    return_objects = []

    dut_args = dut_wrapper_args.copy()

    # We need to include a clock for the tests but the DUT doensn't take one
    del dut_args['clock']

    return_objects.append(signal_slicer(**dut_args))

    return return_objects

class TestSignalSlicerInterface(KeaTestCase):
    ''' The signal_slicer should reject incompatible interfaces and arguments.
    '''

    def setUp(self):

        signal_in_bitwidth = random.randrange(1, 32)
        slice_offset = random.randrange(0, signal_in_bitwidth)
        slice_bitwidth = (
            random.randrange(1, signal_in_bitwidth-slice_offset+1))

        self.dut_wrapper_args, _dut_wrapper_arg_types = (
            test_args_setup(signal_in_bitwidth, slice_bitwidth, slice_offset))

    def test_invalid_slice_offset(self):
        ''' The `signal_slicer` should raise an error if `slice_offset`
        exceeds the bit width of `signal_in`.
        '''
        signal_in_bitwidth = len(self.dut_wrapper_args['signal_in'])
        self.dut_wrapper_args['slice_offset'] = (
            random.randrange(signal_in_bitwidth, signal_in_bitwidth+10))

        self.assertRaisesRegex(
            ValueError,
            ('signal_slicer: slice_offset should be less than the signal_in '
             'width'),
            signal_slicer_wrapper,
            **self.dut_wrapper_args,)

    def test_invalid_bitfield(self):
        ''' The `signal_slicer` should raise an error if the combination of
        `slice_offset` and `slice_bitwidth` exceeds the bit width of
        `signal_in`.
        '''
        min_invalid_bitwidth = (
            len(self.dut_wrapper_args['signal_in']) -
            self.dut_wrapper_args['slice_offset'] + 1)
        self.dut_wrapper_args['slice_bitwidth'] = (
            random.randrange(min_invalid_bitwidth, min_invalid_bitwidth+10))

        self.assertRaisesRegex(
            ValueError,
            'signal_slicer: Slice bitfield should fit within signal_in',
            signal_slicer_wrapper,
            **self.dut_wrapper_args,)

    def test_zero_bitwidth(self):
        ''' The `signal_slicer` should raise and error if `slice_bitwidth` is
        set to 0.
        '''

        self.dut_wrapper_args['slice_bitwidth'] = 0

        self.assertRaisesRegex(
            ValueError,
            'signal_slicer: slice_bitwidth should be greater than 0',
            signal_slicer_wrapper,
            **self.dut_wrapper_args,)

    def test_negative_bitwidth(self):
        ''' The `signal_slicer` should raise and error if `slice_bitwidth` is
        negative.
        '''
        self.dut_wrapper_args['slice_bitwidth'] = random.randrange(-32, 0)

        self.assertRaisesRegex(
            ValueError,
            'signal_slicer: slice_bitwidth should be greater than 0',
            signal_slicer_wrapper,
            **self.dut_wrapper_args,)

    def test_invalid_signal_out_bitwidth(self):
        ''' The `signal_slicer` should raise and error if the `slice_bitwidth`
        is not equal to the bitwidth of the `signal_out`.
        '''

        signal_in_bitwidth = 32
        slice_bitwidth, signal_out_bitwidth = (
            random.sample(range(1, signal_in_bitwidth), 2))

        self.dut_wrapper_args, _dut_wrapper_arg_types = (
            test_args_setup(signal_in_bitwidth, slice_bitwidth, 0))

        self.dut_wrapper_args['signal_out'] = (
            Signal(intbv(0)[signal_out_bitwidth:]))

        self.assertRaisesRegex(
            ValueError,
            ('signal_slicer: slice_bitwidth should be equal to the '
             'signal_out width'),
            signal_slicer_wrapper,
            **self.dut_wrapper_args,)

    def test_invalid_signal_out_max(self):
        ''' When `signal_out` is a signed signal (`signal_out.min` is less
        than 0) the `signal_slicer` should raise an error if the
        `signal_out.max` is not equal to the exclusive upper bound for a
        signed slice of `slice_bitwidth`.
        '''

        signal_in_bitwidth = 32
        slice_bitwidth = random.randrange(8, signal_in_bitwidth)

        self.dut_wrapper_args, _dut_wrapper_arg_types = (
            test_args_setup(signal_in_bitwidth, slice_bitwidth, 0))

        invalid_max = random.randrange(1, 2**(slice_bitwidth-1))
        valid_min = -2**(slice_bitwidth-1)

        self.dut_wrapper_args['signal_out'] = (
            Signal(intbv(0, min=valid_min, max=invalid_max)))

        self.assertRaisesRegex(
            ValueError,
            ('signal_slicer: signal_out.max should be equal to the '
             'exclusive upper bound for a signed signal of '
             'slice_bitwidth bits.'),
            signal_slicer_wrapper,
            **self.dut_wrapper_args,)

    def test_invalid_signal_out_min(self):
        ''' When `signal_out` is a signed signal (`signal_out.min` is less
        than 0) the `signal_slicer` should raise an error if the
        `signal_out.min` is not equal to the inclusive lower bound for a
        signed slice of `slice_bitwidth`.
        '''

        signal_in_bitwidth = 32
        slice_bitwidth = random.randrange(8, signal_in_bitwidth)

        self.dut_wrapper_args, _dut_wrapper_arg_types = (
            test_args_setup(signal_in_bitwidth, slice_bitwidth, 0))

        invalid_min = random.randrange(-2**(slice_bitwidth-1) + 1, 0)
        valid_max = 2**(slice_bitwidth-1)

        self.dut_wrapper_args['signal_out'] = (
            Signal(intbv(0, min=invalid_min, max=valid_max)))

        self.assertRaisesRegex(
            ValueError,
            ('signal_slicer: signal_out.min should be equal to the '
             'inclusive lower bound for a signed signal of '
             'slice_bitwidth bits.'),
            signal_slicer_wrapper,
            **self.dut_wrapper_args,)

class TestSignalSlicer(KeaTestCase):

    def setUp(self):
        pass

    @block
    def check_signal_slicer(self, **dut_wrapper_args):

        clock = dut_wrapper_args['clock']
        signal_in = dut_wrapper_args['signal_in']
        slice_bitwidth = dut_wrapper_args['slice_bitwidth']
        slice_offset = dut_wrapper_args['slice_offset']
        signal_out = dut_wrapper_args['signal_out']

        return_objects = []

        if signal_out.min is None:
            signed_output = False
            expected_output_val = Signal(intbv(0)[slice_bitwidth:0])

        elif signal_out.min < 0:
            signed_output = True
            expected_output_val = (
                Signal(intbv(0, min=signal_out.min, max=signal_out.max)))

        else:
            signed_output = False
            expected_output_val = Signal(intbv(0)[slice_bitwidth:0])

        slice_val_upper_bound = 2**slice_bitwidth
        slice_mask = slice_val_upper_bound - 1

        msb_index = slice_bitwidth-1

        @always(clock.posedge)
        def stim_check():

            # Generate a random input value
            input_val = random.randrange(0, 2**len(signal_in))

            # Randomly drive signal_in
            signal_in.next = input_val

            # Shift and mask the input value to get the expected slice
            expected_output_slice = (input_val >> slice_offset) & slice_mask

            if signed_output:
                if (expected_output_slice >> msb_index) & 1 > 0:
                    # The MSB is the sign bit. If it is 1 then the slice is a
                    # negative number so we need to get it in range for the
                    # expected_output_val signal. Subtract the slice upper
                    # bound to get the expected_output_slice in range.
                    expected_output_slice = (
                        expected_output_slice - slice_val_upper_bound)

            # Use the expected_output_slice to drive the expected_output_val.
            # This aligns expected output with the input data.
            expected_output_val.next = expected_output_slice

            # Check that signal out always equals the expected output
            assert(signal_out==expected_output_val)

        return_objects.append(stim_check)

        return return_objects

    def base_test(
        self, signal_in_bitwidth=None, slice_bitwidth=None, slice_offset=None,
        test_boolean_signal_out=False, signed_output=False):

        if signal_in_bitwidth is None:
            signal_in_bitwidth = random.randrange(1, 33)

        if slice_bitwidth is None:
            slice_bitwidth = (
                random.randrange(1, signal_in_bitwidth+1))

        if slice_offset is None:
            slice_offset = (
                random.randrange(0, signal_in_bitwidth-slice_bitwidth+1))

        dut_wrapper_args, dut_wrapper_arg_types = (
            test_args_setup(
                signal_in_bitwidth, slice_bitwidth, slice_offset,
                signed_output=signed_output))

        if test_boolean_signal_out:
            # Overwrite the signal_out with a boolean signal
            assert(slice_bitwidth == 1)
            assert(len(dut_wrapper_args['signal_out']) == 1)
            dut_wrapper_args['signal_out'] = Signal(False)

        cycles = 2000

        @block
        def stimulate_check(**dut_wrapper_args):

            return_objects = []

            return_objects.append(
                self.check_signal_slicer(**dut_wrapper_args))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, signal_slicer_wrapper, signal_slicer_wrapper,
            dut_wrapper_args, dut_wrapper_arg_types,
            custom_sources=[(stimulate_check, (), dut_wrapper_args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_random_slice(self):
        ''' The `signal_slicer` should connect the correct slice of
        `signal_in` to `signal_out` so that `signal_out` always equals the
        `signal_in` slice.

        The slice is defined by `slice_offset` and `slice_bitwidth`. So
        `signal_out` should always equal
        `signal_in[slice_offset+slice_bitwidth: slice_offset]`.
        '''
        self.base_test()

    def test_min_offset(self):
        ''' The `signal_slicer` should work correctly with a `slice_offset`
        of 0.
        '''
        self.base_test(slice_offset=0)

    def test_max_offset(self):
        ''' The `signal_slicer` should work correctly with a `slice_offset`
        which is equal to the highest bit in `signal_in`. Note that `bitwidth`
        should be 1 in this case.
        '''
        signal_in_bitwidth = random.randrange(1, 33)

        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            slice_bitwidth=1,
            slice_offset=signal_in_bitwidth-1,)

    def test_min_bitwidth(self):
        ''' The `signal_slicer` should work correctly with a `slice_bitwidth`
        of 1.
        '''
        self.base_test(slice_bitwidth=1)

    def test_max_bitwidth(self):
        ''' The `signal_slicer` should work correctly with a `slice_bitwidth`
        which is equal to the bitwidth of `signal_in`. Note that
        `slice_offset` should be 0 in this case.
        '''
        signal_in_bitwidth = random.randrange(1, 33)

        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            slice_bitwidth=signal_in_bitwidth,
            slice_offset=0,)

    def test_bool_output(self):
        ''' The `signal_slicer` should work correctly with a `slice_bitwidth`
        of 1 and a boolean `signal_out`.
        '''
        self.base_test(
            slice_bitwidth=1,
            test_boolean_signal_out=True)

    def test_signed_random_slice(self):
        ''' When `signal_out` is a signed signal, the `signal_slicer` should
        convert the slice to a signed value before assigning it to
        `signal_out`.
        '''
        self.base_test(signed_output=True)

    def test_signed_min_offset(self):
        ''' When `signal_out` is a signed signal, the `signal_slicer` should
        work correctly with a `slice_offset` of 0.
        '''
        self.base_test(
            slice_offset=0,
            signed_output=True)

    def test_signed_max_offset(self):
        ''' When `signal_out` is a signed signal, the `signal_slicer` should
        work correctly with a `slice_offset` which is equal to the highest bit
        in `signal_in`. Note that `bitwidth` should be 1 in this case.
        '''
        signal_in_bitwidth = random.randrange(1, 33)

        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            slice_bitwidth=1,
            slice_offset=signal_in_bitwidth-1,
            signed_output=True)

    def test_signed_min_bitwidth(self):
        ''' When `signal_out` is a signed signal, the `signal_slicer` should
        work correctly with a `slice_bitwidth` of 1.
        '''
        self.base_test(
            slice_bitwidth=1,
            signed_output=True)

    def test_signed_max_bitwidth(self):
        ''' When `signal_out` is a signed signal, the `signal_slicer` should
        work correctly with a `slice_bitwidth` which is equal to the bitwidth
        of `signal_in`. Note that `slice_offset` should be 0 in this case.
        '''
        signal_in_bitwidth = random.randrange(1, 33)

        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            slice_bitwidth=signal_in_bitwidth,
            slice_offset=0,
            signed_output=True)

class TestSignalSlicerVivadoVhdl(
    KeaVivadoVHDLTestCase, TestSignalSlicer):
    pass

class TestSignalSlicerVivadoVerilog(
    KeaVivadoVerilogTestCase, TestSignalSlicer):
    pass
