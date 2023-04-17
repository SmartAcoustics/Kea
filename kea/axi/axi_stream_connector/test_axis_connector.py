import copy
import random

from myhdl import Signal, block, always

from kea.axi import AxiStreamInterface
from kea.test_utils import (
    axi_stream_types_generator, KeaTestCase, KeaVivadoVHDLTestCase,
    KeaVivadoVerilogTestCase)

from ._axis_connector import axis_connector

def generate_axi_interfaces_and_types(
    TDATA_byte_width=4, TID_width=None, TDEST_width=None,
    TUSER_width=None, use_TLAST=True, use_TSTRB=False, use_TKEEP=False):

    axis_stream_interface_args = {
        'bus_width': TDATA_byte_width,
        'TID_width': TID_width,
        'TDEST_width': TDEST_width,
        'TUSER_width': TUSER_width,
        'use_TLAST': use_TLAST,
        'use_TSTRB': use_TSTRB,
        'use_TKEEP': use_TKEEP,
    }

    axis_source = AxiStreamInterface(**axis_stream_interface_args)
    axis_sink = AxiStreamInterface(**axis_stream_interface_args)

    axis_stream_types_generator_args = copy.copy(axis_stream_interface_args)
    del axis_stream_types_generator_args['bus_width']

    axis_source_types = (
        axi_stream_types_generator(
            sink=False, **axis_stream_types_generator_args))
    axis_sink_types = (
        axi_stream_types_generator(
            sink=True, **axis_stream_types_generator_args))

    return axis_source, axis_sink, axis_source_types, axis_sink_types

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''
    clock = Signal(False)

    tdata_bit_width = 16
    assert(tdata_bit_width % 8 == 0)
    tdata_byte_width = tdata_bit_width//8

    axis_source, axis_sink, axis_source_types, axis_sink_types = (
        generate_axi_interfaces_and_types(
            TDATA_byte_width=tdata_byte_width, use_TLAST=False))

    args = {
        'clock': clock,
        'axis_source': axis_source,
        'axis_sink': axis_sink,
    }

    arg_types = {
        'clock': 'clock',
        'axis_source': axis_source_types,
        'axis_sink': axis_sink_types,
    }

    return args, arg_types

class TestAxisConnectorInterface(KeaTestCase):
    ''' The DUT should reject incompatible interfaces and arguments.
    '''

    def setUp(self):
        self.args, _arg_types = test_args_setup()

    def test_invalid_axis_source(self):
        ''' The `axis_connector` should raise an error if `axis_source` is not
        an instance of `AxiStreamInterface`.
        '''

        self.args['axis_source'] = random.randrange(100)

        self.assertRaisesRegex(
            TypeError,
            ('axis_connector: axis_source should be an instance of '
             'AxiStreamInterface.'),
            axis_connector,
            **self.args,
        )

    def test_invalid_axis_sink(self):
        ''' The `axis_connector` should raise an error if `axis_sink` is not
        an instance of `AxiStreamInterface`.
        '''

        self.args['axis_sink'] = random.randrange(100)

        self.assertRaisesRegex(
            TypeError,
            ('axis_connector: axis_sink should be an instance of '
             'AxiStreamInterface.'),
            axis_connector,
            **self.args,
        )

