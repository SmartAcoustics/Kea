import random
import copy

from myhdl import *

from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._double_buffer import double_buffer

class TestDoubleBufferSimulation(KeaTestCase):

    def setUp(self):

        self.clock = Signal(False)
        self.signal_in = Signal(False)
        self.signal_out = Signal(False)

        self.default_args = {
            'clock': self.clock,
            'signal_in': self.signal_in,
            'signal_out': self.signal_out,
        }

        self.default_arg_types = {
            'clock': 'clock',
            'signal_in': 'custom',
            'signal_out': 'output',
        }

    def test_output(self):
        ''' The double buffer should output the input value with a two cycle
        delay.
        '''

        cycles = 1000

        @block
        def stimulate_and_check(clock, signal_in, signal_out):

            test_data = {'expected_output_pipeline': [False, False],
                         'expected_output': False,}

            @always(clock.posedge)
            def stim_check():

                signal_in.next = bool(random.getrandbits(1))

                test_data['expected_output_pipeline'].append(
                    copy.copy(signal_in.val))

                test_data['expected_output'] = (
                    test_data['expected_output_pipeline'].pop(0))

                self.assertTrue(test_data['expected_output']==signal_out)

            return stim_check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, double_buffer, double_buffer,
            self.default_args, self.default_arg_types,
            custom_sources=[(stimulate_and_check, (), self.default_args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_init_val(self):
        ''' If provided, the double buffer should initialize the intermediate
        signal with the `init_val` argument. This is useful if the input and
        output signals are initialised True.
        '''

        cycles = 1000

        init_val = True

        self.default_args['init_val'] = init_val
        self.default_arg_types['init_val'] = 'non-signal'

        self.default_args['signal_in'] = Signal(init_val)
        self.default_args['signal_out'] = Signal(init_val)

        @block
        def stimulate_and_check(clock, signal_in, signal_out, init_val):

            test_data = {'expected_output_pipeline': [init_val, init_val],
                         'expected_output': init_val,}

            @always(clock.posedge)
            def stim_check():

                signal_in.next = bool(random.getrandbits(1))

                test_data['expected_output_pipeline'].append(
                    copy.copy(signal_in.val))

                test_data['expected_output'] = (
                    test_data['expected_output_pipeline'].pop(0))

                self.assertTrue(test_data['expected_output']==signal_out)

            return stim_check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, double_buffer, double_buffer,
            self.default_args, self.default_arg_types,
            custom_sources=[(stimulate_and_check, (), self.default_args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestDoubleBufferVivadoVhdlSimulation(
    KeaVivadoVHDLTestCase, TestDoubleBufferSimulation):
    pass

class TestDoubleBufferVivadoVerilogSimulation(
    KeaVivadoVerilogTestCase, TestDoubleBufferSimulation):
    pass
