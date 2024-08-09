from myhdl import TristateSignal

class NBitsTriStateBuffersIOInterface:
    ''' The IO interface for the n_bit_tri_state_buffers.
    '''
    def __init__(self, n_bits):

        if n_bits <= 0:
            raise ValueError(
                'NBitsTriStateBuffersIOInterface: n_bits should be greater '
                'than 0.')

        self._n_bits = n_bits

        for n in range(self._n_bits):
            setattr(self, 'io_' + str(n), TristateSignal(False))

    @property
    def n_bits(self):
        return self._n_bits

    def io_bit_n(self, bit_n):
        ''' Returns the IO signal for bit_n.
        '''
        io_n = getattr(self, 'io_' + str(bit_n))
        return io_n
