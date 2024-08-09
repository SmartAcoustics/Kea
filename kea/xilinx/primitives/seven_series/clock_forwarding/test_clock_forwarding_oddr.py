import random

from math import ceil
from myhdl import block, Signal, always, intbv, enum

import kea
from kea.testing.test_utils import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._clock_forwarding_oddr import clock_forwarding_oddr

def setup_dut_args(clock_frequency, invert_clock):
    ''' Generate the test_args and test_arg_types for the DUT.
    '''

    dut_args = {
        'clock': Signal(False),
        'reset': Signal(False),
        'initialised': Signal(False),
        'enable_clock_forwarding': Signal(False),
        'forwarded_clock': Signal(False),
        'clock_frequency': clock_frequency,
        'invert_clock': invert_clock,
    }

    # In reality clock is an input here, but we set it as an output so that
    # we can vary the frequency as part of the tests.
    dut_arg_types = {
        'clock': 'output',
        'reset': 'custom',
        'initialised': 'output',
        'enable_clock_forwarding': 'custom',
        'forwarded_clock': 'output',
        'clock_frequency': 'non-signal',
        'invert_clock': 'non-signal',
    }

    return dut_args, dut_arg_types

class TestClockForwardingOddr(KeaTestCase):
    ''' The DUT should reject incompatible interfaces and arguments.
    '''

    @block
    def dut_wrapper(self, test_clock, **dut_args):
        ''' This block wraps the DUT an instantiates a clock_source for the
        DUT clock.
        '''

        clock = dut_args['clock']

        return_objects = []

        test_clock_period = kea.testing.myhdl.cosimulation.PERIOD
        dut_clock_period = 2*test_clock_period
        return_objects.append(
            kea.testing.myhdl.clock_source(clock, dut_clock_period))

        return_objects.append(clock_forwarding_oddr(**dut_args))

        return return_objects

    @block
    def dut_stim(self, **dut_wrapper_args):
        ''' This block stims the reset and enable_clock_forwarding signals.
        '''

        clock = dut_wrapper_args['clock']
        reset = dut_wrapper_args['reset']
        initialised = dut_wrapper_args['initialised']
        enable_clock_forwarding = dut_wrapper_args['enable_clock_forwarding']

        return_objects = []

        @always(clock.posedge)
        def stim():

            #########
            # Reset #
            #########
            if reset:
                if random.random() < 0.3:
                    reset.next = False

            else:
                if random.random() < 0.004:
                    reset.next = True

            ###########################
            # enable_clock_forwarding #
            ###########################
            if initialised:
                if enable_clock_forwarding:
                    if random.random() < 0.005:
                        enable_clock_forwarding.next = False

                else:
                    if random.random() < 0.02:
                        enable_clock_forwarding.next = True

        return_objects.append(stim)

        return return_objects

    @block
    def dut_check(self, **dut_wrapper_args):
        ''' This block checks the outputs from the DUT.
        '''

        test_clock = dut_wrapper_args['test_clock']
        clock = dut_wrapper_args['clock']
        reset = dut_wrapper_args['reset']
        initialised = dut_wrapper_args['initialised']
        enable_clock_forwarding = dut_wrapper_args['enable_clock_forwarding']
        forwarded_clock = dut_wrapper_args['forwarded_clock']
        clock_frequency = dut_wrapper_args['clock_frequency']
        invert_clock = dut_wrapper_args['invert_clock']

        return_objects = []

        # Calculate the init_period
        clock_period = 1/clock_frequency
        oddr_init_period = 240e-9
        oddr_init_period_n_cycles = ceil(oddr_init_period/clock_period)
        oddr_init_count = Signal(intbv(0, 0, oddr_init_period_n_cycles+1))

        expected_forwarded_clock = Signal(False)
        expected_initialised = Signal(False)

        t_state = enum(
            'INIT', 'INIT_PROPAGATION', 'IDLE', 'IDLE_PROPAGATION', 'RUNNING')
        state = Signal(t_state.INIT)

        @always(test_clock.negedge)
        def forwarded_clock_check():

            assert(forwarded_clock == expected_forwarded_clock)

            if state == t_state.INIT:
                if expected_initialised and enable_clock_forwarding:
                    # Enable has been set high
                    state.next = t_state.INIT_PROPAGATION

            elif state == t_state.INIT_PROPAGATION:
                if enable_clock_forwarding:
                    if not invert_clock:
                        # The DUT should set the clock high when not inverting
                        # the clock
                        expected_forwarded_clock.next = True

                    state.next = t_state.RUNNING

            elif state == t_state.IDLE:
                if enable_clock_forwarding:
                    # Enable has been set high
                    state.next = t_state.IDLE_PROPAGATION

            elif state == t_state.IDLE_PROPAGATION:
                if enable_clock_forwarding:
                    # Propagation cycle for the DUT to respond to enable
                    state.next = t_state.RUNNING

            elif state == t_state.RUNNING:
                if enable_clock_forwarding:
                    # Whilst enable is high the forwarded clock should flip
                    expected_forwarded_clock.next = (
                        not expected_forwarded_clock)

                else:
                    # The forwarded_clock should hold its value when enable
                    # goes low
                    state.next = t_state.IDLE

            if reset:
                # When reset is received, the forwarded_clock should be set
                # low and held low for the initialisation period and then
                # until enable goes high.
                expected_forwarded_clock.next = False
                state.next = t_state.INIT

        return_objects.append(forwarded_clock_check)

        @always(clock.posedge)
        def initialised_check():

            assert(initialised == expected_initialised)

            if oddr_init_count < oddr_init_period_n_cycles:
                # Count the initialisation period
                oddr_init_count.next = oddr_init_count + 1

            else:
                # The DUT should set initialised
                expected_initialised.next = True

        return_objects.append(initialised_check)

        return return_objects

    def base_test(self, clock_frequency=50e6, invert_clock=False):

        if not self.testing_using_vivado:
            cycles = 5000
        else:
            cycles = 1000

        dut_args, dut_arg_types = (
            setup_dut_args(clock_frequency, invert_clock))

        # The dut wrapper requires some additional arguments
        dut_wrapper_args = dut_args.copy()
        dut_wrapper_arg_types = dut_arg_types.copy()

        # We create a test_clock to drive the testing framework. All the DUT
        # clocks are generated inside pulser_control_wrapper. This allows us
        # to check the forwarded_clock output
        #
        # NOTE: test clock is initialised True so that the rising edges on
        # test_clock align with the rising edges on clock
        dut_wrapper_args['test_clock'] = Signal(True)
        dut_wrapper_arg_types['test_clock'] = 'clock'

        @block
        def stimulate_check(**dut_wrapper_args):

            return_objects = []

            return_objects.append(self.dut_stim(**dut_wrapper_args))
            return_objects.append(self.dut_check(**dut_wrapper_args))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, self.dut_wrapper, self.dut_wrapper,
            dut_wrapper_args, dut_wrapper_arg_types,
            custom_sources=[(stimulate_check, (), dut_wrapper_args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_non_inverted_clock(self):
        ''' When `initialised` is set high, the `clock_forwarding_oddr` should
        respond to a high on `enable_clock_forwarding` and output `clock` on
        `forwarded_clock`.

        When `enable_clock_forwarding` is set low, `forwarded_clock` should
        hold its value.

        When `reset` is set high, `forwarded_clock` should be set low.

        When `clock_forwarding_oddr` is instantiated with `invert_clock` set
        to `False`, the forwarded clock should be identical to `clock`.
        '''
        self.base_test(invert_clock=False)

    def test_inverted_clock(self):
        ''' When `clock_forwarding_oddr` is instantiated with `invert_clock`
        set to `True`, the forwarded clock should be an inverted version of
        `clock`.
        '''
        self.base_test(invert_clock=True)

    def test_initialisation_period(self):
        ''' From observation of the converted simulation, the `ODDR` primitive
        requires 120ns before it responds to enable.

        The `clock_forwarding_oddr` should wait 240ns before setting
        initialised high.
        '''
        clock_frequency = random.randrange(1, 101) * 1e6
        self.base_test(clock_frequency=clock_frequency)

class TestClockForwardingOddrVivadoVhdl(
    KeaVivadoVHDLTestCase, TestClockForwardingOddr):
    pass

class TestClockForwardingOddrVivadoVerilog(
    KeaVivadoVerilogTestCase, TestClockForwardingOddr):
    pass
