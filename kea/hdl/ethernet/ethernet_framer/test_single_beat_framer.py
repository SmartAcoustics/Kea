import random

from myhdl import Signal, block, always, intbv, enum

from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from .definitions import ETHERNET_HEADER_N_BITS
from .test_utils import (
    dut_args_setup,
    generate_tkeep_trailing_bytes,
    BaseEthernetFramerInterfaceTests,
    BaseEthernetFramerTests)
from ._single_beat_framer import single_beat_framer

class TestSingleBeatFramerInterface(
    BaseEthernetFramerInterfaceTests, KeaTestCase):
    ''' The DUT should reject incompatible interfaces and arguments.
    '''

    # NOTE there are common tests defined on the
    # BaseEthernetFramerInterfaceTests class in test_utils.

    axis_data_bytewidth = 16
    dut_func = staticmethod(single_beat_framer)
    dut_name = 'single_beat_framer'

    def test_axis_data_bitwidth_too_small(self):
        ''' The `single_beat_framer` block should raise an error if the
        bitwidth of the `axis_source.TDATA` is less than
        `ETHERNET_HEADER_N_BITS`.
        '''

        invalid_bytewidth = random.choice([1, 2, 4, 8])

        self.dut_args, _dut_arg_types = (
            dut_args_setup(axis_data_bytewidth=invalid_bytewidth))

        # Check that the system errors
        self.assertRaisesRegex(
            TypeError,
            (self.dut_name + ': this block should only be used for AXI '
            'stream interfaces with a data bitwidth which are greater than ' +
            str(ETHERNET_HEADER_N_BITS) + '. The multi_beat_framer should be '
            'used when the AXI stream data bitwdith is less than ' +
            str(ETHERNET_HEADER_N_BITS) + '.'),
            self.dut_func,
            **self.dut_args,
        )

    def test_non_power_of_two_axis_data_bitwidth(self):
        ''' The `single_beat_framer` block should raise an error if the
        bitwidth of the `axis_source.TDATA` is not a power of two.
        '''

        invalid_bytewidth = 17
        self.dut_args, _dut_arg_types = (
            dut_args_setup(axis_data_bytewidth=invalid_bytewidth))

        # Check that the system errors
        self.assertRaisesRegex(
            TypeError,
            (self.dut_name + ': the bitwidth of the AXI stream data should '
            'be a power of 2.'),
            self.dut_func,
            **self.dut_args,
        )

