import random

from ._ramp_towards import ramp_towards

from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from myhdl import *

class TestRampTowardsInterface(KeaTestCase):
    '''The interface of the ramp_towards block should protect against
    problematic arguments.
    '''

    def setUp(self):

        self.data_in_bitwidth = 15

        data_range = 2**(self.data_in_bitwidth-1)
        self.clock = Signal(False)
        self.target = Signal(intbv(0, min=-data_range, max=data_range))
        self.current_value = Signal(intbv(0, min=-data_range, max=data_range))

        self.default_args = {
            'clock': self.clock,
            'target': self.target,
            'current_value': self.current_value,
            'step_size': 16,
            'cycles_per_step': 1,
        }

    def test_step_size_with_negative_range_error(self):
        '''If ``step_size`` signal is able to take a negative value, a
        ``ValueError`` should be raised.
        '''
        self.default_args['step_size'] = Signal(intbv(0, min=-5, max=16))

        self.assertRaisesRegex(
            ValueError, 'step_size invalid range',
            ramp_towards, **self.default_args)

    def test_cycles_per_step_with_negative_range_error(self):
        '''If the passed ``cycles_per_step`` signal is able to take a
        negative value, a ``ValueError`` should be raised.
        '''
        self.default_args['cycles_per_step'] = (
            Signal(intbv(0, min=-5, max=16)))

        self.assertRaisesRegex(
            ValueError, 'cycles_per_step invalid range',
            ramp_towards, **self.default_args)

    def test_step_size_as_too_long_signal_error(self):
        '''If ``step_size`` is set to be a signal and is a signal that is
        wider than ``target``, a ``ValueError`` should be raised.
        '''
        self.default_args['step_size'] = Signal(
            intbv(0, min=0, max=self.target.max+1))

        self.assertRaisesRegex(
            ValueError, 'step_size invalid range',
            ramp_towards, **self.default_args)

    def test_target_and_current_value_same_range(self):
        '''``target`` and ``current_value`` signals should have the same
        range.
        '''
        self.default_args['target'] = Signal(
            intbv(0, min=self.current_value.min,
                  max=self.current_value.max + 1))

        self.assertRaisesRegex(
            ValueError, 'target and current_value with unequal range',
            ramp_towards, **self.default_args)

        self.default_args['target'] = Signal(
            intbv(0, min=self.current_value.min + 1,
                  max=self.current_value.max))

        self.assertRaisesRegex(
            ValueError, 'target and current_value with unequal range',
            ramp_towards, **self.default_args)


    def test_constant_zero_step_size_error(self):
        '''If ``step_size`` is set to constant zero, a ValueError should be
        raised.
        '''
        self.default_args['step_size'] = 0

        self.assertRaisesRegex(
            ValueError, 'step_size invalid constant value',
            ramp_towards, **self.default_args)

    def test_constant_negative_step_size_error(self):
        '''If ``step_size`` is set to constant negative value, a ValueError
        should be raised.
        '''
        self.default_args['step_size'] = -1

        self.assertRaisesRegex(
            ValueError, 'step_size invalid constant value',
            ramp_towards, **self.default_args)

@block
def ramp_check(clock, target, current_value, step_size, cycles_per_step):

    expected_value = Signal(
        intbv(current_value.val, min=target.min, max=target.max))

    test_data = {'current_cycle': 1,
                 'last_expected_value': None}

    @always(clock.posedge)
    def checker():

        assert expected_value == current_value
        if cycles_per_step == 0:
            # cycles per step == 0 takes precedent
            expected_value.next = target

        else:

            if test_data['current_cycle'] >= cycles_per_step:
                if current_value == target:
                    #nothing to do except count another cycle
                    test_data['current_cycle'] += 1
                    return

                else:
                    test_data['current_cycle'] = 1
                    # now we process

            else:
                test_data['current_cycle'] += 1
                expected_value.next = expected_value
                return

#            if test_data['current_cycle'] < cycles_per_step:
#                test_data['current_cycle'] += 1
#                expected_value.next = expected_value
#                return
#            elif current_value == target:
#                # nothing to do
#                return
#            else:
#                test_data['current_cycle'] = 1

            #elif step_size == 0:
            #    expected_value.next = expected_value

            if target > current_value:
                if expected_value + step_size < target:
                    expected_value.next = expected_value + step_size

                else:
                    expected_value.next = target

            elif target < current_value:
                if expected_value - step_size > target:
                    expected_value.next = expected_value - step_size

                else:
                    expected_value.next = target

            else:
                expected_value.next = target

            # We should never step too far
            if expected_value.next != target:
                assert abs(expected_value.next - current_value) == step_size
            else:
                assert abs(expected_value.next - current_value) <= step_size

        if test_data['last_expected_value'] is not None:
            if step_size == 0:
                # We should never change
                assert test_data['last_expected_value'] == expected_value

        test_data['last_expected_value'] = expected_value

    return checker

