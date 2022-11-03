class BitfieldMap(object):
    ''' Define the bitfields within a data word.
    '''

    def __init__(self):

        self._bitfields = {}
        self._data_word_bit_length = 0
        self._n_assigned_bits = 0

    def add_bitfield(self, name, offset, bit_length):
        ''' Add a bitfield to the map.
        '''

        if name in self._bitfields.keys():
            raise ValueError(
                'BitfieldMap.add_bitfield: Cannot create bitfield as ' +
                name + ' already exists. Please use another name.')

        upper_bound = offset + bit_length
        max_val = upper_bound - 1

        for bitfield in self._bitfields:

            if (offset in self._bitfields[bitfield] or
                max_val in self._bitfields[bitfield]):
                raise ValueError(
                    'BitfieldMap.add_bitfield: Cannot create bitfield as the '
                    'requested range overlaps the ' + bitfield + ' bitfield.')

        # Add the bitfield to the map
        self._bitfields[name] = range(offset, upper_bound)

        if upper_bound > self._data_word_bit_length:
            # Keep track of the length of the data word
            self._data_word_bit_length = upper_bound

        # Keep track of how many bits have been assigned to a bitfield
        self._n_assigned_bits += bit_length

    def pack(self, bitfield_values):
        ''' Packs the values provided by the bitfield_values dict in to their
        respective bitfields and returns the resultant data word.

        Note: the bitfield_values dict can contain any arbitrary subset of
        bitfields that are in this map.
        '''

        if not isinstance(bitfield_values, dict):
            raise TypeError(
                'BitfieldMap.pack: bitfield_values should be a dictionary.')

        packed_word = 0

        for bitfield in bitfield_values.keys():
            if bitfield not in self.bitfield_names:
                raise ValueError(
                    'BitfieldMap.pack: bitfield_values contains a value for '
                    'a bitfield which is not included in this map. The '
                    'invalid bitfield is ' + bitfield + '.')

            bitfield_value = bitfield_values[bitfield]
            value_upper_bound = 2**self.bitfield_bit_length(bitfield)

            if bitfield_value < 0:
                raise ValueError(
                    'BitfieldMap.pack: All bitfield values must be greater '
                    'than 0. The specified value for the ' + bitfield +
                    ' bitfield is ' + str(bitfield_values[bitfield]) + '.')

            if bitfield_value >= value_upper_bound:
                raise ValueError(
                    'BitfieldMap.pack: The value specified for the ' +
                    bitfield + ' bitfield is too large. The specified value '
                    'is ' + str(bitfield_value) + ' but the upper bound on '
                    'the value for this bitfield is ' +
                    str(value_upper_bound) + '.')

            # Shift the value into the correct position in the packed_word
            packed_word |= bitfield_value << self.bitfield_offset(bitfield)

        return packed_word

    def bitfield_offset(self, bitfield):
        ''' Returns the offset of the specified bitfield within the data word.
        '''
        return self._bitfields[bitfield].start

    def bitfield_bit_length(self, bitfield):
        ''' Returns the bit length of the specified bitfield.
        '''
        return len(self._bitfields[bitfield])

    def bitfield_upper_bound_index(self, bitfield):
        ''' Returns the upper bound bit index within the data word assigned to
        the specified bitfield.
        '''
        return self._bitfields[bitfield].stop

    @property
    def n_bitfields(self):
        ''' Returns the number of bitfields on this map.
        '''
        return len(self._bitfields.keys())

    @property
    def bitfield_names(self):
        ''' Returns a list containing the names of all of the bitfields.
        '''
        return list(self._bitfields.keys())

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
