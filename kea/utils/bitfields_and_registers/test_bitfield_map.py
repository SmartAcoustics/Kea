import random
import unittest

from kea.testing.test_utils import KeaTestCase, random_string_generator

from .bitfield_definitions import UintBitfield, BoolBitfield
from .constant_bitfield_definitions import (
    ConstantUintBitfield, ConstantBoolBitfield)
from .bitfield_map import BitfieldMap

def random_bitfield_definitions(n_available_bits, n_bitfields):
    ''' Generates a bitfield_definitions dict with `n_bitfields` which will
    fit within `n_available_bits`.

    This function will raise a ValueError if `n_bitfields` is too large for
    `n_available_bits` or if `n_bitfields` is an invalid number.
    '''

    if n_bitfields > n_available_bits:
        raise ValueError(
            'n_bitfields must be less than or equal to n_available_bits')

    if n_bitfields < 0:
        raise ValueError('n_bitfields must be greater than or equal to 0')

    # Select random offsets within the available range
    offsets = random.sample(range(n_available_bits), n_bitfields)
    offsets.sort()

    expected_bitfields = {}

    for n in range(n_bitfields):

        # Create a random name for the bitfield
        bitfield_name = random_string_generator(random.randrange(6, 12))

        expected_bitfields[bitfield_name] = {}

        if random.random() < 0.5:
            # Make it a boolean bitfield
            expected_bitfields[bitfield_name]['type'] = 'bool'
            expected_bitfields[bitfield_name]['bit_length'] = 1

        else:
            # Make is a uint bitfield
            expected_bitfields[bitfield_name]['type'] = 'uint'

            if random.random() < 0.1:
                # Make a small number of uint bitfields 1 bit long
                bit_length = 1

            else:
                # Determine the number of bits available before the next
                # offset
                if n == n_bitfields-1:
                    gap = n_available_bits - offsets[n]
                else:
                    gap = offsets[n+1] - offsets[n]

                # Select a random bit length that can fit in the space
                # available before the next offset
                bit_length = random.randrange(1, gap + 1)

            # Add the bitlength
            expected_bitfields[bitfield_name]['bit_length'] = bit_length

        if random.random() < 0.5:
            # Give the bitfield a random value
            val = random.randrange(
                2**expected_bitfields[bitfield_name]['bit_length'])
        else:
            val = 0

        if random.random() < 0.5:
            # Make it a constant bitfield
            expected_bitfields[bitfield_name]['constant'] = True
            expected_bitfields[bitfield_name]['value'] = val
        else:
            # Make it a variable bitfield
            expected_bitfields[bitfield_name]['constant'] = False
            expected_bitfields[bitfield_name]['default_value'] = val

        # Add the offset
        expected_bitfields[bitfield_name]['offset'] = offsets[n]

    # Extract the expected_bitfields into a list of tuples and then shuffle
    # the order.
    expected_bitfields_items = list(expected_bitfields.items())
    random.shuffle(expected_bitfields_items)

    bitfield_definitions = {}

    for bitfield_name, bitfield_spec in expected_bitfields_items:
        if bitfield_spec['constant']:
            if bitfield_spec['type'] == 'bool':
                bitfield_definitions[bitfield_name] = (
                    ConstantBoolBitfield(
                        bitfield_spec['offset'],
                        bitfield_spec['value']))

            elif bitfield_spec['type'] == 'uint':
                bitfield_definitions[bitfield_name] = (
                    ConstantUintBitfield(
                        bitfield_spec['offset'],
                        bitfield_spec['bit_length'],
                        bitfield_spec['value']))
            else:
                raise TypeError('Unrecognized type')
        else:
            if bitfield_spec['type'] == 'bool':
                bitfield_definitions[bitfield_name] = (
                    BoolBitfield(
                        bitfield_spec['offset'],
                        bitfield_spec['default_value']))

            elif bitfield_spec['type'] == 'uint':
                bitfield_definitions[bitfield_name] = (
                    UintBitfield(
                        bitfield_spec['offset'],
                        bitfield_spec['bit_length'],
                        bitfield_spec['default_value']))

            else:
                raise TypeError('Unrecognized type')

    return bitfield_definitions, expected_bitfields