class TestSingleBeatFramer(BaseEthernetFramerTests, KeaTestCase):
    ''' The DUT should reject incompatible interfaces and arguments.
    '''

    # NOTE there are common functions defined on the BaseEthernetFramerTests
    # class in test_utils.

    dut_func = staticmethod(single_beat_framer)

    @block
    def check_axis_control_signals(self, **dut_args):
        ''' This block performs continuous checks on the AXI stream control
        signals. We do not check the data lines here as the packet based
        checks above combined with the control line checks in this block are
        sufficient.
        '''

        clock = dut_args['clock']
        reset = dut_args['reset']
        ethernet_header_values_interface = (
            dut_args['ethernet_header_values_interface'])
        axis_source = dut_args['axis_source']
        axis_sink = dut_args['axis_sink']

        return_objects = []

        do_not_accept_data = Signal(False)
        last_sink_word_pending = Signal(False)

        keep_all_bytes = 2**len(axis_sink.TKEEP) - 1
        keep_trailing_bytes = (
            generate_tkeep_trailing_bytes(len(axis_sink.TDATA)))

        expected_axis_sink_tvalid = Signal(False)
        expected_axis_sink_tlast = Signal(False)
        expected_axis_sink_tkeep = Signal(intbv(0)[len(axis_sink.TKEEP):])

        t_state = enum(
            'IDLE', 'HEADER', 'DATA', 'LAST_WORD', 'AWAIT_COMPLETE')
        state = Signal(t_state.IDLE)

        @always(clock.posedge)
        def check():

            #############################
            # axis_source.TREADY checks #
            #############################

            if reset or do_not_accept_data:
                # axis_source.TREADY should be set low in response to a reset
                # or a do_not_accept_data
                assert(not axis_source.TREADY)

            else:
                if axis_sink.TVALID:
                    # There is data on the axis_sink so the DUT should only
                    # set axis_source.TREADY if axis_sink.TREADY is high.
                    assert(axis_source.TREADY == axis_sink.TREADY)

                else:
                    # There is no data on axis_sink so axis_source.TREADY
                    # should be high
                    assert(axis_source.TREADY)

            ####################
            # axis_sink checks #
            ####################

            assert(axis_sink.TVALID == expected_axis_sink_tvalid)
            assert(axis_sink.TLAST == expected_axis_sink_tlast)
            assert(axis_sink.TKEEP == expected_axis_sink_tkeep)

            if axis_sink.TVALID and axis_sink.TREADY:
                # The word on the sink has been received
                expected_axis_sink_tvalid.next = False

                # The do_not_accept_data signal should only ever go high for
                # one axis_sink word
                do_not_accept_data.next = False

                if last_sink_word_pending:
                    last_sink_word_pending.next = False

                    # The DUT should output the last word on the axis_sink
                    expected_axis_sink_tvalid.next = True
                    expected_axis_sink_tlast.next = True
                    expected_axis_sink_tkeep.next = keep_trailing_bytes

            if axis_source.TVALID and axis_source.TREADY:
                # The DUT should output the data
                expected_axis_sink_tvalid.next = True
                expected_axis_sink_tlast.next = False
                expected_axis_sink_tkeep.next = keep_all_bytes

                if axis_source.TLAST:
                    # The DUT has accepted the last word of the packet
                    do_not_accept_data.next = True
                    last_sink_word_pending.next = True

            if reset:
                expected_axis_sink_tvalid.next = False

                do_not_accept_data.next = False
                last_sink_word_pending.next = False

        return_objects.append(check)

        return return_objects

    def test_framing(self):
        ''' The `single_beat_framer` should forward all data packets received
        on the `axis_source` via the `axis_sink`. Each packet should be
        prepended with an ethernet header containing the following (in the
        order written):

            - Destination MAC (6 octets)
            - Source MAC (6 octets)
            - Ethertype (2 octets)

        It should be possible to specify these header values via the
        `ethernet_header_values_interface`. When
        `ethernet_header_values_interface.load_values` is set high the
        `single_beat_framer` should store all destination MAC octets
        (`ethernet_header_values_interface.dest_mac_octet(n)`), all source MAC
        octets (`ethernet_header_values_interface.src_mac_octet(n)`) and the
        ethertype (`ethernet_header_values_interface.ethertype`). It should
        retain the values until `ethernet_header_values_interface.load_values`
        is set high again.

        Before `ethernet_header_values_interface.load_values` is set high,
        the destination MAC, source MAC and ethertype will default to 0.

        MAC addresses are commonly written in the following form:

            00:01:02:03:04:05

        The mapping from this form to the source and destination octets in the
        `ethernet_header_values_interface` is:

            <Octet 0>:<Octet 1>:<Octet 2>:<Octet 3>:<Octet 4>:<Octet 5>

        The `single_beat_framer` should obey the AXI4-Stream spec on all AXI
        stream interfaces (`axis_source` and `axis_sink`).

        The `single_beat_framer` requires that the bitwidth of
        `axis_sink.TDATA` is a power of two. The number of bits in the
        ethernet is not a power of two so it will not align with a word
        boundary. The first `axis_sink` word of each packet will contain the
        header but the header will not fill the entire word so the rest of the
        bits should be packed with data from the first word received on
        `axis_source`.

        This header alignment means that data received on `axis_source` should
        be repackaged onto `axis_sink`. Each source word should be separated
        into leading data and trailing data. The leading data from word `n`
        should be appended to the trailing data from word `n-1` and forwarded
        on `axis_sink`. The byte split between the leading and trailing data
        depends on the bitwidth of `axis_sink.TDATA`.

        This repackaging continues through the entire data packet and the
        last word on `axis_sink` should include only the trailing bytes of the
        last word received on `axis_source`. The `single_beat_framer` should
        set `axis_sink.TKEEP` to indicate which bytes in the last word are
        valid.

        The data on `axis_sink` should be packed according to the following
        example when `axis_sink.TDATA` is 128 bits wide:

            Destination MAC = 00:01:02:03:04:05
            Source MAC = 10:11:12:13:14:15
            Ethertype = 0x2021

            Beat 0:

                TDATA[128:120] = axis_source word 0 byte 1
                TDATA[120:112] = axis_source word 0 byte 0
                TDATA[112:104] = EtherType byte 1 (0x20)
                TDATA[104:96]  = EtherType byte 0 (0x21)
                TDATA[96:88]   = Source MAC octet 5 (0x15)
                TDATA[88:80]   = Source MAC octet 4 (0x14)
                TDATA[80:72]   = Source MAC octet 3 (0x13)
                TDATA[72:64]   = Source MAC octet 2 (0x12)
                TDATA[64:56]   = Source MAC octet 1 (0x11)
                TDATA[56:48]   = Source MAC octet 0 (0x10)
                TDATA[48:40]   = Destination MAC octet 5 (0x05)
                TDATA[40:32]   = Destination MAC octet 4 (0x04)
                TDATA[32:24]   = Destination MAC octet 3 (0x03)
                TDATA[24:16]   = Destination MAC octet 2 (0x02)
                TDATA[16:8]    = Destination MAC octet 1 (0x01)
                TDATA[8:0]     = Destination MAC octet 0 (0x00)

                TLAST = False
                TKEEP = 0b1111111111111111

            Beat 1:

                TDATA[128:120] = axis_source word 1 byte 1
                TDATA[120:112] = axis_source word 1 byte 0
                TDATA[112:104] = axis_source word 0 byte 15
                TDATA[104:96]  = axis_source word 0 byte 14
                TDATA[96:88]   = axis_source word 0 byte 13
                TDATA[88:80]   = axis_source word 0 byte 12
                TDATA[80:72]   = axis_source word 0 byte 11
                TDATA[72:64]   = axis_source word 0 byte 10
                TDATA[64:56]   = axis_source word 0 byte 9
                TDATA[56:48]   = axis_source word 0 byte 8
                TDATA[48:40]   = axis_source word 0 byte 7
                TDATA[40:32]   = axis_source word 0 byte 6
                TDATA[32:24]   = axis_source word 0 byte 5
                TDATA[24:16]   = axis_source word 0 byte 4
                TDATA[16:8]    = axis_source word 0 byte 3
                TDATA[8:0]     = axis_source word 0 byte 2

                TLAST = False
                TKEEP = 0b1111111111111111

            ...

            Beat n

                TDATA[128:120] = Don't care
                TDATA[120:112] = Don't care
                TDATA[112:104] = axis_source word m byte 15
                TDATA[104:96]  = axis_source word m byte 14
                TDATA[96:88]   = axis_source word m byte 13
                TDATA[88:80]   = axis_source word m byte 12
                TDATA[80:72]   = axis_source word m byte 11
                TDATA[72:64]   = axis_source word m byte 10
                TDATA[64:56]   = axis_source word m byte 9
                TDATA[56:48]   = axis_source word m byte 8
                TDATA[48:40]   = axis_source word m byte 7
                TDATA[40:32]   = axis_source word m byte 6
                TDATA[32:24]   = axis_source word m byte 5
                TDATA[24:16]   = axis_source word m byte 4
                TDATA[16:8]    = axis_source word m byte 3
                TDATA[8:0]     = axis_source word m byte 2

                TLAST = True
                TKEEP = 0b0011111111111111
        '''
        self.base_test(axis_data_bytewidth=16)

    def test_framing_larger_bitwidths(self):
        ''' The `single_beat_framer` should function correctly for any
        bitwidths of `axis_source.TDATA` and `axis_sink.TDATA` which are
        greater than the number of bits in the header.
        '''
        self.base_test(axis_data_bytewidth=32)

    def test_rapid_header_value_updates(self):
        ''' The `single_beat_framer` should function correctly when new header
        values are being loaded in rapid sucession.

        The `single_beat_framer` should always use the latest header values,
        even if `axis_source.TVALID` stays high after a packet completion. ie
        the `single_beat_framer` should function correctly when packet `n`
        immediately follows packet `n-1`.
        '''
        self.base_test(axis_data_bytewidth=16, load_values_p=0.2)

    def test_varying_tvalid_and_tready(self):
        ''' The `single_beat_framer` should function correctly when the
        `axis_source.TVALID` and `axis_sink.TREADY` signals are varying.
        '''
        self.base_test(
            axis_data_bytewidth=16,
            vary_axis_source_tvalid=True,
            axis_sink_tready_probability=0.5)

    def test_reset(self):
        ''' While `reset` is high, the `single_beat_framer` should
        asynchronously hold `axis_source.TREADY` low.

        When `reset` is set high,  the `single_beat_framer` should
        synchronously set `axis_sink.TVALID` low.

        A reset should not clear the header values.
        '''
        self.base_test(
            axis_data_bytewidth=16, reset_toggle_p=0.001, reset_pulse_p=0.003)

    def test_reset_varying_tvalid_and_tready(self):
        ''' The `single_beat_framer` should correctly handle `reset` when the
        `axis_source.TVALID` and `axis_sink.TREADY` are varying.
        '''
        self.base_test(
            axis_data_bytewidth=16,
            vary_axis_source_tvalid=True,
            axis_sink_tready_probability=0.5,
            reset_toggle_p=0.0005,
            reset_pulse_p=0.001)

    def test_reset_varying_tvalid_and_tready_larger_bitwidths(self):
        ''' The `single_beat_framer` should correctly handle `reset` when the
        `axis_source.TVALID` and `axis_sink.TREADY` are varying for any
        bitwidths of `axis_source.TDATA` and `axis_sink.TDATA` which are
        greater than the number of bits in the header.
        '''
        self.base_test(
            axis_data_bytewidth=32,
            vary_axis_source_tvalid=True,
            axis_sink_tready_probability=0.5,
            reset_toggle_p=0.0005,
            reset_pulse_p=0.001)

class TestTestSingleBeatFramerVivadoVhdl(
    KeaVivadoVHDLTestCase, TestSingleBeatFramer):
    pass

class TestTestSingleBeatFramerVivadoVerilog(
    KeaVivadoVerilogTestCase, TestSingleBeatFramer):
    pass
