from myhdl import Signal, intbv

class AxiStreamFlexiBitInterface(object):
    '''  AXI stream like interface definition '''

    @property
    def bus_bitwidth(self):
        return self._bus_bitwidth

    @property
    def bus_width(self):
        raise NotImplementedError(
            'Bus width is defined in bits rather than bytes.')

    @property
    def TID_width(self):
        return None

    @property
    def TDEST_width(self):
        return None

    @property
    def TUSER_width(self):
        return None

    def __init__(
        self, bus_bitwidth=32, TVALID_init=False, TREADY_init=False,
        use_TLAST=True):
        ''' Creates an AXI4 Stream like interface object which allows bit wide
        data widths. The AXI spec requires data widths to be a multiple of 8
        bits wide. This interface does not impose this requirement.

        ``bus_bitwidth`` gives the width of the data bus, ``TDATA``, in bits.
        '''

        self._bus_bitwidth = int(bus_bitwidth)

        self.TVALID = Signal(bool(TVALID_init))
        self.TREADY = Signal(bool(TREADY_init))
        self.TDATA = Signal(intbv(0)[self.bus_bitwidth:])

        if use_TLAST:
            self.TLAST = Signal(bool(0))
