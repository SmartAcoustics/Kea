from myhdl import Signal, intbv

class MultiplexerInputInterface(object):

    def __init__(self, n_signals, signal_bit_width):

        if n_signals <= 0:
            raise ValueError(
                'MultiplexerInputInterface: n_signals should be greater than '
                'zero.')

        if signal_bit_width <= 0:
            raise ValueError(
                'MultiplexerInputInterface: signal_bit_width should be '
                'greater than zero.')

        self._n_signals = n_signals
        self._signal_bit_width = signal_bit_width

        for n in range(self._n_signals):
            signal_n = Signal(intbv(0)[self._signal_bit_width:])
            setattr(self, 'signal_'+str(n), signal_n)

    @property
    def n_signals(self):
        ''' Returns the number of signals on this interface.
        '''
        return self._n_signals

    @property
    def signal_bit_width(self):
        ''' Returns the bit width of the signals on this interface.
        '''
        return self._signal_bit_width

    def signal(self, n):
        ''' Returns the input signal specified by n.
        '''
        signal = getattr(self, 'signal_'+str(n))
        return signal
