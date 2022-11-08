from ._bitfield_definitions import BitfieldDefinition

class BitfieldMap(object):
    ''' Define the bitfields within a data word.
    '''

    def __init__(self, bitfield_definitions):

        if not isinstance(bitfield_definitions, dict):
            raise TypeError(
                'BitfieldMap: bitfield_definitions should be a dict.')

        self._bitfield_names = []
        self._data_word_bit_length = 0
        self._n_assigned_bits = 0

        for new_bitfield_name in bitfield_definitions:

            new_bitfield = bitfield_definitions[new_bitfield_name]

            if not issubclass(type(new_bitfield), BitfieldDefinition):
                raise TypeError(
                    'BitfieldMap: Every element in bitfield_definitions '
                    'should be a sub-class of BitfieldDefinition.')

            for existing_bitfield_name in self._bitfield_names:

                existing_bitfield = getattr(self, existing_bitfield_name)

                higher_offset = max(
                    new_bitfield.offset,
                    existing_bitfield.offset)
                lower_upper_bound = min(
                    new_bitfield.index_upper_bound,
                    existing_bitfield.index_upper_bound)

                # Check that the bitfield does not overlap with another
                if len(range(higher_offset, lower_upper_bound)) > 0:
                    raise ValueError(
                        'BitfieldMap: Overlapping bitfields. The overlapping '
                        'bitfields are ' + new_bitfield_name + ' and ' +
                        existing_bitfield_name + '.')

            # We know new_bitfield_name is unique as it is a key from a dict
            setattr(self, new_bitfield_name, new_bitfield)

            # Keep a record of the bitfields
            self._bitfield_names.append(new_bitfield_name)

            if new_bitfield.index_upper_bound > self._data_word_bit_length:
                # Keep track of the length of the data word
                self._data_word_bit_length = new_bitfield.index_upper_bound

            # Keep track of how many bits have been assigned to a bitfield
            self._n_assigned_bits += new_bitfield.bit_length

    def pack(self, bitfield_values):
        ''' Packs the values provided by the bitfield_values dict in to their
        respective bitfields and returns the resultant data word.

        Any bitfields not included in bitfield_values will have a value of 0.

        Note: the bitfield_values dict can contain any arbitrary subset of
        bitfields that are in this map.
        '''

        if not isinstance(bitfield_values, dict):
            raise TypeError(
                'BitfieldMap: bitfield_values should be a dictionary.')

        packed_word = 0

        for bitfield_name in bitfield_values.keys():
            if bitfield_name not in self._bitfield_names:
                raise ValueError(
                    'BitfieldMap: bitfield_values contains a value for a '
                    'bitfield which is not included in this map. The invalid '
                    'bitfield is ' + bitfield_name + '.')

            bitfield = getattr(self, bitfield_name)

            # Shift the value into the correct position in the packed_word
            packed_word |= bitfield.pack(bitfield_values[bitfield_name])

        return packed_word

    def bitfield(self, bitfield_name):
        ''' Returns the bitfield specified by bitfield_name.
        '''
        # Check that the requested bitfield_name is valid
        if bitfield_name not in self._bitfield_names:
            raise ValueError(
                'BitfieldMap: The requested bitfield is not included in this '
                'map')

        bitfield = getattr(self, bitfield_name)

        return bitfield

    @property
    def n_bitfields(self):
        ''' Returns the number of bitfields on this map.
        '''
        return len(self._bitfield_names)

    @property
    def bitfield_names(self):
        ''' Returns a list containing the names of all of the bitfields.
        '''
        return self._bitfield_names

    @property
    def data_word_bit_length(self):
        ''' Returns the total bit length of the data word (which contains all
        of the bitfields in this map).
        '''
        return self._data_word_bit_length

    @property
    def n_assigned_bits(self):
        ''' The number of bits that have been assigned to bitfields.

        If self.n_assigned_bits == self.data_word_bit_length then the data
        word is been packed in the most efficient way and there are no gaps
        between bitfields.

        If self.n_assigned_bits <= self.data_word_bit_length then there are
        gaps between bitfields in the data word.
        '''
        return self._n_assigned_bits
