import copy
import random

from myhdl import Signal, intbv, block, always, enum, StopSimulation

from kea.axi import AxiStreamInterface, AxiStreamMasterBFM, AxiStreamSlaveBFM
from kea.test_utils import (
    axi_stream_types_generator, KeaTestCase, KeaVivadoVHDLTestCase,
    KeaVivadoVerilogTestCase)
from kea.utils import or_gate

from ._axis_tdest_selector import axis_tdest_selector

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''
    clock = Signal(False)
    reset = Signal(False)

    tdata_bit_width = 16
    assert(tdata_bit_width % 8 == 0)
    tdata_byte_width = tdata_bit_width//8

    tdest_bit_width = 4

    axis_source = AxiStreamInterface(tdata_byte_width, use_TLAST=True)
    axis_sink = (
        AxiStreamInterface(
            tdata_byte_width, TDEST_width=tdest_bit_width,
            use_TLAST=True))

    tdest_select = Signal(intbv(0)[tdest_bit_width:])

    args = {
        'clock': clock,
        'reset': reset,
        'axis_source': axis_source,
        'axis_sink': axis_sink,
        'tdest_select': tdest_select,
    }

    axis_source_types = (
        axi_stream_types_generator(sink=False, use_TLAST=True))

    axis_sink_types = (
        axi_stream_types_generator(
            sink=True, TDEST_width=tdest_bit_width, use_TLAST=True))

    arg_types = {
        'clock': 'clock',
        'reset': 'custom',
        'axis_source': axis_source_types,
        'axis_sink': axis_sink_types,
        'tdest_select': 'custom',
    }

    return args, arg_types

