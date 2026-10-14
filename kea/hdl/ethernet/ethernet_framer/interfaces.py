from myhdl import Signal, intbv

from kea.hdl.ethernet.definitions import (
    OCTET_BITWIDTH,
    DEST_MAC_N_OCTETS,
    SRC_MAC_N_OCTETS,
    ETHERTYPE_BITWIDTH)

class EthernetHeaderValuesInterface(object):
    '''An interface that carries the values to use in the ethernet header.
    '''

    def __init__(self):

        self.load_values = Signal(False)

        for n in range(DEST_MAC_N_OCTETS):
            setattr(
                self, 'dest_mac_octet_'+str(n),
                Signal(intbv(0)[OCTET_BITWIDTH:]))

        for n in range(SRC_MAC_N_OCTETS):
            setattr(
                self, 'src_mac_octet_'+str(n),
                Signal(intbv(0)[OCTET_BITWIDTH:]))

        self.ethertype = Signal(intbv(0)[ETHERTYPE_BITWIDTH:])

    def dest_mac_octet(self, octet_n):
        ''' Returns the specificed destination MAC octet
        '''
        octet = getattr(self, 'dest_mac_octet_'+str(octet_n))

        return octet

    def src_mac_octet(self, octet_n):
        ''' Returns the specificed source MAC octet
        '''
        octet = getattr(self, 'src_mac_octet_'+str(octet_n))

        return octet
