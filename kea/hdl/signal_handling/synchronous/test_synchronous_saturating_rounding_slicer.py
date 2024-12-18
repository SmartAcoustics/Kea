import random

from myhdl import Signal, intbv, block, always, StopSimulation

from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._synchronous_saturating_rounding_slicer import (
    synchronous_saturating_rounding_slicer)

def test_args_setup(
    signal_in_bitwidth, signal_out_bitwidth, slice_offset, signed_input,
    signed_output):
    ''' Generate the arguments and argument types for the DUT.
    '''

    if signed_input:
        signal_in_max = 2**(signal_in_bitwidth-1)
        signal_in_min = -2**(signal_in_bitwidth-1)
        signal_in = Signal(intbv(0, min=signal_in_min, max=signal_in_max))

    else:
        signal_in = Signal(intbv(0)[signal_in_bitwidth:])

    if signed_output:
        signal_out_max = 2**(signal_out_bitwidth-1)
        signal_out_min = -2**(signal_out_bitwidth-1)
        signal_out = Signal(intbv(0, min=signal_out_min, max=signal_out_max))

    else:
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
                signed_input=False, signed_output=False))

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

        # Shift the signal_out lower bound so that it ends up in the slice.
        lowest_non_sat_val = signal_out_incl_lower_bound << slice_offset
        # If slice_offset is not zero then the DUT will try to round. We add
        # 1 shifted up by slice_offset to make sure we don't round down to the
        # signal_out lower bound.
        lowest_val_inside_range = lowest_non_sat_val + (1 << slice_offset)
        first_low_sat_val = lowest_non_sat_val - 1

        # Shift the signal_out max value so that it ends up in the slice
        highest_non_sat_val = (signal_out_excl_upper_bound-1) << slice_offset
        # If slice_offset is not zero then the DUT will try to round. We
        # subtract 1 shifted up by slice_offset to make sure we don't round up
        # to the signal_out max value.
        highest_val_inside_range = highest_non_sat_val - (1 << slice_offset)
        first_high_sat_val = highest_non_sat_val + 1

        # Set up the values_to_test with a zero, the lowest value that
        # signal_in can take and the highest value that signal_in can take
        values_to_test = [
            0, signal_in_incl_lower_bound, signal_in_excl_upper_bound-1]

        if signal_in_incl_lower_bound < 0:
            # Add -1 to the values_to_test
            values_to_test.append(-1)

            if slice_offset > 0:
                # If slice_offset is non zero then shift -1 into the integer
                # bits and add it to the values_to_test
                values_to_test.append(-(1 << slice_offset))

        if signal_in_excl_upper_bound > 1:
            # Add 1 to the values_to_test
            values_to_test.append(1)

            if slice_offset > 0:
                # If slice_offset is non zero then shift 1 into the integer
                # bits and add it to the values_to_test.
                values_to_test.append(1 << slice_offset)

        # Create ranges_to_test
        ranges_to_test = []

        if signal_in_incl_lower_bound < lowest_non_sat_val:
            # Signal_in can take a value which is more negative than
            # signal_out.

            if lowest_non_sat_val < 0:
                # Add a random value in a range from the lowest value that
                # signal_out can take to 0. This is to make sure we test non
                # saturating values
                ranges_to_test.append((lowest_non_sat_val, 0))

            # Add a range that will cause the output to saturate
            ranges_to_test.append(
                (signal_in_incl_lower_bound, lowest_non_sat_val))
            # Add the lowest value which is inside the output signal range
            values_to_test.append(lowest_val_inside_range)
            # Add the lowest value isn't saturating
            values_to_test.append(lowest_non_sat_val)
            # Add the first negative saturating value
            values_to_test.append(first_low_sat_val)

        else:
            # The signal_in negative range is smaller than the signal_out
            # negative range
            if signal_in_incl_lower_bound < 0:
                # There are negative numbers available in the signal_in range
                # so add the negative range to ranges_to_test
                ranges_to_test.append((signal_in_incl_lower_bound, 0))

        if signal_in_excl_upper_bound > first_high_sat_val:
            # Signal_in can take a larger value than signal_out.

            if first_high_sat_val > 0:
                # Add a random value in a range from 0 to the highest value
                # that signal_out can take to 0. This is to make sure we test
                # non saturating values
                ranges_to_test.append((0, first_high_sat_val))

            # Add a range that will cause the output to saturate
            ranges_to_test.append(
                (first_high_sat_val, signal_in_excl_upper_bound))
            # Add the highest value which is inside the output signal range
            values_to_test.append(highest_val_inside_range)
            # Add the highest value isn't saturating
            values_to_test.append(highest_non_sat_val)
            # Add the first positive saturating value
            values_to_test.append(first_high_sat_val)

        else:
            # The signal_in positive range is smaller than the signal_out
            # positive range
            if signal_in_excl_upper_bound > 0:
                # There are positive numbers available in the signal_in range
                # so add the positive range to ranges_to_test
                ranges_to_test.append((0, signal_in_excl_upper_bound))

        # Remove any duplicate values in values_to_test and ranges_to_test
        values_to_test = list(set(values_to_test))
        ranges_to_test = list(set(ranges_to_test))

        # Remove any out of range values from values_to_test
        values_to_test = [
            val for val in values_to_test
            if val >= signal_in_incl_lower_bound and
            val < signal_in_excl_upper_bound]

        @always(clock.posedge)
        def stim_input():

            if enable:
                if random.random() < 0.03:
                    enable.next = False

            else:
                if random.random() < 0.05:
                    enable.next = True

            random_val = random.random()

            if random_val < 0.5:
                range_to_test = random.choice(ranges_to_test)

                # Sanity check the range_to_test only contains 2 values
                assert(len(range_to_test) == 2)

                # Generate a random value from range_to_test
                input_val = (
                    random.randrange(range_to_test[0], range_to_test[1]))

            else:
                # Choose a random value_to_test
                input_val = random.choice(values_to_test)

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
        slice_offset=None, signed_input=False, signed_output=False):

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
                signed_input, signed_output))

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

    ##################################
    # Zero offset, direct assignment #
    ##################################

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
            signed_input=False,
            signed_output=False)

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
            signed_input=True,
            signed_output=True)

    def test_zero_offset_unsigned_to_equal_upper_bound_signed(self):
        ''' If `slice_offset` is zero and `signal_out` is signed but has the
        same upper bound as the unsigned `signal_in`, then `signal_in` should
        be assigned to `signal_out` without alteration.
        '''
        signal_in_bitwidth = random.randrange(1, 33)
        signal_out_bitwidth = signal_in_bitwidth+1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_input=False,
            signed_output=True)

    def test_zero_offset_small_signed_to_bigger_signed(self):
        ''' If `slice_offset` is zero and `signal_out` is signed but has a
        larger range than the signed `signal_in`, then `signal_in` should
        be assigned to `signal_out` without alteration.
        '''
        signal_in_bitwidth = random.randrange(1, 33)
        signal_out_bitwidth = (
            random.randrange(signal_in_bitwidth+1, signal_in_bitwidth+5))
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_input=True,
            signed_output=True)

    def test_zero_offset_small_unsigned_to_bigger_unsigned(self):
        ''' If `slice_offset` is zero and `signal_out` is unsigned but has a
        larger range than the unsigned `signal_in`, then `signal_in` should
        be assigned to `signal_out` without alteration.
        '''
        signal_in_bitwidth = random.randrange(1, 33)
        signal_out_bitwidth = (
            random.randrange(signal_in_bitwidth+1, signal_in_bitwidth+5))
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_input=False,
            signed_output=False)

    def test_zero_offset_unsigned_to_greater_upper_bound_signed(self):
        ''' If `slice_offset` is zero and `signal_out` is signed but has a
        higher upper bound than the unsigned `signal_in`, then `signal_in`
        should be assigned to `signal_out` without alteration.
        '''
        signal_in_bitwidth = random.randrange(1, 33)
        signal_out_bitwidth = (
            random.randrange(signal_in_bitwidth+2, signal_in_bitwidth+6))
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_input=False,
            signed_output=True)

    ###############
    # Zero offset #
    ###############

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
            signed_input=False,
            signed_output=False)

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
            signed_input=True,
            signed_output=True)

    def test_zero_offset_signed_to_equal_upper_bound_unsigned(self):
        ''' The saturation should function correctly when `slice_offset` is
        zero and `signal_out` is unsigned but has the same upper bound as the
        signed `signal_in`.

        In this case, negative numbers on `signal_in` should cause the
        `signal_out` to saturate at 0.
        '''
        signal_out_bitwidth = random.randrange(1, 33)
        signal_in_bitwidth = signal_out_bitwidth+1
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_input=True,
            signed_output=False)

    def test_zero_offset_unsigned_to_smaller_signed(self):
        ''' The saturation should function correctly when `slice_offset` is
        zero, `signal_in` is unsigned and `signal_out` is signed and has an
        upper bound which is less than the `signal_in`.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        signal_out_bitwidth = random.randrange(2, signal_in_bitwidth+1)
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_input=False,
            signed_output=True)

    def test_zero_offset_signed_to_smaller_unsigned(self):
        ''' The saturation should function correctly when `slice_offset` is
        zero, `signal_in` is signed and `signal_out` is unsigned but has an
        upper bound which is less than the `signal_in`.
        '''
        signal_in_bitwidth = random.randrange(4, 33)
        signal_out_bitwidth = random.randrange(2, signal_in_bitwidth-1)
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_input=True,
            signed_output=False)

    def test_zero_offset_signed_to_greater_upper_bound_unsigned(self):
        ''' The saturation should function correctly when `slice_offset` is
        zero, `signal_in` is signed and `signal_out` is unsigned but has a
        higher upper bound than the unsigned `signal_in`.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        signal_out_bitwidth = (
            random.randrange(signal_in_bitwidth, signal_in_bitwidth+5))
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=0,
            signed_input=True,
            signed_output=False)

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
            signed_input=False,
            signed_output=False)

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
            signed_input=True,
            signed_output=True)

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
            signed_input=False,
            signed_output=False)

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
            signed_input=True,
            signed_output=True)

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
            signed_input=True,
            signed_output=True)

    ###################
    # Non zero offset #
    ###################

    def test_smaller_out_range_unsigned(self):
        '''  If `slice_offset` is not zero, then `signal_in` should be
        assigned to `signal_out` with rounding and saturation.

        Lets call the bits up to `slice_offset` the fractional bits.

        Lets call the rest of the bits the integer bits.

        If the integer bits are greater than or equal to the maximum value
        that `signal_out` can take, the
        `synchronous_saturating_rounding_slicer` block should saturate
        `signal_out` at its maximum value.

        If the integer bits are less than the minimum value that `signal_out`
        can take, the `synchronous_saturating_rounding_slicer` block should
        saturate `signal_out` at its minimum value.

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
        and `signal_out` are both unsigned and the `signal_out` range is
        smaller than the range of the integer bits.
        '''
        signal_in_bitwidth = random.randrange(5, 33)
        signal_out_bitwidth = random.randrange(2, signal_in_bitwidth-2)
        slice_offset = (
            random.randrange(1, signal_in_bitwidth-signal_out_bitwidth-1))
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_input=False,
            signed_output=False)

    def test_smaller_out_range_signed(self):
        ''' The saturation and rounding should function correctly when
        `slice_offset` is not zero and both `signal_in` and `signal_out` are
        signed and the `signal_out` range is smaller than the range of the
        integer bits.
        '''
        signal_in_bitwidth = random.randrange(5, 33)
        signal_out_bitwidth = random.randrange(2, signal_in_bitwidth-2)
        slice_offset = (
            random.randrange(1, signal_in_bitwidth-signal_out_bitwidth-1))

        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_input=True,
            signed_output=True)

    def test_equal_out_range_unsigned(self):
        ''' The rounding should function correctly when `slice_offset` is not
        zero and both `signal_in` and `signal_out` are unsigned and the
        `signal_out` range is equal to the range of the integer bits.

        Note that saturation will not be required in these circumstances.
        '''
        signal_in_bitwidth = random.randrange(5, 33)
        slice_offset = random.randrange(1, signal_in_bitwidth-1)
        signal_out_bitwidth = signal_in_bitwidth - slice_offset
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_input=False,
            signed_output=False)

    def test_equal_out_range_signed(self):
        ''' The rounding should function correctly when `slice_offset` is not
        zero and both `signal_in` and `signal_out` are signed and the
        `signal_out` range is equal to the range of the integer bits.

        Note that saturation will not be required in these circumstances.
        '''
        signal_in_bitwidth = random.randrange(5, 33)
        slice_offset = random.randrange(1, signal_in_bitwidth-1)
        signal_out_bitwidth = signal_in_bitwidth - slice_offset
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_input=True,
            signed_output=True)

    def test_unsigned_to_equal_upper_bound_signed(self):
        ''' The rounding should function correctly when `slice_offset` is not
        zero and `signal_out` is signed but has the same upper bound as the
        integer bits.

        Note that saturation will not be required in these circumstances.
        '''
        signal_in_bitwidth = random.randrange(5, 33)
        signal_out_bitwidth = signal_in_bitwidth+1
        slice_offset = random.randrange(1, signal_in_bitwidth-1)
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_input=False,
            signed_output=True)

    def test_signed_to_equal_upper_bound_unsigned(self):
        ''' The saturating and rounding should function correctly when
        `slice_offset` is not zero and `signal_out` is unsigned but has the
        same upper bound as the integer bits.

        Note negative numbers on `signal_in` will saturate the `signal_out` at
        0. There will be no positive saturation in these cirumstances.
        '''
        signal_out_bitwidth = random.randrange(5, 33)
        signal_in_bitwidth = signal_out_bitwidth+1
        slice_offset = random.randrange(1, signal_in_bitwidth-1)
        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_input=True,
            signed_output=False)

    def test_small_signed_to_bigger_signed(self):
        ''' The rounding should function correctly when `slice_offset` is not
        zero and `signal_out` is signed but has a greater range than the
        integer bits.

        Note that saturation will not be required in these circumstances.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        slice_offset = random.randrange(1, signal_in_bitwidth-1)

        n_integer_bits = signal_in_bitwidth-slice_offset
        signal_out_bitwidth = (
            random.randrange(n_integer_bits+1, n_integer_bits+5))

        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_input=True,
            signed_output=True)

    def test_small_unsigned_to_bigger_unsigned(self):
        ''' The rounding should function correctly when `slice_offset` is not
        zero and `signal_out` is unsigned but has a greater range than the
        integer bits.

        Note that saturation will not be required in these circumstances.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        slice_offset = random.randrange(1, signal_in_bitwidth-1)

        n_integer_bits = signal_in_bitwidth-slice_offset
        signal_out_bitwidth = (
            random.randrange(n_integer_bits+1, n_integer_bits+5))

        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_input=False,
            signed_output=False)

    def test_unsigned_to_smaller_signed(self):
        ''' The saturating and rounding should function correctly when
        `slice_offset` is not zero and `signal_out` is signed and has a
        smaller upper bound than the integer bits.

        Note Large positive numbers on `signal_in` will saturate `signal_out`
        positively.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        slice_offset = random.randrange(1, signal_in_bitwidth-1)

        n_integer_bits = signal_in_bitwidth-slice_offset
        signal_out_bitwidth = random.randrange(1, n_integer_bits)

        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_input=False,
            signed_output=True)

    def test_unsigned_to_bigger_signed(self):
        ''' The rounding should function correctly when `slice_offset` is not
        zero and `signal_out` is signed and has a bigger upper bound than the
        integer bits.

        Note that saturation will not be required in these circumstances.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        slice_offset = random.randrange(1, signal_in_bitwidth-1)

        n_integer_bits = signal_in_bitwidth-slice_offset
        signal_out_bitwidth = (
            random.randrange(n_integer_bits+2, n_integer_bits+6))

        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_input=False,
            signed_output=True)

    def test_signed_to_bigger_unsigned(self):
        ''' The saturating and rounding should function correctly when
        `slice_offset` is not zero and `signal_out` is unsigned but has a
        greater upper bound than the integer bits.

        Note negative numbers on `signal_in` will saturate the `signal_out` at
        0. There will be no positive saturation in these cirumstances.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        slice_offset = random.randrange(1, signal_in_bitwidth-1)

        n_integer_bits = signal_in_bitwidth-slice_offset
        signal_out_bitwidth = (
            random.randrange(n_integer_bits+1, n_integer_bits+5))

        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_input=True,
            signed_output=False)

    def test_signed_to_smaller_unsigned(self):
        ''' The saturating and rounding should function correctly when
        `slice_offset` is not zero and `signal_out` is unsigned and has a
        smaller upper bound than the integer bits.

        Note negative numbers on `signal_in` will saturate the `signal_out` at
        0. Large positive numbers will saturate positively.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        slice_offset = random.randrange(1, signal_in_bitwidth-1)

        n_integer_bits = signal_in_bitwidth-slice_offset
        signal_out_bitwidth = random.randrange(1, n_integer_bits)

        self.base_test(
            signal_in_bitwidth=signal_in_bitwidth,
            signal_out_bitwidth=signal_out_bitwidth,
            slice_offset=slice_offset,
            signed_input=True,
            signed_output=False)

    def test_slice_offset_one_unsigned(self):
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
            signed_input=False,
            signed_output=False)

    def test_slice_offset_one_signed(self):
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
            signed_input=True,
            signed_output=True)

    def test_output_bitwidth_one_unsigned(self):
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
            signed_input=False,
            signed_output=False)

    def test_output_bitwidth_one_signed(self):
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
            signed_input=True,
            signed_output=True)

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
            signed_input=False,
            signed_output=False)

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
            signed_input=True,
            signed_output=True)

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
            signed_input=True,
            signed_output=True)

class TestSynchronousSaturatingRoundingSlicerVivadoVhdl(
    KeaVivadoVHDLTestCase, TestSynchronousSaturatingRoundingSlicer):
    pass

class TestSynchronousSaturatingRoundingSlicerVivadoVerilog(
    KeaVivadoVerilogTestCase, TestSynchronousSaturatingRoundingSlicer):
    pass
