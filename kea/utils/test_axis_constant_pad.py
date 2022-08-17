
from myhdl import *
import random
import copy

from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)
from kea.axi import AxiStreamInterface

from ._axis_constant_pad import axis_constant_pad


class TestAxisConstantPad(KeaTestCase):

    def setUp(self):

        self.clock = Signal(False)
        self.enable = Signal(True)
        self.axis_in = AxiStreamInterface(4, use_TLAST=False)
        self.axis_out = AxiStreamInterface(4, use_TLAST=False)

        axis_in_signal_types = {
            'TDATA': 'random',
            'TVALID': 'random',
            'TREADY': 'output'}

        axis_out_signal_types = {
            'TDATA': 'output',
            'TVALID': 'output',
            'TREADY': 'random'}

        self.default_args = {
            'clock': self.clock,
            'enable': self.enable,
            'axis_in': self.axis_in,
            'axis_out': self.axis_out}

        self.default_arg_types = {
            'clock': 'clock',
            'enable': 'custom',
            'axis_in': axis_in_signal_types,
            'axis_out': axis_out_signal_types}

    def test_axis_in_interface(self):
        '''The axis_in port should be an instance of
        ``kea.axi.AxiStreamInterface``.

        Anything else should raise a ValueError.
        '''

        args = self.default_args.copy()
        args['axis_in'] = 'not a valid interface'

        self.assertRaisesRegex(
             ValueError, 'Invalid axis_in port', axis_constant_pad, **args)

    def test_axis_out_interface(self):
        '''The axis_out port should be an instance of
        ``kea.axi.AxiStreamInterface``.

        Anything else should raise a ValueError.
        '''

        args = self.default_args.copy()
        args['axis_out'] = 'not a valid interface'

        self.assertRaisesRegex(
             ValueError, 'Invalid axis_out port', axis_constant_pad, **args)

    def test_zero_output(self):
        '''The axis_constant_pad block should always output a value if it is
        enabled.

        If the input is a valid transaction, then the output TDATA should
        be the input TDATA.

        If the input is not a valid transaction then the output TDATA should
        be constant. If constant is not set, it should default to zero.

        No attempt should be made to buffer inputs, so axis_out.TREADY is
        ignored.
        '''

        samples = 500

        @block
        def enable_driver(clock, enable):

            @always(clock.posedge)
            def driver():

                if random.random() > 0.9:
                    enable.next = False
                else:
                    enable.next = True

            return driver

        @block
        def checker(clock, enable, axis_in, axis_out):

            check_data = {
                'next_output': None}

            @always(clock.posedge)
            def check():

                if enable:
                    assert axis_in.TREADY == True

                    if check_data['next_output'] is not None:

                        assert axis_out.TDATA == check_data['next_output']
                        assert axis_out.TVALID == True

                        if axis_in.TREADY and axis_in.TVALID:
                            check_data['next_output'] = (
                                copy.copy(axis_in.TDATA.val))
                        else:
                            check_data['next_output'] = 0


                    elif axis_in.TREADY and axis_in.TVALID:
                        check_data['next_output'] = (
                                copy.copy(axis_in.TDATA.val))

                    else:
                        check_data['next_output'] = None

                else:
                    assert axis_out.TVALID == False
                    assert axis_in.TREADY == False

                    check_data['next_output'] = None

            return check

        custom_sources = [
            (enable_driver, (self.clock, self.enable), {}),
            (checker,
             (self.clock, self.enable, self.axis_in, self.axis_out), {})]

        dut_results, ref_results = self.cosimulate(
            samples, axis_constant_pad, axis_constant_pad,
            self.default_args, self.default_arg_types,
            custom_sources=custom_sources)

        self.assertTrue(dut_results == ref_results)

    def test_constant_output(self):
        '''The axis_constant_pad block should always output a value if it is
        enabled.

        If the input is a valid transaction, then the output TDATA should
        be the input TDATA.

        If the input is not a valid transaction then the output TDATA should
        be constant.

        No attempt should be made to buffer inputs, so axis_out.TREADY is
        ignored.
        '''

        samples = 500

        self.default_args['constant'] = 1
        self.default_arg_types['constant'] = 'non-signal'

        @block
        def enable_driver(clock, enable):

            @always(clock.posedge)
            def driver():

                if random.random() > 0.9:
                    enable.next = False
                else:
                    enable.next = True

            return driver

        @block
        def checker(clock, enable, axis_in, axis_out):

            check_data = {
                'next_output': None}

            @always(clock.posedge)
            def check():

                if enable:
                    assert axis_in.TREADY == True

                    if check_data['next_output'] is not None:

                        assert axis_out.TDATA == check_data['next_output']
                        assert axis_out.TVALID == True

                        if axis_in.TREADY and axis_in.TVALID:
                            check_data['next_output'] = (
                                copy.copy(axis_in.TDATA.val))
                        else:
                            check_data['next_output'] = 1


                    elif axis_in.TREADY and axis_in.TVALID:
                        check_data['next_output'] = (
                                copy.copy(axis_in.TDATA.val))

                    else:
                        check_data['next_output'] = None

                else:
                    assert axis_out.TVALID == False
                    assert axis_in.TREADY == False

                    check_data['next_output'] = None

            return check

        custom_sources = [
            (enable_driver, (self.clock, self.enable), {}),
            (checker,
             (self.clock, self.enable, self.axis_in, self.axis_out), {})]

        dut_results, ref_results = self.cosimulate(
            samples, axis_constant_pad, axis_constant_pad,
            self.default_args, self.default_arg_types,
            custom_sources=custom_sources)

        self.assertTrue(dut_results == ref_results)

class TestAxisConstantPadVivadoVHDL(
    KeaVivadoVHDLTestCase, TestAxisConstantPad):
    pass

class TestAxisConstantPadVivadoVerilog(
    KeaVivadoVerilogTestCase, TestAxisConstantPad):
    pass

