import copy

from abc import ABC, abstractmethod

from .utils import VALID_BOOLEAN_VALUES

class ConstantBitfieldDefinition(ABC):
    ''' An abstact base class specifying the requirements for constant
    bitfield definitions.
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

    @property
    @abstractmethod
    def value(self):
        pass

    @property
    @abstractmethod
    def pack(self):
        pass

    @abstractmethod
    def unpack(self, word):
        pass

class ConstantUintBitfield(ConstantBitfieldDefinition):
    ''' A constant uint bitfield definition.
    '''

    def __init__(self, offset, bit_length, value):
        ''' offset = Offset of the bitfield.

        bit_length = The length of the bitfield in bits.

        value = The constant value of the bitfield.
        '''

        if offset < 0:
            raise ValueError(
                'ConstantUintBitfield: offset should not be negative.')

        if bit_length <= 0:
            raise ValueError(
                'ConstantUintBitfield: bit_length should be greater than 0.')

        if value < 0:
            raise ValueError(
                'ConstantUintBitfield: value should not be negative.')

        if value.bit_length() > bit_length:
            raise ValueError(
                'ConstantUintBitfield: The requested value requires more '
                'bits than the requested bit_length.')

        self._offset = offset
        self._bit_length = bit_length
        self._index_upper_bound = self._offset + self._bit_length
        self._value = value
        self._packed_value = self._value << self._offset

    @property
    def offset(self):
        return self._offset

    @property
    def bit_length(self):
        return self._bit_length

    @property
    def index_upper_bound(self):
        return self._index_upper_bound

    @property
    def value(self):
        return self._value

    @property
    def pack(self):
        ''' Returns the constant value shifted in to the correct offset.
        '''
        return self._packed_value

    def unpack(self, word):
        ''' Unpacks this bitfield from the word.
        '''
        mask = 2**self.bit_length - 1
        value = (word >> self.offset) & mask

        return value

class ConstantBoolBitfield(ConstantBitfieldDefinition):
    ''' A constant boolean bitfield definition
    '''

    def __init__(self, offset, value):
        ''' offset = Offset of the bitfield.

        value = The constant value of the bitfield.
        '''

        if offset < 0:
            raise ValueError(
                'ConstantBoolBitfield: offset should not be negative.')

        if value not in VALID_BOOLEAN_VALUES:
            raise ValueError(
                'ConstantBoolBitfield: value should be one of ' +
                ', '.join([str(v) for v in VALID_BOOLEAN_VALUES]) + '.')

        self._offset = offset
        self._bit_length = 1
        self._index_upper_bound = self._offset + self._bit_length
        self._value = value
        self._packed_value = self._value << self._offset

    @property
    def offset(self):
        return self._offset

    @property
    def bit_length(self):
        return self._bit_length

    @property
    def index_upper_bound(self):
        return self._index_upper_bound

    @property
    def value(self):
        return self._value

    @property
    def pack(self):
        ''' Returns the constant value shifted in to the correct offset.
        '''
        return self._packed_value

    def unpack(self, word):
        ''' Unpacks this bitfield from the word.
        '''
        value = (word >> self.offset) & 1

        return value
