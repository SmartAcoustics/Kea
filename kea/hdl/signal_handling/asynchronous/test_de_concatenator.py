import random

from myhdl import Signal, intbv, block, always

from kea.testing.test_utils import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase,
    generate_value)

from ._de_concatenator import de_concatenator

@block
def de_concatenator_wrapper(clock, signal_in, output_signals):
    ''' We need to wrap the de_concatenator as the testing framework requires
    the DUT to take a clock.
    '''

    return de_concatenator(signal_in, output_signals)

def wrapper_args_setup(
    signal_in_bitwidth, n_output_signals, signal_out_bitwidth):
    ''' Generate the arguments and argument types for the DUT.
    '''

    signal_in = Signal(intbv(0)[signal_in_bitwidth:])
    output_signals = [
        Signal(intbv(0)[signal_out_bitwidth:])
        for n in range(n_output_signals)]

    wrapper_args = {
        'clock': Signal(False),
        'signal_in': signal_in,
        'output_signals': output_signals,
    }

    wrapper_arg_types = {
        'clock': 'clock',
        'signal_in': 'custom',
        'output_signals': 'output',
    }

    return wrapper_args, wrapper_arg_types

class TestDeConcatenatorInterface(KeaTestCase):
    ''' The de_concatenator should reject incompatible interfaces and
    arguments.
    '''

    def setUp(self):

        self.dut_wrapper_args, _dut_wrapper_arg_types = (
            wrapper_args_setup(
                signal_in_bitwidth=16,
                n_output_signals=16,
                signal_out_bitwidth=1))

    def test_empty_output_signals(self):
        ''' The `de_concatenator` should raise an error if the
        `output_signals` is an empty list.
        '''
        self.dut_wrapper_args['output_signals'] = []

        self.assertRaisesRegex(
            ValueError,
            ('de_concatenator: the output_signals list is empty.'),
            de_concatenator_wrapper,
            **self.dut_wrapper_args
            )

    def test_mismatched_output_bitwidths(self):
        ''' The `de_concatenator` should raise an error if the signal in the
        `output_signals` list are not all the same size.
        '''
        index = random.randrange(len(self.dut_wrapper_args['output_signals']))
        invalid_bitwidth = len(self.dut_wrapper_args['output_signals'][0]) + 1
        self.dut_wrapper_args['output_signals'][index] = (
            Signal(intbv(0)[invalid_bitwidth:]))

        self.assertRaisesRegex(
            ValueError,
            ('de_concatenator: all signals in the output_signals list '
             'should be the same bitwidth.'),
            de_concatenator_wrapper,
            **self.dut_wrapper_args
            )

    def test_invalid_total_output_bitwidth(self):
        ''' The `de_concatenator` should raise an error if the total bitwidth
        of the `output_signals` is greater than the bitwidth of `signal_in`.
        '''
        invalid_bitwidth = (
            random.randrange(1, len(self.dut_wrapper_args['signal_in'])))
        self.dut_wrapper_args['signal_in'] = (
            Signal)(intbv(0)[invalid_bitwidth:])

        self.assertRaisesRegex(
            ValueError,
            ('de_concatenator: the total output bitwidth should be less than '
            'or equal to the signal_in bitwidth.'),
            de_concatenator_wrapper,
            **self.dut_wrapper_args
            )

