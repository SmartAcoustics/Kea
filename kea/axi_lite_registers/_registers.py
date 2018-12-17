from myhdl import (Signal, intbv)
from collections import OrderedDict

class RegisterSet(object):
    pass

class Registers(object):
    ''' A general purpose register definition.
    '''

    @property
    def register_types(self):
        return self._register_types

    def __init__(
        self, register_list, register_types=None, register_width=32,
        initial_values=None):

        if register_types is None:
            # Create a register types dictionary so that the system can handle
            # an empty register types argument.
            register_types = {}

        # Create an ordered dictionary
        self._register_types = OrderedDict()

        for each in register_types:
            if each not in register_list:
                # Check that the register types have a corresponding register
                # in the register list. If not error.
                raise ValueError(
                    'Invalid register in register_types: %s' % each)

        if initial_values is None:
            initial_values = {}

        for initial_val_key in initial_values:

            if (register_types.get(initial_val_key, 'axi_read_write') !=
                'axi_read_write'):

                raise ValueError(
                    'Only read-write registers can take initial values: %s' %
                    initial_val_key + ': ' +
                    str(register_types[initial_val_key]))

        for name in register_list:

            # Create the registers
            setattr(self, name, Signal(
                intbv(initial_values.get(name, 0))[register_width:]))

            # Populate the ordered dictionary with the appropriate
            # register types, defaulting to 'axi_read_write'
            self._register_types[name] = (
                register_types.get(name, 'axi_read_write'))

