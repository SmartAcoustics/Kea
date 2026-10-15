from myhdl import block, Signal, always

from kea.hdl.cdc import double_buffer
from kea.hdl.signal_handling.asynchronous import sig_assigner
from kea.utils.interface_checks import check_bool_signal

from .interfaces import EthernetStatusInterface

@block
def ethernet_monitor(
    clock, reset, raw_ethernet_status_interface, ethernet_status_interface,
    ethernet_errors_interface):
    ''' Monitors the ethernet status.

    It also buffers the raw ethernet status signals and outputs the buffered
    version.
    '''

    check_bool_signal(clock, 'clock')
    check_bool_signal(reset, 'reset')

    if not isinstance(raw_ethernet_status_interface, EthernetStatusInterface):
        raise TypeError(
            'ethernet_monitor: raw_ethernet_status_interface should be an '
            'instance of EthernetStatusInterface.')

    if not isinstance(ethernet_status_interface, EthernetStatusInterface):
        raise TypeError(
            'ethernet_monitor: ethernet_status_interface should be an '
            'instance of EthernetStatusInterface.')

    if not isinstance(ethernet_errors_interface, EthernetStatusInterface):
        raise TypeError(
            'ethernet_monitor: ethernet_errors_interface should be an '
            'instance of EthernetStatusInterface.')

    return_objects = []

    internal_mac_clock_locked = Signal(False)
    internal_sfp_rx_loss_of_signal = Signal(False)
    internal_sfp_module_absent = Signal(False)
    internal_sfp_tx_fault = Signal(False)

    # Double buffer the raw ethernet status signals #

    return_objects.append(
        double_buffer(
            clock, raw_ethernet_status_interface.mac_clock_locked,
            internal_mac_clock_locked))

    return_objects.append(
        double_buffer(
            clock, raw_ethernet_status_interface.sfp_rx_loss_of_signal,
            internal_sfp_rx_loss_of_signal))

    return_objects.append(
        double_buffer(
            clock, raw_ethernet_status_interface.sfp_module_absent,
            internal_sfp_module_absent))

    return_objects.append(
        double_buffer(
            clock, raw_ethernet_status_interface.sfp_tx_fault,
            internal_sfp_tx_fault))

    # Connect the double buffered status signals to the status interface #

    return_objects.append(
        sig_assigner(
            internal_mac_clock_locked,
            ethernet_status_interface.mac_clock_locked))

    return_objects.append(
        sig_assigner(
            internal_sfp_rx_loss_of_signal,
            ethernet_status_interface.sfp_rx_loss_of_signal))

    return_objects.append(
        sig_assigner(
            internal_sfp_module_absent,
            ethernet_status_interface.sfp_module_absent))

    return_objects.append(
        sig_assigner(
            internal_sfp_tx_fault,
            ethernet_status_interface.sfp_tx_fault))

    @always(clock.posedge)
    def monitor():

        # Monitor the status signals and set the errors #

        if not internal_mac_clock_locked:
            ethernet_errors_interface.mac_clock_locked.next = True

        if internal_sfp_rx_loss_of_signal:
            ethernet_errors_interface.sfp_rx_loss_of_signal.next = True

        if internal_sfp_module_absent:
            ethernet_errors_interface.sfp_module_absent.next = True

        if internal_sfp_tx_fault:
            ethernet_errors_interface.sfp_tx_fault.next = True

        if reset:

            # Reset the errors #

            ethernet_errors_interface.mac_clock_locked.next = False
            ethernet_errors_interface.sfp_rx_loss_of_signal.next = False
            ethernet_errors_interface.sfp_module_absent.next = False
            ethernet_errors_interface.sfp_tx_fault.next = False

    return_objects.append(monitor)

    return return_objects
