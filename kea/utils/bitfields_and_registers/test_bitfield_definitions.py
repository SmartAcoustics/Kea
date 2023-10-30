import random

from kea.testing.test_utils import KeaTestCase

from .utils import VALID_BOOLEAN_VALUES
from .bitfield_definitions import (
    BitfieldDefinition, UintBitfield, BoolBitfield)

class TestUintBitfield(KeaTestCase):

    def setUp(self):

        self.args = {
            'offset': random.randrange(0, 129),
            'bit_length': random.randrange(1, 129),
        }

        self.uint_bitfield = UintBitfield(**self.args)

    def test_negative_offset(self):
        ''' The `UintBitfield` should raise an error if the `offset` is
        less than 0.
        '''

        self.args['offset'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('UintBitfield: offset should not be negative.'),
            UintBitfield,
            **self.args,
        )

    def test_invalid_bit_length(self):
        ''' The `UintBitfield` should raise an error if the `bit_length` is
        less than or equal to 0.
        '''

        self.args['bit_length'] = 0

        self.assertRaisesRegex(
            ValueError,
            ('UintBitfield: bit_length should be greater than 0.'),
            UintBitfield,
            **self.args,
        )

        self.args['bit_length'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('UintBitfield: bit_length should be greater than 0.'),
            UintBitfield,
            **self.args,
        )

    def test_negative_default_value(self):
        ''' The `UintBitfield` should raise an error if the `default_value` is
        less than 0.
        '''

        self.args['default_value'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('UintBitfield: default_value should not be negative.'),
            UintBitfield,
            **self.args,
        )

    def test_invalid_default_value_bit_length(self):
        ''' The `UintBitfield` should raise an error if the `default_value` is
        too large for the requested `bit_length`.
        '''

        valid_upper_bound = 2**self.args['bit_length']
        self.args['default_value'] = (
            random.randrange(valid_upper_bound, valid_upper_bound+200))

        self.assertRaisesRegex(
            ValueError,
            ('UintBitfield: The requested default_value requires more '
             'bits than the requested bit_length.'),
            UintBitfield,
            **self.args,
        )

    def test_invalid_default_value(self):
        ''' The `UintBitfield` should raise an error if the
        `restricted_values` argument is not None and the `default_value` is
        not in the `restricted_values`.
        '''

        self.args['bit_length'] = random.randrange(4, 17)
        valid_upper_bound = 2**self.args['bit_length']

        self.args['restricted_values'] = (
            random.sample(range(valid_upper_bound), 10))

        self.args['default_value'] = self.args['restricted_values'].pop()

        self.assertRaisesRegex(
            ValueError,
            ('UintBitfield: The requested default_value is not included in '
             'the restricted_values.'),
            UintBitfield,
            **self.args,
        )

    def test_negative_restricted_value(self):
        ''' The `UintBitfield` should raise an error if the
        `restricted_values` contains a value which is less than 0.
        '''

        self.args['bit_length'] = random.randrange(4, 17)
        valid_upper_bound = 2**self.args['bit_length']

        self.args['restricted_values'] = (
            random.sample(range(valid_upper_bound), 10))
        self.args['default_value'] = self.args['restricted_values'][0]

        self.args['restricted_values'].append(random.randrange(-100, 0))

        self.assertRaisesRegex(
            ValueError,
            ('UintBitfield: restricted_values should not contain '
             'negative values.'),
            UintBitfield,
            **self.args,
        )

    def test_invalid_restricted_value_bit_length(self):
        ''' The `UintBitfield` should raise an error if the
        `restricted_values` contains a value which is too large for the
        requested `bit_length`.
        '''

        self.args['bit_length'] = random.randrange(4, 17)
        valid_upper_bound = 2**self.args['bit_length']

        self.args['restricted_values'] = (
            random.sample(range(valid_upper_bound), 10))
        self.args['default_value'] = self.args['restricted_values'][0]

        self.args['restricted_values'].append(
            random.randrange(valid_upper_bound, valid_upper_bound+1000))

        self.assertRaisesRegex(
            ValueError,
            ('UintBitfield: restricted_values should not require '
             'more bits than the requested bit_length.'),
            UintBitfield,
            **self.args,
        )

    def test_offset(self):
        ''' The `offset` property on a `UintBitfield` should return the
        offset specified at initialisation of that `UintBitfield`.
        '''

        assert(self.uint_bitfield.offset == self.args['offset'])

    def test_bit_length(self):
        ''' The `bit_length` property on a `UintBitfield` should return
        the bit length specified at initialisation of that
        `UintBitfield`.
        '''

        assert(self.uint_bitfield.bit_length == self.args['bit_length'])

    def test_index_upper_bound(self):
        ''' The `index_upper_bound` property on a `UintBitfield` should
        return the upper bound bit index of the bitfield.
        '''

        expected_index_upper_bound = (
            self.args['offset'] + self.args['bit_length'])

        assert(
            self.uint_bitfield.index_upper_bound ==
            expected_index_upper_bound)

    def test_default_value(self):
        ''' The `default_value` property on a `UintBitfield` should return the
        default value specified at initialisation of that `UintBitfield`.
        '''
        self.args['default_value'] = (
            random.randrange(2**self.args['bit_length']))
        self.uint_bitfield = UintBitfield(**self.args)

        assert(self.uint_bitfield.default_value == self.args['default_value'])

    def test_restricted_values(self):
        ''' The `restricted_values` property on a `UintBitfield` should return
        the restricted values specified at initialisation of that
        `UintBitfield`.
        '''
        self.args['bit_length'] = random.randrange(4, 17)
        valid_upper_bound = 2**self.args['bit_length']

        self.args['restricted_values'] = (
            random.sample(range(valid_upper_bound), 10))
        self.args['default_value'] = self.args['restricted_values'][0]

        self.uint_bitfield = UintBitfield(**self.args)

        assert(
            self.uint_bitfield.restricted_values ==
            self.args['restricted_values'])

    def test_pack_default(self):
        ''' The `pack_default` method on a `UintBitfield` should return the
        `default_value` specified at initialisation of that `UintBitfield`
        shifted by the bitfield offset.
        '''
        self.args['default_value'] = (
            random.randrange(2**self.args['bit_length']))

        self.uint_bitfield = UintBitfield(**self.args)

        expected_result = self.args['default_value'] << self.args['offset']
        dut_result = self.uint_bitfield.pack_default

        assert(dut_result == expected_result)

    def test_pack_negative_value(self):
        ''' The `pack` method on a `UintBitfield` should raise an error
        if the `value` argument is less than 0.
        '''
        value = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('UintBitfield: The value passed to pack should not be '
             'negative.'),
            self.uint_bitfield.pack,
            value,
        )

    def test_pack_invalid_value(self):
        ''' The `pack` method on a `UintBitfield` should raise an error if the
        `value` argument is too large.
        '''
        value_upper_bound = 2**self.args['bit_length']
        value = random.randrange(value_upper_bound, value_upper_bound+100)

        self.assertRaisesRegex(
            ValueError,
            ('UintBitfield: Value requires too many bits. This bitfield has '
             'a bit length of ' + str(self.args['bit_length']) + '.'),
            self.uint_bitfield.pack,
            value,
        )

    def test_pack_non_restricted_value(self):
        ''' The `pack` method on a `UintBitfield` should raise an error if the
        `value` argument is too large.
        '''
        self.args['bit_length'] = random.randrange(4, 17)
        valid_upper_bound = 2**self.args['bit_length']

        self.args['restricted_values'] = (
            random.sample(range(valid_upper_bound), 10))
        self.args['default_value'] = self.args['restricted_values'][0]

        value = self.args['restricted_values'].pop()

        self.uint_bitfield = UintBitfield(**self.args)

        self.assertRaisesRegex(
            ValueError,
            ('UintBitfield: The value passed to pack is not permitted '
             'in this bitfield.'),
            self.uint_bitfield.pack,
            value,
        )

    def test_pack(self):
        ''' The `pack` method on a `UintBitfield` should return the
        `value` argument shifted by the bitfield offset.
        '''

        # UintBitfield has no restricted values
        # =====================================
        value_upper_bound = 2**self.uint_bitfield.bit_length
        value = random.randrange(0, value_upper_bound)

        expected_result = value << self.args['offset']
        dut_result = self.uint_bitfield.pack(value)

        assert(dut_result == expected_result)

        # UintBitfield has restricted values
        # ==================================
        self.args['bit_length'] = random.randrange(4, 17)
        valid_upper_bound = 2**self.args['bit_length']

        self.args['restricted_values'] = (
            random.sample(range(valid_upper_bound), 10))
        self.args['default_value'] = self.args['restricted_values'][0]

        self.uint_bitfield = UintBitfield(**self.args)

        value = self.args['restricted_values'][-1]

        expected_result = value << self.args['offset']
        dut_result = self.uint_bitfield.pack(value)

        assert(dut_result == expected_result)


    def test_unpack(self):
        ''' The `unpack` method on a `UintBitfield` should extract the
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
            dut_value = self.uint_bitfield.unpack(word)

            assert(dut_value == expected_value)

class TestBoolBitfield(KeaTestCase):

    def setUp(self):

        self.args = {
            'offset': random.randrange(0, 129),
        }

        self.bool_bitfield = BoolBitfield(**self.args)

    def test_negative_offset(self):
        ''' The `BoolBitfield` should raise an error if the `offset` is less
        than 0.
        '''

        self.args['offset'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('BoolBitfield: offset should not be negative.'),
            BoolBitfield,
            **self.args
        )

    def test_invalid_default_value(self):
        ''' The `BoolBitfield` should raise an error if the `default_value` is
        not valid for a boolean bitfield.
        '''

        self.args['default_value'] = random.randrange(2, 100)

        self.assertRaisesRegex(
            ValueError,
            ('BoolBitfield: default_value should be one of ' +
             ', '.join([str(v) for v in VALID_BOOLEAN_VALUES]) + '.'),
            BoolBitfield,
            **self.args,
        )

    def test_offset(self):
        ''' The `offset` property on a `BoolBitfield` should return the
        offset specified at initialisation of that `BoolBitfield`.
        '''

        assert(self.bool_bitfield.offset == self.args['offset'])

    def test_bit_length(self):
        ''' The `bit_length` property on a `BoolBitfield` should return 1.
        '''

        assert(self.bool_bitfield.bit_length == 1)

    def test_index_upper_bound(self):
        ''' The `index_upper_bound` property on a `BoolBitfield` should
        return the upper bound bit index of the bitfield.
        '''

        expected_index_upper_bound = self.args['offset'] + 1

        assert(
            self.bool_bitfield.index_upper_bound ==
            expected_index_upper_bound)

    def test_default_value(self):
        ''' The `default_value` property on a `BoolBitfield` should return the
        default value specified at initialisation of that `BoolBitfield`.
        '''
        self.args['default_value'] = random.randrange(2)
        self.bool_bitfield = BoolBitfield(**self.args)

        assert(self.bool_bitfield.default_value == self.args['default_value'])

    def test_pack_default(self):
        ''' The `pack_default` method on a `BoolBitfield` should return the
        `default_value` specified at initialisation of that `BoolBitfield`
        shifted by the bitfield offset.
        '''
        self.args['default_value'] = random.randrange(2)

        self.bool_bitfield = BoolBitfield(**self.args)

        expected_result = self.args['default_value'] << self.args['offset']
        dut_result = self.bool_bitfield.pack_default

        assert(dut_result == expected_result)


    def test_pack_invalid_value(self):
        ''' The `pack` method on a `BoolBitfield` should raise an error
        if the `value` argument is not valid for a boolean bitfield.
        '''
        value = random.randrange(2, 100)

        self.assertRaisesRegex(
            ValueError,
            ('BoolBitfield: The value passed to pack should be one of ' +
             ', '.join([str(v) for v in VALID_BOOLEAN_VALUES]) + '.'),
            self.bool_bitfield.pack,
            value,
        )

    def test_pack_boolean(self):
        ''' The `pack` method on a `BoolBitfield` should return the boolean
        `value` shifted by the bitfield offset.
        '''
        value = True

        expected_result = value << self.args['offset']
        dut_result = self.bool_bitfield.pack(value)

        assert(dut_result == expected_result)

        value = False

        expected_result = value << self.args['offset']
        dut_result = self.bool_bitfield.pack(value)

        assert(dut_result == expected_result)

    def test_pack_uint(self):
        ''' The `pack` method on a `BoolBitfield` should return the uint
        `value` shifted by the bitfield offset.
        '''
        value = 1

        expected_result = value << self.args['offset']
        dut_result = self.bool_bitfield.pack(value)

        assert(dut_result == expected_result)

        value = 0

        expected_result = value << self.args['offset']
        dut_result = self.bool_bitfield.pack(value)

        assert(dut_result == expected_result)

    def test_unpack(self):
        ''' The `unpack` method on a `BoolBitfield` should extract the
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
            dut_value = self.bool_bitfield.unpack(word)

            assert(dut_value == expected_value)

