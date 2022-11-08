from abc import ABC, abstractmethod

class BitfieldDefinition(ABC):
    ''' An abstact base class specifying the requirements for bitfield
    definitions.
    '''

    @property
    @abstractmethod
    def offset(self):
        pass

    @property
    @abstractmethod
    def bit_length(self):
        pass

    @property
    @abstractmethod
    def index_upper_bound(self):
        pass

    @abstractmethod
    def pack(self, value):
        pass

    @abstractmethod
    def unpack(self, word):
        pass

class UintBitfield(BitfieldDefinition):
    ''' A uint bitfield definition.
    '''

    def __init__(self, offset, bit_length):

        if offset < 0:
            raise ValueError('UintBitfield: offset cannot be negative.')

        if bit_length <= 0:
            raise ValueError(
                'UintBitfield: bit_length should be greater than 0.')

        self._bitfield = range(offset, offset + bit_length)

    @property
    def offset(self):
        return self._bitfield.start

    @property
    def bit_length(self):
        return len(self._bitfield)

    @property
    def index_upper_bound(self):
        return self._bitfield.stop

    def pack(self, value):
        ''' Checks the value is valid and packs it in to the correct offset.
        '''

        if value < 0:
            raise ValueError(
                'UintBitfield: The value passed to pack should be greater '
                'than or equal to 0.')

        if value.bit_length() > self.bit_length:
            raise ValueError(
                'UintBitfield: Value requires too many bits. This bitfield '
                'has a bit length of ' + str(self.bit_length) + '.')

        packed_value = value << self.offset

        return packed_value

    def unpack(self, word):
        ''' Unpacks this bitfield from the word.
        '''

        mask = 2**self.bit_length - 1
        value = (word >> self.offset) & mask

        return value

class BoolBitfield(BitfieldDefinition):
    ''' A boolean bitfield definition
    '''

    def __init__(self, offset):

        if offset < 0:
            raise ValueError('BoolBitfield: offset cannot be negative.')

        self._offset = offset

    @property
    def offset(self):
        return self._offset

    @property
    def bit_length(self):
        return 1

    @property
    def index_upper_bound(self):
        return self.offset + 1

    def pack(self, value):
        ''' Checks the value is valid and packs it in to the correct offset.
        '''

        if value < 0:
            raise ValueError(
                'BoolBitfield: The value passed to pack should be greater '
                'than or equal to 0.')

        if value.bit_length() > self.bit_length:
            raise ValueError(
                'BoolBitfield: Value requires too many bits. This bitfield '
                'has a bit length of 1.')

        packed_value = value << self.offset

        return packed_value

    def unpack(self, word):
        ''' Unpacks this bitfield from the word.
        '''

        value = (word >> self.offset) & 1

        return value