class TestAxisConnector(KeaTestCase):

    def setUp(self):

        self.args, self.arg_types = test_args_setup()

    @block
    def signal_stim(self, clock, signal_to_stim):

        return_objects = []

        signal_value_upper_bound = 2**len(signal_to_stim)

        @always(clock.posedge)
        def stim():

            signal_to_stim.next = random.randrange(signal_value_upper_bound)

        return_objects.append(stim)

        return return_objects

    @block
    def axis_connector_stim(self, **kwargs):

        clock = kwargs['clock']
        axis_source = kwargs['axis_source']
        axis_sink = kwargs['axis_sink']

        return_objects = []

        return_objects.append(self.signal_stim(clock, axis_source.TVALID))
        return_objects.append(self.signal_stim(clock, axis_source.TDATA))

        return_objects.append(self.signal_stim(clock, axis_sink.TREADY))

        if axis_source.TDEST_width is not None:
            return_objects.append(self.signal_stim(clock, axis_source.TDEST))

        if axis_source.TID_width is not None:
            return_objects.append(self.signal_stim(clock, axis_source.TID))

        if axis_source.TUSER_width is not None:
            return_objects.append(self.signal_stim(clock, axis_source.TUSER))

        if hasattr(axis_source, 'TLAST'):
            return_objects.append(self.signal_stim(clock, axis_source.TLAST))

        if hasattr(axis_source, 'TSTRB'):
            return_objects.append(self.signal_stim(clock, axis_source.TSTRB))

        if hasattr(axis_source, 'TKEEP'):
            return_objects.append(self.signal_stim(clock, axis_source.TKEEP))

        return return_objects

    @block
    def signal_check(self, clock, signal_0, signal_1):

        return_objects = []

        @always(clock.posedge)
        def check():

            assert(signal_0 == signal_1)

        return_objects.append(check)

        return return_objects

    @block
    def axis_connector_check(self, **kwargs):

        clock = kwargs['clock']
        axis_source = kwargs['axis_source']
        axis_sink = kwargs['axis_sink']

        return_objects = []

        return_objects.append(
            self.signal_check(clock, axis_source.TVALID, axis_sink.TVALID))
        return_objects.append(
            self.signal_check(clock, axis_source.TDATA, axis_sink.TDATA))

        return_objects.append(
            self.signal_check(clock, axis_source.TREADY, axis_sink.TREADY))

        if axis_source.TDEST_width is not None:
            return_objects.append(
                self.signal_check(clock, axis_source.TDEST, axis_sink.TDEST))

        if axis_source.TID_width is not None:
            return_objects.append(
                self.signal_check(clock, axis_source.TID, axis_sink.TID))

        if axis_source.TUSER_width is not None:
            return_objects.append(
                self.signal_check(clock, axis_source.TUSER, axis_sink.TUSER))

        if hasattr(axis_source, 'TLAST'):
            return_objects.append(
                self.signal_check(clock, axis_source.TLAST, axis_sink.TLAST))

        if hasattr(axis_source, 'TSTRB'):
            return_objects.append(
                self.signal_check(clock, axis_source.TSTRB, axis_sink.TSTRB))

        if hasattr(axis_source, 'TKEEP'):
            return_objects.append(
                self.signal_check(clock, axis_source.TKEEP, axis_sink.TKEEP))

        return return_objects

    def test_axis_connector_required_signals(self):
        ''' The `axis_connector` should always connect all signals on
        `axis_source` to the corresponding signals on `axis_sink`.

        The AXI stream specification requires the following signals:

            - `TVALID`
            - `TREADY`
            - `TDATA`

        The `axis_connector` should function correctly when only these signals
        are included in the `axis_source` and `axis_sink` interfaces.
        '''

        cycles = 3000

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            return_objects.append(self.axis_connector_stim(**kwargs))
            return_objects.append(self.axis_connector_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axis_connector, axis_connector, self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_axis_connector_all_signals(self):
        ''' The AXI stream specification includes the following optional
        signals:

            - `TDEST`
            - `TID`
            - `TUSER`
            - `TLAST`
            - `TSTRB`
            - `TKEEP`

        The `axis_connector` should function correctly when all of these
        signals are included in the `axis_source` and `axis_sink` interfaces.
        '''

        cycles = 3000

        generate_axi_interfaces_and_types_args = {
            'TDATA_byte_width': 4,
            'TID_width': 4,
            'TDEST_width': 4,
            'TUSER_width': 4,
            'use_TLAST': True,
            'use_TSTRB': True,
            'use_TKEEP': True,
        }

        (self.args['axis_source'],
         self.args['axis_sink'],
         self.arg_types['axis_source'],
         self.arg_types['axis_sink']) = (
             generate_axi_interfaces_and_types(
                 **generate_axi_interfaces_and_types_args))

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            return_objects.append(self.axis_connector_stim(**kwargs))
            return_objects.append(self.axis_connector_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axis_connector, axis_connector, self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_axis_connector_random_optional_signals(self):
        ''' The `axis_connector` should function correctly when any
        combination of optional signals are included in the `axis_source` and
        `axis_sink` interfaces.
        '''

        cycles = 3000

        generate_axi_interfaces_and_types_args = {
            'TDATA_byte_width': 4,
            'TID_width': random.choice([None, 4]),
            'TDEST_width': random.choice([None, 4]),
            'TUSER_width': random.choice([None, 4]),
            'use_TLAST': bool(random.randrange(2)),
            'use_TSTRB': bool(random.randrange(2)),
            'use_TKEEP': bool(random.randrange(2)),
        }

        (self.args['axis_source'],
         self.args['axis_sink'],
         self.arg_types['axis_source'],
         self.arg_types['axis_sink']) = (
             generate_axi_interfaces_and_types(
                 **generate_axi_interfaces_and_types_args))

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            return_objects.append(self.axis_connector_stim(**kwargs))
            return_objects.append(self.axis_connector_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axis_connector, axis_connector, self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestAxisConnectorVivadoVhdl(
    KeaVivadoVHDLTestCase, TestAxisConnector):
    pass

class TestAxisConnectorVivadoVerilog(
    KeaVivadoVerilogTestCase, TestAxisConnector):
    pass