def generate_random_bitfield_values(bitfield_map, n_bitfields=None):
    ''' Generates random and valid bitfield values for BitfieldMap.pack().
    '''

    variable_bitfields = bitfield_map.variable_bitfield_names
    n_variable_bitfields = len(bitfield_map.variable_bitfield_names)

    if n_variable_bitfields <= 0:
        # There are no variable bitfields in the bitfield map so return an
        # empty dict
        return {}

    if n_bitfields is None:
        # Pick a random selection of bitfields to receive a value
        n_bitfields = random.randrange(1, n_variable_bitfields+1)

    # Pick a random selection of bitfields to get a value
    bitfields = random.sample(variable_bitfields, n_bitfields)

    bitfield_values = {}

    for bitfield_name in bitfields:
        # Generate a valid random value for each bitfield
        bitfield = bitfield_map.bitfield(bitfield_name)
        val_upper_bound = 2**bitfield.bit_length
        val = random.randrange(val_upper_bound)

        bitfield_values[bitfield_name] = val

    return bitfield_values

def generate_expected_packed_word(expected_bitfields, bitfield_values):
    ''' Generates the expected packed word based on `expected_bitfields` and
    `bitfield_values`

    `expected_bitfields` should be the output from
    `random_bitfield_definitions`

    `bitfield_values` should be the output from
    `generate_random_bitfield_values`
    '''

    expected_packed_word = 0

    for bitfield in expected_bitfields.keys():
        if bitfield in bitfield_values:
            expected_packed_word |= (
                bitfield_values[bitfield] <<
                expected_bitfields[bitfield]['offset'])

        else:
            if expected_bitfields[bitfield]['constant']:
                expected_packed_word |= (
                    expected_bitfields[bitfield]['value'] <<
                    expected_bitfields[bitfield]['offset'])

            else:
                expected_packed_word |= (
                    expected_bitfields[bitfield]['default_value'] <<
                    expected_bitfields[bitfield]['offset'])

    return expected_packed_word

