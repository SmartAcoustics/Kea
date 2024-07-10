import random

from myhdl import Signal, intbv, block, always, StopSimulation

from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._synchronous_saturating_rounding_slicer import (
    synchronous_saturating_rounding_slicer)

def test_args_setup(
    signal_in_bitwidth, signal_out_bitwidth, slice_offset, signed_in_out):
    ''' Generate the arguments and argument types for the DUT.
    '''

    if signed_in_out:
        signal_in_max = 2**(signal_in_bitwidth-1)
        signal_in_min = -2**(signal_in_bitwidth-1)
        signal_in = Signal(intbv(0, min=signal_in_min, max=signal_in_max))

        signal_out_max = 2**(signal_out_bitwidth-1)
        signal_out_min = -2**(signal_out_bitwidth-1)
        signal_out = Signal(intbv(0, min=signal_out_min, max=signal_out_max))

    else:
        signal_in = Signal(intbv(0)[signal_in_bitwidth:])
        signal_out = Signal(intbv(0)[signal_out_bitwidth:])

    args = {
        'clock': Signal(False),
        'enable': Signal(False),
        'signal_in': signal_in,
        'signal_out': signal_out,
        'slice_offset': slice_offset,
    }

    arg_types = {
        'clock': 'clock',
        'enable': 'custom',
        'signal_in': 'custom',
        'signal_out': 'output',
        'slice_offset': 'non-signal',
    }

    return args, arg_types

def round_and_saturate(
    val, signal_out_incl_lower_bound, signal_out_excl_upper_bound,
    slice_offset):
    ''' This function rounds and saturates `val`.
    '''

    divisor = 2**slice_offset

    division_result, remainder = divmod(val, divisor)
    remainder_fraction = remainder/divisor

    if remainder_fraction == 0.5:
        # Round to even
        if division_result % 2 == 0:
            rounded = division_result

        else:
            rounded = division_result + 1

    elif remainder_fraction > 0.5:
        # Round up
        rounded = division_result + 1

    else:
        # Round down
        rounded = division_result

    if rounded >= signal_out_excl_upper_bound:
        rounded_and_saturated = signal_out_excl_upper_bound - 1

    elif rounded < signal_out_incl_lower_bound:
        rounded_and_saturated = signal_out_incl_lower_bound

    else:
        rounded_and_saturated = rounded

    return rounded_and_saturated

