from myhdl import block, always, Signal, intbv

from kea.hdl.signal_handling import signal_assigner

from .interfaces import MultiplexerInputInterface

@block
def synchronous_multiplexer(clock, input_interface, output_signal, select):
    ''' Drives the output_signal with the input_interface signal specified by
    select.
    '''

    if not isinstance(input_interface, MultiplexerInputInterface):
        raise TypeError(
            'synchronous_multiplexer: input_interface should be an instance '
            'of MultiplexerInputInterface.')

    if len(output_signal) < input_interface.signal_bit_width:
        raise ValueError(
            'synchronous_multiplexer: The output_signal should be at least '
            'as wide as the signals on the input_interface.')

    if 2**len(select) < input_interface.n_signals:
        raise ValueError(
            'synchronous_multiplexer: The select signal should be wide '
            'enough to select any input.')

    return_objects = []

    # Extract the signal from the input_interface
    input_signals = [
        input_interface.signal(n) for n in range(input_interface.n_signals)]

    # Create an internal select which is an intbv and drive this with select.
    # This is necessary as we want check that select is less than
    # input_interface.n_signals. VHDL cannot perform a less than check between
    # a bool and an int (if select is a bool signal).
    internal_select = Signal(intbv(0)[len(select):])
    return_objects.append(signal_assigner(select, internal_select))

    @always(clock.posedge)
    def mux():

        if internal_select < input_interface.n_signals:
            # Drive the output_signal with the input signal specified by
            # select
            output_signal.next = input_signals[internal_select]

        else:
            # An invalid input signal has been selected so set output to 0
            output_signal.next = 0

    return_objects.append(mux)

    return return_objects
