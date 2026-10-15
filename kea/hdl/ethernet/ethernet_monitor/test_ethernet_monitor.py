import random

from myhdl import block, Signal, always, StopSimulation

from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)
from kea.utils.interface_checks import (
    check_bool_signal,
    get_dut_function_call_arguments,
    verify_dut_called_function)

from .interfaces import EthernetStatusInterface
from ._ethernet_monitor import ethernet_monitor

def ethernet_status_interface_types_generator(direction):
    ''' Generates the types for the `ethernet_header_values_interface`.
    '''

    if direction == 'input':
        signal_type = 'custom'

    elif direction == 'output':
        signal_type = 'output'

    else:
        raise ValueError(
            'ethernet_status_interface_types_generator: invalid direction.')

    types = {
        'mac_clock_locked': signal_type,
        'sfp_rx_loss_of_signal': signal_type,
        'sfp_module_absent': signal_type,
        'sfp_tx_fault': signal_type,
    }

    return types

def dut_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    dut_args = {
        'clock': Signal(False),
        'reset': Signal(False),
        'raw_ethernet_status_interface': EthernetStatusInterface(),
        'ethernet_status_interface': EthernetStatusInterface(),
        'ethernet_errors_interface': EthernetStatusInterface(),
    }

    ethernet_status_input_types = (
        ethernet_status_interface_types_generator('input'))

    ethernet_status_output_types = (
        ethernet_status_interface_types_generator('output'))

    dut_arg_types = {
        'clock': 'clock',
        'reset': 'custom',
        'raw_ethernet_status_interface': ethernet_status_input_types,
        'ethernet_status_interface': ethernet_status_output_types,
        'ethernet_errors_interface': ethernet_status_output_types,
    }

    return dut_args, dut_arg_types

class TestEthernetMonitorInterface(KeaTestCase):
    ''' The DUT should reject incompatible interfaces and arguments.
    '''

    def setUp(self):

        self.dut_args, _dut_arg_types = dut_args_setup()

    def test_bool_ports_checked(self):
        '''The `clock` and `reset` ports should be boolean signals.

        Anything else should raise an error.
        '''
        dut = ethernet_monitor
        bool_port_names = ['clock', 'reset']

        # Get all calls to check_bool_signal made by the DUT
        dut_function_call_arguments_list = (
            get_dut_function_call_arguments(
                check_bool_signal, dut, self.dut_args))

        for port_name in bool_port_names:
            expected_args_dict = {
                'test_signal': self.dut_args[port_name],
                'name': port_name,
            }

            # Check that the specified port was checked
            verify_dut_called_function(
                check_bool_signal, dut_function_call_arguments_list,
                expected_args_dict, 'test_signal', port_name)

    def test_invalid_raw_ethernet_status_interface(self):
        ''' The `ethernet_monitor` should raise an error if the
        `raw_ethernet_status_interface` is not an instance of
        `EthernetStatusInterface`.
        '''

        self.dut_args['raw_ethernet_status_interface'] = (
            random.randrange(0, 100))

        # Check that the system errors
        self.assertRaisesRegex(
            TypeError,
            ('ethernet_monitor: raw_ethernet_status_interface should be an '
             'instance of EthernetStatusInterface.'),
            ethernet_monitor,
            **self.dut_args,
        )

    def test_invalid_ethernet_status_interface(self):
        ''' The `ethernet_monitor` should raise an error if the
        `ethernet_status_interface` is not an instance of
        `EthernetStatusInterface`.
        '''

        self.dut_args['ethernet_status_interface'] = (
            random.randrange(0, 100))

        # Check that the system errors
        self.assertRaisesRegex(
            TypeError,
            ('ethernet_monitor: ethernet_status_interface should be an '
             'instance of EthernetStatusInterface.'),
            ethernet_monitor,
            **self.dut_args,
        )

    def test_invalid_ethernet_errors_interface(self):
        ''' The `ethernet_monitor` should raise an error if the
        `ethernet_errors_interface` is not an instance of
        `EthernetStatusInterface`.
        '''

        self.dut_args['ethernet_errors_interface'] = (
            random.randrange(0, 100))

        # Check that the system errors
        self.assertRaisesRegex(
            TypeError,
            ('ethernet_monitor: ethernet_errors_interface should be an '
             'instance of EthernetStatusInterface.'),
            ethernet_monitor,
            **self.dut_args,
        )

