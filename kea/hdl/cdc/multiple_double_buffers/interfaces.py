from myhdl import Signal

class DoubleBufferArrayInterface(object):

    def __init__(self, n_signals, init_val=False):

        if n_signals <= 0:
            raise ValueError(
                'DoubleBufferArrayInterface: n_signals should be greater '
                'than zero.')

        if not isinstance(init_val, bool):
            raise TypeError(
                'DoubleBufferArrayInterface: init_val should be a bool.')

        self._n_signals = n_signals
        self._init_val = init_val

        for n in range(self._n_signals):
            setattr(self, 'input_signal_'+str(n), Signal(self._init_val))
            setattr(self, 'output_signal_'+str(n), Signal(self._init_val))

    @property
    def n_signals(self):
        ''' Returns the number of signals on this interface.
        '''
        return self._n_signals

    @property
    def init_val(self):
        ''' Returns the initial value of the signals on this interface.
        '''
        return self._init_val

    def input_signal(self, n):
        ''' Returns the input signal specified by n.
        '''
        signal = getattr(self, 'input_signal_'+str(n))
        return signal

    def output_signal(self, n):
        ''' Returns the output signal specified by n.
        '''
        signal = getattr(self, 'output_signal_'+str(n))
        return signal
