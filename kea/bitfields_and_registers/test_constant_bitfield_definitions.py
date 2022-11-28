import random

from kea.test_utils import KeaTestCase

from .utils import VALID_BOOLEAN_VALUES
from .constant_bitfield_definitions import (
    ConstantBitfieldDefinition, ConstantUintBitfield, ConstantBoolBitfield)

class TestConstantUintBitfield(KeaTestCase):

    def setUp(self):

        bit_length = random.randrange(1, 129)
        value = random.randrange(2**bit_length)

        self.args = {
            'offset': random.randrange(0, 129),
            'bit_length': bit_length,
            'value': value,
        }

        self.constant_uint_bitfield = ConstantUintBitfield(**self.args)

    def test_negative_offset(self):
        ''' The `ConstantUintBitfield` should raise an error if the `offset`
        is less than 0.
        '''

        self.args['offset'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('ConstantUintBitfield: offset should not be negative.'),
            ConstantUintBitfield,
            **self.args,
        )

    def test_invalid_bit_length(self):
        ''' The `ConstantUintBitfield` should raise an error if the
        `bit_length` is less than or equal to 0.
        '''

        self.args['bit_length'] = 0

        self.assertRaisesRegex(
            ValueError,
            ('ConstantUintBitfield: bit_length should be greater than 0.'),
            ConstantUintBitfield,
            **self.args,
        )

        self.args['bit_length'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('ConstantUintBitfield: bit_length should be greater than 0.'),
            ConstantUintBitfield,
            **self.args,
        )

    def test_negative_value(self):
        ''' The `ConstantUintBitfield` should raise an error if the `value` is
        less than 0.
        '''

        self.args['value'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('ConstantUintBitfield: value should not be negative.'),
            ConstantUintBitfield,
            **self.args,
        )

    def test_invalid_value_bit_length(self):
        ''' The `ConstantUintBitfield` should raise an error if the `value` is
        too large for the requested `bit_length`.
        '''

        valid_upper_bound = 2**self.args['bit_length']
        self.args['value'] = (
            random.randrange(valid_upper_bound, valid_upper_bound+200))

        self.assertRaisesRegex(
            ValueError,
            ('ConstantUintBitfield: The requested value requires more bits '
             'than the requested bit_length.'),
            ConstantUintBitfield,
            **self.args,
        )

    def test_offset(self):
        ''' The `offset` property on a `ConstantUintBitfield` should return
        the offset specified at initialisation of that `ConstantUintBitfield`.
        '''

        assert(self.constant_uint_bitfield.offset == self.args['offset'])

    def test_bit_length(self):
        ''' The `bit_length` property on a `ConstantUintBitfield` should
        return the bit length specified at initialisation of that
        `ConstantUintBitfield`.
        '''

        assert(
            self.constant_uint_bitfield.bit_length == self.args['bit_length'])

    def test_index_upper_bound(self):
        ''' The `index_upper_bound` property on a `ConstantUintBitfield`
        should return the upper bound bit index of the bitfield.
        '''

        expected_index_upper_bound = (
            self.args['offset'] + self.args['bit_length'])

        assert(
            self.constant_uint_bitfield.index_upper_bound ==
            expected_index_upper_bound)

    def test_value(self):
        ''' The `value` property on a `ConstantUintBitfield` should return the
        value specified at initialisation of that `ConstantUintBitfield`.
        '''
        assert(self.constant_uint_bitfield.value == self.args['value'])

    def test_pack(self):
        ''' The `pack` method on a `ConstantUintBitfield` should return the
        `value` specified at initialisation of that `ConstantUintBitfield`
        shifted by the bitfield offset.
        '''
        expected_result = self.args['value'] << self.args['offset']
        dut_result = self.constant_uint_bitfield.pack

        assert(dut_result == expected_result)

    def test_unpack(self):
        ''' The `unpack` method on a `ConstantUintBitfield` should extract the
        bitfield from the `word` argument and return it.
        '''

        bitfield_index_upper_bound = (
            self.args['offset'] + self.args['bit_length'])
        # Make sure the word upper bound is double the bitfield upper bound
        # index.
        word_upper_bound = 2**(bitfield_index_upper_bound + 1)

        for n in range(10):
            # Generate a random word
            word = random.randrange(word_upper_bound)

            expected_value = (
                (word >> self.args['offset']) &
                (2**self.args['bit_length'] - 1))
            dut_value = self.constant_uint_bitfield.unpack(word)

            assert(dut_value == expected_value)

class TestConstantBoolBitfield(KeaTestCase):

    def setUp(self):

        self.args = {
            'offset': random.randrange(0, 129),
            'value': random.randrange(2),
        }

        self.constant_bool_bitfield = ConstantBoolBitfield(**self.args)

    def test_negative_offset(self):
        ''' The `ConstantBoolBitfield` should raise an error if the `offset`
        is less than 0.
        '''

        self.args['offset'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('ConstantBoolBitfield: offset should not be negative.'),
            ConstantBoolBitfield,
            **self.args
        )

    def test_invalid_value(self):
        ''' The `ConstantBoolBitfield` should raise an error if the `value` is
        not valid for a boolean bitfield.
        '''

        self.args['value'] = random.randrange(2, 100)

        self.assertRaisesRegex(
            ValueError,
            ('ConstantBoolBitfield: value should be one of ' +
             ', '.join([str(v) for v in VALID_BOOLEAN_VALUES]) + '.'),
            ConstantBoolBitfield,
            **self.args,
        )

    def test_offset(self):
        ''' The `offset` property on a `ConstantBoolBitfield` should return
        the offset specified at initialisation of that `ConstantBoolBitfield`.
        '''

        assert(self.constant_bool_bitfield.offset == self.args['offset'])

    def test_bit_length(self):
        ''' The `bit_length` property on a `ConstantBoolBitfield` should
        return 1.
        '''

        assert(self.constant_bool_bitfield.bit_length == 1)

    def test_index_upper_bound(self):
        ''' The `index_upper_bound` property on a `ConstantBoolBitfield`
        should return the upper bound bit index of the bitfield.
        '''

        expected_index_upper_bound = self.args['offset'] + 1

        assert(
            self.constant_bool_bitfield.index_upper_bound ==
            expected_index_upper_bound)

    def test_value(self):
        ''' The `value` property on a `ConstantBoolBitfield` should return the
        value specified at initialisation of that `ConstantBoolBitfield`.
        '''
        assert(self.constant_bool_bitfield.value == self.args['value'])

    def test_pack(self):
        ''' The `pack` method on a `ConstantBoolBitfield` should return the
        `value` specified at initialisation of that `ConstantBoolBitfield`
        shifted by the bitfield offset.
        '''
        expected_result = self.args['value'] << self.args['offset']
        dut_result = self.constant_bool_bitfield.pack

        assert(dut_result == expected_result)

    def test_unpack(self):
        ''' The `unpack` method on a `ConstantBoolBitfield` should extract the
        bitfield from the `word` argument and return it.
        '''

        bitfield_index_upper_bound = self.args['offset'] + 1
        # Make sure the word upper bound is double the bitfield upper bound
        # index.
        word_upper_bound = 2**(bitfield_index_upper_bound + 1)

        for n in range(10):
            # Generate a random word
            word = random.randrange(word_upper_bound)

            expected_value = (word >> self.args['offset']) & 1
            dut_value = self.constant_bool_bitfield.unpack(word)

            assert(dut_value == expected_value)