class TestDeConcatenator(KeaTestCase):

    @block
    def de_concatenator_stim_check(self, **dut_wrapper_args):

        clock = dut_wrapper_args['clock']
        signal_in = dut_wrapper_args['signal_in']
        output_signals = dut_wrapper_args['output_signals']

        return_objects = []

        signal_in_upper_bound = 2**len(signal_in)

        n_output_signals = len(output_signals)
        output_signal_bitwdith = len(output_signals[0])

        expected_outputs = [
            Signal(intbv(0)[output_signal_bitwdith:])
            for n in range(n_output_signals)]

        output_mask = 2**output_signal_bitwdith - 1

        @always(clock.posedge)
        def stim_check():

            # Generate a random stim_value
            stim_value = generate_value(0, signal_in_upper_bound, 0.1, 0.1)

            # Drive signal_in with the stim_value
            signal_in.next = stim_value

            for n in range(n_output_signals):
                # Generate the expected outputs (for next cycle)
                offset = n*output_signal_bitwdith
                expected_outputs[n].next = (
                    (stim_value >> offset) & output_mask)

                # Check currect outputs
                assert(output_signals[n] == expected_outputs[n])

        return_objects.append(stim_check)

        return return_objects

    def base_test(
        self, signal_in_bitwidth, n_output_signals, signal_out_bitwidth):

        dut_wrapper_args, dut_wrapper_arg_types = (
            wrapper_args_setup(
                signal_in_bitwidth, n_output_signals, signal_out_bitwidth))

        if not self.testing_using_vivado:
            cycles = 5000
        else:
            cycles = 1000

        @block
        def stimulate_check(**dut_wrapper_args):

            return_objects = []

            return_objects.append(
                self.de_concatenator_stim_check(**dut_wrapper_args))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, de_concatenator_wrapper, de_concatenator_wrapper,
            dut_wrapper_args, dut_wrapper_arg_types,
            custom_sources=[(stimulate_check, (), dut_wrapper_args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_one_bit_outputs_all_bits_assigned(self):
        ''' Let `n_output_signals` be the number of signals in the
        `output_signals` list.

        Let `output_bitwidth` be the bit width of all the signals in the
        `output_signals` list.

        The `de_concatenator` should split the `signal_in` into
        `n_output_signals` slices of `output_bitwidth` bits. These slices
        should be assigned to their corresponding output signal.

        For example, if the `input_signal` is 8 bits wide and `output_signals`
        contains 8 signals of 1 bit then:

            - `input_signal` bit 0 -> `output_signals` signal 0.
            - `input_signal` bit 1 -> `output_signals` signal 1.
            ...
            - `input_signal` bit 7 -> `output_signals` signal 7.
        '''
        signal_in_bitwidth = random.randrange(2, 33)
        n_output_signals = signal_in_bitwidth
        signal_out_bitwidth = 1

        self.base_test(
            signal_in_bitwidth,
            n_output_signals,
            signal_out_bitwidth)

    def test_random_output_bitwidth_all_bits_assigned(self):
        ''' The `de_concatenator` should work correctly when the
        `output_bitwidth` is greater than 1.
        '''

        signal_out_bitwidth = random.randrange(2, 9)
        n_output_signals = random.randrange(2, 6)
        signal_in_bitwidth = n_output_signals*signal_out_bitwidth

        self.base_test(
            signal_in_bitwidth,
            n_output_signals,
            signal_out_bitwidth)

    def test_one_bit_outputs_not_all_bits_assigned(self):
        ''' Let `total_output_bitwidth` be the sum of the bitwidths of the
        signals in `output_signals`.

        The `de_concatenator` should work correctly when the
        `output_bitwidth` is 1 and the `total_output_bitwidth` is less than
        bitwidth of `signal_in`.

        In this case, only the lower bits of `signal_in` should be sliced and
        assigned.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        n_output_signals = random.randrange(2, signal_in_bitwidth)
        signal_out_bitwidth = 1

        self.base_test(
            signal_in_bitwidth,
            n_output_signals,
            signal_out_bitwidth)

    def test_random_output_bitwidth_not_all_bits_assigned(self):
        ''' The `de_concatenator` should work correctly when the
        `output_bitwidth` is greater than 1 and the `total_output_bitwidth` is
        less than bitwidth of `signal_in`.
        '''
        signal_out_bitwidth = random.randrange(2, 9)
        n_output_signals = random.randrange(2, 6)
        total_output_bitwidth = n_output_signals*signal_out_bitwidth
        signal_in_bitwidth = (
            random.randrange(
                total_output_bitwidth+1, total_output_bitwidth+10))

        self.base_test(
            signal_in_bitwidth,
            n_output_signals,
            signal_out_bitwidth)

    def test_one_bit_input_and_output(self):
        ''' The `de_concatenator` should work correctly when `signal_in` is 1
        bit wide, and `output_signals` contains a single signal of 1 bit.
        '''
        signal_in_bitwidth = 1
        n_output_signals = 1
        signal_out_bitwidth = 1

        self.base_test(
            signal_in_bitwidth,
            n_output_signals,
            signal_out_bitwidth)

    def test_random_output_bitwidth_input_and_output(self):
        ''' The `de_concatenator` should work correctly when `output_signals`
        contains a single signal which is the same bitwidth as `signal_in`.
        '''
        signal_in_bitwidth = random.randrange(2, 33)
        n_output_signals = 1
        signal_out_bitwidth = signal_in_bitwidth

        self.base_test(
            signal_in_bitwidth,
            n_output_signals,
            signal_out_bitwidth)

    def test_single_output_smaller_than_input(self):
        ''' The `de_concatenator` should work correctly when `output_signals`
        contains a single signal which has a bitwidth which is less than
        `signal_in`.
        '''
        signal_in_bitwidth = random.randrange(3, 33)
        n_output_signals = 1
        signal_out_bitwidth = random.randrange(2, signal_in_bitwidth)

        self.base_test(
            signal_in_bitwidth,
            n_output_signals,
            signal_out_bitwidth)

class TestDeConcatenatorVivadoVhdl(
    KeaVivadoVHDLTestCase, TestDeConcatenator):
    pass

class TestDeConcatenatorVivadoVerilog(
    KeaVivadoVerilogTestCase, TestDeConcatenator):
    pass
