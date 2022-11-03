import random

from kea.test_utils import KeaTestCase, random_string_generator

from ._bitfield_map import BitfieldMap

def random_bitfield_map(n_available_bits, n_bitfields):
    ''' Generates `n_bitfields` which will fit within `n_available_bits`.

    This function will raise a ValueError if `n_bitfields` is too large for
    `n_available_bits` or if `n_bitfields` is an invalid number.
    '''

    if n_bitfields > n_available_bits:
        raise ValueError(
            'n_bitfields must be less than or equal to n_available_bits')

    if n_bitfields <= 0:
        raise ValueError('n_bitfields must be greater than 0')

    # Select random offsets within the available range
    offsets = random.sample(range(n_available_bits), n_bitfields)
    offsets.sort()

    expected_bitfields = {}
    bitfield_map = BitfieldMap()

    for n in range(n_bitfields):

        # Create a random name for the bitfield
        bitfield_name = random_string_generator(random.randrange(6, 12))

        if random.random() < 0.1:
            # Make it a 1 bit bitfield
            bit_length = 1

        else:
            # Determine the number of bits available before the next offset
            if n == n_bitfields-1:
                gap = n_available_bits - offsets[n]
            else:
                gap = offsets[n+1] - offsets[n]

            # Select a random bit length that can fit in the space available
            # before the next offset
            bit_length = random.randrange(1, gap + 1)

        bitfield_map.add_bitfield(bitfield_name, offsets[n], bit_length)

        expected_bitfields[bitfield_name] = {
            'offset': offsets[n],
            'bit_length': bit_length,
        }

    return bitfield_map, expected_bitfields

def generate_random_bitfield_values(bitfield_map, n_bitfields=None):
    ''' Generates random and valid bitfield values for BitfieldMap.pack().
    '''

    if n_bitfields is None:
        # Pick a random selection of bitfields to receive a value
        n_bitfields = random.randrange(1, bitfield_map.n_bitfields+1)

    bitfields = random.sample(bitfield_map.bitfield_names, n_bitfields)

    bitfield_values = {}

    for bitfield in bitfields:
        # Generate a valid random value for each bitfield
        val_upper_bound = 2**bitfield_map.bitfield_bit_length(bitfield)
        val = random.randrange(val_upper_bound)

        bitfield_values[bitfield] = val

    return bitfield_values