class TestAxisTDestSelectorInterface(KeaTestCase):
    ''' The DUT should reject incompatible interfaces and arguments.
    '''

    def setUp(self):
        self.args, _arg_types = test_args_setup()

    def test_invalid_axis_source(self):
        ''' The `axis_tdest_selector` should raise an error if
        `axis_source` is not an instance of `AxiStreamInterface`.
        '''

        self.args['axis_source'] = random.randrange(100)

        self.assertRaisesRegex(
            TypeError,
            ('axis_tdest_selector: axis_source should be an instance '
             'of AxiStreamInterface.'),
            axis_tdest_selector,
            **self.args,
        )

    def test_invalid_axis_sink(self):
        ''' The `axis_tdest_selector` should raise an error if
        `axis_sink` is not an instance of `AxiStreamInterface`.
        '''

        self.args['axis_sink'] = random.randrange(100)

        self.assertRaisesRegex(
            TypeError,
            ('axis_tdest_selector: axis_sink should be an instance '
             'of AxiStreamInterface.'),
            axis_tdest_selector,
            **self.args,
        )

    def test_invalid_axis_source_tdest(self):
        ''' The `axis_tdest_selector` should raise an error if
        `axis_source` includes a `TDEST`.
        '''

        tdata_byte_width = self.args['axis_source'].bus_width
        tdest_bit_width = self.args['axis_sink'].TDEST_width

        self.args['axis_source'] = (
            AxiStreamInterface(
                tdata_byte_width, TDEST_width=tdest_bit_width,
                use_TLAST=True))

        self.assertRaisesRegex(
            ValueError,
            ('The axis_tdest_selector does not support TDEST on '
             'axis_source.'),
            axis_tdest_selector,
            **self.args,
        )

    def test_no_axis_sink_tdest(self):
        ''' The `axis_tdest_selector` should raise an error if
        `axis_sink` does not include a `TDEST`.
        '''

        tdata_byte_width = self.args['axis_source'].bus_width

        self.args['axis_sink'] = (
            AxiStreamInterface(tdata_byte_width, use_TLAST=True))

        self.assertRaisesRegex(
            ValueError,
            ('The axis_tdest_selector requires a TDEST on axis_sink.'),
            axis_tdest_selector,
            **self.args,
        )

    def test_invalid_tdest_select_bit_width(self):
        ''' The `axis_tdest_selector` should raise an error if
        `tdest_select` is wider than `axis_sink.TDEST`.
        '''

        tdata_byte_width = self.args['axis_source'].bus_width

        tdest_bit_width, tdest_select_bit_width = (
            sorted(random.sample([n for n in range(2, 8)], 2)))

        self.args['axis_sink'] = (
            AxiStreamInterface(
                tdata_byte_width, TDEST_width=tdest_bit_width,
                use_TLAST=True))
        self.args['tdest_select'] = Signal(intbv(0)[tdest_select_bit_width:])

        self.assertRaisesRegex(
            ValueError,
            ('axis_tdest_selector: tdest_select is too wide for '
             'axis_sink.TDEST.'),
            axis_tdest_selector,
            **self.args,
        )

    def test_no_tlast(self):
        ''' The `axis_tdest_selector` should raise an error if the
        `axis_source` and `axis_sink` interfaces don't contain `TLAST`.
        '''

        tdata_byte_width = self.args['axis_source'].bus_width
        tdest_bit_width = self.args['axis_sink'].TDEST_width

        self.args['axis_source'] = (
            AxiStreamInterface(tdata_byte_width, use_TLAST=False))
        self.args['axis_sink'] = (
            AxiStreamInterface(
                tdata_byte_width, TDEST_width=tdest_bit_width,
                use_TLAST=False))

        self.assertRaisesRegex(
            ValueError,
            ('The axis_tdest_selector requires a TLAST.'),
            axis_tdest_selector,
            **self.args,
        )

    def test_invalid_tid(self):
        ''' The `axis_tdest_selector` should raise an error if the
        `axis_source` and `axis_sink` interfaces contain `TID`.
        '''

        tdata_byte_width = self.args['axis_source'].bus_width
        tdest_bit_width = self.args['axis_sink'].TDEST_width
        tid_bit_width = random.randrange(2, 9)

        self.args['axis_source'] = (
            AxiStreamInterface(
                tdata_byte_width, use_TLAST=True, TID_width=tid_bit_width))
        self.args['axis_sink'] = (
            AxiStreamInterface(
                tdata_byte_width, TDEST_width=tdest_bit_width,
                use_TLAST=True, TID_width=tid_bit_width))

        self.assertRaisesRegex(
            ValueError,
            ('The axis_tdest_selector does not support TID.'),
            axis_tdest_selector,
            **self.args,
        )

    def test_invalid_tuser(self):
        ''' The `axis_tdest_selector` should raise an error if the
        `axis_source` and `axis_sink` interfaces contain `TUSER`.
        '''

        tdata_byte_width = self.args['axis_source'].bus_width
        tdest_bit_width = self.args['axis_sink'].TDEST_width
        tuser_bit_width = random.randrange(2, 9)

        self.args['axis_source'] = (
            AxiStreamInterface(
                tdata_byte_width, use_TLAST=True,
                TUSER_width=tuser_bit_width))
        self.args['axis_sink'] = (
            AxiStreamInterface(
                tdata_byte_width, TDEST_width=tdest_bit_width,
                use_TLAST=True, TUSER_width=tuser_bit_width))

        self.assertRaisesRegex(
            ValueError,
            ('The axis_tdest_selector does not support TUSER.'),
            axis_tdest_selector,
            **self.args,
        )

    def test_invalid_tstrb(self):
        ''' The `axis_tdest_selector` should raise an error if the
        `axis_source` and `axis_sink` interfaces contain `TSTRB`.
        '''

        tdata_byte_width = self.args['axis_source'].bus_width
        tdest_bit_width = self.args['axis_sink'].TDEST_width

        self.args['axis_source'] = (
            AxiStreamInterface(
                tdata_byte_width, use_TLAST=True, use_TSTRB=True))
        self.args['axis_sink'] = (
            AxiStreamInterface(
                tdata_byte_width, TDEST_width=tdest_bit_width,
                use_TLAST=True, use_TSTRB=True))

        self.assertRaisesRegex(
            ValueError,
            ('The axis_tdest_selector does not support TSTRB.'),
            axis_tdest_selector,
            **self.args,
        )

    def test_invalid_tkeep(self):
        ''' The `axis_tdest_selector` should raise an error if the
        `axis_source` and `axis_sink` interfaces contain `TKEEP`.
        '''

        tdata_byte_width = self.args['axis_source'].bus_width
        tdest_bit_width = self.args['axis_sink'].TDEST_width

        self.args['axis_source'] = (
            AxiStreamInterface(
                tdata_byte_width, use_TLAST=True, use_TKEEP=True))
        self.args['axis_sink'] = (
            AxiStreamInterface(
                tdata_byte_width, TDEST_width=tdest_bit_width,
                use_TLAST=True, use_TKEEP=True))

        self.assertRaisesRegex(
            ValueError,
            ('The axis_tdest_selector does not support TKEEP.'),
            axis_tdest_selector,
            **self.args,
        )

def add_runs_of_none(
    data, probability_of_run=0.25, min_length_of_run=0, max_length_of_run=16):
    ''' Given a list of data, this function will insert a run of ``None``
    values of random length at random intervals in the data list.
    '''
    manipulated_data = copy.copy(data)

    for n in reversed(range(len(manipulated_data))):
        # Run through every index in the data. If we don't reverse the order
        # of n here we increment up through the Nones we may have just
        # inserted into the list and may add more Nones in the middle.
        if random.random() > probability_of_run:
            # At random indexes create a run of nones of random length and
            # insert them into the data list
            none_run = (
                [None]*random.randrange(min_length_of_run, max_length_of_run))
            for each in none_run:
                manipulated_data.insert(n, each)

    return manipulated_data