class TestEthernetMonitor(KeaTestCase):

    def setUp(self):

        self.test_count = 0
        self.tests_complete = False

    @block
    def monitor_tests(self, n_tests, **dut_args):

        clock = dut_args['clock']

        return_objects = []

        @always(clock.posedge)
        def monitor():

            if self.test_count >= n_tests:
                # Check that all the tests are run
                self.tests_complete = True

                raise StopSimulation

        return_objects.append(monitor)

        return return_objects

    @block
    def stim_dut(self, **dut_args):

        clock = dut_args['clock']
        reset = dut_args['reset']
        raw_ethernet_status_interface = (
            dut_args['raw_ethernet_status_interface'])

        return_objects = []

        signal_change_p = 0.005

        raw_mac_clock_locked = raw_ethernet_status_interface.mac_clock_locked
        raw_sfp_rx_loss_of_signal = (
            raw_ethernet_status_interface.sfp_rx_loss_of_signal)
        raw_sfp_module_absent = (
            raw_ethernet_status_interface.sfp_module_absent)
        raw_sfp_tx_fault = raw_ethernet_status_interface.sfp_tx_fault

        hold_reset_high = Signal(False)

        @always(clock.posedge)
        def stim():

            #################################
            # raw_ethernet_status_interface #
            #################################

            if random.random() < signal_change_p:
                raw_mac_clock_locked.next = not raw_mac_clock_locked

            if random.random() < signal_change_p:
                raw_sfp_rx_loss_of_signal.next = not raw_sfp_rx_loss_of_signal

            if random.random() < signal_change_p:
                raw_sfp_module_absent.next = not raw_sfp_module_absent

            if random.random() < signal_change_p:
                raw_sfp_tx_fault.next = not raw_sfp_tx_fault

            #########
            # Reset #
            #########

            if random.random() < 0.001:
                # Hold reset high for extended period
                hold_reset_high.next = not hold_reset_high
                reset.next = not reset

            elif not hold_reset_high:

                reset.next = False

                if random.random() < 0.003:
                    # Randomly pulse reset
                    reset.next = True

        return_objects.append(stim)

        return return_objects

    @block
    def check_dut(self, **dut_args):

        clock = dut_args['clock']
        reset = dut_args['reset']
        raw_ethernet_status_interface = (
            dut_args['raw_ethernet_status_interface'])
        ethernet_status_interface = dut_args['ethernet_status_interface']
        ethernet_errors_interface = dut_args['ethernet_errors_interface']

        return_objects = []

        # Extract the raw status signals
        raw_mac_clocked_locked = (
            raw_ethernet_status_interface.mac_clock_locked)
        raw_sfp_rx_loss_of_signal = (
            raw_ethernet_status_interface.sfp_rx_loss_of_signal)
        raw_sfp_module_absent = (
            raw_ethernet_status_interface.sfp_module_absent)
        raw_sfp_tx_fault = raw_ethernet_status_interface.sfp_tx_fault

        # Create the intermediate register for th raw status signals
        raw_mac_clocked_locked_d0 = Signal(False)
        raw_sfp_rx_loss_of_signal_d0 = Signal(False)
        raw_sfp_module_absent_d0 = Signal(False)
        raw_sfp_tx_fault_d0 = Signal(False)

        # Extract the status signals
        mac_clocked_locked = ethernet_status_interface.mac_clock_locked
        sfp_rx_loss_of_signal = (
            ethernet_status_interface.sfp_rx_loss_of_signal)
        sfp_module_absent = ethernet_status_interface.sfp_module_absent
        sfp_tx_fault = ethernet_status_interface.sfp_tx_fault

        # Extract the error signals
        mac_clock_locked_error = ethernet_errors_interface.mac_clock_locked
        sfp_rx_loss_of_signal_error = (
            ethernet_errors_interface.sfp_rx_loss_of_signal)
        sfp_module_absent_error = ethernet_errors_interface.sfp_module_absent
        sfp_tx_fault_error = ethernet_errors_interface.sfp_tx_fault

        expected_mac_clocked_locked = Signal(False)
        expected_sfp_rx_loss_of_signal = Signal(False)
        expected_sfp_module_absent = Signal(False)
        expected_sfp_tx_fault = Signal(False)

        expected_mac_clock_locked_error = Signal(False)
        expected_sfp_rx_loss_of_signal_error = Signal(False)
        expected_sfp_module_absent_error = Signal(False)
        expected_sfp_tx_fault_error = Signal(False)

        @always(clock.posedge)
        def check():

            # Check the status signals
            assert(mac_clocked_locked == expected_mac_clocked_locked)
            assert(sfp_rx_loss_of_signal == expected_sfp_rx_loss_of_signal)
            assert(sfp_module_absent == expected_sfp_module_absent)
            assert(sfp_tx_fault == expected_sfp_tx_fault)

            # Check the error signals
            assert(mac_clock_locked_error == expected_mac_clock_locked_error)
            assert(
                sfp_rx_loss_of_signal_error ==
                expected_sfp_rx_loss_of_signal_error)
            assert(
                sfp_module_absent_error == expected_sfp_module_absent_error)
            assert(sfp_tx_fault_error == expected_sfp_tx_fault_error)

            # The raw status signals should be double buffered
            raw_mac_clocked_locked_d0.next = raw_mac_clocked_locked
            raw_sfp_rx_loss_of_signal_d0.next = raw_sfp_rx_loss_of_signal
            raw_sfp_module_absent_d0.next = raw_sfp_module_absent
            raw_sfp_tx_fault_d0.next = raw_sfp_tx_fault

            expected_mac_clocked_locked.next = raw_mac_clocked_locked_d0
            expected_sfp_rx_loss_of_signal.next = raw_sfp_rx_loss_of_signal_d0
            expected_sfp_module_absent.next = raw_sfp_module_absent_d0
            expected_sfp_tx_fault.next = raw_sfp_tx_fault_d0

            if reset:
                # A reset should set all errors low
                expected_mac_clock_locked_error.next = False
                expected_sfp_rx_loss_of_signal_error.next = False
                expected_sfp_module_absent_error.next = False
                expected_sfp_tx_fault_error.next = False

                if (expected_mac_clock_locked_error or
                    expected_sfp_rx_loss_of_signal_error or
                    expected_sfp_module_absent_error or
                    expected_sfp_tx_fault_error):

                    self.test_count += 1

            else:

                if not mac_clocked_locked:
                    expected_mac_clock_locked_error.next = True

                if sfp_rx_loss_of_signal:
                    expected_sfp_rx_loss_of_signal_error.next = True

                if sfp_module_absent:
                    expected_sfp_module_absent_error.next = True

                if sfp_tx_fault:
                    expected_sfp_tx_fault_error.next = True

        return_objects.append(check)

        return return_objects

    def base_test(self):

        dut_args, dut_arg_types = dut_args_setup()

        if not self.testing_using_vivado:
            cycles = 100000
            n_tests = 100
        else:
            cycles = 40000
            n_tests = 40

        @block
        def stimulate_check(**dut_args):

            return_objects = []

            return_objects.append(self.monitor_tests(n_tests, **dut_args))
            return_objects.append(self.stim_dut(**dut_args))
            return_objects.append(self.check_dut(**dut_args))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, ethernet_monitor, ethernet_monitor, dut_args,
            dut_arg_types, custom_sources=[(stimulate_check, (), dut_args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_ethernet_monitor(self):
        ''' The `ethernet_monitor` should double buffer the following signals:

            - `raw_ethernet_status_interface.mac_clock_locked`
            - `raw_ethernet_status_interface.sfp_rx_loss_of_signal`
            - `raw_ethernet_status_interface.sfp_module_absent`
            - `raw_ethernet_status_interface.sfp_tx_fault`

        The double buffered version of these signals should be output on the
        corresponding signal:

            - `ethernet_status_interface.mac_clock_locked`
            - `ethernet_status_interface.sfp_rx_loss_of_signal`
            - `ethernet_status_interface.sfp_module_absent`
            - `ethernet_status_interface.sfp_tx_fault`

        The `ethernet_monitor` should monitor the double buffered signals. If
        any of them enter their active state then the `ethernet_monitor`
        should set the corresponding error high:

            - `ethernet_errors_interface.mac_clock_locked`
            - `ethernet_errors_interface.sfp_rx_loss_of_signal`
            - `ethernet_errors_interface.sfp_module_absent`
            - `ethernet_errors_interface.sfp_tx_fault`

        These errors signals should stay high until `reset` is set high at
        which point all error signals should be set low.
        '''
        self.base_test()

class TestEthernetMonitorVivadoVhdl(
    KeaVivadoVHDLTestCase, TestEthernetMonitor):
    pass

class TestEthernetMonitorVivadoVerilog(
    KeaVivadoVerilogTestCase, TestEthernetMonitor):
    pass
