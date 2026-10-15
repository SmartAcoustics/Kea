from math import ceil, log

from myhdl import Signal, block, always, intbv, enum

from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from .definitions import ETHERNET_HEADER_N_BITS
from .test_utils import (
    ethernet_header_values_interface_types_generator,
    dut_args_setup,
    generate_tkeep_trailing_bytes,
    BaseEthernetFramerInterfaceTests,
    BaseEthernetFramerTests)
from ._multi_beat_framer import multi_beat_framer


class TestMultiBeatFramerInterface(
    BaseEthernetFramerInterfaceTests, KeaTestCase):
    ''' The DUT should reject incompatible interfaces and arguments.
    '''

    # NOTE there are common tests defined on the
    # BaseEthernetFramerInterfaceTests class in test_utils.

    axis_data_bytewidth = 4
    dut_func = staticmethod(multi_beat_framer)
    dut_name = 'multi_beat_framer'

    def test_axis_data_bitwidth_too_small(self):
        ''' The `multi_beat_framer` block should raise an error if the
        bitwidth of the `axis_source.TDATA` is less than 32.
        '''

        self.dut_args, _dut_arg_types = dut_args_setup(axis_data_bytewidth=2)

        # Check that the system errors
        self.assertRaisesRegex(
            TypeError,
            (self.dut_name + ': this block supports AXI stream data '
             'bitwidths that are greater than or equal to 32 bits.'),
            self.dut_func,
            **self.dut_args,
        )

    def test_axis_data_bitwidth_too_big(self):
        ''' The `multi_beat_framer` block should raise an error if the
        bitwidth of the `axis_source.TDATA` is greater than
        `ETHERNET_HEADER_N_BITS`.
        '''

        invalid_bitwidth = 2**ceil(log(ETHERNET_HEADER_N_BITS, 2))
        invalid_bytewidth = invalid_bitwidth/8

        self.dut_args, _dut_arg_types = (
            dut_args_setup(axis_data_bytewidth=invalid_bytewidth))

        # Check that the system errors
        self.assertRaisesRegex(
            TypeError,
            (self.dut_name + ': this block should only be used for AXI '
            'stream interfaces with a data bitwidth which is less than ' +
            str(ETHERNET_HEADER_N_BITS) + '. The single_beat_framer should '
            'be used when the AXI stream data bitwdith is greater than or '
            'equal to ' + str(ETHERNET_HEADER_N_BITS) + '.'),
            self.dut_func,
            **self.dut_args,
        )

    def test_non_power_of_two_axis_data_bitwidth(self):
        ''' The `multi_beat_framer` block should raise an error if the
        bitwidth of the `axis_source.TDATA` is not a power of two.
        '''

        invalid_bytewidth = 5
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

