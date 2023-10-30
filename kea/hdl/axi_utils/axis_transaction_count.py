
from myhdl import *
from kea.hdl.axi import AxiStreamInterface

@block
def axis_count_valid_transactions(clock, reset, axis_interface, count):
    '''A block that counts the number of valid transactions that occur on the
    `axis_interface` AXI stream interface.

    The number of transactions that have occurred are presented on the
    ``count`` signal. If too many transactions are counted that would cause
    ``count`` to exceed its bounds, then further transactions are ignored.

    The starting value of ``count`` is set through the signal creation.

    ``reset`` is an active high synchronous reset that resets the value of
    ``count`` to zero. If a transaction occurs when ``reset`` is asserted,
    the transaction is ignored.

    This block is entirely transparent to the ``axis_interface`` signals
    signals. It simply monitors what happens between the sink and the source.
    '''
    if not isinstance(axis_interface, AxiStreamInterface):
        raise ValueError('Invalid axis_interface port: The '
                         'axis_interface port should be an instance of '
                         'AxiStreamInterface.')

    # axis_interface.TDATA is unused so set read
    axis_interface.TDATA.read = True

    # FIXME this is not ideal and is a work around to deal with the
    # fact that VHDL gets hung up on large integers, and myhdl did not work
    # around it properly. It should be fixed in MyHDL and I'll do it when
    # the policy is properly worked out. whg 6/9/2018
    count_threshold = Signal(
        intbv(count.max - 1, min=count.min, max=count.max))

    @always(clock.posedge)
    def counter():

        # Assigning on every cycle is not necessary to function correctly
        # when initial value assignments are turned on, but this keeps
        # the converter happy.
        count_threshold.next = count_threshold

        if reset:
            count.next = 0
        else:
            if axis_interface.TVALID and axis_interface.TREADY:
                if(count < count_threshold):
                    count.next = count + 1

    return counter

@block
def axis_count_sink_not_ready_transactions(
    clock, reset, axis_interface, count):
    '''A block that counts the number of axis transactions in which the source
    is valid, but the sink is not ready that occur on the `axis_interface`
    AXI stream interface.

    The number of transactions that have occurred are presented on the
    ``count`` signal. If too many transactions are counted that would cause
    ``count`` to exceed its bounds, then further transactions are ignored.

    The starting value of ``count`` is set through the signal creation.

    ``reset`` is an active high synchronous reset that resets the value of
    ``count`` to zero. If a transaction occurs when ``reset`` is asserted,
    the transaction is ignored.

    This block is entirely transparent to the ``axis_interface`` signals
    signals. It simply monitors what happens between the sink and the source.
    '''

    if not isinstance(axis_interface, AxiStreamInterface):
        raise ValueError('Invalid axis_interface port: The '
                         'axis_interface port should be an instance of '
                         'AxiStreamInterface.')

    # axis_interface.TDATA is unused so set read
    axis_interface.TDATA.read = True

    # FIXME see valid transaction case above
    count_threshold = Signal(
        intbv(count.max - 1, min=count.min, max=count.max))

    @always(clock.posedge)
    def counter():

        # Assigning on every cycle is not necessary to function correctly
        # when initial value assignments are turned on, but this keeps
        # the converter happy.
        count_threshold.next = count_threshold

        if reset:
            count.next = 0
        else:
            if axis_interface.TVALID and not axis_interface.TREADY:
                if(count < count_threshold):
                    count.next = count + 1

    return counter

@block
def axis_count_source_not_valid_transactions(
    clock, reset, axis_interface, count):
    '''A block that counts the number of axis transactions in which the sink is
    ready but the source is not valid that occur on the `axis_interface`
    AXI stream interface.

    The number of transactions that have occurred are presented on the
    ``count`` signal. If too many transactions are counted that would cause
    ``count`` to exceed its bounds, then further transactions are ignored.

    The starting value of ``count`` is set through the signal creation.

    ``reset`` is an active high synchronous reset that resets the value of
    ``count`` to zero. If a transaction occurs when ``reset`` is asserted,
    the transaction is ignored.

    This block is entirely transparent to the ``axis_interface`` signals
    signals. It simply monitors what happens between the sink and the source.
    '''

    if not isinstance(axis_interface, AxiStreamInterface):
        raise ValueError('Invalid axis_interface port: The '
                         'axis_interface port should be an instance of '
                         'AxiStreamInterface.')

    # axis_interface.TDATA is unused so set read
    axis_interface.TDATA.read = True

    # FIXME see valid transaction case above
    count_threshold = Signal(
        intbv(count.max - 1, min=count.min, max=count.max))

    @always(clock.posedge)
    def counter():

        # Assigning on every cycle is not necessary to function correctly
        # when initial value assignments are turned on, but this keeps
        # the converter happy.
        count_threshold.next = count_threshold

        if reset:
            count.next = 0
        else:
            if not axis_interface.TVALID and axis_interface.TREADY:
                if(count < count_threshold):
                    count.next = count + 1

    return counter
