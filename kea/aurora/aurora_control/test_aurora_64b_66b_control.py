import random

from myhdl import Signal, block, always, intbv, enum, StopSimulation

from kea.test_utils import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)
from kea.utils import double_buffer

from ._aurora_64b_66b_control import aurora_64b_66b_control

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    clock_frequency = 250

    args = {
        'clock': Signal(False),
        'enable': Signal(False),
        'ready': Signal(False),
        'reset_pb': Signal(True),
        'pma_init': Signal(True),
        'clock_frequency': clock_frequency,
    }

    arg_types = {
        'clock': 'clock',
        'enable': 'custom',
        'ready': 'output',
        'reset_pb': 'output',
        'pma_init': 'output',
        'clock_frequency': 'non-signal',
    }

    return args, arg_types

class TestAurora64b66bControlInterface(KeaTestCase):
    ''' The DUT should reject incompatible interfaces and arguments.
    '''

    def setUp(self):
        self.args, _arg_types = test_args_setup()

    def test_negative_clock_frequency(self):
        ''' The `aurora_64b_66b_control` should raise an error if
        `clock_frequency` is negative.
        '''

        self.args['clock_frequency'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('aurora_64b_66b_control: clock_frequency should be greater than '
             '0.'),
            aurora_64b_66b_control,
            **self.args,
        )

    def test_zero_clock_frequency(self):
        ''' The `aurora_64b_66b_control` should raise an error if
        `clock_frequency` is zero.
        '''

        self.args['clock_frequency'] = 0

        self.assertRaisesRegex(
            ValueError,
            ('aurora_64b_66b_control: clock_frequency should be greater than '
             '0.'),
            aurora_64b_66b_control,
            **self.args,
        )

    def test_ready_invalid_init_val(self):
        ''' The `aurora_64b_66b_control` should raise an error if `ready` is
        initialised with anything that isn't `False`.
        '''

        self.args['ready'] = Signal(True)

        self.assertRaisesRegex(
            ValueError,
            ('aurora_64b_66b_control: ready should initialise False.'),
            aurora_64b_66b_control,
            **self.args,
        )

    def test_reset_pb_invalid_init_val(self):
        ''' The `aurora_64b_66b_control` should raise an error if `reset_pb`
        is initialised with anything that isn't `True`.
        '''

        self.args['reset_pb'] = Signal(False)

        self.assertRaisesRegex(
            ValueError,
            ('aurora_64b_66b_control: reset_pb should initialise True.'),
            aurora_64b_66b_control,
            **self.args,
        )

    def test_pma_init_invalid_init_val(self):
        ''' The `aurora_64b_66b_control` should raise an error if `pma_init`
        is initialised with anything that isn't `True`.
        '''

        self.args['pma_init'] = Signal(False)

        self.assertRaisesRegex(
            ValueError,
            ('aurora_64b_66b_control: pma_init should initialise True.'),
            aurora_64b_66b_control,
            **self.args,
        )

