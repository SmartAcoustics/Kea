
from myhdl import *
import myhdl

from kea.testing.myhdl import (
    check_intbv_signal, check_bool_signal, check_reset_signal)
from kea.hdl.axi import AxiStreamInterface

@block
def axis_periodic_enable(
    clock, reset, axis_in, axis_out, period):
    '''A block that enables transactions periodically between the input axi
    stream and the output axi stream, with the period between assertions set
    by ``period`` cycles of ``clock``.

    The intent is for a transaction to take place every ``period`` cycles. The
    mechanism for doing this is to set ``axis_in.TREADY`` low for all cycles
    except those that are N times ``period`` cycles from the last reset. In
    those cycles, ``axis_in.TREADY == axis_out.TREADY``.

    ``period`` can either be a signal or a constant.

    If ``axis_out.TREADY`` is not asserted during the expected cycle, then
    ``axis_in.TREADY`` is also not asserted.

    ``reset`` causes the period counter to be reset to zero, so on the next
    cycle, and every ``period`` cycles subsequently, it will enable a
    transaction.

    ``axis_out.TDATA`` is updated whenever a valid transaction occurs,
    otherwise it is held unchanged (so can be used without knowledge of the
    other ``axis_out`` signals).

    ``axis_out.TLAST == axis_in.TLAST``for every cycle.

    This block introduces no latency to the transactions when they happen
    (that is, on the periodic ticks, data will pass through as though this
    block was transparent).
    '''
    check_bool_signal(clock, 'clock')
    check_bool_signal(reset, 'reset')

    if not isinstance(axis_in, AxiStreamInterface):
        raise ValueError('Invalid axis_in port: The '
                         'axis_in port should be an instance of '
                         'AxiStreamInterface.')

    if not isinstance(axis_out, AxiStreamInterface):
        raise ValueError('Invalid axis_out port: The '
                         'axis_out port should be an instance of '
                         'AxiStreamInterface.')

    if isinstance(period, myhdl._Signal._Signal):
        check_intbv_signal(
            period, 'period', val_range=(1, 2**len(period)-1))

        count_max = period.max

    else:
        try:
            period = int(period)
            if period <= 0:
                raise ValueError

            count_max = period

        except ValueError:
            raise ValueError(
                'Period not a signal or an integer: period should be either '
                'an intbv signal or else a constant that can be properly '
                'converted to an integer with a call to int().')

    count = Signal(intbv(0, min=0, max=count_max))

    held_axis_out_TDATA = Signal(
        intbv(0, min=axis_out.TDATA.min, max=axis_out.TDATA.max))

    output_instances = []

    if hasattr(axis_out, 'TLAST') and hasattr(axis_in, 'TLAST'):
        # axis_out and axis_in have TLAST so connect them

        @always_comb
        def assign_TLAST():
            axis_out.TLAST.next = axis_in.TLAST

        output_instances.append(assign_TLAST)

    elif hasattr(axis_out, 'TLAST') and not hasattr(axis_in, 'TLAST'):
        # axis_out has TLAST but axis_in does not so drive axis_out.TLAST low

        @always(clock.posedge)
        def assign_TLAST():
            axis_out.TLAST.next = False

        output_instances.append(assign_TLAST)

    elif not hasattr(axis_out, 'TLAST') and hasattr(axis_in, 'TLAST'):
        # axis_out doesn't have a TLAST but axis_in does to set read on
        # axis_in.TLAST

        axis_in.TLAST.read = True

    else:
        # Neither axis_out or axis_in have TLAST so do nothing
        pass

    @always_comb
    def assign_signals():

        if (not reset) and count == 0:
            axis_out.TVALID.next = axis_in.TVALID
            axis_in.TREADY.next = axis_out.TREADY

            axis_out.TDATA.next = axis_in.TDATA
        else:
            axis_out.TVALID.next = False
            axis_in.TREADY.next = False

            axis_out.TDATA.next = held_axis_out_TDATA

    @always(clock.posedge)
    def axis_out_TDATA_holder():

        if axis_out.TVALID and axis_out.TREADY:
            held_axis_out_TDATA.next = axis_out.TDATA


    @always(clock.posedge)
    def enable_counter():

        if reset:
            count.next = 0
        else:
            if count >= period - 1:
                count.next = 0
            else:
                count.next = count + 1

    output_instances.extend(
        [enable_counter, assign_signals, axis_out_TDATA_holder])

    return output_instances