def generate_data(
    data_upper_bound, n_packets_upper_bound=4,
    n_samples_per_packet_upper_bound=65, randomise_tvalid=False):
    ''' This function will generate stimulus data.

    If randomise_tvalid is True then this funciton will add runs of None to
    the data so that the AXIS master BFM varies the TVALID signals during the
    data stream.
    '''

    assert(n_packets_upper_bound > 1)
    n_packets = random.randrange(1, n_packets_upper_bound)

    data = []

    for n in range(n_packets):
        # Randomly set n_samples
        n_samples = random.randrange(1, n_samples_per_packet_upper_bound)

        # Generate data
        packet = [
            random.randrange(data_upper_bound) for n in range(n_samples)]

        if randomise_tvalid:
            # Add Nones so that TVALID varies
            packet = add_runs_of_none(packet)

        data.append(packet)

    return data

class TestAxisTDestSelector(KeaTestCase):

    def setUp(self):
        self.args, self.arg_types = test_args_setup()

        self.test_count = 0
        self.tests_run = False

    @block
    def end_tests(self, n_tests, **kwargs):

        clock = kwargs['clock']

        return_objects = []

        @always(clock.posedge)
        def control():

            if self.test_count >= n_tests:
                self.tests_run = True
                raise StopSimulation

        return_objects.append(control)

        return return_objects

    @block
    def axis_tdest_selector_stim(
        self, randomise_axis_control_signals=False,
        n_samples_per_packet_upper_bound=65, stim_reset=False, **kwargs):

        clock = kwargs['clock']
        reset = kwargs['reset']
        axis_source = kwargs['axis_source']
        axis_sink = kwargs['axis_sink']
        tdest_select = kwargs['tdest_select']

        return_objects = []

        if randomise_axis_control_signals:
            tready_probability = 0.5

        else:
            tready_probability = 1.0

        # Create the reset for the source BFM
        axis_source_reset = Signal(False)
        combined_axis_source_reset = Signal(False)
        return_objects.append(
            or_gate(reset, axis_source_reset, combined_axis_source_reset))

        # Create the source BFM
        axis_source_bfm = AxiStreamMasterBFM()
        return_objects.append(
            axis_source_bfm.model(
                clock, axis_source, reset=combined_axis_source_reset))

        # Create the sink BFM
        axis_sink_bfm = AxiStreamSlaveBFM()
        return_objects.append(
            axis_sink_bfm.model(
                clock, axis_sink, TREADY_probability=tready_probability))

        tdest_select_upper_bound = 2**len(tdest_select)
        n_packets_upper_bound = 4

        generate_data_args = {
            'data_upper_bound': 2**(len(axis_source.TDATA)),
            'n_packets_upper_bound': n_packets_upper_bound,
            'n_samples_per_packet_upper_bound': (
                n_samples_per_packet_upper_bound),
            'randomise_tvalid': randomise_axis_control_signals,
        }

        n_packets = Signal(intbv(0, 0, n_packets_upper_bound))
        packet_count = Signal(intbv(0, 0, n_packets_upper_bound))

        t_state = enum('ADD_DATA', 'AWAIT_COMPLETE')
        state = Signal(t_state.ADD_DATA)

        @always(clock.posedge)
        def stim():

            #####################
            # tdest_select stim #
            #####################

            # Drive tdest_select with random values
            tdest_select.next = random.randrange(tdest_select_upper_bound)

            ##############
            # Reset stim #
            ##############

            reset.next = False

            if stim_reset:
                if random.random() < 0.005:
                    reset.next = True

            ############
            # AXI stim #
            ############

            if state == t_state.ADD_DATA:
                if random.random() < 0.01:
                    # Reset the receiving bfm
                    axis_sink_bfm.reset()

                    # Generate the stim data
                    stim_data = generate_data(**generate_data_args)

                    # Keep a record of the number of packets in the stim data
                    n_packets.next = len(stim_data)

                    axis_source_bfm.add_data(stim_data)

                    state.next = t_state.AWAIT_COMPLETE

            elif state == t_state.AWAIT_COMPLETE:
                if axis_sink.TVALID and axis_sink.TREADY and axis_sink.TLAST:
                    if packet_count >= n_packets-1:
                        # All packets in stim data have completed
                        packet_count.next = 0
                        state.next = t_state.ADD_DATA

                    else:
                        # Count the completed packets
                        packet_count.next = packet_count + 1

            if reset:
                packet_count.next = 0
                state.next = t_state.ADD_DATA

        return_objects.append(stim)

        return return_objects

    @block
    def axis_tdest_selector_check(self, **kwargs):

        clock = kwargs['clock']
        reset = kwargs['reset']
        axis_source = kwargs['axis_source']
        axis_sink = kwargs['axis_sink']
        tdest_select = kwargs['tdest_select']

        return_objects = []

        packet_in_progress = Signal(False)

        expected_axis_sink_tdest = Signal(intbv(0)[axis_sink.TDEST_width:])

        @always(clock.posedge)
        def check():

            # The TVALID, TDATA, TLAST and TREADY signals should be passed
            # through
            assert(axis_sink.TVALID == axis_source.TVALID)
            assert(axis_sink.TDATA == axis_source.TDATA)
            assert(axis_sink.TLAST == axis_source.TLAST)
            assert(axis_source.TREADY == axis_sink.TREADY)

            # Check axis_sink.TDEST is set correctly
            assert(axis_sink.TDEST == expected_axis_sink_tdest)

            if not packet_in_progress:
                if axis_source.TVALID and not (
                    axis_sink.TREADY and axis_source.TLAST):
                    # Packet has started
                    packet_in_progress.next = True

                else:
                    expected_axis_sink_tdest.next = tdest_select

            elif (axis_source.TVALID and
                  axis_sink.TREADY and
                  axis_source.TLAST):
                # Packet has completed
                expected_axis_sink_tdest.next = tdest_select
                packet_in_progress.next = False

                self.test_count += 1

            if reset:
                expected_axis_sink_tdest.next = tdest_select
                packet_in_progress.next = False

        return_objects.append(check)

        return return_objects

    def test_axis_tdest_selector(self):
        ''' The `axis_tdest_selector` should directly connect the following
        signals:

            - `axis_source.TVALID` to `axis_sink.TVALID`.
            - `axis_source.TDATA` to `axis_sink.TDATA`.
            - `axis_source.TLAST` to `axis_sink.TLAST`.
            - `axis_sink.TREADY` to `axis_source.TREADY`.

        Under the AXI stream spec, a packet is deemed to commence when
        `axis_source.TVALID` is set high. It remains in progress until
        `axis_source.TVALID`, `axis_source.TLAST` and `axis_sink.TREADY` are
        all set high at the same time.

        The `axis_sink.TDEST` signal should not change when a packet is in
        progress.
        '''

        cycles = 15000
        n_tests = 20

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            return_objects.append(self.end_tests(n_tests, **kwargs))
            return_objects.append(self.axis_tdest_selector_stim(**kwargs))
            return_objects.append(self.axis_tdest_selector_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axis_tdest_selector, axis_tdest_selector, self.args,
            self.arg_types, custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_varying_tvalid_and_tready(self):
        ''' The `axis_tdest_selector` should function correctly when the
        `TVALID` and `TREADY` signals vary.
        '''

        cycles = 15000
        n_tests = 20

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            return_objects.append(self.end_tests(n_tests, **kwargs))
            return_objects.append(
                self.axis_tdest_selector_stim(
                    randomise_axis_control_signals=True, **kwargs))
            return_objects.append(self.axis_tdest_selector_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axis_tdest_selector, axis_tdest_selector, self.args,
            self.arg_types, custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_one_word_packets(self):
        ''' The `axis_tdest_selector` should function correctly when the AXI
        stream is conveying one word packets.
        '''

        cycles = 15000
        n_tests = 20

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            return_objects.append(self.end_tests(n_tests, **kwargs))
            return_objects.append(
                self.axis_tdest_selector_stim(
                    randomise_axis_control_signals=True,
                    n_samples_per_packet_upper_bound=2, **kwargs))
            return_objects.append(self.axis_tdest_selector_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axis_tdest_selector, axis_tdest_selector, self.args,
            self.arg_types, custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_reset(self):
        ''' When `reset` is set high the `axis_tdest_selector` should treat
        any packets in progress as completed and updated `axis_sink.TDEST`
        the `tdest_select`. It should then wait for the next packet.
        '''

        cycles = 15000
        n_tests = 20

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            return_objects.append(self.end_tests(n_tests, **kwargs))
            return_objects.append(
                self.axis_tdest_selector_stim(
                    randomise_axis_control_signals=True, stim_reset=True,
                    **kwargs))
            return_objects.append(self.axis_tdest_selector_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axis_tdest_selector, axis_tdest_selector, self.args,
            self.arg_types, custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

class TestAxisTDestSelectorVivadoVhdl(
    KeaVivadoVHDLTestCase, TestAxisTDestSelector):
    pass

class TestAxisTDestSelectorVivadoVerilog(
    KeaVivadoVerilogTestCase, TestAxisTDestSelector):
    pass
