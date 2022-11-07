class BitfieldDefinition(object):

    def __init__(self, offset, bit_length):

        if offset < 0:
            raise ValueError('BitfieldDefinition: offset cannot be negative.')

        if bit_length <= 0:
            raise ValueError(
                'BitfieldDefinition: bit_length should be greater than 0.')

        self._bitfield = range(offset, offset + bit_length)

    @property
    def offset(self):
        return self._bitfield.start

    @property
    def bit_length(self):
        return len(self._bitfield)

    @property
    def upper_bound_index(self):
        return self._bitfield.stop

    def pack(self, value):
        ''' Packs the value provided in to the correct offset.
        '''

        if value < 0:
            raise ValueError(
                'BitfieldDefinition: values passed to pack should be greater '
                'than or equal to 0.')

        value_upper_bound = 2**self.bit_length

        if value >= value_upper_bound:
            raise ValueError(
                'BitfieldDefinition: Value is too large. This bitfield has '
                'a value upper bound of ' + str(value_upper_bound) + '.')

        packed_value = value << self.offset

        return packed_value
