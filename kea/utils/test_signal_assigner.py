import random

from myhdl import *

from jackdaw.test_utils.base_test import (
    JackdawTestCase, JackdawVivadoVHDLTestCase, JackdawVivadoVerilogTestCase)

from ._signal_assigner import signal_assigner

class TestSignalAssignerInterfaceSimulation(JackdawTestCase):
    ''' The signal_assigner should reject incompatible interfaces and
    arguments.
    '''

    def test_invalid_widths(self):
        ''' The signal_assigner should raise a value error if the signal_out
        is not wide enough to take the signal_in shifted by offset.
        '''
        in_width, out_width = random.sample(range(1, 64), 2)

        invalid_offset = random.randrange(out_width-in_width+1, out_width*2)

        signal_in = Signal(intbv(0)[in_width:])
        signal_out = Signal(intbv(0)[out_width:])

        self.assertRaisesRegex(
            ValueError,
            'signal_out must be wide enough to accomodate the signal_in '
            'shifted by offset.',
            signal_assigner,
            signal_in,
            signal_out,
            invalid_offset,
            )

    def test_non_boolean_in_boolean_out(self):
        ''' The signal_assigner should raise a value error if the signal_out
        is a boolean and signal_in is wider than 1.
        '''
        in_width = random.randrange(2, 64)
        offset = 0

        signal_in = Signal(intbv(0)[in_width:])
        signal_out = Signal(False)

        self.assertRaisesRegex(
            ValueError,
            'signal_out must be wide enough to accomodate the signal_in '
            'shifted by offset.',
            signal_assigner,
            signal_in,
            signal_out,
            offset,
            )

    def test_boolean_in_out_with_offset(self):
        ''' The signal_assigner should raise a value error if both the
        signal_out and signal_in are booleans but the offset is non zero.
        '''
        invalid_offset = random.randrange(1, 64)

        signal_in = Signal(False)
        signal_out = Signal(False)

        self.assertRaisesRegex(
            ValueError,
            'signal_out must be wide enough to accomodate the signal_in '
            'shifted by offset.',
            signal_assigner,
            signal_in,
            signal_out,
            invalid_offset,
            )

@block
def signal_assigner_wrapper(
    clock, signal_in, signal_out, offset, convert_to_signed):

    return signal_assigner(signal_in, signal_out, offset, convert_to_signed)

