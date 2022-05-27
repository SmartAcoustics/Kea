import random

from myhdl import Signal, intbv, block, always

from kea.test_utils import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._combined_signal_assigner import combined_signal_assigner

def generate_random_input_signals(
    min_n_input_signals, n_input_signals_upper_bound,
    total_input_bitwidth_upper_bound):
    ''' Generate a random list of `input_signals`.
    '''

    # If this is not the case then it would be impossible to create enough
    # input signals and stay within the total_input_bitwidth_upper_bound
    assert(total_input_bitwidth_upper_bound > min_n_input_signals)

    # If this is not the case then it may not be possible to create enough
    # input signals and stay within the total_input_bitwidth_upper_bound
    assert(total_input_bitwidth_upper_bound >= n_input_signals_upper_bound)

    # Generate a random number of input signals
    n_input_signals = (
        random.randrange(min_n_input_signals, n_input_signals_upper_bound))

    # Calculate the upper bound on the input signals bitwidth which will stay
    # within the total_input_bitwidth_upper_bound
    sig_bitwidth_upper_bound = (
        (total_input_bitwidth_upper_bound-1)//n_input_signals + 1)

    # Generate input signals
    sig_bitwidth = random.randrange(1, sig_bitwidth_upper_bound)
    input_signals = [
        Signal(intbv(0)[sig_bitwidth:]) for n in range(n_input_signals)]

    total_input_bitwidth = sig_bitwidth*n_input_signals

    return input_signals, total_input_bitwidth

class TestCombinedSignalAssignerInterface(KeaTestCase):
    ''' The combined_signal_assigner should reject incompatible interfaces and
    arguments.
    '''

    def test_empty_input_signals(self):
        ''' The `combined_signal_assigner` should raise an error if the
        `input_signals` is an empty list.
        '''
        input_signals = []
        signal_out = Signal(intbv(0)[32:])

        self.assertRaisesRegex(
            ValueError,
            ('combined_signal_assigner: input_signals should contain at '
             'least one signal.'),
            combined_signal_assigner,
            input_signals,
            signal_out,
            )

    def test_input_signals_of_varying_widths(self):
        ''' The `combined_signal_assigner` should raise an error if the
        `input_signals` contain signal which are not all the same length.
        '''
        input_signals, total_input_bitwidth = (
            generate_random_input_signals(2, 11, 129))
        input_sig_to_vary = random.choice(range(len(input_signals)))

        invalid_bitwidth = len(input_signals[input_sig_to_vary]) + 1
        input_signals[input_sig_to_vary] = Signal(intbv(0)[invalid_bitwidth:])

        signal_out = Signal(intbv(0)[total_input_bitwidth:])

        self.assertRaisesRegex(
            ValueError,
            ('combined_signal_assigner: All signals in the '
             'input_signals list should be the same bitwidth.'),
            combined_signal_assigner,
            input_signals,
            signal_out,
            )

    def test_invalid_signal_out_bitwidth(self):
        ''' The `combined_signal_assigner` should raise an error if the
        `signal_out` is not wide enough for the combined `input_signals`.
        '''
        input_signals, total_input_bitwidth = (
            generate_random_input_signals(2, 11, 129))

        signal_out_bitwidth = random.randrange(1, total_input_bitwidth)
        signal_out = Signal(intbv(0)[signal_out_bitwidth:])

        self.assertRaisesRegex(
            ValueError,
            ('combined_signal_assigner: The signal_out is not wide enough '
             'for all of the input_signals.'),
            combined_signal_assigner,
            input_signals,
            signal_out,
            )

@block
def combined_signal_assigner_wrapper(clock, input_signals, signal_out):
    ''' We need to wrap the combined_signal_assigner as veriutils requires
    the DUT to take a clock.
    '''

    return combined_signal_assigner(input_signals, signal_out)

class TestCombinedSignalAssigner(KeaTestCase):

    def setUp(self):
        clock = Signal(False)
        input_signals, total_input_bitwidth = (
            generate_random_input_signals(2, 11, 129))
        signal_out = Signal(intbv(0)[total_input_bitwidth:])

        self.args = {
            'clock': clock,
            'input_signals': input_signals,
            'signal_out': signal_out,
        }

        self.arg_types = {
            'clock': 'clock',
            'input_signals': 'custom',
            'signal_out': 'output',
        }

    @block
    def random_signal_driver(self, clock, sig_to_drive):

        val_upper_bound = 2**len(sig_to_drive)

        @always(clock.posedge)
        def driver():

            sig_to_drive.next = random.randrange(val_upper_bound)

        return driver

    @block
    def check_combined_signal_assigner(self, **kwargs):

        clock = kwargs['clock']
        input_signals = kwargs['input_signals']
        signal_out = kwargs['signal_out']

        return_objects = []

        individual_sig_in_bitwidth = len(input_signals[0])

        for sig_in in input_signals:
            # Sanity check to make sure all input signals are the same
            # bitwidth
            assert(len(sig_in) == individual_sig_in_bitwidth)

            # Create a random signal driver for each input
            return_objects.append(self.random_signal_driver(clock, sig_in))

        @always(clock.posedge)
        def check():

            expected_val = 0
            for n in range(len(input_signals)):
                expected_val |= (
                    input_signals[n] << n*individual_sig_in_bitwidth)

            assert(signal_out == expected_val)

        return_objects.append(check)

        return return_objects

    def test_combined_signal_assigner(self):
        ''' The `combined_signal_assigner` block should concatenate all
        signals in the `input_signals` list and use them to drive
        `signal_out`.
        '''

        cycles = 2000

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(
                self.check_combined_signal_assigner(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, combined_signal_assigner_wrapper,
            combined_signal_assigner_wrapper, self.args, self.arg_types,
            custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_output_bitwidth_wider_than_input_bitwidth(self):
        ''' The `combined_signal_assigner` block should work correctly when
        the output is wider than the input.
        '''

        cycles = 2000

        # Sum up the total input bitwidth
        total_input_bitwidth = 0
        for sig_in in self.args['input_signals']:
            total_input_bitwidth += len(sig_in)

        # Generate a signal_out which is wider than the input
        min_sig_out_bitwidth = total_input_bitwidth+1
        signal_out_bitwidth = (
            random.randrange(min_sig_out_bitwidth, min_sig_out_bitwidth*2))
        self.args['signal_out'] = Signal(intbv(0)[signal_out_bitwidth:])

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(
                self.check_combined_signal_assigner(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, combined_signal_assigner_wrapper,
            combined_signal_assigner_wrapper, self.args, self.arg_types,
            custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_one_bit_input_signals(self):
        ''' The `combined_signal_assigner` block should work correctly when
        the input signals are all 1 bit wide.
        '''

        cycles = 2000

        n_input_signals = random.randrange(2, 33)

        # Generate input signals which are one bit wide.
        self.args['input_signals'] = [
            Signal(intbv(0)[1:]) for n in range(n_input_signals)]
        self.args['signal_out'] = Signal(intbv(0)[n_input_signals:])

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(
                self.check_combined_signal_assigner(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, combined_signal_assigner_wrapper,
            combined_signal_assigner_wrapper, self.args, self.arg_types,
            custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_boolean_input_signals(self):
        ''' The `combined_signal_assigner` block should function correctly
        when the input signals are all booleans.
        '''

        cycles = 2000

        n_input_signals = random.randrange(2, 33)

        # Generate input signals which are one bit wide.
        self.args['input_signals'] = [
            Signal(False) for n in range(n_input_signals)]
        self.args['signal_out'] = Signal(intbv(0)[n_input_signals:])

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(
                self.check_combined_signal_assigner(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, combined_signal_assigner_wrapper,
            combined_signal_assigner_wrapper, self.args, self.arg_types,
            custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_single_input_signals(self):
        ''' The `combined_signal_assigner` block should function correctly
        when the `input_signals` list contains a single signal.
        '''

        cycles = 2000

        n_input_signals = 1

        self.args['input_signals'], total_input_bitwidth = (
            generate_random_input_signals(
                n_input_signals, n_input_signals+1, 65))
        self.args['signal_out'] = Signal(intbv(0)[total_input_bitwidth:])

        @block
        def test(**kwargs):

            return_objects = []

            return_objects.append(
                self.check_combined_signal_assigner(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, combined_signal_assigner_wrapper,
            combined_signal_assigner_wrapper, self.args, self.arg_types,
            custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestCombinedSignalAssignerVivadoVhdl(
    KeaVivadoVHDLTestCase, TestCombinedSignalAssigner):
    pass

class TestCombinedSignalAssignerVivadoVerilog(
    KeaVivadoVerilogTestCase, TestCombinedSignalAssigner):
    pass
