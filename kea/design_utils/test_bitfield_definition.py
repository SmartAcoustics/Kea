import random

from kea.test_utils import KeaTestCase

from ._bitfield_definition import BitfieldDefinition

class TestBitfieldDefinition(KeaTestCase):

    def setUp(self):

        self.offset = random.randrange(0, 129)
        self.bit_length = random.randrange(1, 129)

        self.bitfield_definition = (
            BitfieldDefinition(self.offset, self.bit_length))

    def test_negative_offset(self):
        ''' The `BitfieldDefinition` should raise an error if the `offset` is
        less than 0.
        '''

        offset = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldDefinition: offset cannot be negative.'),
            BitfieldDefinition,
            offset,
            self.bit_length,
        )

    def test_invalid_bit_length(self):
        ''' The `BitfieldDefinition` should raise an error if the `bit_length`
        is less than or equal to 0.
        '''

        bit_length = 0

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldDefinition: bit_length should be greater than 0.'),
            BitfieldDefinition,
            self.offset,
            bit_length,
        )

        bit_length = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldDefinition: bit_length should be greater than 0.'),
            BitfieldDefinition,
            self.offset,
            bit_length,
        )

    def test_offset(self):
        ''' The `offset` property on a `BitfieldDefinition` should return the
        offset specified at initialisation of that `BitfieldDefinition`.
        '''

        assert(self.bitfield_definition.offset == self.offset)

    def test_bit_length(self):
        ''' The `bit_length` property on a `BitfieldDefinition` should return
        the bit length specified at initialisation of that
        `BitfieldDefinition`.
        '''

        assert(self.bitfield_definition.bit_length == self.bit_length)

    def test_upper_bound_index(self):
        ''' The `upper_bound_index` property on a `BitfieldDefinition` should
        return the upper bound bit index of the bitfield.
        '''

        expected_upper_bound_index = self.offset + self.bit_length

        assert(
            self.bitfield_definition.upper_bound_index ==
            expected_upper_bound_index)

    def test_pack_negative_value(self):
        ''' The `pack` method on a `BitfieldDefinition` should raise an error
        if the `value` argument is less than 0.
        '''
        value = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldDefinition: values passed to pack should be greater '
             'than or equal to 0.'),
            self.bitfield_definition.pack,
            value,
        )

    def test_pack_invalid_value(self):
        ''' The `pack` method on a `BitfieldDefinition` should raise an error
        if the `value` argument is too large.
        '''
        value_upper_bound = 2**self.bitfield_definition.bit_length
        value = random.randrange(value_upper_bound, value_upper_bound+100)

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldDefinition: Value is too large. This bitfield has '
             'a value upper bound of ' + str(value_upper_bound) + '.'),
            self.bitfield_definition.pack,
            value,
        )

    def test_pack(self):
        ''' The `pack` method on a `BitfieldDefinition` should return the
        `value` argument shifted by the bitfield offset.
        '''
        value_upper_bound = 2**self.bitfield_definition.bit_length
        value = random.randrange(0, value_upper_bound)

        expected_result = value << self.offset
        dut_result = self.bitfield_definition.pack(value)

        assert(dut_result == expected_result)