class TestSynchronousSaturatingRoundingSlicerInterface(KeaTestCase):
    ''' The DUT should reject incompatible interfaces and arguments.
    '''

    def setUp(self):

        signal_in_bitwidth = random.randrange(1, 33)
        slice_offset = random.randrange(0, signal_in_bitwidth)
        signal_out_bitwidth = (
            random.randrange(1, signal_in_bitwidth-slice_offset+1))

        self.dut_args, _dut_arg_types = (
            test_args_setup(
                signal_in_bitwidth, signal_out_bitwidth, slice_offset,
                signed_in_out=False))

    def test_invalid_signal_in_type(self):
        ''' The `synchronous_saturating_rounding_slicer` should raise an error
        if `signal_in` is not an intbv signal.
        '''
        self.dut_args['signal_in'] = Signal(False)

        self.assertRaisesRegex(
            TypeError,
            ('synchronous_saturating_rounding_slicer: signal_in should be an '
             'intbv signal'),
            synchronous_saturating_rounding_slicer,
            **self.dut_args,)

    def test_invalid_signal_out_type(self):
        ''' The `synchronous_saturating_rounding_slicer` should raise an error
        if `signal_out` is not an intbv signal.
        '''
        self.dut_args['signal_out'] = Signal(False)

        self.assertRaisesRegex(
            TypeError,
            ('synchronous_saturating_rounding_slicer: signal_out should be '
             'an intbv signal'),
            synchronous_saturating_rounding_slicer,
            **self.dut_args,)

    def test_invalid_slice_offset(self):
        ''' The `synchronous_saturating_rounding_slicer` should raise an error
        if `slice_offset` exceeds the bit width of `signal_in`.
        '''
        signal_in_bitwidth = len(self.dut_args['signal_in'])
        self.dut_args['slice_offset'] = (
            random.randrange(signal_in_bitwidth, signal_in_bitwidth+10))

        self.assertRaisesRegex(
            ValueError,
            ('synchronous_saturating_rounding_slicer: slice_offset should be '
             'less than the bitwidth of signal_in'),
            synchronous_saturating_rounding_slicer,
            **self.dut_args,)

    def test_negative_slice_offset(self):
        ''' The `synchronous_saturating_rounding_slicer` should raise an error
        if `slice_offset` is negative.
        '''
        self.dut_args['slice_offset'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('synchronous_saturating_rounding_slicer: slice_offset should be '
             'greater than or equal to 0.'),
            synchronous_saturating_rounding_slicer,
            **self.dut_args,)

    def test_invalid_bitfield(self):
        ''' The `synchronous_saturating_rounding_slicer` should raise an error
        if the sum of `slice_offset` and the bit width of `signal_out` exceeds
        the bit width of `signal_in`.
        '''
        min_invalid_bitwidth = (
            len(self.dut_args['signal_in']) -
            self.dut_args['slice_offset'] + 1)
        invalid_bitwidth = (
            random.randrange(min_invalid_bitwidth, min_invalid_bitwidth+10))

        self.dut_args['signal_out'] = Signal(intbv(0)[invalid_bitwidth:])

        self.assertRaisesRegex(
            ValueError,
            ('synchronous_saturating_rounding_slicer: the slice bitfield '
             'should fit within signal_in'),
            synchronous_saturating_rounding_slicer,
            **self.dut_args,)

    def test_signed_input_unsigned_output(self):
        ''' The `synchronous_saturating_rounding_slicer` should raise an error
        if `signal_in` is signed and `signal_out` is unsigned.
        '''
        self.dut_args['signal_in'] = Signal(intbv(0, min=-8, max=8))
        self.dut_args['signal_out'] = Signal(intbv(0, min=0, max=16))
        self.dut_args['slice_offset'] = 0

        self.assertRaisesRegex(
            TypeError,
            ('synchronous_saturating_rounding_slicer: both signal_in and '
             'signal_out should signed or both should be unsigned.'),
            synchronous_saturating_rounding_slicer,
            **self.dut_args,)

    def test_unsigned_input_signed_output(self):
        ''' The `synchronous_saturating_rounding_slicer` should raise an error
        if `signal_in` is unsigned and `signal_out` is signed.
        '''
        self.dut_args['signal_in'] = Signal(intbv(0, min=0, max=16))
        self.dut_args['signal_out'] = Signal(intbv(0, min=-8, max=8))
        self.dut_args['slice_offset'] = 0

        self.assertRaisesRegex(
            TypeError,
            ('synchronous_saturating_rounding_slicer: both signal_in and '
             'signal_out should signed or both should be unsigned.'),
            synchronous_saturating_rounding_slicer,
            **self.dut_args,)

