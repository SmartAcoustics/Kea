from myhdl import block

from kea.hdl.signal_handling.asynchronous import sig_assigner

from .interfaces import EthernetHeaderValuesInterface

@block
def ethernet_header_values_connector(
    load_values, dest_mac_octet_0, dest_mac_octet_1, dest_mac_octet_2,
    dest_mac_octet_3, dest_mac_octet_4, dest_mac_octet_5, src_mac_octet_0,
    src_mac_octet_1, src_mac_octet_2, src_mac_octet_3, src_mac_octet_4,
    src_mac_octet_5, ethertype, ethernet_header_values_interface):
    ''' This block will connect the given signals to their counterpart on the
    `ethernet_header_values_interface`.
    '''

    if not isinstance(
        ethernet_header_values_interface, EthernetHeaderValuesInterface):
        raise TypeError(
            'ethernet_header_values_connector: '
            'ethernet_header_values_interface should be an instance of '
            'EthernetHeaderValuesInterface.')

    return_objects = []

    return_objects.append(
        sig_assigner(
            load_values, ethernet_header_values_interface.load_values))

    return_objects.append(
        sig_assigner(
            dest_mac_octet_0,
            ethernet_header_values_interface.dest_mac_octet(0)))
    return_objects.append(
        sig_assigner(
            dest_mac_octet_1,
            ethernet_header_values_interface.dest_mac_octet(1)))
    return_objects.append(
        sig_assigner(
            dest_mac_octet_2,
            ethernet_header_values_interface.dest_mac_octet(2)))
    return_objects.append(
        sig_assigner(
            dest_mac_octet_3,
            ethernet_header_values_interface.dest_mac_octet(3)))
    return_objects.append(
        sig_assigner(
            dest_mac_octet_4,
            ethernet_header_values_interface.dest_mac_octet(4)))
    return_objects.append(
        sig_assigner(
            dest_mac_octet_5,
            ethernet_header_values_interface.dest_mac_octet(5)))

    return_objects.append(
        sig_assigner(
            src_mac_octet_0,
            ethernet_header_values_interface.src_mac_octet(0)))
    return_objects.append(
        sig_assigner(
            src_mac_octet_1,
            ethernet_header_values_interface.src_mac_octet(1)))
    return_objects.append(
        sig_assigner(
            src_mac_octet_2,
            ethernet_header_values_interface.src_mac_octet(2)))
    return_objects.append(
        sig_assigner(
            src_mac_octet_3,
            ethernet_header_values_interface.src_mac_octet(3)))
    return_objects.append(
        sig_assigner(
            src_mac_octet_4,
            ethernet_header_values_interface.src_mac_octet(4)))
    return_objects.append(
        sig_assigner(
            src_mac_octet_5,
            ethernet_header_values_interface.src_mac_octet(5)))

    return_objects.append(
        sig_assigner(
            ethertype, ethernet_header_values_interface.ethertype))

    return return_objects
