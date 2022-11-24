from .utils import overlapping_ranges
from ._bitfield_definitions import BitfieldDefinition
from ._constant_bitfield_definitions import ConstantBitfieldDefinition

def valid_constant_bitfield(bitfield):
    ''' Returns True if bitfield is a valid constant bitfield.
    '''
    return issubclass(type(bitfield), ConstantBitfieldDefinition)

def valid_variable_bitfield(bitfield):
    ''' Returns True if bitfield is a valid variable bitfield.
    '''
    return issubclass(type(bitfield), BitfieldDefinition)

def check_bitfield_type(bitfield):
    ''' Errors if the bitfield is not a valid type.
    '''

    valid = (
        valid_constant_bitfield(bitfield) or
        valid_variable_bitfield(bitfield))

    if not valid:
        raise TypeError(
            'BitfieldMap: Bitfield should be a sub-class of '
            'BitfieldDefinition or ConstantBitfieldDefinition.')

def overlapping_bitfields(bitfield_0, bitfield_1):
    ''' Returns True if the bitfields are overlapping and False if they are
    not overlapping.
    '''

    check_bitfield_type(bitfield_0)
    check_bitfield_type(bitfield_1)

    return overlapping_ranges(
        range(bitfield_0.offset, bitfield_0.index_upper_bound),
        range(bitfield_1.offset, bitfield_1.index_upper_bound))

class BitfieldMap(object):
    ''' Define the bitfields within a data word.
    '''

    def __init__(self, bitfield_definitions):

        if not isinstance(bitfield_definitions, dict):
            raise TypeError(
                'BitfieldMap: bitfield_definitions should be a dict.')

        self._constant_bitfield_names = []
        self._variable_bitfield_names = []
        self._bit_length = 0
        self._n_assigned_bits = 0

        for new_bitfield_name in bitfield_definitions:

            # Extract the bitfield and check the validity
            new_bitfield = bitfield_definitions[new_bitfield_name]
            check_bitfield_type(new_bitfield)

            # Combine the constant_bitfields and variable_bitfields lists into
            # a single list of existing_bitfields
            existing_bitfields = [
                *self._constant_bitfield_names,
                *self._variable_bitfield_names]

            for existing_bitfield_name in existing_bitfields:

                # Extract each existing bitfield in turn
                existing_bitfield = getattr(self, existing_bitfield_name)

                # Check that the bitfield does not overlap with another
                if overlapping_bitfields(new_bitfield, existing_bitfield):
                    raise ValueError(
                        'BitfieldMap: Overlapping bitfields. The overlapping '
                        'bitfields are ' + new_bitfield_name + ' and ' +
                        existing_bitfield_name + '.')

            # We know new_bitfield_name is unique as it is a key from a dict
            setattr(self, new_bitfield_name, new_bitfield)

            if valid_constant_bitfield(new_bitfield):
                # Keep a record of which bitfields are constant bitfields
                self._constant_bitfield_names.append(new_bitfield_name)

            elif valid_variable_bitfield(new_bitfield):
                # Keep a record of which bitfields are variable bitfields
                self._variable_bitfield_names.append(new_bitfield_name)

            else:
                raise TypeError(
                    'BitfieldMap: This error should never occur as the '
                    'bitfield type should be checked above.')

            if new_bitfield.index_upper_bound > self._bit_length:
                # Keep track of the length of the data word
                self._bit_length = new_bitfield.index_upper_bound

            # Keep track of how many bits have been assigned to a bitfield
            self._n_assigned_bits += new_bitfield.bit_length

    def pack(self, bitfield_values):
        ''' Packs all bitfield_values in to their respective bitfields and
        returns the resultant data word.

        Any bitfields not included in bitfield_values will contain the default
        value for that bitfield.

        It is not possible to pack a value into a constant bitfield. If a
        value is provided in bitfield_values for a constant bitfield then an
        error will be raised. Any constant bitfields in the map will contain
        the constant value for that bitfield.

        Note: the bitfield_values dict can contain any arbitrary subset of non
        constant bitfields that are in this map.
        '''

        if not isinstance(bitfield_values, dict):
            raise TypeError(
                'BitfieldMap: bitfield_values should be a dictionary.')

        for bitfield_name in bitfield_values:
            if bitfield_name not in self.bitfield_names:
                raise ValueError(
                    'BitfieldMap: bitfield_values contains a value for a '
                    'bitfield which is not included in this map. The invalid '
                    'bitfield is ' + bitfield_name + '.')

            if bitfield_name in self.constant_bitfield_names:
                raise ValueError(
                    'BitfieldMap: bitfield_values contains a value for a '
                    'bitfield which is a constant and so cannot be set.')

        packed_word = 0

        for bitfield_name in self.bitfield_names:

            bitfield = getattr(self, bitfield_name)

            if bitfield_name in self.constant_bitfield_names:
                # A constant bitfield so pack it in to the word
                packed_word |= bitfield.pack

            else:
                if bitfield_name in bitfield_values:
                    # Shift the value into the correct position in the
                    # packed_word
                    packed_word |= (
                        bitfield.pack(bitfield_values[bitfield_name]))

                else:
                    # No value has been specified for this bitfield so use the
                    # default.
                    packed_word |= bitfield.pack_default

        return packed_word

    def unpack(self, word):
        ''' Unpacks all bitfield values from `word` and returns the values in
        a dict.
        '''

        unpacked_values = {}

        for bitfield_name in self.bitfield_names:
            # Go through each bitfield and unpack the word
            bitfield = getattr(self, bitfield_name)
            unpacked_values[bitfield_name] = bitfield.unpack(word)

        return unpacked_values

    def bitfield(self, bitfield_name):
        ''' Returns the bitfield specified by bitfield_name.

        Note: the bitfield can be accessed directly using
        `bitfield_map.<bitfield_name>`. This method makes it easier to iterate
        over the bitfields.
        '''
        # Check that the requested bitfield_name is valid
        if bitfield_name not in self.bitfield_names:
            raise ValueError(
                'BitfieldMap: The requested bitfield is not included in this '
                'map')

        bitfield = getattr(self, bitfield_name)

        return bitfield

    @property
    def n_bitfields(self):
        ''' Returns the number of bitfields on this map.
        '''
        return len(self.bitfield_names)

    @property
    def bitfield_names(self):
        ''' Returns a list containing the names of all of the bitfields.
        '''
        return [
            *self._constant_bitfield_names, *self._variable_bitfield_names]

    @property
    def constant_bitfield_names(self):
        ''' Returns a list containing the names of all of the constant
        bitfields.
        '''
        return self._constant_bitfield_names

    @property
    def variable_bitfield_names(self):
        ''' Returns a list containing the names of all of the variable
        bitfields.
        '''
        return self._variable_bitfield_names

    @property
    def bit_length(self):
        ''' Returns the total bit length of the bitmap.
        '''
        return self._bit_length

    @property
    def n_assigned_bits(self):
        ''' The number of bits that have been assigned to bitfields.

        If self.n_assigned_bits == self.bit_length then the data word has been
        packed in the most efficient way and there are no gaps between
        bitfields.

        If self.n_assigned_bits <= self.bit_length then there are gaps between
        bitfields.
        '''
        return self._n_assigned_bits