class TestSignalAssignerSimulation(JackdawTestCase):

    def setUp(self):

        self.clock = Signal(False)

        self.width = random.randrange(1, 64)

        self.signal_in = Signal(intbv(0)[self.width: 0])
        self.signal_out = Signal(intbv(0)[self.width: 0])

        self.offset = 0

        self.convert_to_signed = False

        # Define the default arguments for the DUT
        self.args = {
            'clock': self.clock,
            'signal_in': self.signal_in,
            'signal_out': self.signal_out,
            'offset': self.offset,
            'convert_to_signed': self.convert_to_signed,
        }

        self.arg_types = {
            'clock': 'clock',
            'signal_in': 'custom',
            'signal_out': 'output',
            'offset': 'non-signal',
            'convert_to_signed': 'non-signal',
        }

    def test_zero_offset_matching_widths(self):
        ''' If offset is 0 the output of the signal_assigner should track the
        input.
        '''

        self.args['offset'] = 0

        cycles = 2000

        @block
        def stimulate_check(
            clock, signal_in, signal_out, offset, convert_to_signed):

            @always(clock.posedge)
            def stim_check():

                # Randomly drive signal_in
                signal_in.next = random.randrange(2**len(signal_in))

                assert(signal_out == signal_in)

            return stim_check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, signal_assigner_wrapper, signal_assigner_wrapper,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_zero_offset_boolean_in_out(self):
        ''' The boolean output of the signal_assigner should always track the
        boolean input.
        '''

        self.args['signal_in'] = Signal(False)
        self.args['signal_out'] = Signal(False)

        cycles = 2000

        @block
        def stimulate_check(
            clock, signal_in, signal_out, offset, convert_to_signed):

            @always(clock.posedge)
            def stim_check():

                # Randomly drive signal_in
                signal_in.next = bool(random.randrange(2))

                assert(signal_out == signal_in)

            return stim_check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, signal_assigner_wrapper, signal_assigner_wrapper,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_zero_offset_wider_output(self):
        ''' If the output of the signal_assigner is wider than the input and
        offset is 0, the output should track the input.
        '''

        in_width = random.randrange(1, 64)
        out_width = random.randrange(in_width, in_width*2)

        self.args['signal_in'] = Signal(intbv(0)[in_width:])
        self.args['signal_out'] = Signal(intbv(0)[out_width:])

        self.args['offset'] = 0

        cycles = 2000

        @block
        def stimulate_check(
            clock, signal_in, signal_out, offset, convert_to_signed):

            @always(clock.posedge)
            def stim_check():

                # Randomly drive signal_in
                signal_in.next = random.randrange(2**len(signal_in))

                assert(signal_out == signal_in)

            return stim_check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, signal_assigner_wrapper, signal_assigner_wrapper,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_offset(self):
        ''' If the offset is not zero, the output of the signal_assigner
        should track the input shifted by offset.
        '''

        in_width = random.randrange(1, 64)
        offset = random.randrange(1, 32)

        # Generate a random out width which is wide enough for the shifted
        # input
        out_width = random.randrange(in_width+offset, (in_width+offset)*2)

        self.args['signal_in'] = Signal(intbv(0)[in_width:])
        self.args['signal_out'] = Signal(intbv(0)[out_width:])

        self.args['offset'] = offset

        cycles = 2000

        @block
        def stimulate_check(
            clock, signal_in, signal_out, offset, convert_to_signed):

            @always(clock.posedge)
            def stim_check():

                # Randomly drive signal_in
                signal_in.next = random.randrange(2**len(signal_in))

                assert(signal_out == signal_in << offset)

            return stim_check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, signal_assigner_wrapper, signal_assigner_wrapper,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_zero_offset_boolean_in(self):
        ''' If the offset is zero, and in the input is a boolean, bit zero of
        the output should track the boolean input.
        '''

        out_width = random.randrange(1, 64)

        self.args['signal_in'] = Signal(False)
        self.args['signal_out'] = Signal(intbv(0)[out_width:])

        self.args['offset'] = 0

        cycles = 2000

        @block
        def stimulate_check(
            clock, signal_in, signal_out, offset, convert_to_signed):

            @always(clock.posedge)
            def stim_check():

                # Randomly drive signal_in
                signal_in.next = random.randrange(2**len(signal_in))

                assert(signal_out == signal_in << offset)

            return stim_check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, signal_assigner_wrapper, signal_assigner_wrapper,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_boolean_in_with_offset(self):
        ''' If the offset is not zero, and in the input is a boolean, the
        specified offset bit in the output should track the boolean input.
        '''

        out_width = random.randrange(1, 64)
        offset = random.randrange(out_width)

        self.args['signal_in'] = Signal(False)
        self.args['signal_out'] = Signal(intbv(0)[out_width:])

        self.args['offset'] = offset

        cycles = 2000

        @block
        def stimulate_check(
            clock, signal_in, signal_out, offset, convert_to_signed):

            @always(clock.posedge)
            def stim_check():

                # Randomly drive signal_in
                signal_in.next = random.randrange(2**len(signal_in))

                assert(signal_out == signal_in << offset)

            return stim_check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, signal_assigner_wrapper, signal_assigner_wrapper,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_boolean_out(self):
        ''' If the output is a boolean, and the input is a one bit intbv the
        output should track the input.
        '''

        self.args['signal_in'] = Signal(intbv(0)[1:])
        self.args['signal_out'] = Signal(False)

        self.args['offset'] = 0

        cycles = 2000

        @block
        def stimulate_check(
            clock, signal_in, signal_out, offset, convert_to_signed):

            @always(clock.posedge)
            def stim_check():

                # Randomly drive signal_in
                signal_in.next = random.randrange(2**len(signal_in))

                assert(signal_out == signal_in)

            return stim_check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, signal_assigner_wrapper, signal_assigner_wrapper,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_zero_offset_convert_to_signed(self):
        ''' If offset is 0 and convert_to_signed is true, the output of the
        signal_assigner should track the signed version of the input.
        '''

        signal_width = random.randrange(2, 64)

        self.args['signal_in'] = Signal(intbv(0)[signal_width:])
        self.args['signal_out'] = (
            Signal(intbv(0, -2**(signal_width-1), 2**(signal_width-1))))

        self.args['offset'] = 0
        self.args['convert_to_signed'] = True

        cycles = 2000

        @block
        def stimulate_check(
            clock, signal_in, signal_out, offset, convert_to_signed):

            @always(clock.posedge)
            def stim_check():

                # Randomly drive signal_in
                signal_in.next = random.randrange(2**len(signal_in))

                assert(signal_out == signal_in.signed())

            return stim_check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, signal_assigner_wrapper, signal_assigner_wrapper,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_convert_to_signed_with_offset(self):
        ''' If the offset is not zero and convert_to_signed is true, the
        output of the signal_assigner should track the signed version of the
        input shifted by offset.
        '''

        in_width = random.randrange(1, 64)

        offset = random.randrange(1, 32)

        # Generate a random out width which is wide enough for the shifted
        # input
        out_width = random.randrange(in_width+offset, in_width+offset+10)

        self.args['signal_in'] = Signal(intbv(0)[in_width:])
        self.args['signal_out'] = (
            Signal(intbv(0, -2**(out_width-1), 2**(out_width-1))))

        self.args['offset'] = offset
        self.args['convert_to_signed'] = True

        cycles = 2000

        @block
        def stimulate_check(
            clock, signal_in, signal_out, offset, convert_to_signed):

            @always(clock.posedge)
            def stim_check():

                # Randomly drive signal_in
                signal_in.next = random.randrange(2**len(signal_in))

                assert(signal_out == signal_in.signed() << offset)

            return stim_check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, signal_assigner_wrapper, signal_assigner_wrapper,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestSignalAssignerVivadoVhdlSimulation(
    JackdawVivadoVHDLTestCase, TestSignalAssignerSimulation):
    pass

class TestSignalAssignerVivadoVerilogSimulation(
    JackdawVivadoVerilogTestCase, TestSignalAssignerSimulation):
    pass
