from myhdl import Signal, intbv

class DeConcatenatorOutputInterface:
    ''' The output interface for the de-concatenator.
    '''
    def __init__(self, n_signals, signal_bitwidth):

        if n_signals <= 0:
            raise ValueError(
                'DeConcatenatorOutputInterface: n_signals should be greater '
                'than 0.')

        if signal_bitwidth <= 0:
            raise ValueError(
                'DeConcatenatorOutputInterface: signal_bitwidth should be '
                'greater than 0.')

        self._n_signals = n_signals
        self._signal_bitwidth = signal_bitwidth

        for n in range(self._n_signals):
            setattr(
                self, 'signal_' + str(n),
                Signal(intbv(0)[self._signal_bitwidth:]))

    @property
    def n_signals(self):
        return self._n_signals

    @property
    def signal_bitwidth(self):
        return self._signal_bitwidth

    def signal_n(self, n):
        ''' Returns signal n.
        '''
        sig = getattr(self, 'signal_' + str(n))
        return sig
