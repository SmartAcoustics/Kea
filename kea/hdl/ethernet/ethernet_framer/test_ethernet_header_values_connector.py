import random

from myhdl import block, Signal, intbv, always

from kea.hdl.ethernet.definitions import (
    OCTET_BITWIDTH, DEST_MAC_N_OCTETS, SRC_MAC_N_OCTETS, ETHERTYPE_BITWIDTH)
from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._ethernet_header_values_connector import (
    ethernet_header_values_connector)
from .interfaces import EthernetHeaderValuesInterface

def ethernet_header_values_interface_types_generator():
    ''' Generates the types for the `EthernetHeaderValuesInterface`.
    '''

    types = {
        'load_values': 'output',
        'ethertype': 'output',
    }

    for n in range(DEST_MAC_N_OCTETS):
        types['dest_mac_octet_'+str(n)] = 'output'

    for n in range(SRC_MAC_N_OCTETS):
        types['src_mac_octet_'+str(n)] = 'output'

    return types

def dut_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    ethernet_header_values_interface = EthernetHeaderValuesInterface()

    dut_args = {
        'load_values': Signal(False),
        'dest_mac_octet_0': Signal(intbv(0)[OCTET_BITWIDTH:]),
        'dest_mac_octet_1': Signal(intbv(0)[OCTET_BITWIDTH:]),
        'dest_mac_octet_2': Signal(intbv(0)[OCTET_BITWIDTH:]),
        'dest_mac_octet_3': Signal(intbv(0)[OCTET_BITWIDTH:]),
        'dest_mac_octet_4': Signal(intbv(0)[OCTET_BITWIDTH:]),
        'dest_mac_octet_5': Signal(intbv(0)[OCTET_BITWIDTH:]),
        'src_mac_octet_0': Signal(intbv(0)[OCTET_BITWIDTH:]),
        'src_mac_octet_1': Signal(intbv(0)[OCTET_BITWIDTH:]),
        'src_mac_octet_2': Signal(intbv(0)[OCTET_BITWIDTH:]),
        'src_mac_octet_3': Signal(intbv(0)[OCTET_BITWIDTH:]),
        'src_mac_octet_4': Signal(intbv(0)[OCTET_BITWIDTH:]),
        'src_mac_octet_5': Signal(intbv(0)[OCTET_BITWIDTH:]),
        'ethertype': Signal(intbv(0)[ETHERTYPE_BITWIDTH:]),
        'ethernet_header_values_interface': ethernet_header_values_interface,
    }

    ethernet_header_values_interface_types = (
        ethernet_header_values_interface_types_generator())

    dut_arg_types = {
        'load_values': 'custom',
        'dest_mac_octet_0': 'custom',
        'dest_mac_octet_1': 'custom',
        'dest_mac_octet_2': 'custom',
        'dest_mac_octet_3': 'custom',
        'dest_mac_octet_4': 'custom',
        'dest_mac_octet_5': 'custom',
        'src_mac_octet_0': 'custom',
        'src_mac_octet_1': 'custom',
        'src_mac_octet_2': 'custom',
        'src_mac_octet_3': 'custom',
        'src_mac_octet_4': 'custom',
        'src_mac_octet_5': 'custom',
        'ethertype': 'custom',
        'ethernet_header_values_interface': (
            ethernet_header_values_interface_types),
    }

    return dut_args, dut_arg_types

def dut_wrapper_args_setup():
    ''' Generate the arguments and argument types for the DUT wrapper.
    '''

    dut_wrapper_args, dut_wrapper_arg_types = dut_args_setup()

    dut_wrapper_args['clock'] = Signal(False)
    dut_wrapper_arg_types['clock'] = 'clock'

    return dut_wrapper_args, dut_wrapper_arg_types

@block
def ethernet_header_values_connector_wrapper(clock, **dut_args):
    ''' A wrapper so the test has a clock.
    '''
    return_objects = []

    return_objects.append(ethernet_header_values_connector(**dut_args))

    return return_objects

class TestEthernetHeaderValuesConnectorInterface(KeaTestCase):

    def setUp(self):

        self.dut_args, _dut_arg_types = dut_args_setup()

    def test_invalid_ethernet_header_values_interface(self):
        '''The `ethernet_header_values_interface` should be an instance of
        `EthernetHeaderValuesInterface`.

        Anything else should raise an error.
        '''
        self.dut_args['ethernet_header_values_interface'] = (
            'This is not an interface')

        # Check that the system errors
        self.assertRaisesRegex(
            TypeError,
            ('ethernet_header_values_connector: '
             'ethernet_header_values_interface should be an instance of '
             'EthernetHeaderValuesInterface.'),
            ethernet_header_values_connector,
            **self.dut_args,
        )

