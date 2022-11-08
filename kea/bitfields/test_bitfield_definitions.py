import random

from kea.test_utils import KeaTestCase

from ._bitfield_definitions import (
    BitfieldDefinition, UintBitfield, BoolBitfield)

class TestUintBitfield(KeaTestCase):

    def setUp(self):

        self.offset = random.randrange(0, 129)
        self.bit_length = random.randrange(1, 129)

        self.uint_bitfield = UintBitfield(self.offset, self.bit_length)

    def test_negative_offset(self):
        ''' The `UintBitfield` should raise an error if the `offset` is
        less than 0.
        '''

        offset = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('UintBitfield: offset cannot be negative.'),
            UintBitfield,
            offset,
            self.bit_length,
        )

    def test_invalid_bit_length(self):
        ''' The `UintBitfield` should raise an error if the `bit_length` is
        less than or equal to 0.
        '''

        bit_length = 0

        self.assertRaisesRegex(
            ValueError,
            ('UintBitfield: bit_length should be greater than 0.'),
            UintBitfield,
            self.offset,
            bit_length,
        )

        bit_length = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('UintBitfield: bit_length should be greater than 0.'),
            UintBitfield,
            self.offset,
            bit_length,
        )

    def test_offset(self):
        ''' The `offset` property on a `UintBitfield` should return the
        offset specified at initialisation of that `UintBitfield`.
        '''

        assert(self.uint_bitfield.offset == self.offset)

    def test_bit_length(self):
        ''' The `bit_length` property on a `UintBitfield` should return
        the bit length specified at initialisation of that
        `UintBitfield`.
        '''

        assert(self.uint_bitfield.bit_length == self.bit_length)

    def test_index_upper_bound(self):
        ''' The `index_upper_bound` property on a `UintBitfield` should
        return the upper bound bit index of the bitfield.
        '''

        expected_index_upper_bound = self.offset + self.bit_length

        assert(
            self.uint_bitfield.index_upper_bound ==
            expected_index_upper_bound)

    def test_pack_negative_value(self):
        ''' The `pack` method on a `UintBitfield` should raise an error
        if the `value` argument is less than 0.
        '''
        value = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('UintBitfield: The value passed to pack should be greater '
             'than or equal to 0.'),
            self.uint_bitfield.pack,
            value,
        )

    def test_pack_invalid_value(self):
        ''' The `pack` method on a `UintBitfield` should raise an error if the
        `value` argument is too large.
        '''
        value_upper_bound = 2**self.bit_length
        value = random.randrange(value_upper_bound, value_upper_bound+100)

        self.assertRaisesRegex(
            ValueError,
            ('UintBitfield: Value requires too many bits. This bitfield has '
             'a bit length of ' + str(self.bit_length) + '.'),
            self.uint_bitfield.pack,
            value,
        )

    def test_pack(self):
        ''' The `pack` method on a `UintBitfield` should return the
        `value` argument shifted by the bitfield offset.
        '''
        value_upper_bound = 2**self.uint_bitfield.bit_length
        value = random.randrange(0, value_upper_bound)

        expected_result = value << self.offset
        dut_result = self.uint_bitfield.pack(value)

        assert(dut_result == expected_result)

    def test_unpack(self):
        ''' The `unpack` method on a `UintBitfield` should extract the
        bitfield from the `word` argument and return it.
        '''

        bitfield_index_upper_bound = self.offset + self.bit_length
        # Make sure the word upper bound is double the bitfield upper bound
        # index.
        word_upper_bound = 2**(bitfield_index_upper_bound + 1)

        for n in range(10):
            # Generate a random word
            word = random.randrange(word_upper_bound)

            expected_value = (word >> self.offset) & (2**self.bit_length - 1)
            dut_value = self.uint_bitfield.unpack(word)

            assert(dut_value == expected_value)

class TestBoolBitfield(KeaTestCase):

    def setUp(self):

        self.offset = random.randrange(0, 129)

        self.bool_bitfield = BoolBitfield(self.offset)

    def test_negative_offset(self):
        ''' The `BoolBitfield` should raise an error if the `offset` is less
        than 0.
        '''

        offset = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('BoolBitfield: offset cannot be negative.'),
            BoolBitfield,
            offset,
        )

    def test_offset(self):
        ''' The `offset` property on a `BoolBitfield` should return the
        offset specified at initialisation of that `BoolBitfield`.
        '''

        assert(self.bool_bitfield.offset == self.offset)

    def test_bit_length(self):
        ''' The `bit_length` property on a `BoolBitfield` should return 1.
        '''

        assert(self.bool_bitfield.bit_length == 1)

    def test_index_upper_bound(self):
        ''' The `index_upper_bound` property on a `BoolBitfield` should
        return the upper bound bit index of the bitfield.
        '''

        expected_index_upper_bound = self.offset + 1

        assert(
            self.bool_bitfield.index_upper_bound ==
            expected_index_upper_bound)

    def test_pack_negative_value(self):
        ''' The `pack` method on a `BoolBitfield` should raise an error
        if the `value` argument is negative.
        '''
        value = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('BoolBitfield: The value passed to pack should be greater '
             'than or equal to 0.'),
            self.bool_bitfield.pack,
            value,
        )

    def test_pack_invalid_value(self):
        ''' The `pack` method on a `BoolBitfield` should raise an error
        if the `value` argument is not a boolean.
        '''
        value = random.randrange(2, 100)

        self.assertRaisesRegex(
            ValueError,
            ('BoolBitfield: Value requires too many bits. This bitfield '
             'has a bit length of 1.'),
            self.bool_bitfield.pack,
            value,
        )

    def test_pack_boolean(self):
        ''' The `pack` method on a `BoolBitfield` should return the boolean
        `value` shifted by the bitfield offset.
        '''
        value = True

        expected_result = value << self.offset
        dut_result = self.bool_bitfield.pack(value)

        assert(dut_result == expected_result)

        value = False

        expected_result = value << self.offset
        dut_result = self.bool_bitfield.pack(value)

        assert(dut_result == expected_result)

    def test_pack_uint(self):
        ''' The `pack` method on a `BoolBitfield` should return the uint
        `value` shifted by the bitfield offset.
        '''
        value = 1

        expected_result = value << self.offset
        dut_result = self.bool_bitfield.pack(value)

        assert(dut_result == expected_result)

        value = 0

        expected_result = value << self.offset
        dut_result = self.bool_bitfield.pack(value)

        assert(dut_result == expected_result)

    def test_unpack(self):
        ''' The `unpack` method on a `BoolBitfield` should extract the
        bitfield from the `word` argument and return it.
        '''

        bitfield_index_upper_bound = self.offset + 1
        # Make sure the word upper bound is double the bitfield upper bound
        # index.
        word_upper_bound = 2**(bitfield_index_upper_bound + 1)

        for n in range(10):
            # Generate a random word
            word = random.randrange(word_upper_bound)

            expected_value = (word >> self.offset) & 1
            dut_value = self.bool_bitfield.unpack(word)

            assert(dut_value == expected_value)