class TestAurora64b66bControl(KeaTestCase):

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
    def aurora_64b_66b_control_stim(self, stim_enable=False, **kwargs):

        clock = kwargs['clock']
        enable = kwargs['enable']

        return_objects = []

        @always(clock.posedge)
        def stim():

            if stim_enable:
                if enable:
                    if random.random() < 0.001:
                        # Randomly set enable
                        enable.next = False

                else:
                    if random.random() < 0.01:
                        enable.next = True

            else:
                if random.random() < 0.01:
                    # Randomly set enable
                    enable.next = True

        return_objects.append(stim)

        return return_objects

    @block
    def aurora_64b_66b_control_check(self, **kwargs):

        clock = kwargs['clock']
        enable = kwargs['enable']
        ready = kwargs['ready']
        reset_pb = kwargs['reset_pb']
        pma_init = kwargs['pma_init']
        clock_frequency = kwargs['clock_frequency']

        return_objects = []

        buffered_enable = Signal(False)
        return_objects.append(double_buffer(clock, enable, buffered_enable))

        reset_pb_n_cycles = 128
        pma_init_n_cycles = clock_frequency

        pma_init_high_cycle = reset_pb_n_cycles
        pma_init_low_cycle = pma_init_high_cycle + pma_init_n_cycles
        reset_pb_low_cycle = pma_init_low_cycle + reset_pb_n_cycles

        count_upper_bound = reset_pb_low_cycle + 1
        count = Signal(intbv(0, 0, count_upper_bound))

        expected_ready = Signal(False)
        expected_reset_pb = Signal(True)
        expected_pma_init = Signal(True)

        t_state = enum('RESET', 'RUNNING')
        state = Signal(t_state.RESET)

        @always(clock.posedge)
        def check():

            ##########
            # Checks #
            ##########

            assert(ready == expected_ready)
            assert(reset_pb == expected_reset_pb)
            assert(pma_init == expected_pma_init)

            if pma_init is True:
                # Check that reset_pb is high when pma_init is high
                assert(reset_pb is True)

            ##############
            # Sequencing #
            ##############

            if state == t_state.RESET:
                if count < reset_pb_low_cycle:
                    count.next = count + 1

                    if count == pma_init_high_cycle-1:
                        expected_pma_init.next = True

                    elif count == pma_init_low_cycle-1:
                        expected_pma_init.next = False

                    elif count == reset_pb_low_cycle-1:
                        expected_reset_pb.next = False
                        expected_ready.next = True

                        count.next = 0

                        self.test_count += 1
                        state.next = t_state.RUNNING

            elif state == t_state.RUNNING:
                pass

            if not buffered_enable:
                expected_ready.next = False
                expected_reset_pb.next = True
                count.next = 0
                state.next = t_state.RESET

        return_objects.append(check)

        return return_objects

    def test_power_up(self):
        ''' This spec is based on the Reset and Power Down section of the
        PG074 Aurora 64B/66B LogiCORE IP Product Guide.

        At power on the `aurora_64b_66b_control` block should perform the
        following sequence:

            - Hold `ready` low, hold `reset_pb` high and hold `pma_init` high.
            - Wait for `enable` to go high.
            - Set `pma_init` low.
            - Wait 128 clock cycles.
            - Set `reset_pb` low and `ready` high.
        '''

        cycles = 5000
        n_tests = 1

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            return_objects.append(self.end_tests(n_tests, **kwargs))
            return_objects.append(self.aurora_64b_66b_control_stim(**kwargs))
            return_objects.append(self.aurora_64b_66b_control_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, aurora_64b_66b_control, aurora_64b_66b_control, self.args,
            self.arg_types, custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_enable(self):
        ''' When the `enable` signal goes low the `aurora_64b_66b_control`
        should:

            - Set `ready` low.
            - Set `reset_pb` high.

        If should then wait for `enable` to go high before performing the
        following sequence:

            - Wait 128 clock cycles.
            - Set `pma_init` high.
            - Wait 1 second (this equates to `clock_frequency` cycles).
            - Set `pma_init` low.
            - Wait 128 clock cycles.
            - Set `reset_pb` low and `ready` high.
        '''

        cycles = 40000
        n_tests = 10

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            return_objects.append(self.end_tests(n_tests, **kwargs))
            return_objects.append(
                self.aurora_64b_66b_control_stim(stim_enable=True, **kwargs))
            return_objects.append(self.aurora_64b_66b_control_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, aurora_64b_66b_control, aurora_64b_66b_control, self.args,
            self.arg_types, custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_clock_frequency(self):
        ''' The `aurora_64b_66b_control` block should use the
        `clock_frequency` to determine the `pma_init` high period. The
        `pma_init` should be set high for 1 second as part of the reset
        sequences. This equates to `clock_frequency` cycles.
        '''

        cycles = 40000
        n_tests = 10

        self.args['clock_frequency'] = random.randrange(1, 500)

        @block
        def stimulate_check(**kwargs):

            return_objects = []

            return_objects.append(self.end_tests(n_tests, **kwargs))
            return_objects.append(
                self.aurora_64b_66b_control_stim(stim_enable=True,**kwargs))
            return_objects.append(self.aurora_64b_66b_control_check(**kwargs))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, aurora_64b_66b_control, aurora_64b_66b_control, self.args,
            self.arg_types, custom_sources=[(stimulate_check, (), self.args)])

        assert(self.tests_run)
        self.assertEqual(dut_outputs, ref_outputs)

class TestAurora64b66bControlVivadoVhdl(
    KeaVivadoVHDLTestCase, TestAurora64b66bControl):
    pass

class TestAurora64b66bControlVivadoVerilog(
    KeaVivadoVerilogTestCase, TestAurora64b66bControl):
    pass
