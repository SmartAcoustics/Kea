import random

from math import ceil, log

from myhdl import Signal, intbv, block, always, enum, StopSimulation

from kea.axi import AxiStreamInterface
from kea.test_utils import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase,
    axi_stream_types_generator)

from ._aurora_64b_66b_flow_control import aurora_64b_66b_flow_control

def aurora_system_max_word_capacity():
    ''' Calculate the maximum number of words that can be within the Aurora
    system (TX aurora block, transceivers, optical fibre and RX aurora block)
    at any given moment.
    '''

    aurora_latency = 55
    aurora_bit_width = 64
    aurora_max_lane_bit_rate = 12e9 # 12 Gbps

    max_fibre_length = 100

    time_in_flight = max_fibre_length/2e8 # Speed of light in fibre = 2e8

    n_bits_in_flight = aurora_max_lane_bit_rate*time_in_flight
    n_words_in_flight = ceil(n_bits_in_flight/aurora_bit_width)

    word_capacity = n_words_in_flight + aurora_latency

    return word_capacity

def flow_control_propagation_max_n_words():
    ''' Calculate the maximum number of words which may be produced by the
    Aurora system in between a flow control word being received by the Aurora
    block and that flow control taking effect.
    '''

    n_words = 2*aurora_system_max_word_capacity()

    return n_words

def expected_min_fifo_depth():
    ''' Calculate the expected minimum valid FIFO depth for the
    `aurora_64b_66b_flow_control`. This is the minimum value which ensures the
    `flow_on_threshold` is not greater than the `flow_off_threshold`.
    '''

    # We need to handle the full and empty case so double
    # flow_control_propagation_max_n_words to get the min_fifo_depth.
    min_fifo_depth = 2*flow_control_propagation_max_n_words()

    return min_fifo_depth

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    fifo_depth = 1024

    clock = Signal(False)
    reset = Signal(False)

    fifo_count_bit_width = ceil(log(fifo_depth)/log(2)) + 1
    fifo_count = Signal(intbv(0)[fifo_count_bit_width:])

    axis_aurora_nfc = AxiStreamInterface(bus_width=2, use_TLAST=False)
    axis_aurora_nfc_types = (
        axi_stream_types_generator(sink=True, use_TLAST=False))

    args = {
        'clock': clock,
        'reset': reset,
        'fifo_count': fifo_count,
        'axis_aurora_nfc': axis_aurora_nfc,
        'fifo_depth': fifo_depth,
    }

    arg_types = {
        'clock': 'clock',
        'reset': 'custom',
        'fifo_count': 'custom',
        'axis_aurora_nfc': axis_aurora_nfc_types,
        'fifo_depth': 'non-signal',
    }

    return args, arg_types

class TestAurora64b66bFlowControlInterface(KeaTestCase):
    ''' The DUT should reject incompatible interfaces and arguments.
    '''

    def setUp(self):
        self.args, _arg_types = test_args_setup()

    def test_invalid_axis_aurora_nfc(self):
        ''' The `aurora_64b_66b_flow_control` should raise an error if
        `axis_aurora_nfc` is not an instance of AxiStreamInterface.
        '''

        self.args['axis_aurora_nfc'] = random.randrange(100)

        self.assertRaisesRegex(
            TypeError,
            ('aurora_64b_66b_flow_control: axis_aurora_nfc should be an '
             'instance of AxiStreamInterface.'),
            aurora_64b_66b_flow_control,
            **self.args,
        )

    def test_invalid_fifo_count_bit_width(self):
        ''' The `aurora_64b_66b_flow_control` should raise an error if
        `fifo_count` is not wide enough for the `fifo_depth`.
        '''

        invalid_fifo_count_bit_width_upper_bound = (
            ceil(log(self.args['fifo_depth'])/log(2)) + 1)
        invalid_fifo_count_bit_width = (
            random.randrange(1, invalid_fifo_count_bit_width_upper_bound))
        self.args['fifo_count'] = (
            Signal(intbv(0)[invalid_fifo_count_bit_width:]))

        self.assertRaisesRegex(
            ValueError,
            ('aurora_64b_66b_flow_control: The fifo_count should be able to '
             'carry a value equal to the fifo_depth.'),
            aurora_64b_66b_flow_control,
            **self.args,
        )

    def test_invalid_fifo_depth(self):
        ''' The `aurora_64b_66b_flow_control` should raise an error if
        `fifo_count` is not wide enough for the `fifo_depth`.
        '''

        min_fifo_depth = expected_min_fifo_depth()
        self.args['fifo_depth'] = random.randrange(min_fifo_depth)

        self.assertRaisesRegex(
            ValueError,
            ('aurora_64b_66b_flow_control: The fifo_depth should be at least '
            + str(min_fifo_depth) + '.'),
            aurora_64b_66b_flow_control,
            **self.args,
        )

