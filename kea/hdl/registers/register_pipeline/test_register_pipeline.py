import copy
import random

from collections import deque
from myhdl import Signal, intbv, block, always

from kea.testing.test_utils import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase,
    generate_value)

from ._register_pipeline import register_pipeline

def dut_args_setup(data_bitwidth, n_stages):
    ''' Generate the arguments and argument types for the DUT.
    '''

    assert(data_bitwidth > 0)
    assert(n_stages > 0)

    dut_args = {
        'clock': Signal(False),
        'reset': Signal(False),
        'enable': Signal(False),
        'source_data': Signal(intbv(0)[data_bitwidth:]),
        'sink_data': Signal(intbv(0)[data_bitwidth:]),
        'n_stages': n_stages,
    }

    dut_arg_types = {
        'clock': 'clock',
        'reset': 'custom',
        'enable': 'custom',
        'source_data': 'custom',
        'sink_data': 'output',
        'n_stages': 'non-signal',
    }

    return dut_args, dut_arg_types

class TestRegisterPipelineInterface(KeaTestCase):

    def setUp(self):
        data_bitwidth = 1
        n_stages = 4
        self.dut_args, _dut_arg_types = (
            dut_args_setup(data_bitwidth, n_stages))

    def test_zero_n_stages(self):
        ''' The `register_pipeline` should raise an error if `n_stages` is
        0.
        '''
        self.dut_args['n_stages'] = 0

        self.assertRaisesRegex(
            ValueError,
            ('register_pipeline: n_stages should be greater than 0.'),
            register_pipeline,
            **self.dut_args,
        )

    def test_negative_n_stages(self):
        ''' The `register_pipeline` should raise an error if `n_stages` is
        less than 0.
        '''
        self.dut_args['n_stages'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('register_pipeline: n_stages should be greater than 0.'),
            register_pipeline,
            **self.dut_args,
        )

    def test_invalid_sink_max_value(self):
        ''' The `register_pipeline` should raise an error if the
        `sink_data.max` is less than `source_data.max`.
        '''
        max_values = random.sample(range(1, 1029), 2)
        source_data_max = max(max_values)
        sink_data_max = min(max_values)

        self.dut_args['source_data'] = (
            Signal(intbv(0, min=0, max=source_data_max)))
        self.dut_args['sink_data'] = (
            Signal(intbv(0, min=0, max=sink_data_max)))

        self.assertRaisesRegex(
            ValueError,
            ('register_pipeline: sink_data.max should be greater than or '
             'equal to source_data.max.'),
            register_pipeline,
            **self.dut_args,
        )

    def test_invalid_sink_min_value(self):
        ''' The `register_pipeline` should raise an error if the
        `sink_data.min` is greater than `source_data.min`.
        '''
        min_values = random.sample(range(-1028, 1), 2)
        source_data_min = min(min_values)
        sink_data_min = max(min_values)

        self.dut_args['source_data'] = (
            Signal(intbv(0, min=source_data_min, max=1)))
        self.dut_args['sink_data'] = (
            Signal(intbv(0, min=sink_data_min, max=1)))

        self.assertRaisesRegex(
            ValueError,
            ('register_pipeline: sink_data.min should be less than or equal '
             'to source_data.min.'),
            register_pipeline,
            **self.dut_args,
        )