class TestSynchronousSaturatingRoundingSlicer(KeaTestCase):

    def setUp(self):
        self.test_count = 0
        self.tests_complete = False

    @block
    def end_tests(self, n_tests_to_run, **dut_args):

        clock = dut_args['clock']

        return_objects = []

        stop_simulation = Signal(False)

        @always(clock.posedge)
        def check():

            if self.test_count >= n_tests_to_run:
                # Give the DUT one more cycle before raising StopSimulation
                stop_simulation.next = True

            if stop_simulation:
                self.tests_complete = True
                raise StopSimulation

        return_objects.append(check)

        return return_objects

    def signal_bounds(self, signal):
        ''' Generate the inclusive lower bound and exclusive upper bound for
        signal.
        '''

        signal_bitwidth = len(signal)

        if signal.min is None:
            assert(signal.max is None)

            signal_incl_lower_bound = 0
            signal_excl_upper_bound = 2**signal_bitwidth

        elif signal.min < 0:
            assert(signal.max is not None)
            assert(signal.min == -2**(signal_bitwidth-1))
            assert(signal.max == 2**(signal_bitwidth-1))

            signal_incl_lower_bound = signal.min
            signal_excl_upper_bound = signal.max

        else:
            assert(signal.max is not None)
            assert(signal.min == 0)
            assert(signal.max == 2**signal_bitwidth)

            signal_incl_lower_bound = signal.min
            signal_excl_upper_bound = signal.max

        return signal_incl_lower_bound, signal_excl_upper_bound

    @block
    def stim(self, **dut_args):

        clock = dut_args['clock']
        enable = dut_args['enable']
        signal_in = dut_args['signal_in']
        signal_out = dut_args['signal_out']
        slice_offset = dut_args['slice_offset']

        return_objects = []

        signal_in_incl_lower_bound, signal_in_excl_upper_bound = (
            self.signal_bounds(signal_in))
        signal_out_incl_lower_bound, signal_out_excl_upper_bound = (
            self.signal_bounds(signal_out))

        shift_into_slice = slice_offset

        # Shift the bounds so that they end up in the slice.
        highest_non_sat_val = (
            (signal_out_excl_upper_bound-1) << shift_into_slice)
        lowest_non_sat_val = signal_out_incl_lower_bound << shift_into_slice
        first_low_sat_val = (
            (signal_out_incl_lower_bound-1) << shift_into_slice)
        first_high_sat_val = signal_out_excl_upper_bound << shift_into_slice

        if signal_in_excl_upper_bound > highest_non_sat_val+1:
            test_upper_saturation = True
        else:
            test_upper_saturation = False

        if signal_in_incl_lower_bound < lowest_non_sat_val:
            test_lower_saturation = True
        else:
            test_lower_saturation = False

        # Set up specific values to test as well as the random ones
        specific_values_to_test = [
            0, signal_in_incl_lower_bound, (signal_in_excl_upper_bound-1)]

        # Test the lowest value signal_out can take.
        assert(lowest_non_sat_val >= signal_in_incl_lower_bound)
        specific_values_to_test.append(lowest_non_sat_val)

        # Test the highest value signal_out can take. Shift the
        # signal_out_excl_upper_bound so that it ends up in the slice.
        assert(highest_non_sat_val < signal_in_excl_upper_bound)
        specific_values_to_test.append(highest_non_sat_val)

        if signal_in_incl_lower_bound <= first_low_sat_val:
            # Test the first value that is less than the signal_out range
            specific_values_to_test.append(first_low_sat_val)

        if signal_in_excl_upper_bound > first_high_sat_val:
            # Test the first value that is greater than the signal_out range
            specific_values_to_test.append(first_high_sat_val)

        # Remove any duplicate values in specific_values_to_test
        specific_values_to_test = list(set(specific_values_to_test))

        @always(clock.posedge)
        def stim_input():

            if enable:
                if random.random() < 0.03:
                    enable.next = False

            else:
                if random.random() < 0.05:
                    enable.next = True

            random_val = random.random()

            if random_val < 0.25:
                input_val = random.choice(specific_values_to_test)

            elif test_upper_saturation and random_val < 0.5:
                # Test random saturating value which is greater than the
                # signal_out range
                input_val = (
                    random.randrange(
                        highest_non_sat_val+1, signal_in_excl_upper_bound))

            elif test_lower_saturation and random_val < 0.75:
                # Test random saturating value which is less than the
                # signal_out range
                input_val = (
                    random.randrange(
                        signal_in_incl_lower_bound, lowest_non_sat_val))

            else:
                # Test random non saturating value
                input_val = (
                    random.randrange(
                        lowest_non_sat_val, highest_non_sat_val+1))


            # Drive signal_in with the input_val
            signal_in.next = input_val

        return_objects.append(stim_input)

        return return_objects

    @block
    def check(self, **dut_args):

        clock = dut_args['clock']
        enable = dut_args['enable']
        signal_in = dut_args['signal_in']
        signal_out = dut_args['signal_out']
        slice_offset = dut_args['slice_offset']

        return_objects = []

        signal_out_incl_lower_bound, signal_out_excl_upper_bound = (
            self.signal_bounds(signal_out))

        expected_signal_out = (
            Signal(intbv(
                0, min=signal_out_incl_lower_bound,
                max=signal_out_excl_upper_bound)))

        @always(clock.posedge)
        def check_output():

            input_val = int(signal_in.val)

            if enable:
                # Update the expected_signal_out
                expected_signal_out.next = (
                    round_and_saturate(
                        input_val, signal_out_incl_lower_bound,
                        signal_out_excl_upper_bound, slice_offset))

                self.test_count += 1

            # Check that signal out always equals the expected output
            assert(signal_out == expected_signal_out)

        return_objects.append(check_output)

        return return_objects

    def base_test(
        self, signal_in_bitwidth=None, signal_out_bitwidth=None,
        slice_offset=None, signed_in_out=False):

        if signal_in_bitwidth is None:
            signal_in_bitwidth = random.randrange(1, 33)

        if signal_out_bitwidth is None:
            signal_out_bitwidth = random.randrange(1, signal_in_bitwidth+1)

        if slice_offset is None:
            slice_offset = (
                random.randrange(0, signal_in_bitwidth-signal_out_bitwidth+1))

        dut_args, dut_arg_types = (
            test_args_setup(
                signal_in_bitwidth, signal_out_bitwidth, slice_offset,
                signed_in_out))

        cycles = 5000
        n_tests = 1000

        @block
        def stimulate_check(**dut_args):

            return_objects = []

            return_objects.append(self.stim(**dut_args))
            return_objects.append(self.check(**dut_args))
            return_objects.append(self.end_tests(n_tests, **dut_args))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_saturating_rounding_slicer,
            synchronous_saturating_rounding_slicer, dut_args, dut_arg_types,
            custom_sources=[(stimulate_check, (), dut_args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_zero_offset_equal_range_unsigned(self):
        ''' If `slice_offset` is zero and `signal_out` has the same unsigned
        range as `signal_in`, then `signal_in` should be assigned to
        `signal_out` without alteration.
        '''
        bitwidth = random.randrange(1, 33)
        self.base_test(
            signal_in_bitwidth=bitwidth,
            signal_out_bitwidth=bitwidth,
            slice_offset=0,
            signed_in_out=False)

    def test_zero_offset_equal_range_signed(self):
        ''' If `slice_offset` is zero and `signal_out` has the same signed
        range as `signal_in`, then `signal_in` should be assigned to
        `signal_out` without alteration.
        '''
        bitwidth = random.randrange(1, 33)
        self.base_test(
            signal_in_bitwidth=bitwidth,
            signal_out_bitwidth=bitwidth,
            slice_offset=0,
            signed_in_out=True)

    def test_zero_offset_smaller_out_range_unsigned(self):
        ''' If `slice_offset` is zero and `signal_out` takes a smaller range
        of values than `signal_in`, then `signal_in` should be assigned to
        `signal_out` with saturation.

        If the value on `signal_in` is greater than the maximum value that
        `signal_out` can take, this block will saturate the `signal_out` at
        its maximum value.

        If the value on `signal_in` is less than the minimum value that
        `signal_out` can take, this block will saturate the `signal_out` at
        its minimum value.

        Otherwise the value on `signal_in` should be assigned to `signal_out`.

        The saturation should function correctly when `signal_in` and
        `signal_out` are both unsigned.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        signal_out_bitwidth = random.randrange(2, signal_in_bitwidth)
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_in_out=False)

    def test_zero_offset_smaller_out_range_signed(self):
        ''' The saturation should function correctly when `slice_offset` is
        zero, `signal_out` takes a smaller range of values than `signal_in`
        and both `signal_in` and `signal_out` are signed.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        signal_out_bitwidth = random.randrange(2, signal_in_bitwidth)
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_in_out=True)

    def test_zero_offset_output_bitwidth_of_one_unsigned(self):
        ''' The saturation should function correctly when `slice_offset` is
        zero, `signal_out` is 1 bit wide and both `signal_in` and `signal_out`
        are unsigned.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        signal_out_bitwidth = 1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_in_out=False)

    def test_zero_offset_output_bitwidth_of_one_signed(self):
        ''' The saturation should function correctly when `slice_offset` is
        zero, `signal_out` is 1 bit wide and both `signal_in` and `signal_out`
        are signed.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        signal_out_bitwidth = 1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_in_out=True)

    def test_zero_offset_large_output_bitwidth_unsigned(self):
        ''' The saturation should function correctly when `slice_offset` is
        zero, the bitwidth of `signal_out` is 1 bit less than the bitwidth of
        `signal_in` and both `signal_in` and `signal_out` are unsigned.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        signal_out_bitwidth = signal_in_bitwidth - 1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_in_out=False)

    def test_zero_offset_large_output_bitwidth_signed(self):
        ''' The saturation should function correctly when `slice_offset` is
        zero, the bitwidth of `signal_out` is 1 bit less than the bitwidth of
        `signal_in` and both `signal_in` and `signal_out` are signed.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        signal_out_bitwidth = signal_in_bitwidth - 1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_in_out=True)

    def test_zero_offset_input_bitwidth_two_unsigned(self):
        ''' The saturation should function correctly when `slice_offset` is
        zero, the bitwidth of `signal_in` is 1 and both `signal_in` and
        `signal_out` are unsigned.
        '''
        signal_in_bitwidth = 2
        signal_out_bitwidth = 1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_in_out=False)

    def test_zero_offset_input_bitwidth_two_signed(self):
        ''' The saturation should function correctly when `slice_offset` is
        zero, the bitwidth of `signal_in` is 1 and both `signal_in` and
        `signal_out` are signed.
        '''
        signal_in_bitwidth = 2
        signal_out_bitwidth = 1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_in_out=True)

    def test_zero_offset_large_bounds(self):
        ''' The `synchronous_saturating_rounding_slicer` should function
        correctly when the `signal_out` saturation values require more than 32
        bits.

        This test is included to make sure the conversion to VHDL is correct.
        There is a bug in the VHDL conversion code which presents when
        comparing to a constant which is greater than 2**32.
        '''
        signal_in_bitwidth = 41
        signal_out_bitwidth = 40
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_in_out=True)

    def test_rounding_and_saturation_unsigned(self):
        '''  If `slice_offset` is not zero, then `signal_in` should be
        assigned to `signal_out` with rounding and saturation.

        Lets call the bits up to `slice_offset` the fractional bits.

        If, after slicing off the fractional bits, the `signal_in` is greater
        than or equal to the maximum value that `signal_out` can take, the
        `synchronous_saturating_rounding_slicer` block should saturate
        `signal_out` at its maximum value.

        If, after slicing off the fractional bits, the `signal_in` is less
        than the minimum value that `signal_out` can take, the
        `synchronous_saturating_rounding_slicer` block should saturate
        `signal_out` at its minimum value.

        If the output has not saturated, the
        `synchronous_saturating_rounding_slicer` block should round the slice
        according to the fractional bits. The slice should be rounded using a
        round half to even strategy.

        If the fractional bits are greater than half the range of the
        fractional bits, then this block should round up.

        If the fractional bits are less than half the range of the fractional
        bits, then this block should round down.

        If the fractional bits equal half the range of the fractional bits
        then this block should round to the closest even value.

        Otherwise the value on `signal_in` should be assigned to `signal_out`.

        The saturation and rounding should function correctly when `signal_in`
        and `signal_out` are both unsigned.
        '''
        signal_in_bitwidth = random.randrange(5, 33)
        signal_out_bitwidth = random.randrange(2, signal_in_bitwidth-2)
        slice_offset = (
            random.randrange(1, signal_in_bitwidth-signal_out_bitwidth-1))
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_in_out=False)

    def test_rounding_and_saturation_signed(self):
        ''' The saturation and rounding should function correctly when
        `slice_offset` is not zero and both `signal_in` and `signal_out` are
        signed.
        '''
        signal_in_bitwidth = random.randrange(5, 33)
        signal_out_bitwidth = random.randrange(2, signal_in_bitwidth-2)
        slice_offset = (
            random.randrange(1, signal_in_bitwidth-signal_out_bitwidth-1))
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_in_out=True)

    def test_slice_offset_one_rounding_and_saturation_unsigned(self):
        ''' The saturation and rounding should function correctly when
        `slice_offset` is one and both `signal_in` and `signal_out` are
        unsigned.
        '''
        signal_in_bitwidth = random.randrange(5, 33)
        signal_out_bitwidth = random.randrange(2, signal_in_bitwidth-2)
        slice_offset = 1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_in_out=False)

    def test_slice_offset_one_rounding_and_saturation_signed(self):
        ''' The saturation and rounding should function correctly when
        `slice_offset` is one and both `signal_in` and `signal_out` are
        signed.
        '''
        signal_in_bitwidth = random.randrange(5, 33)
        signal_out_bitwidth = random.randrange(2, signal_in_bitwidth-2)
        slice_offset = 1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_in_out=True)

    def test_max_slice_offset_rounding_and_saturation_unsigned(self):
        ''' The saturation and rounding should function correctly when
        `slice_offset` is equal to the bitwidth of `signal_in` and both
        `signal_in` and `signal_out` are unsigned.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        signal_out_bitwidth = 1
        slice_offset = signal_in_bitwidth - 1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_in_out=False)

    def test_max_slice_offset_rounding_and_saturation_signed(self):
        ''' The saturation and rounding should function correctly when
        `slice_offset` is equal to the bitwidth of `signal_in` and both
        `signal_in` and `signal_out` are signed.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        signal_out_bitwidth = 1
        slice_offset = signal_in_bitwidth - 1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_in_out=True)

    def test_output_bitwidth_one_rounding_and_saturation_unsigned(self):
        ''' The saturation and rounding should function correctly when
        the bitwidth of `signal_out` is one and both `signal_in` and
        `signal_out` are unsigned.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        signal_out_bitwidth = 1
        slice_offset = random.randrange(1, signal_in_bitwidth)
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_in_out=False)

    def test_output_bitwidth_one_rounding_and_saturation_signed(self):
        ''' The saturation and rounding should function correctly when
        the bitwidth of `signal_out` is one and both `signal_in` and
        `signal_out` are signed.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        signal_out_bitwidth = 1
        slice_offset = random.randrange(1, signal_in_bitwidth)
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_in_out=True)

    def test_large_output_bitwidth_rounding_and_saturation_unsigned(self):
        ''' The saturation and rounding should function correctly when
        the bitwidth of `signal_out` is one less than `signal_in` and both
        `signal_in` and `signal_out` are unsigned.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        signal_out_bitwidth = signal_in_bitwidth - 1
        slice_offset = 1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_in_out=False)

    def test_large_output_bitwidth_rounding_and_saturation_signed(self):
        ''' The saturation and rounding should function correctly when
        the bitwidth of `signal_out` is one less than `signal_in` and both
        `signal_in` and `signal_out` are signed.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        signal_out_bitwidth = signal_in_bitwidth - 1
        slice_offset = 1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_in_out=True)

    def test_high_slice_rounding_and_saturation_unsigned(self):
        ''' The saturation and rounding should function correctly when the
        combination of `slice_offset` and `signal_out` bitwidth places the
        slice in the top bits of `signal_in` and both `signal_in` and
        `signal_out` are unsigned.
        '''
        signal_in_bitwidth = random.randrange(4, 33)
        signal_out_bitwidth = random.randrange(2, signal_in_bitwidth)
        slice_offset = signal_in_bitwidth - signal_out_bitwidth
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_in_out=False)

    def test_high_slice_rounding_and_saturation_signed(self):
        ''' The saturation and rounding should function correctly when the
        combination of `slice_offset` and `signal_out` bitwidth places the
        slice in the top bits of `signal_in` and both `signal_in` and
        `signal_out` are signed.
        '''
        signal_in_bitwidth = random.randrange(4, 33)
        signal_out_bitwidth = random.randrange(2, signal_in_bitwidth)
        slice_offset = signal_in_bitwidth - signal_out_bitwidth
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_in_out=True)

    def test_input_bitwidth_two_unsigned(self):
        ''' The saturation and rounding should function correctly when
        `slice_offset` is zero, the bitwidth of `signal_in` is 1 and both
        `signal_in` and `signal_out` are unsigned.
        '''
        signal_in_bitwidth = 2
        signal_out_bitwidth = 1
        slice_offset = 1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_in_out=False)

    def test_input_bitwidth_two_signed(self):
        ''' The saturation and rounding should function correctly when
        `slice_offset` is zero, the bitwidth of `signal_in` is 1 and both
        `signal_in` and
        `signal_out` are signed.
        '''
        signal_in_bitwidth = 2
        signal_out_bitwidth = 1
        slice_offset = 1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_in_out=True)

    def test_large_bounds(self):
        ''' The `synchronous_saturating_rounding_slicer` should function
        correctly when the `signal_out` saturation values require more than 32
        bits.

        This test is included to make sure the conversion to VHDL is correct.
        There is a bug in the VHDL conversion code which presents when
        comparing to a constant which is greater than 2**32.
        '''
        signal_in_bitwidth = 41
        signal_out_bitwidth = 40
        slice_offset = 1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_in_out=True)

class TestSynchronousSaturatingRoundingSlicerVivadoVhdl(
    KeaVivadoVHDLTestCase, TestSynchronousSaturatingRoundingSlicer):
    pass

class TestSynchronousSaturatingRoundingSlicerVivadoVerilog(
    KeaVivadoVerilogTestCase, TestSynchronousSaturatingRoundingSlicer):
    pass