@block
def stimulate_and_check(
    clock, target, current_value, step_size, cycles_per_step):

    test_data = {'ramping': False,
                 'chance_of_update': True}

    ramp_checker = ramp_check(
        clock, target, current_value, step_size, cycles_per_step)

    @always(clock.posedge)
    def stimulate():

        force_update = False

        if test_data['chance_of_update']:
            if random.random() < 0.05:
                force_update = True

        if ((not test_data['ramping'] and random.random() < 0.1)
            or force_update):

            if random.random() < 0.5:
                test_data['chance_of_update'] = True
            else:
                test_data['chance_of_update'] = False

            test_data['ramping'] = True
            target.next = (
                target - target.min + random.choice((-1, 1)) *
                random.randrange((2**len(target))/4)) % (
                    2**len(target)) + target.min

        if target == current_value:
            test_data['ramping'] = False

    return ramp_checker, stimulate

class TestRampTowardsSimulation(KeaTestCase):
    '''There should be a ramp_towards block that ramps a ``current_value``
    signal towards a ``target`` value.
    '''

    def setUp(self):

        self.data_in_bitwidth = 15

        data_range = 2**(self.data_in_bitwidth-1)
        self.clock = Signal(False)
        self.target = Signal(intbv(0, min=-data_range, max=data_range))
        self.current_value = Signal(intbv(0, min=-data_range, max=data_range))

        self.default_args = {
            'clock': self.clock,
            'target': self.target,
            'current_value': self.current_value,
            'step_size': 16,
            'cycles_per_step': 1,
        }

        self.default_arg_types = {
            'clock': 'clock',
            'target': 'custom',
            'current_value': 'output',
            'step_size': 'non-signal',
            'cycles_per_step': 'non-signal',
        }

    def test_ramp_towards(self):
        '''The ramp_towards block should read a ``target`` signal and
        increment or decrement the ``current_value`` signal until it reaches
        the target value.

        The step size should be given by the ``step_size`` argument and
        the number of clock cycles between step should be given by the
        ``cycles_per_step`` argument.

        If ``step_size`` is larger than the difference between ``target``
        and ``current_value``, then ``current_value`` should be set to target
        on the next step.
        '''

        if not self.testing_using_vivado:
            test_set = ((6000, 16, 1),)

        else:
            test_set = ((6000, 16, 1),)

        for cycles, step_size, cycles_per_step in test_set:

            self.default_args['cycles_per_step'] = cycles_per_step
            self.default_args['step_size'] = step_size

            dut_outputs, ref_outputs = self.cosimulate(
                cycles, ramp_towards, ramp_towards,
                self.default_args, self.default_arg_types,
                custom_sources=[(stimulate_and_check, (), self.default_args)])

            self.assertEqual(dut_outputs, ref_outputs)

    def test_constant_zero_cycles_per_step(self):
        '''If ``cycles_per_step`` is set to a constant zero, ``current_value``
        should be set to ``target`` on the next cycle.
        '''
        if not self.testing_using_vivado:
            test_set = ((6000, 16, 0),)

        else:
            test_set = ((6000, 16, 0),)

        for cycles, step_size, cycles_per_step in test_set:

            self.default_args['cycles_per_step'] = cycles_per_step
            self.default_args['step_size'] = step_size

            dut_outputs, ref_outputs = self.cosimulate(
                cycles, ramp_towards, ramp_towards,
                self.default_args, self.default_arg_types,
                custom_sources=[(stimulate_and_check, (), self.default_args)])

            self.assertEqual(dut_outputs, ref_outputs)

    def test_step_size_as_signal(self):
        '''It should be possible to set ``step_size`` as a signal, in which
        case the step size should change dynamically.
        '''

        if not self.testing_using_vivado:
            test_set = ((6000, 1),)

        else:
            test_set = ((6000, 1),)

        for cycles, cycles_per_step in test_set:

            self.default_args['cycles_per_step'] = cycles_per_step
            self.default_args['step_size'] = Signal(intbv(1, max=33))
            self.default_arg_types['step_size'] = 'custom'

            @block
            def ss_stimulate_and_check(
                clock, target, current_value, step_size, cycles_per_step):

                main_stimulate_and_check = stimulate_and_check(
                    clock, target, current_value, step_size, cycles_per_step)

                @always(clock.posedge)
                def drive_step_size():
                    if random.random() < 0.01:
                        step_size.next = random.randrange(1, step_size.max)

                return drive_step_size, main_stimulate_and_check

            dut_outputs, ref_outputs = self.cosimulate(
                cycles, ramp_towards, ramp_towards,
                self.default_args, self.default_arg_types,
                custom_sources=[
                    (ss_stimulate_and_check, (), self.default_args)])

            self.assertEqual(dut_outputs, ref_outputs)


    def test_cycles_per_step_as_signal(self):
        '''It should be possible to set ``cycles_per_step`` as a signal, in
        which case the cycles per step should change dynamically.
        '''
        if not self.testing_using_vivado:
            test_set = ((20000, 1),)

        else:
            test_set = ((10000, 1),)

        for cycles, step_size in test_set:

            self.default_args['step_size'] = step_size
            self.default_args['cycles_per_step'] = Signal(
                intbv(1, min=0, max=16))
            self.default_arg_types['cycles_per_step'] = 'custom'

            @block
            def ss_stimulate_and_check(
                clock, target, current_value, step_size, cycles_per_step):

                main_stimulate_and_check = stimulate_and_check(
                    clock, target, current_value, step_size, cycles_per_step)

                @always(clock.posedge)
                def drive_cycles_per_step():
                    if random.random() < 0.01:
                        cycles_per_step.next = (
                            random.randrange(1, cycles_per_step.max))

                return drive_cycles_per_step, main_stimulate_and_check

            dut_outputs, ref_outputs = self.cosimulate(
                cycles, ramp_towards, ramp_towards,
                self.default_args, self.default_arg_types,
                custom_sources=[
                    (ss_stimulate_and_check, (), self.default_args)])

            self.assertEqual(dut_outputs, ref_outputs)

    def test_step_size_as_signal(self):
        '''If ``step_size`` is a signal and is zero, the output should never
        change.
        '''

        if not self.testing_using_vivado:
            test_set = ((6000, 1),)

        else:
            test_set = ((6000, 1),)

        for cycles, cycles_per_step in test_set:

            self.default_args['cycles_per_step'] = cycles_per_step
            self.default_args['step_size'] = Signal(intbv(0, min=0, max=4))
            self.default_arg_types['step_size'] = 'custom'

            @block
            def ss_stimulate_and_check(
                clock, target, current_value, step_size, cycles_per_step):

                main_stimulate_and_check = stimulate_and_check(
                    clock, target, current_value, step_size, cycles_per_step)

                @always(clock.posedge)
                def drive_step_size():
                    if random.random() < 0.01:
                        step_size.next = random.randrange(0, step_size.max)

                return drive_step_size, main_stimulate_and_check

            dut_outputs, ref_outputs = self.cosimulate(
                cycles, ramp_towards, ramp_towards,
                self.default_args, self.default_arg_types,
                custom_sources=[
                    (ss_stimulate_and_check, (), self.default_args)])

            self.assertEqual(dut_outputs, ref_outputs)

    def test_cycles_per_step_and_step_size_signals_both_zero(self):
        '''If ``cycles_per_step`` and ``step_size`` are signals and both
        are zero, then `step_size` is effectively ignored and the next value
        is always set to be the target value.
        '''
        if not self.testing_using_vivado:
            test_set = (20000,)

        else:
            test_set = (10000,)

        for cycles in test_set:

            self.default_args['step_size'] = Signal(intbv(1, min=0, max=33))
            self.default_arg_types['step_size'] = 'custom'

            self.default_args['cycles_per_step'] = Signal(
                intbv(1, min=0, max=16))
            self.default_arg_types['cycles_per_step'] = 'custom'

            @block
            def ss_stimulate_and_check(
                clock, target, current_value, step_size, cycles_per_step):

                main_stimulate_and_check = stimulate_and_check(
                    clock, target, current_value, step_size, cycles_per_step)

                @always(clock.posedge)
                def drive_cycles_per_step():
                    if random.random() < 0.01:
                        cycles_per_step.next = (
                            random.randrange(1, cycles_per_step.max))
                        step_size.next = (
                            random.randrange(1, step_size.max))

                    elif random.random() < 0.01:
                        cycles_per_step.next = step_size.next = 0

                return drive_cycles_per_step, main_stimulate_and_check

            dut_outputs, ref_outputs = self.cosimulate(
                cycles, ramp_towards, ramp_towards,
                self.default_args, self.default_arg_types,
                custom_sources=[
                    (ss_stimulate_and_check, (), self.default_args)])

            self.assertTrue(dut_outputs==ref_outputs)


class TestRampTowardsVivadoVHDLSimulation(
    KeaVivadoVHDLTestCase, TestRampTowardsSimulation):
    pass

class TestRampTowardsVivadoVerilogSimulation(
    KeaVivadoVerilogTestCase, TestRampTowardsSimulation):
    pass