class TestAurora64b66bFlowControl(KeaTestCase):

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
    def aurora_64b_66b_flow_control_stim(self, stim_reset=False, **kwargs):

        clock = kwargs['clock']
        reset = kwargs['reset']
        fifo_count = kwargs['fifo_count']
        axis_aurora_nfc = kwargs['axis_aurora_nfc']
        fifo_depth = kwargs['fifo_depth']

        return_objects = []

        tvalid = axis_aurora_nfc.TVALID
        tready = axis_aurora_nfc.TREADY

        # Calculate the flow control thresholds
        nfc_propagation_max_n_words = flow_control_propagation_max_n_words()
        flow_on_threshold = nfc_propagation_max_n_words
        flow_off_threshold = fifo_depth - nfc_propagation_max_n_words

        if flow_on_threshold == flow_off_threshold:
            thresholds_equal = True

        else:
            thresholds_equal = False

        t_fifo_state = enum(
            'EMPTY', 'LOW', 'BETWEEN_THRESHOLDS', 'HIGH', 'FULL')
        fifo_state = Signal(t_fifo_state.EMPTY)

        @always(clock.posedge)
        def stim():

            ###################
            # AXIS aurora NFC #
            ###################

            tready.next = False

            if tvalid and not tready:
                if random.random() < 0.05:
                    tready.next = True

            ##############
            # FIFO count #
            ##############

            if random.random() < 0.01:
                fifo_state_selector = random.random()

                if fifo_state_selector < 0.05:
                    fifo_state.next = t_fifo_state.EMPTY

                elif fifo_state_selector < 0.35:
                    fifo_state.next = t_fifo_state.LOW

                elif fifo_state_selector < 0.65 and not thresholds_equal:
                    fifo_state.next = t_fifo_state.BETWEEN_THRESHOLDS

                elif fifo_state_selector < 0.95:
                    fifo_state.next = t_fifo_state.HIGH

                else:
                    fifo_state.next = t_fifo_state.FULL

            if fifo_state == t_fifo_state.EMPTY:
                fifo_count.next = 0

            elif fifo_state == t_fifo_state.LOW:
                fifo_count.next = random.randrange(1, flow_on_threshold)

            elif fifo_state == t_fifo_state.BETWEEN_THRESHOLDS:
                fifo_count.next = (
                    random.randrange(flow_on_threshold, flow_off_threshold))

            elif fifo_state == t_fifo_state.HIGH:
                fifo_count.next = (
                    random.randrange(flow_off_threshold, fifo_depth))

            elif fifo_state == t_fifo_state.FULL:
                fifo_count.next = fifo_depth

            #########
            # Reset #
            #########

            if stim_reset:
                if reset:
                    if random.random() < 0.1:
                        reset.next = False

                else:
                    if random.random() < 0.01:
                        reset.next = True

        return_objects.append(stim)

        return return_objects

    @block
    def aurora_64b_66b_flow_control_check(self, **kwargs):

        clock = kwargs['clock']
        reset = kwargs['reset']
        fifo_count = kwargs['fifo_count']
        axis_aurora_nfc = kwargs['axis_aurora_nfc']
        fifo_depth = kwargs['fifo_depth']

        return_objects = []

        tvalid = axis_aurora_nfc.TVALID
        tready = axis_aurora_nfc.TREADY
        tdata = axis_aurora_nfc.TDATA

        # Calculate the flow control thresholds
        nfc_propagation_max_n_words = flow_control_propagation_max_n_words()
        flow_on_threshold = nfc_propagation_max_n_words
        flow_off_threshold = fifo_depth - nfc_propagation_max_n_words

        flow_off = Signal(False)
        flow_on = Signal(False)

        aurora_nfc_off_word = 0x0100
        aurora_nfc_on_word = 0x0000

        expected_tvalid = Signal(False)
        expected_tdata = Signal(intbv(0)[len(tdata):])

        @always(clock.posedge)
        def check():

            assert(tvalid == expected_tvalid)
            assert(tdata == expected_tdata)

            if tvalid and tready:
                self.test_count += 1
                expected_tvalid.next = False

            if not tvalid and not flow_off:
                if fifo_count >= flow_off_threshold:
                    flow_off.next = True
                    flow_on.next = False
                    expected_tvalid.next = True
                    expected_tdata.next = aurora_nfc_off_word

            if not tvalid and not flow_on:
                if fifo_count < flow_on_threshold:
                    flow_off.next = False
                    flow_on.next = True
                    expected_tvalid.next = True
                    expected_tdata.next = aurora_nfc_on_word

            if reset:
                flow_off.next = False
                flow_on.next = False

                expected_tvalid.next = False

        return_objects.append(check)

        return return_objects

    def test_flow_control(self):
        ''' The `aurora_64b_66b_flow_control` block should control the flow
        of the Aurora system.

        The Aurora system cannot handle back pressure but instead provides
        native flow control (NFC) which allows the user blocks to control the
        data flow via an AXI stream interface (`axis_aurora_nfc`). The NFC can
        be controlled by writing control words to the `axis_aurora_nfc`
        interface.

        The only bit in the control word that the
        `aurora_64b_66b_flow_control` should use is bit 8. All other bits
        should be held low.

        When bit 8 is set high the Aurora system will turn the data off. When
        bit 8 is set low the Aurora system will turn the data on:

            NFC on: 0x10
            NFC off: 0x00

        The flow control cannot turn the data off instantaneously. The Aurora
        block needs to transmit the start and stop commands to the other end
        of the Aurora system. This means there is an NFC delay between the
        user block sending a control word and the flow out of the Aurora
        system starting or stopping.

        The `aurora_64b_66b_flow_control` block should monitor the
        `fifo_count` to detect filling and draining of the FIFO and act to
        prevent data loss whilst maximising throughput.

        When the FIFO fills beyond the flow-off threshold, the
        `aurora_64b_66b_flow_control` block should stop the flow to prevent
        data loss. The flow-off threshold should leave enough space in the
        FIFO for all the data out of the Aurora system during the NFC delay.

        When the FIFO drains below the flow-on threshold, the
        `aurora_64b_66b_flow_control` block should stop the flow to prevent
        gaps on the read side of the FIFO and maximise throughput. The flow-on
        threshold should leave enough data in the FIFO for the external system
        to read during the NFC delay.

        The for a 100m length of optical fibre, the maximum number of bits in
        the optical fibre (max_n_bits_in_fibre) at any given time can be
        calculated:

            (100 / Speed of Light in fibre) * Aurora lane max data rate

        This can be converted to the maximum number of words in the optical
        fibre (max_n_words_in_fibre):

            max_n_bits_in_fibre / 64

        The Aurora bus also includes 55 words of latency, therefore words in
        the Aurora system in one direction (total_words_in_aurora_one_d) is:

            max_n_words_in_fibre + 55

        The NFC control words need to propagate in one direction and then the
        data already in the system needs to finish propagating in the other
        direction. Therefore the maximum amount of data we need to handle
        during the NFC delay (max_n_words_during_nfc_delay) is:

            2 * total_words_in_aurora_one_d

        Therefore the flow-on threshold should be:

            max_n_words_during_nfc_delay

        And the flow-off threshold should be:

            `fifo_depth` - max_n_words_during_nfc_delay
        '''

        cycles = 20000
        n_tests = 40

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            return_objects.append(self.end_tests(n_tests, **kwargs))
            return_objects.append(
                self.aurora_64b_66b_flow_control_stim(**kwargs))
            return_objects.append(
                self.aurora_64b_66b_flow_control_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, aurora_64b_66b_flow_control, aurora_64b_66b_flow_control,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        for each in dut_outputs:
            if dut_outputs[each] != ref_outputs[each]:
                print(each)

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_min_fifo_depth(self):
        ''' The `aurora_64b_66b_flow_control` should function correctly when
        the `fifo_depth` is such that the flow-on threshold is equal to the
        flow-off threshold. This is the minimum valid `fifo_depth`.
        '''

        self.args['fifo_depth'] = 2*flow_control_propagation_max_n_words()

        cycles = 20000
        n_tests = 40

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            return_objects.append(self.end_tests(n_tests, **kwargs))
            return_objects.append(
                self.aurora_64b_66b_flow_control_stim(**kwargs))
            return_objects.append(
                self.aurora_64b_66b_flow_control_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, aurora_64b_66b_flow_control, aurora_64b_66b_flow_control,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        for each in dut_outputs:
            if dut_outputs[each] != ref_outputs[each]:
                print(each)

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_reset(self):
        ''' When `reset` is set high the `aurora_64b_66b_flow_control` should
        abandon any `axis_aurora_nfc` transactions by setting
        `axis_aurora_nfc.TVALID` low. It should then return to its
        initialisation state so it can turn the flow on or off depending on
        the `fifo_count` when the `reset` goes low.
        '''

        cycles = 20000
        n_tests = 40

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            return_objects.append(self.end_tests(n_tests, **kwargs))
            return_objects.append(
                self.aurora_64b_66b_flow_control_stim(
                    stim_reset=True, **kwargs))
            return_objects.append(
                self.aurora_64b_66b_flow_control_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, aurora_64b_66b_flow_control, aurora_64b_66b_flow_control,
            self.args, self.arg_types,
            custom_sources=[(stimulate_check, (), self.args)])

        for each in dut_outputs:
            if dut_outputs[each] != ref_outputs[each]:
                print(each)

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

class TestAurora64b66bFlowControlVivadoVhdl(
    KeaVivadoVHDLTestCase, TestAurora64b66bFlowControl):
    pass

class TestAurora64b66bFlowControlVivadoVerilog(
    KeaVivadoVerilogTestCase, TestAurora64b66bFlowControl):
    pass
