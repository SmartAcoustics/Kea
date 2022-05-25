
from myhdl import *
import myhdl

from kea.utils import constant_assigner

@block
def ramp_towards(
    clock, target, current_value, step_size=16, cycles_per_step=1):
    '''The block ramps ``current_value`` towards target at a rate of
    ``step_size`` every ``cycles_per_step`` clock cycles.

    ``step_size`` must always be positive. If ``target`` is greater than
    ``current_value``, ``current_value`` is incremented by ``step_size``.
    If ``target`` is less than ``current_value``, ``current_value`` is
    decremented by ``step_size``.

    If ``step_size`` is greater than the difference between ``target`` and
    ``current_value``, then ``current_value`` is set to ``target`` on the
    next step (or held constant if they are already equal).

    ``step_size`` and ``cycles_per_step`` can be either positive constants
    (for elaboration-time configuration) or positive signals (for run-time
    configuration). Either or both can be either constant or a signal.
    As constants, setting them to be anything other than a positive constant
    will result in a ValueError.

    ``step_size`` cannot be a constant zero. In the case of ``step_size``
    being a signal, setting its value to zero will result in ``current_value``
    remaining constant, unless ``cycles_per_step`` is also zero.

    If ``cycles_per_step`` is zero, the ``current_value`` will always be
    set to ``target`` on the next cycle.

    ``target`` and ``current_value`` signals should have the same range and
    ``step_size`` should be a positive signal of the same length or shorter.

    '''

    if target.max != current_value.max or target.min != current_value.min:
        raise ValueError('target and current_value with unequal range: '
                         'target must have the same min and max values as '
                         'current_value')

    if isinstance(step_size, myhdl._Signal._Signal):
        if step_size.min < 0:
            raise ValueError(
                'step_size invalid range: '
                'step_size can only take a positive value.')

        if step_size.max > target.max:
            raise ValueError(
                'step_size invalid range: '
                'step_size cannot be allowed to take a range larger than '
                'the range of target.')

    elif step_size <= 0:
        raise ValueError(
            'step_size invalid constant value: '
            'A constant step_size cannot be zero or negative.')

    if isinstance(cycles_per_step, myhdl._Signal._Signal):
        if cycles_per_step.min < 0:
            raise ValueError(
                'cycles_per_step invalid range: '
                'cycles_per_step cannot be allowed to take a negative value.')

        max_cycle_count = cycles_per_step.max

    elif cycles_per_step == 0:
        max_cycle_count = 1

    else:
        max_cycle_count = cycles_per_step

    return_objects = []

    # We always have at least one cycle
    cycle_count = Signal(intbv(1, min=0, max=max_cycle_count + 1))

    residual_min = target.min - (current_value.max - 1)
    residual_max = target.max - current_value.min

    residual = Signal(intbv(0, residual_min, residual_max))

    # This is a work around because VHDL can only take signed integers ie
    # -2**31 -> 2**31 - 1. Turning it into a signal allows us to have larger
    # integers.
    max_cycle_count_val = Signal(intbv(max_cycle_count, 0, max_cycle_count+1))
    return_objects.append(
        constant_assigner(max_cycle_count, max_cycle_count_val))

    @always_comb
    def compute_residual():
        residual.next = target - current_value

    return_objects.append(compute_residual)

    @always(clock.posedge)
    def ramper():

        if cycles_per_step == 0:
            current_value.next = target

        elif residual != 0:

            if cycle_count < cycles_per_step:
                cycle_count.next = cycle_count + 1

            else:
                # Restart; the .next implies one cycle counted
                cycle_count.next = 1
                if residual > 0:
                    if step_size < residual:
                        current_value.next = current_value + step_size

                    else:
                        current_value.next = target

                elif residual < 0:
                    if -step_size > residual:
                        current_value.next = current_value - step_size

                    else:
                        current_value.next = target

        else:
            if cycle_count < max_cycle_count_val:
                # We keep counting so that as soon as new data arrives, if
                # enough cycles have happened we clock it out immediately.
                # We need to keep counting all the time because at some point
                # the cycles_per_step might change, meaning enough cycles have
                # passed.
                cycle_count.next = cycle_count + 1

            current_value.next = target

    return_objects.append(ramper)

    return return_objects
