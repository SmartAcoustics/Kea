import random

from myhdl import *

from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._constant_assigner import constant_assigner

class TestConstantAssignerInterfaceSimulation(KeaTestCase):
    ''' The constant_assigner should reject incompatible interfaces and
    arguments.
    '''

    def test_oversized_constant(self):
        ''' The constant_assigner should raise a value error if the constant
        is too large for the signal.
        '''

        signal_width = random.randrange(1, 33)
        constant = random.randrange(2**signal_width, 2**signal_width + 20)
        signal = Signal(intbv(0)[signal_width:])

        self.assertRaisesRegex(
            ValueError,
            'Constant is too large for the signal',
            constant_assigner,
            constant,
            signal,
        )

    def test_negative_constant(self):
        ''' The constant_assigner should raise a value error if the constant
        is negative.
        '''

        constant = random.randrange(-100, 0)

        signal_width = random.randrange(1, 33)
        signal = Signal(intbv(0)[signal_width:])

        self.assertRaisesRegex(
            ValueError,
            'Constant must not be negative',
            constant_assigner,
            constant,
            signal,
        )

    def test_boolean_signal_large_constant(self):
        ''' The constant_assigner should raise a value error if an integer
        which is greater than 1 cannot be assigned to a boolean signal.
        '''

        constant = random.randrange(2, 10)

        signal = Signal(False)

        self.assertRaisesRegex(
            ValueError,
            'Constant is too large for the signal',
            constant_assigner,
            constant,
            signal,
        )

@block
def constant_assigner_wrapper(clock, constant, signal):

    return constant_assigner(constant, signal)

class TestConstantAssignerSimulation(KeaTestCase):

    def setUp(self):

        self.signal_width = random.randrange(1, 65)

        self.clock = Signal(False)
        self.constant = random.randrange(1, 2**self.signal_width)
        self.signal = Signal(intbv(0)[self.signal_width: 0])

        self.args = {
            'clock': self.clock,
            'constant': self.constant,
            'signal': self.signal,
        }

        self.arg_types = {
            'clock': 'clock',
            'constant': 'non-signal',
            'signal': 'output',
        }

    def test_intbv_signal(self):
        ''' The system should be able to drive intbv signals of any width with
        the constant.
        '''
        cycles = 2000

        @block
        def stimulate_check(clock, constant, signal):

            @always(clock.posedge)
            def stim_check():

                assert(signal == constant)

            return stim_check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, constant_assigner_wrapper, constant_assigner_wrapper,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_boolean_signal_boolean_constant(self):
        ''' The system should be able to drive boolean signals with a boolean
        constant.
        '''
        cycles = 2000

        self.args['constant'] = bool(random.randrange(2))
        self.args['signal'] = Signal(False)

        @block
        def stimulate_check(clock, constant, signal):

            @always(clock.posedge)
            def stim_check():

                assert(signal == constant)

            return stim_check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, constant_assigner_wrapper, constant_assigner_wrapper,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_boolean_signal_int_constant(self):
        ''' The system should be able to drive boolean signals with a 1 bit
        integer constant.
        '''
        cycles = 2000

        self.args['constant'] = random.randrange(2)
        self.args['signal'] = Signal(False)

        @block
        def stimulate_check(clock, constant, signal):

            @always(clock.posedge)
            def stim_check():

                assert(signal == constant)

            return stim_check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, constant_assigner_wrapper, constant_assigner_wrapper,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_one_bit_intbv_signal_int_constant(self):
        ''' The system should be able to drive 1 bit intbv signals with a 1
        bit integer constant.
        '''
        cycles = 2000

        self.args['constant'] = random.randrange(2)
        self.args['signal'] = Signal(intbv(0)[1:0])

        @block
        def stimulate_check(clock, constant, signal):

            @always(clock.posedge)
            def stim_check():

                assert(signal == constant)

            return stim_check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, constant_assigner_wrapper, constant_assigner_wrapper,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_one_bit_intbv_signal_boolean_constant(self):
        ''' The system should be able to drive 1 bit intbv signals with a
        boolean constant.
        '''
        cycles = 2000

        self.args['constant'] = bool(random.randrange(2))
        self.args['signal'] = Signal(intbv(0)[1:0])

        @block
        def stimulate_check(clock, constant, signal):

            @always(clock.posedge)
            def stim_check():

                assert(signal == constant)

            return stim_check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, constant_assigner_wrapper, constant_assigner_wrapper,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestConstantAssignerVivadoVhdlSimulation(
    KeaVivadoVHDLTestCase, TestConstantAssignerSimulation):
    pass

class TestConstantAssignerVivadoVerilogSimulation(
    KeaVivadoVerilogTestCase, TestConstantAssignerSimulation):
    pass