class BitfieldMapSimulationMixIn(object):

    def setUp(self):

        self.bitfield_definitions, self.expected_bitfields = (
            random_bitfield_definitions(
                self.n_available_bits, self.n_bitfields))

        # Create the bitfield map
        self.bitfield_map = BitfieldMap(self.bitfield_definitions)

    def test_invalid_bitfield_definitions(self):
        ''' The `BitfieldMap` should raise an error if the
        `bitfield_definitions` is not a `dict`.
        '''

        bitfield_definitions = random.randrange(0, 100)

        self.assertRaisesRegex(
            TypeError,
            ('BitfieldMap: bitfield_definitions should be a dict.'),
            BitfieldMap,
            bitfield_definitions,
        )

    def test_invalid_bitfield_definition(self):
        ''' The `BitfieldMap` should raise an error if any entry in the
        `bitfield_definitions` is not a sub-class of `BitfieldDefinition` or
        `ConstantBitfieldDefinition`.
        '''

        # Pick a random bitfield and set it to the wrong type
        bitfield = random.choice(list(self.bitfield_definitions.keys()))
        self.bitfield_definitions[bitfield] = random.randrange(0, 100)

        self.assertRaisesRegex(
            TypeError,
            ('BitfieldMap: Bitfield should be a sub-class of '
            'BitfieldDefinition or ConstantBitfieldDefinition.'),
            BitfieldMap,
            self.bitfield_definitions,
        )

    def test_overlapping_bitfields(self):
        ''' The `add_bitfield` method on the `BitfieldMap` should raise an
        error if the specified `offset` and `bit_length` overlap a bitfield
        which already exists.
        '''

        overlapped = random.choice(list(self.expected_bitfields.keys()))
        overlapped_offset = self.expected_bitfields[overlapped]['offset']
        overlapped_bit_length = (
            self.expected_bitfields[overlapped]['bit_length'])
        overlapped_index_upper_bound = (
            overlapped_offset + overlapped_bit_length)

        overlapping_name = random_string_generator(random.randrange(3, 12))
        overlapping_bit_length = 1

        # Overlapping the lower index
        # ===========================

        overlapping_offset = overlapped_offset

        self.bitfield_definitions[overlapping_name] = (
            UintBitfield(overlapping_offset, overlapping_bit_length))

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldMap: Overlapping bitfields. The overlapping '
             'bitfields are ' + overlapping_name + ' and ' +
             overlapped + '.'),
            BitfieldMap,
            self.bitfield_definitions,
        )

        # Overlapping the upper index
        # ===========================
        overlapping_offset = overlapped_index_upper_bound - 1

        self.bitfield_definitions[overlapping_name] = (
            UintBitfield(overlapping_offset, overlapping_bit_length))

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldMap: Overlapping bitfields. The overlapping '
             'bitfields are ' + overlapping_name + ' and ' +
             overlapped + '.'),
            BitfieldMap,
            self.bitfield_definitions,
        )

        # Overlapping a random bit in the bitfield
        # ========================================
        overlapping_offset = (
            random.randrange(overlapped_offset, overlapped_index_upper_bound))

        self.bitfield_definitions[overlapping_name] = (
            UintBitfield(overlapping_offset, overlapping_bit_length))

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldMap: Overlapping bitfields. The overlapping '
             'bitfields are ' + overlapping_name + ' and ' +
             overlapped + '.'),
            BitfieldMap,
            self.bitfield_definitions,
        )

    def test_bitfield_map_abutting_bitfields(self):
        ''' It should be possible to add abutting bit fields. Ie it is not
        necessary to have a gap between bitfields.
        '''

        bitfield_definitions = {}

        offset = 0

        for n in range(4):
            name = random_string_generator(random.randrange(3, 12))
            bit_length = random.randrange(1, 10)

            bitfield_definitions[name] = UintBitfield(offset, bit_length)

            # Increase the offset by the bit length
            offset += bit_length

        try:
            # Create the bitfield map
            BitfieldMap(bitfield_definitions)

        except:
            self.fail("Exception raised")

    def test_n_bitfields(self):
        ''' The `n_bitfields` property on the `BitfieldMap` should return the
        number of bitfields in the map.
        '''

        dut_n_bitfields = self.bitfield_map.n_bitfields
        expected_n_bitfields = len(self.expected_bitfields.keys())

        assert(dut_n_bitfields == expected_n_bitfields)

    def test_bitfield_names(self):
        ''' The `bitfield_names` property on the `BitfieldMap` should return
        a list containing the names of all the bitfields in the map.
        '''

        dut_names = self.bitfield_map.bitfield_names
        expected_names = list(self.expected_bitfields.keys())

        dut_names.sort()
        expected_names.sort()

        assert(dut_names == expected_names)

    def test_constant_bitfield_names(self):
        ''' The `constant_bitfield_names` property on the `BitfieldMap` should
        return a list containing the names of all the constant bitfields in
        the map.
        '''

        dut_names = self.bitfield_map.constant_bitfield_names
        expected_names = []
        for bitfield_name in self.expected_bitfields.keys():
            if self.expected_bitfields[bitfield_name]['constant']:
                expected_names.append(bitfield_name)

        dut_names.sort()
        expected_names.sort()

        assert(dut_names == expected_names)

    def test_variable_bitfield_names(self):
        ''' The `variable_bitfield_names` property on the `BitfieldMap` should
        return a list containing the names of all the variable bitfields in
        the map.
        '''

        dut_names = self.bitfield_map.variable_bitfield_names
        expected_names = []
        for bitfield_name in self.expected_bitfields.keys():
            if not self.expected_bitfields[bitfield_name]['constant']:
                expected_names.append(bitfield_name)

        dut_names.sort()
        expected_names.sort()

        assert(dut_names == expected_names)

    def test_bit_length(self):
        ''' The `bit_length` property on the `BitfieldMap` should return the
        number of bits required by the full set of bitfields.
        '''

        bitfield_upper_bounds = []
        for bitfield in self.expected_bitfields.keys():
            bitfield_upper_bounds.append(
                self.expected_bitfields[bitfield]['offset'] +
                self.expected_bitfields[bitfield]['bit_length'])

        if len(self.expected_bitfields) > 0:
            expected_bit_length = max(bitfield_upper_bounds)

        else:
            expected_bit_length = 0

        dut_bit_length = self.bitfield_map.bit_length

        assert(dut_bit_length == expected_bit_length)

    def test_n_assigned_bits(self):
        ''' The `n_assigned_bits` property on the `BitfieldMap` should return
        the number of bits within the data word which have been assigned to a
        bitfield.
        '''

        expected_n_assigned_bits = sum([
            self.expected_bitfields[bitfield]['bit_length']
            for bitfield in self.expected_bitfields.keys()])

        dut_n_assigned_bits = self.bitfield_map.n_assigned_bits

        assert(dut_n_assigned_bits == expected_n_assigned_bits)

    def test_pack_invalid_bitfield_values(self):
        ''' The `pack` method on the `BitfieldMap` should raise an error if
        the `bitfield_values` argument is not a `dict`.
        '''

        bitfield_values = random.randrange(0, 100)

        self.assertRaisesRegex(
            TypeError,
            ('BitfieldMap: bitfield_values should be a dictionary.'),
            self.bitfield_map.pack,
            bitfield_values,
        )

    def test_pack_invalid_bitfield_name(self):
        ''' The `pack` method on the `BitfieldMap` should raise an error if
        the `bitfield_values` argument contains a value for a bitfield which
        doesn't exist.
        '''

        invalid_name = random_string_generator(4)

        bitfield_values = generate_random_bitfield_values(self.bitfield_map)

        bitfield_values[invalid_name] = random.randrange(0, 100)

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldMap: bitfield_values contains a value for a bitfield '
             'which is not included in this map. The invalid bitfield is ' +
             invalid_name + '.'),
            self.bitfield_map.pack,
            bitfield_values,
        )

    def test_pack_constant_bitfield(self):
        ''' The `pack` method on the `BitfieldMap` should raise an error if
        the `bitfield_values` argument contains a value for a constant
        bitfield.
        '''

        if len(self.bitfield_map.constant_bitfield_names) <= 0:
            # There are no constants in the bitfield map so we can't run this
            # test
            return True

        invalid_name = (
            random.choice(self.bitfield_map.constant_bitfield_names))

        bitfield_values = generate_random_bitfield_values(self.bitfield_map)

        bitfield_values[invalid_name] = random.randrange(0, 100)

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldMap: bitfield_values contains a value for a bitfield '
             'which is a constant and so cannot be set.'),
            self.bitfield_map.pack,
            bitfield_values,
        )

    def test_pack_all_variable_bitfields(self):
        ''' The `pack` method on the `BitfieldMap` should pack all values in
        the `bitfield_values` argument into their assigned bitfields and then
        return the resultant word.

        The `pack` method will raise an error if `bitfield_values` contains
        a value for a constant bitfield.

        Any constant bitfields will be included in the resultant word with
        their constant value at the correct offset.

        Any variable bitfields not included in bitfield_values should be
        included in the resultant word with their default value at the correct
        offset.
        '''

        n_variable_bitfields = len(self.bitfield_map.variable_bitfield_names)

        bitfield_values = (
            generate_random_bitfield_values(
                self.bitfield_map, n_bitfields=n_variable_bitfields))

        dut_packed_word = self.bitfield_map.pack(bitfield_values)

        expected_packed_word = (
            generate_expected_packed_word(
                self.expected_bitfields, bitfield_values))

        assert(dut_packed_word == expected_packed_word)

    def test_pack_one_bitfield(self):
        ''' The `pack` method should function correctly when a value is passed
        for a single bitfield.
        '''

        bitfield_values = (
            generate_random_bitfield_values(self.bitfield_map, n_bitfields=1))

        dut_packed_word = self.bitfield_map.pack(bitfield_values)

        expected_packed_word = (
            generate_expected_packed_word(
                self.expected_bitfields, bitfield_values))

        assert(dut_packed_word == expected_packed_word)

    def test_pack_random_n_bitfields(self):
        ''' The `pack` method should function correctly when a value is passed
        for a arbitrary subset of the available bitfields.
        '''

        bitfield_values = (
            generate_random_bitfield_values(self.bitfield_map))

        dut_packed_word = self.bitfield_map.pack(bitfield_values)

        expected_packed_word = (
            generate_expected_packed_word(
                self.expected_bitfields, bitfield_values))

        assert(dut_packed_word == expected_packed_word)

    def test_unpack(self):
        ''' The `unpack` method on the `BitfieldMap` should extract the values
        from each bitfield in the word and return the values in a dict with
        the bitfield names as the keys.
        '''

        word = random.randrange(2**self.bitfield_map.bit_length)

        dut_unpacked_values = self.bitfield_map.unpack(word)

        # Check the DUT unpacked values contains all the bitfields
        assert(dut_unpacked_values.keys() == self.expected_bitfields.keys())

        for bitfield_name in self.expected_bitfields.keys():
            # Extract the expected offset and bit length for each bitfield
            offset = self.expected_bitfields[bitfield_name]['offset']
            bit_length = self.expected_bitfields[bitfield_name]['bit_length']

            # Create a mask to remove all other bitfields
            mask = 2**bit_length-1

            # Shift the word and mask out the other bitfields to get the
            # bitfield value
            expected_unpacked_bitfield = (word >> offset) & mask

            # Check the DUT unpacked values are correct
            assert(
                dut_unpacked_values[bitfield_name] ==
                expected_unpacked_bitfield)

    def test_bitfield_invalid_bitfield_name(self):
        ''' The `bitfield` method on the `BitfieldMap` should raise an error
        if the `bitfield_name` does not exist in the `BitfieldMap`.
        '''

        invalid_name = random_string_generator(4)

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldMap: The requested bitfield is not included in this '
             'map'),
            self.bitfield_map.bitfield,
            invalid_name,
        )

    def test_bitfield(self):
        ''' The `bitfield` method on the `BitfieldMap` should return the
        bitfield specified by `bitfield_name`.
        '''

        for bitfield_name in self.expected_bitfields.keys():
            bitfield = self.bitfield_map.bitfield(bitfield_name)

            dut_offset = bitfield.offset
            expected_offset = self.expected_bitfields[bitfield_name]['offset']

            assert(dut_offset == expected_offset)

            dut_bit_length = bitfield.bit_length
            expected_bit_length = (
                self.expected_bitfields[bitfield_name]['bit_length'])

            assert(dut_bit_length == expected_bit_length)

class TestBitfieldMapNBitfields(BitfieldMapSimulationMixIn, KeaTestCase):
    n_available_bits = 64
    n_bitfields = 32

class TestBitfieldMapOneBitfield(BitfieldMapSimulationMixIn, KeaTestCase):
    n_available_bits = 32
    n_bitfields = 1

class TestBitfieldMapZeroBitfields(BitfieldMapSimulationMixIn, KeaTestCase):
    n_available_bits = 32
    n_bitfields = 0

    @unittest.skip("Cannot run this test with an empty bitfield defintions.")
    def test_overlapping_bitfields():
        pass

    @unittest.skip("Cannot run this test with an empty bitfield defintions.")
    def test_invalid_bitfield_definition():
        pass