class TestRegisterPipeline(KeaTestCase):

    @block
    def dut_stim(self, **dut_args):
        ''' A block to stim the inputs to the DUT.
        '''
        clock = dut_args['clock']
        reset = dut_args['reset']
        enable = dut_args['enable']
        source_data = dut_args['source_data']

        return_objects = []

        data_lower_bound = source_data.min
        data_upper_bound = source_data.max

        @always(clock.posedge)
        def stim():

            if reset:
                if random.random() < 0.3:
                    reset.next = False

            else:
                if random.random() < 0.01:
                    reset.next = True

            if enable:
                if random.random() < 0.02:
                    enable.next = False

            else:
                if random.random() < 0.08:
                    enable.next = True

            source_data.next = (
                generate_value(data_lower_bound, data_upper_bound, 0.1, 0.1))

        return_objects.append(stim)

        return return_objects

    @block
    def dut_check(self, **dut_args):
        ''' Check the outputs of the DUT.
        '''

        clock = dut_args['clock']
        reset = dut_args['reset']
        enable = dut_args['enable']
        source_data = dut_args['source_data']
        sink_data = dut_args['sink_data']
        n_stages = dut_args['n_stages']

        return_objects = []

        expected_sink_data = Signal(intbv(0)[len(sink_data):])

        if n_stages > 1:
            pipeline_len = n_stages-1
            pipeline = deque([0]*pipeline_len, maxlen=pipeline_len)

        @always(clock.posedge)
        def check():

            assert(sink_data == expected_sink_data)

            if enable:

                if n_stages > 1:
                    # Get the next value out of the pipeline then add the new
                    # value. Because pipeline has a maxlen, this will remove
                    # the oldest value in the pipeline.
                    expected_sink_data.next = pipeline[0]
                    pipeline.append(copy.copy(source_data.val))

                else:
                    expected_sink_data.next = source_data

            if reset:
                expected_sink_data.next = 0

                if n_stages > 1:
                    for n in range(n_stages):
                        # Reset all values in the pipeline to 0
                        pipeline.append(0)

        return_objects.append(check)

        return return_objects

    def base_test(self, data_bitwidth, n_stages):

        dut_args, dut_arg_types = dut_args_setup(data_bitwidth, n_stages)

        if not self.testing_using_vivado:
            cycles = 5000

        else:
            cycles = 1000

        @block
        def stimulate_check(**dut_args):

            return_objects = []

            return_objects.append(self.dut_stim(**dut_args))
            return_objects.append(self.dut_check(**dut_args))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, register_pipeline, register_pipeline, dut_args,
            dut_arg_types, custom_sources=[(stimulate_check, (), dut_args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_one_bit_data(self):
        ''' The `register_pipeline` should instantiate a pipeline of
        `n_stages`.

        When `reset` is set high all registers in the pipeline should be reset
        to 0.

        When `enable` is set high, data should shift through the registers in
        the pipeline.

        Note: `n_stages` can also be considered the number of cycles between
        `source_data` being clocked in to the `register_pipeline` and it being
        assigned to `sink_data`
        '''
        self.base_test(
            data_bitwidth=1,
            n_stages=4)

    def test_two_bit_data(self):
        ''' The `register_pipeline` should function correctly when the
        `source_data` and `sink_data` are 2 bits wide.
        '''
        self.base_test(
            data_bitwidth=2,
            n_stages=4)

    def test_random_bitwidth_data(self):
        ''' The `register_pipeline` should function correctly for any bitwidth
        of `source_data` and `sink_data`.
        '''
        data_bitwidth = random.randrange(2, 17)
        self.base_test(
            data_bitwidth=data_bitwidth,
            n_stages=4)

    def test_one_stage(self):
        ''' The `register_pipeline` should function correctly when the
        `n_stages` is set to 1.

        When `n_stages` is set to 1 the `register_pipeline` should assign
        `source_data` to `sink_data` on the next rising edge of `clock`.
        '''
        self.base_test(
            data_bitwidth=4,
            n_stages=1)

    def test_two_stages(self):
        ''' The `register_pipeline` should function correctly when the
        `n_stages` is set to 2.
        '''
        self.base_test(
            data_bitwidth=4,
            n_stages=2)

    def test_random_n_stages(self):
        ''' The `register_pipeline` should function correctly for any value of
        `n_stages`.
        '''
        n_stages = random.randrange(3, 9)
        self.base_test(
            data_bitwidth=4,
            n_stages=n_stages)

class TestRegisterPipelineVivadoVHDL(
    KeaVivadoVHDLTestCase, TestRegisterPipeline):
    pass

class TestRegisterPipelineVivadoVerilog(
    KeaVivadoVerilogTestCase, TestRegisterPipeline):
    pass
