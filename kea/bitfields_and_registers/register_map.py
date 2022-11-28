from math import ceil

from .utils import overlapping_ranges

from .register_definition import RegisterDefinition

def power_of_two(value):
    ''' Returns True if value is a power of 2 and False if not.
    '''
    return (value != 0) and (value & (value-1) == 0)

class RegisterMap(object):
    ''' Define the registers within a register space.
    '''

    def __init__(
        self, register_bit_width, register_definitions,
        addressable_location_bit_width=8):
        ''' Initialise a RegisterMap.

        register_bit_width: the width of the registers in bits. Note: the
        registers in register_definitions can have a bit length that is less
        than or equal to register_bit_width but not greater.

        register_definitions: A dict containing n RegisterDefinitions.

        addressable_location_bit_width: Specifies the bit width of each
        addressable memory location. ie if this is set to 8 then each
        increment in the address will point to the next byte in memory.
        '''

        if register_bit_width <= 0:
            raise ValueError(
                'RegisterMap: register_bit_width should be a greater than 0.')

        if not power_of_two(register_bit_width):
            raise ValueError(
                'RegisterMap: register_bit_width should be a power of 2.')

        if not isinstance(register_definitions, dict):
            raise TypeError(
                'RegisterMap: register_definitions should be a dict.')

        # The 8 bit limit on addressable_location_bit_width limit is fairly
        # arbitrary but it seems unlikely that anyone would require an
        # addressable_location_bit_width of less than 8. We set this limit to
        # reduce the testing burden. If required, this limit can be changed.
        if addressable_location_bit_width < 8:
            raise ValueError(
                'RegisterMap: addressable_location_bit_width should be '
                'greater than or equal to 8.')

        if not power_of_two(addressable_location_bit_width):
            raise ValueError(
                'RegisterMap: addressable_location_bit_width should be a '
                'power of 2.')

        self._register_bit_width = register_bit_width
        self._register_names = []

        n_addresses_per_register = ceil(
            self._register_bit_width/addressable_location_bit_width)
        offsets = []

        for register_name in register_definitions:

            register = register_definitions[register_name]

            if not isinstance(register, RegisterDefinition):
                raise TypeError(
                    'RegisterMap: All registers in register_definitions '
                    'should be an instance of RegisterDefinition.')

            if register.offset % n_addresses_per_register != 0:
                raise ValueError(
                    'RegisterMap: Register offsets should be a multiple of '
                    'the number of addresses occupied by each register.')

            if register.bit_length > self._register_bit_width:
                raise ValueError(
                    'RegisterMap: Register ' + register_name + ' is too wide '
                    'for the specified register_bit_width.')

            if register.offset in offsets:
                raise ValueError(
                    'RegisterMap: Register offsets should be unique. '
                    'The offset for register ' + register_name + ' is the '
                    'same as another register.')

            offsets.append(register.offset)

            # We know register_name is unique as it is a key from a dict
            setattr(self, register_name, register)

            self._register_names.append(register_name)

    def register(self, register_name):
        ''' Returns the register specified by register_name.

        Note: the register can be accessed directly using
        `register_map.<register_name>`. This method makes it easier to iterate
        over the registers.
        '''
        # Check that the requested register_name is valid
        if register_name not in self.register_names:
            raise ValueError(
                'RegisterMap: The requested register is not included in this '
                'map.')

        register = getattr(self, register_name)

        return register

    @property
    def n_registers(self):
        ''' Returns the number of registers on this map.
        '''
        return len(self.register_names)

    @property
    def register_names(self):
        ''' Returns a list containing the names of all of the registers.
        '''
        return self._register_names

    @property
    def register_bit_width(self):
        ''' Returns the bit width of the registers in this map.
        '''
        return self._register_bit_width
