import copy

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

    @property
    @abstractmethod
    def default_value(self):
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

    def __init__(
        self, offset, bit_length, default_value=0, restricted_values=None):
        ''' offset = Offset of the bitfield.

        bit_length = The length of the bitfield in bits.

        default_value = The default value of the bitfield.

        restricted_values = The values this bitfield is restricted to. If
        None, any value that fits is valid.
        '''

        if offset < 0:
            raise ValueError('UintBitfield: offset should not be negative.')

        if bit_length <= 0:
            raise ValueError(
                'UintBitfield: bit_length should be greater than 0.')

        if default_value < 0:
            raise ValueError(
                'UintBitfield: default_value should not be negative.')

        if default_value.bit_length() > bit_length:
            raise ValueError(
                'UintBitfield: The requested default_value requires more '
                'bits than the requested bit_length.')

        if restricted_values is not None:
            if default_value not in restricted_values:
                raise ValueError(
                    'UintBitfield: The requested default_value is not '
                    'included in the restricted_values.')

            for restricted_value in restricted_values:
                if restricted_value < 0:
                    raise ValueError(
                        'UintBitfield: restricted_values should not contain '
                        'negative values.')

                if restricted_value.bit_length() > bit_length:
                    raise ValueError(
                        'UintBitfield: restricted_values should not require '
                        'more bits than the requested bit_length.')

        self._bitfield = range(offset, offset + bit_length)
        self._default_value = default_value
        self._restricted_values = copy.deepcopy(restricted_values)

    @property
    def offset(self):
        return self._bitfield.start

    @property
    def bit_length(self):
        return len(self._bitfield)

    @property
    def index_upper_bound(self):
        return self._bitfield.stop

    @property
    def default_value(self):
        return self._default_value

    @property
    def restricted_values(self):
        return self._restricted_values

    @property
    def pack_default(self):
        ''' Packs the default value in to the correct offset.
        '''
        packed_value = self.default_value << self.offset

        return packed_value

    def pack(self, value):
        ''' Checks the value is valid and packs it in to the correct offset.
        '''
        if value < 0:
            raise ValueError(
                'UintBitfield: The value passed to pack should not be '
                'negative.')

        if value.bit_length() > self.bit_length:
            raise ValueError(
                'UintBitfield: Value requires too many bits. This '
                'bitfield has a bit length of ' + str(self.bit_length) +
                '.')

        if self.restricted_values is not None:
            if value not in self.restricted_values:
                raise ValueError(
                    'UintBitfield: The value passed to pack is not permitted '
                    'in this bitfield.')

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

    def __init__(self, offset, default_value=0):
        ''' offset = Offset of the bitfield.

        default_value = The default value of the bitfield.
        '''

        if offset < 0:
            raise ValueError('BoolBitfield: offset should not be negative.')

        self._valid_values = [True, False, 1, 0]

        if default_value not in self._valid_values:
            raise ValueError(
                'BoolBitfield: default_value should be one of ' +
                ', '.join([str(v) for v in self._valid_values]) + '.')

        self._offset = offset
        self._bit_length = 1
        self._default_value = default_value

    @property
    def offset(self):
        return self._offset

    @property
    def bit_length(self):
        return self._bit_length

    @property
    def index_upper_bound(self):
        return self.offset + self.bit_length

    @property
    def default_value(self):
        return self._default_value

    @property
    def pack_default(self):
        ''' Packs the default value in to the correct offset.
        '''
        packed_value = self.default_value << self.offset

        return packed_value

    def pack(self, value):
        ''' Checks the value is valid and packs it in to the correct offset.
        '''

        if value not in self._valid_values:
            raise ValueError(
                'BoolBitfield: The value passed to pack should be one of ' +
                ', '.join([str(v) for v in self._valid_values]) + '.')

        packed_value = value << self.offset

        return packed_value

    def unpack(self, word):
        ''' Unpacks this bitfield from the word.
        '''
        value = (word >> self.offset) & 1

        return value