class TestMultiBeatFramer(BaseEthernetFramerTests, KeaTestCase):
    ''' The DUT should reject incompatible interfaces and arguments.
    '''

    # NOTE there are common functions defined on the BaseEthernetFramerTests
    # class in test_utils.

    dut_func = staticmethod(multi_beat_framer)

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

        accept_src_data = Signal(False)

        n_header_words = ETHERNET_HEADER_N_BITS//len(axis_sink.TDATA)
        header_word_count = Signal(intbv(0, 0, n_header_words))

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

            if reset or not accept_src_data:
                # axis_source.TREADY should be set low in response to a reset
                # or a low on accept_src_data
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

            if state == t_state.IDLE:
                if axis_source.TVALID:
                    # The DUT should start outputting the header
                    expected_axis_sink_tvalid.next = True
                    expected_axis_sink_tlast.next = False
                    expected_axis_sink_tkeep.next = keep_all_bytes

                    if n_header_words > 2:
                        # The DUT has more header words to output before it
                        # needs the first data word
                        header_word_count.next = 0
                        state.next = t_state.HEADER

                    else:
                        # The DUT should accept the first data word so it can
                        # fill the word (the remaining bits of the header
                        # won't fill the word).
                        accept_src_data.next = True
                        state.next = t_state.DATA

            elif state == t_state.HEADER:
                if axis_sink.TVALID and axis_sink.TREADY:
                    expected_axis_sink_tvalid.next = True

                    # Count the header words out of the DUT
                    header_word_count.next = header_word_count + 1

                    if header_word_count >= n_header_words - 2:
                        # The DUT should accept the first data word so it can
                        # fill the word (the remaining bits of the header
                        # won't fill the word).
                        accept_src_data.next = True
                        state.next = t_state.DATA

            elif state == t_state.DATA:
                if axis_sink.TVALID and axis_sink.TREADY:
                    # The word on the sink has been received
                    expected_axis_sink_tvalid.next = False

                if axis_source.TVALID and axis_source.TREADY:

                    # The DUT should output the data
                    expected_axis_sink_tvalid.next = True

                    if axis_source.TLAST:
                        # The DUT has accepted the last word of the packet
                        accept_src_data.next = False

                        state.next = t_state.LAST_WORD

            elif state == t_state.LAST_WORD:
                if axis_sink.TVALID and axis_sink.TREADY:
                    # The DUT should output the last data word
                    expected_axis_sink_tvalid.next = True
                    expected_axis_sink_tlast.next = True
                    expected_axis_sink_tkeep.next = keep_trailing_bytes

                    state.next = t_state.AWAIT_COMPLETE

            elif state == t_state.AWAIT_COMPLETE:
                if axis_sink.TVALID and axis_sink.TREADY:
                    if axis_source.TVALID:
                        # There is more data arriving on the source so the DUT
                        # should start outputting the header
                        expected_axis_sink_tvalid.next = True
                        expected_axis_sink_tlast.next = False
                        expected_axis_sink_tkeep.next = keep_all_bytes

                        if n_header_words > 2:
                            # The DUT has more header words to output before
                            # it needs the first data word
                            header_word_count.next = 0
                            state.next = t_state.HEADER

                        else:
                            # The DUT should accept the first data word so it
                            # can fill the word (the remaining bits of the
                            # header won't fill the word).
                            accept_src_data.next = True
                            state.next = t_state.DATA

                    else:
                        # The data output has completed
                        expected_axis_sink_tvalid.next = False
                        state.next = t_state.IDLE

            if reset:
                expected_axis_sink_tvalid.next = False

                accept_src_data.next = False

                state.next = t_state.IDLE

        return_objects.append(check)

        return return_objects

    def test_framing_32_bit(self):
        ''' The `multi_beat_framer` should forward all data packets received
        on the `axis_source` via the `axis_sink`. Each packet should be
        prepended with an ethernet header containing the following (in the
        order written):

            - Destination MAC (6 octets)
            - Source MAC (6 octets)
            - Ethertype (2 octets)

        It should be possible to specify these header values via the
        `ethernet_header_values_interface`. When
        `ethernet_header_values_interface.load_values` is set high the
        `multi_beat_framer` should store all destination MAC octets
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

        The `multi_beat_framer` should obey the AXI4-Stream spec on all AXI
        stream interfaces (`axis_source` and `axis_sink`).

        The `multi_beat_framer` requires that the bitwidth of
        `axis_sink.TDATA` is a power of two. The number of bits in the
        ethernet is not a power of two so it will not align with a word
        boundary. The `axis_sink` word which contains the last word of the
        header should be packed with data from the first word received on
        `axis_source`.

        This header alignment means that data received on `axis_source` should
        be repackaged onto `axis_sink`. Each source word should be separated
        into leading data and trailing data. The leading data from word `n`
        should be appended to the trailing data from word `n-1` and forwarded
        on `axis_sink`. The byte split between the leading and trailing data
        depends on the bitwidth of `axis_sink.TDATA`.

        This repackaging continues through the entire data packet and the
        last word on `axis_sink` should include only the trailing bytes of the
        last word received on `axis_source`. The `multi_beat_framer` should
        set `axis_sink.TKEEP` to indicate which bytes in the last word are
        valid.

        The data on `axis_sink` should be packed according to the following
        example when `axis_sink.TDATA` is 32 bits wide:

            Destination MAC = 00:01:02:03:04:05
            Source MAC = 10:11:12:13:14:15
            Ethertype = 0x2021

            Beat 0:

                TDATA[32:24] = Destination MAC octet 3 (0x03)
                TDATA[24:16] = Destination MAC octet 2 (0x02)
                TDATA[16:8]  = Destination MAC octet 1 (0x01)
                TDATA[8:0]   = Destination MAC octet 0 (0x00)

                TLAST = False
                TKEEP = 0b1111

            Beat 1:

                TDATA[32:24] = Source MAC octet 1 (0x11)
                TDATA[24:16] = Source MAC octet 0 (0x10)
                TDATA[16:8]  = Destination MAC octet 5 (0x05)
                TDATA[8:0]   = Destination MAC octet 4 (0x04)

                TLAST = False
                TKEEP = 0b1111

            Beat 2:

                TDATA[32:24] = Source MAC octet 5 (0x15)
                TDATA[24:16] = Source MAC octet 4 (0x14)
                TDATA[16:8]  = Source MAC octet 3 (0x13)
                TDATA[8:0]   = Source MAC octet 2 (0x12)

                TLAST = False
                TKEEP = 0b1111

            Beat 3:

                TDATA[32:24] = axis_source word 0 byte 1
                TDATA[24:16] = axis_source word 0 byte 0
                TDATA[16:8]  = EtherType byte 1 (0x20)
                TDATA[8:0]   = EtherType byte 0 (0x21)

                TLAST = False
                TKEEP = 0b1111

            Beat 4:

                TDATA[32:24] = axis_source word 1 byte 1
                TDATA[24:16] = axis_source word 1 byte 0
                TDATA[16:8]  = axis_source word 0 byte 3
                TDATA[8:0]   = axis_source word 0 byte 2

                TLAST = False
                TKEEP = 0b1111

            ...

            Beat n

                TDATA[32:24] = Don't care
                TDATA[24:16] = Don't care
                TDATA[16:8]  = axis_source word m byte 3
                TDATA[8:0]   = axis_source word m byte 2

                TLAST = True
                TKEEP = 0b0011
        '''
        self.base_test(axis_data_bytewidth=4)

    def test_framing_64_bit(self):
        ''' The `multi_beat_framer` should function correctly when the
        `axis_source.TDATA` and `axis_sink.TDATA` are 64 bits wide.

        The data on `axis_sink` should be packed according to the following
        example when `axis_sink.TDATA` is 64 bits wide:

            Destination MAC = 00:01:02:03:04:05
            Source MAC = 10:11:12:13:14:15
            Ethertype = 0x2021

            Beat 0:

                TDATA[64:56] = Source MAC octet 1 (0x11)
                TDATA[56:48] = Source MAC octet 0 (0x10)
                TDATA[48:40] = Destination MAC octet 5 (0x05)
                TDATA[40:32] = Destination MAC octet 4 (0x04)
                TDATA[32:24] = Destination MAC octet 3 (0x03)
                TDATA[24:16] = Destination MAC octet 2 (0x02)
                TDATA[16:8]  = Destination MAC octet 1 (0x01)
                TDATA[8:0]   = Destination MAC octet 0 (0x00)

                TLAST = False
                TKEEP = 0b11111111

            Beat 1:

                TDATA[64:56] = axis_source word 0 byte 1
                TDATA[56:48] = axis_source word 0 byte 0
                TDATA[48:40] = EtherType byte 1 (0x20)
                TDATA[40:32] = EtherType byte 0 (0x21)
                TDATA[32:24] = Source MAC octet 5 (0x15)
                TDATA[24:16] = Source MAC octet 4 (0x14)
                TDATA[16:8]  = Source MAC octet 3 (0x13)
                TDATA[8:0]   = Source MAC octet 2 (0x12)

                TLAST = False
                TKEEP = 0b11111111

            Beat 2:

                TDATA[64:56] = axis_source word 1 byte 1
                TDATA[56:48] = axis_source word 1 byte 0
                TDATA[48:40] = axis_source word 0 byte 7
                TDATA[40:32] = axis_source word 0 byte 6
                TDATA[32:24] = axis_source word 0 byte 5
                TDATA[24:16] = axis_source word 0 byte 4
                TDATA[16:8]  = axis_source word 0 byte 3
                TDATA[8:0]   = axis_source word 0 byte 2

                TLAST = False
                TKEEP = 0b11111111

            ...

            Beat n

                TDATA[64:56] = Don't care
                TDATA[56:48] = Don't care
                TDATA[48:40] = axis_source word m byte 7
                TDATA[40:32] = axis_source word m byte 6
                TDATA[32:24] = axis_source word m byte 5
                TDATA[24:16] = axis_source word m byte 4
                TDATA[16:8]  = axis_source word m byte 3
                TDATA[8:0]   = axis_source word m byte 2

                TLAST = True
                TKEEP = 0b00111111
        '''
        self.base_test(axis_data_bytewidth=8)

    def test_rapid_header_value_updates_32_bit(self):
        ''' The `multi_beat_framer` should function correctly when new header
        values are being loaded in rapid sucession.

        The header values should always update atomically. If new header
        values are loaded whilst the `multi_beat_framer` is outputting a
        header it should continue with the old header values and switch to the
        new header values for the next packet.

        The `multi_beat_framer` should always use the latest header values,
        even if `axis_source.TVALID` stays high after a packet completion. ie
        the `multi_beat_framer` should function correctly when packet `n`
        immediately follows packet `n-1`.
        '''
        self.base_test(axis_data_bytewidth=4, load_values_p=0.2)

    def test_rapid_header_value_updates_64_bit(self):
        ''' The `multi_beat_framer` should correclty handle rapid header value
        loading when `axis_source.TDATA` and `axis_sink.TDATA` are 64 bits
        wide.
        '''
        self.base_test(axis_data_bytewidth=8, load_values_p=0.2)

    def test_varying_tvalid_and_tready_32_bit(self):
        ''' The `multi_beat_framer` should function correctly when the
        `axis_source.TVALID` and `axis_sink.TREADY` signals are varying.
        '''
        self.base_test(
            axis_data_bytewidth=4,
            vary_axis_source_tvalid=True,
            axis_sink_tready_probability=0.5)

    def test_varying_tvalid_and_tready_64_bit(self):
        ''' The `multi_beat_framer` should correctly handle
        `axis_source.TVALID` and `axis_sink.TREADY` varying when
        `axis_source.TDATA` and `axis_sink.TDATA` are 64 bits wide.
        '''
        self.base_test(
            axis_data_bytewidth=8,
            vary_axis_source_tvalid=True,
            axis_sink_tready_probability=0.5)

    def test_reset_32_bit(self):
        ''' While `reset` is high, the `multi_beat_framer` should
        asynchronously hold `axis_source.TREADY` low.

        When `reset` is set high,  the `multi_beat_framer` should
        synchronously set `axis_sink.TVALID` low.

        A reset should not clear the header values.
        '''
        self.base_test(
            axis_data_bytewidth=4, reset_toggle_p=0.001, reset_pulse_p=0.003)

    def test_reset_64_bit(self):
        ''' The `multi_beat_framer` should correctly handle `reset` when
        `axis_source.TDATA` and `axis_sink.TDATA` are 64 bits wide.
        '''
        self.base_test(
            axis_data_bytewidth=8, reset_toggle_p=0.001, reset_pulse_p=0.003)

    def test_reset_varying_tvalid_and_tready_32_bit(self):
        ''' The `multi_beat_framer` should correctly handle `reset` when the
        `axis_source.TVALID` and `axis_sink.TREADY` are varying and
        `axis_source.TDATA` and `axis_sink.TDATA` are 32 bits wide.
        '''
        self.base_test(
            axis_data_bytewidth=4,
            vary_axis_source_tvalid=True,
            axis_sink_tready_probability=0.5,
            reset_toggle_p=0.0005,
            reset_pulse_p=0.001)

    def test_reset_varying_tvalid_and_tready_64_bit(self):
        ''' The `multi_beat_framer` should correctly handle `reset` when the
        `axis_source.TVALID` and `axis_sink.TREADY` are varying and
        `axis_source.TDATA` and `axis_sink.TDATA` are 64 bits wide.
        '''
        self.base_test(
            axis_data_bytewidth=8,
            vary_axis_source_tvalid=True,
            axis_sink_tready_probability=0.5,
            reset_toggle_p=0.0005,
            reset_pulse_p=0.001)

class TestTestMultiBeatFramerVivadoVhdl(
    KeaVivadoVHDLTestCase, TestMultiBeatFramer):
    pass

class TestTestMultiBeatFramerVivadoVerilog(
    KeaVivadoVerilogTestCase, TestMultiBeatFramer):
    pass