class TestBitfieldMap(KeaTestCase):

    def setUp(self):

        self.bitfield_map, self.expected_bitfields = (
            random_bitfield_map(32, 4))

    def test_repeated_bitfield_name(self):
        ''' The `add_bitfield` method on the `BitfieldMap` should raise an
        error if the specified `name` already exists.
        '''

        repeated_name = random.choice(list(self.expected_bitfields.keys()))
        offset = 0
        bit_length = 1

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldMap.add_bitfield: Cannot create bitfield as ' +
             repeated_name + ' already exists. Please use another name.'),
            self.bitfield_map.add_bitfield,
            repeated_name,
            offset,
            bit_length,
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
        overlapped_upper_bound_index = (
            overlapped_offset + overlapped_bit_length)

        overlapping_name = random_string_generator(random.randrange(3, 12))
        overlapping_bit_length = 1

        # Overlapping the lower index
        # ===========================
        overlapping_offset = overlapped_offset

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldMap.add_bitfield: Cannot create bitfield as the '
             'requested range overlaps the ' + overlapped + ' bitfield.'),
            self.bitfield_map.add_bitfield,
            overlapping_name,
            overlapping_offset,
            overlapping_bit_length,
        )

        # Overlapping the upper index
        # ===========================
        overlapping_offset = overlapped_upper_bound_index - 1

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldMap.add_bitfield: Cannot create bitfield as the '
             'requested range overlaps the ' + overlapped + ' bitfield.'),
            self.bitfield_map.add_bitfield,
            overlapping_name,
            overlapping_offset,
            overlapping_bit_length,
        )

        # Overlapping a random bit in the bitfield
        # =======================================
        overlapping_offset = (
            random.randrange(overlapped_offset, overlapped_upper_bound_index))

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldMap.add_bitfield: Cannot create bitfield as the '
             'requested range overlaps the ' + overlapped + ' bitfield.'),
            self.bitfield_map.add_bitfield,
            overlapping_name,
            overlapping_offset,
            overlapping_bit_length,
        )


    def test_bitfield_offset(self):
        ''' The `bitfield_offset` method on the `BitfieldMap` should return
        the offset of the specified bitfield.
        '''

        for bitfield in self.expected_bitfields.keys():
            dut_offset = self.bitfield_map.bitfield_offset(bitfield)
            expected_offset = self.expected_bitfields[bitfield]['offset']

            assert(dut_offset == expected_offset)

    def test_bitfield_bit_length(self):
        ''' The `bitfield_bit_length` method on the `BitfieldMap` should
        return the bit length of the specified bitfield.
        '''

        for bitfield in self.expected_bitfields.keys():
            dut_bit_length = self.bitfield_map.bitfield_bit_length(bitfield)
            expected_bit_length = (
                self.expected_bitfields[bitfield]['bit_length'])

            assert(dut_bit_length == expected_bit_length)

    def test_bitfield_upper_bound_index(self):
        ''' The `bitfield_upper_bound_index` method on the `BitfieldMap`
        should return the upper bound bit index within the data word assigned
        to the specified bitfield.
        '''

        for bitfield in self.expected_bitfields.keys():
            dut_upper_bound_index = (
                self.bitfield_map.bitfield_upper_bound_index(bitfield))
            expected_upper_bound_index = (
                self.expected_bitfields[bitfield]['offset'] +
                self.expected_bitfields[bitfield]['bit_length'])

            assert(dut_upper_bound_index == expected_upper_bound_index)

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

        assert(dut_names == expected_names)

    def test_data_word_bit_length(self):
        ''' The `data_word_bit_length` property on the `BitfieldMap` should
        return the number of bits required by the full set of bitfields.
        '''

        bitfield_upper_bounds = []
        for bitfield in self.expected_bitfields.keys():
            bitfield_upper_bounds.append(
                self.expected_bitfields[bitfield]['offset'] +
                self.expected_bitfields[bitfield]['bit_length'])

        expected_bit_length = max(bitfield_upper_bounds)
        dut_data_word_bit_length = self.bitfield_map.data_word_bit_length

        assert(dut_data_word_bit_length == expected_bit_length)

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

    def test_abutting_bitfields(self):
        ''' It should be possible to add abutting bit fields. Ie it is not
        necessary to have a gap between bitfields.
        '''

        offset = self.bitfield_map.data_word_bit_length

        for n in range(4):
            name = random_string_generator(random.randrange(3, 12))
            bit_length = random.randrange(1, 10)

            try:
                # Add the bitfield in the next free index
                self.bitfield_map.add_bitfield(name, offset, bit_length)
            except:
                self.fail("Exception raised")

            # Increase the offset by the bit length
            offset += bit_length

    def test_pack_invalid_bitfield_values(self):
        ''' The `pack` method on the `BitfieldMap` should raise an error if
        the `bitfield_values` argument is not a `dict`.
        '''

        bitfield_values = random.randrange(0, 100)

        self.assertRaisesRegex(
            TypeError,
            ('BitfieldMap.pack: bitfield_values should be a dictionary.'),
            self.bitfield_map.pack,
            bitfield_values,
        )

    def test_pack_invalid_bitfield_name(self):
        ''' The `pack` method on the `BitfieldMap` should raise an error if
        the `bitfield_values` argument contains a value for a bitfield which
        doesn't exist.
        '''

        bitfield_values = generate_random_bitfield_values(self.bitfield_map)

        # Select a random bitfield to give an invalid name
        bitfield_to_invalidate = random.choice(list(bitfield_values.keys()))
        invalid_name = random_string_generator(4)

        # Replace a valid name with an invalid name
        bitfield_values[invalid_name] = (
            bitfield_values.pop(bitfield_to_invalidate))

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldMap.pack: bitfield_values contains a value for '
             'a bitfield which is not included in this map. The '
             'invalid bitfield is ' + invalid_name + '.'),
            self.bitfield_map.pack,
            bitfield_values,
        )

    def test_pack_negative_value(self):
        ''' The `pack` method on the `BitfieldMap` should raise an error if
        the `bitfield_values` argument contains a value which is negative.
        '''

        bitfield_values = generate_random_bitfield_values(self.bitfield_map)

        # Select a random bitfield to give a negative number
        bitfield_to_invalidate = random.choice(list(bitfield_values.keys()))
        invalid_val = random.randrange(-100, 0)

        # Give one bitfield an invalid value
        bitfield_values[bitfield_to_invalidate] = invalid_val

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldMap.pack: All bitfield values must be greater '
             'than 0. The specified value for the ' + bitfield_to_invalidate +
             ' bitfield is ' + str(invalid_val) + '.'),
            self.bitfield_map.pack,
            bitfield_values,
        )

    def test_pack_invalid_value(self):
        ''' The `pack` method on the `BitfieldMap` should raise an error if
        the `bitfield_values` argument contains a value which is too large for
        the bitfield length.
        '''

        bitfield_values = generate_random_bitfield_values(self.bitfield_map)

        # Select a random bitfield to give a negative number
        bitfield_to_invalidate = random.choice(list(bitfield_values.keys()))
        bitfield_to_invalidate_val_upper_bound = (
            2**self.expected_bitfields[bitfield_to_invalidate]['bit_length'])
        invalid_val = (
            random.randrange(
                bitfield_to_invalidate_val_upper_bound,
                bitfield_to_invalidate_val_upper_bound+100))

        # Give one bitfield an invalid value
        bitfield_values[bitfield_to_invalidate] = invalid_val

        self.assertRaisesRegex(
            ValueError,
            ('BitfieldMap.pack: The value specified for the ' +
             bitfield_to_invalidate + ' bitfield is too large. The specified '
             'value is ' + str(invalid_val) + ' but the upper bound on '
             'the value for this bitfield is ' +
             str(bitfield_to_invalidate_val_upper_bound) + '.'),
            self.bitfield_map.pack,
            bitfield_values,
        )

    def test_pack_all_bitfields(self):
        ''' The `pack` method on the `BitfieldMap` should pack all values in
        the `bitfield_values` argument into their assigned bitfields and then
        return the resultant word.

        Any bitfields not included in bitfield_values should have a value of
        0.
        '''

        bitfield_values = (
            generate_random_bitfield_values(
                self.bitfield_map, n_bitfields=self.bitfield_map.n_bitfields))

        dut_packed_word = self.bitfield_map.pack(bitfield_values)

        expected_packed_word = 0
        for bitfield in bitfield_values.keys():
            expected_packed_word |= (
                bitfield_values[bitfield] <<
                self.expected_bitfields[bitfield]['offset'])

        assert(dut_packed_word == expected_packed_word)

    def test_pack_one_bitfield(self):
        ''' The `pack` method should function correctly when a value is passed
        for a single bitfield.
        '''

        bitfield_values = (
            generate_random_bitfield_values(self.bitfield_map, n_bitfields=1))

        dut_packed_word = self.bitfield_map.pack(bitfield_values)

        expected_packed_word = 0
        for bitfield in bitfield_values.keys():
            expected_packed_word |= (
                bitfield_values[bitfield] <<
                self.expected_bitfields[bitfield]['offset'])

        assert(dut_packed_word == expected_packed_word)

    def test_pack_random_n_bitfields(self):
        ''' The `pack` method should function correctly when a value is passed
        for a arbitrary subset of the available bitfields.
        '''

        bitfield_values = (
            generate_random_bitfield_values(self.bitfield_map))

        dut_packed_word = self.bitfield_map.pack(bitfield_values)

        expected_packed_word = 0
        for bitfield in bitfield_values.keys():
            expected_packed_word |= (
                bitfield_values[bitfield] <<
                self.expected_bitfields[bitfield]['offset'])

        assert(dut_packed_word == expected_packed_word)