class TestEthernetHeaderValuesConnector(KeaTestCase):

    @block
    def stim_check_dut(self, **dut_wrapper_args):

        clock = dut_wrapper_args['clock']
        load_values_in = dut_wrapper_args['load_values']
        dest_mac_octets_in = [
            dut_wrapper_args['dest_mac_octet_0'],
            dut_wrapper_args['dest_mac_octet_1'],
            dut_wrapper_args['dest_mac_octet_2'],
            dut_wrapper_args['dest_mac_octet_3'],
            dut_wrapper_args['dest_mac_octet_4'],
            dut_wrapper_args['dest_mac_octet_5'],
        ]
        src_mac_octets_in = [
            dut_wrapper_args['src_mac_octet_0'],
            dut_wrapper_args['src_mac_octet_1'],
            dut_wrapper_args['src_mac_octet_2'],
            dut_wrapper_args['src_mac_octet_3'],
            dut_wrapper_args['src_mac_octet_4'],
            dut_wrapper_args['src_mac_octet_5'],
        ]
        ethertype_in = dut_wrapper_args['ethertype']
        ethernet_header_values_interface = (
            dut_wrapper_args['ethernet_header_values_interface'])

        return_objects = []

        # Sanity check
        assert(len(dest_mac_octets_in) == DEST_MAC_N_OCTETS)
        assert(len(src_mac_octets_in) == SRC_MAC_N_OCTETS)

        load_values_out = ethernet_header_values_interface.load_values

        dest_mac_octets_out = [
            ethernet_header_values_interface.dest_mac_octet(n)
            for n in range(DEST_MAC_N_OCTETS)]

        src_mac_octets_out = [
            ethernet_header_values_interface.src_mac_octet(n)
            for n in range(SRC_MAC_N_OCTETS)]

        ethertype_out = ethernet_header_values_interface.ethertype

        octet_upper_bound = 2**OCTET_BITWIDTH
        ethertype_upper_bound = 2**ETHERTYPE_BITWIDTH

        @always(clock.posedge)
        def stim_check():

            load_values_in.next = bool(random.randrange(2))
            assert(load_values_out == load_values_in)

            for n in range(DEST_MAC_N_OCTETS):
                dest_mac_octets_in[n].next = (
                    random.randrange(octet_upper_bound))
                assert(dest_mac_octets_out[n] == dest_mac_octets_in[n])

            for n in range(SRC_MAC_N_OCTETS):
                src_mac_octets_in[n].next = (
                    random.randrange(octet_upper_bound))
                assert(src_mac_octets_out[n] == src_mac_octets_in[n])

            ethertype_in.next = random.randrange(ethertype_upper_bound)
            assert(ethertype_out == ethertype_in)

        return_objects.append(stim_check)

        return return_objects

    def base_test(self):

        dut_wrapper_args, dut_wrapper_arg_types = dut_wrapper_args_setup()

        if not self.testing_using_vivado:
            cycles = 4000
        else:
            cycles = 1000

        @block
        def stimulate_check(**dut_wrapper_args):

            return_objects = []

            return_objects.append(self.stim_check_dut(**dut_wrapper_args))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, ethernet_header_values_connector_wrapper,
            ethernet_header_values_connector_wrapper, dut_wrapper_args,
            dut_wrapper_arg_types,
            custom_sources=[(stimulate_check, (), dut_wrapper_args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_connections(self):
        ''' The `ethernet_header_values_connector` should connect the:

            - `load_values` to `ethernet_header_values_interface.load_values`.
            - `dest_mac_octet_<n>` signals to their corresponding signal on
            the `ethernet_header_values_interface`.
            - `src_mac_octet_<n>` signals to their corresponding signal on
            the `ethernet_header_values_interface`.
            - `ethertype` to `ethernet_header_values_interface.ethertype`.
            - `data` to `ethernet_header_values_interface.data`.
        '''
        self.base_test()

class TestEthernetHeaderValuesConnectorVivadoVhdl(
    KeaVivadoVHDLTestCase, TestEthernetHeaderValuesConnector):
    pass

class TestEthernetHeaderValuesConnectorVivadoVerilog(
    KeaVivadoVerilogTestCase, TestEthernetHeaderValuesConnector):
    pass
