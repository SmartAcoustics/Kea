import random

import unittest

from math import ceil

from kea.testing.test_utils import KeaTestCase, random_string_generator

from .bitfield_definitions import UintBitfield
from .test_bitfield_map import random_bitfield_definitions
from .register_definition import RegisterDefinition
from .register_map import RegisterMap

def random_register_definitions(
    register_bit_width, n_registers, addressable_location_bit_width):
    ''' Generate register_definitions containing `n_registers` which all have
    a bit width which is less than or equal to `register_bit_width`
    '''

    register_definitions = {}

    n_registers_upper_bound = 1025

    assert(n_registers < n_registers_upper_bound)

    # Calculate how many memory addresses each register occupies
    n_addresses_per_register = ceil(
        register_bit_width/addressable_location_bit_width)

    # Generate random offsets
    offset_multipliers = (
        random.sample(range(n_registers_upper_bound), n_registers))
    offsets = [n_addresses_per_register*x for x in offset_multipliers]

    for n in range(n_registers):

        # Select n_bitfields for each register
        n_bitfields = random.randrange(1, ceil(register_bit_width/2)+1)

        # Generate random bitfield definitions
        bitfield_definitions, _expected_bitfields = (
            random_bitfield_definitions(register_bit_width, n_bitfields))

        # Generate a register
        register = RegisterDefinition(offsets[n], bitfield_definitions)

        # Create a random name for the register
        register_name = random_string_generator(random.randrange(6, 12))

        # Add the register to the register_definitions
        register_definitions[register_name] = register

    return register_definitions

class RegisterMapSimulationMixIn(object):

    def setUp(self):

        register_definitions = (
            random_register_definitions(
                self.register_bit_width,
                self.n_registers,
                self.addressable_location_bit_width))

        self.args = {
            'register_bit_width': self.register_bit_width,
            'register_definitions': register_definitions,
            'addressable_location_bit_width': (
                self.addressable_location_bit_width),
        }

        self.register_map = RegisterMap(**self.args)

    def test_invalid_register_bit_width(self):
        ''' The `RegisterMap` should raise an error if the
        `register_bit_width` is less than or equal to 0.
        '''

        self.args['register_bit_width'] = 0

        self.assertRaisesRegex(
            ValueError,
            ('RegisterMap: register_bit_width should be a greater than 0.'),
            RegisterMap,
            **self.args,
        )

        self.args['register_bit_width'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('RegisterMap: register_bit_width should be a greater than 0.'),
            RegisterMap,
            **self.args,
        )

    def test_non_power_of_two_register_bit_width(self):
        ''' The `RegisterMap` should raise an error if the
        `register_bit_width` is not a power of 2.
        '''

        bit_width = random.randrange(1, 129)

        if bit_width == 1:
            # Bit width is a power of 2 and incrementing by 1 will give
            # another power of 2 so increment it by 2
            bit_width += 2

        elif (bit_width & (bit_width-1)) == 0:
            # Bit width is a power of two so increment by 1
            bit_width += 1

        self.args['register_bit_width'] = bit_width

        self.assertRaisesRegex(
            ValueError,
            ('RegisterMap: register_bit_width should be a power of 2.'),
            RegisterMap,
            **self.args,
        )

    def test_invalid_register_definitions(self):
        ''' The `RegisterMap` should raise an error if the
        `register_definitions` is not a `dict`.
        '''

        self.args['register_definitions'] = random.randrange(0, 100)

        self.assertRaisesRegex(
            TypeError,
            ('RegisterMap: register_definitions should be a dict.'),
            RegisterMap,
            **self.args,
        )

    def test_invalid_addressable_location_bit_width(self):
        ''' The `RegisterMap` should raise an error if the
        `addressable_location_bit_width` is less than 8.
        '''

        self.args['addressable_location_bit_width'] = random.randrange(1, 8)

        self.assertRaisesRegex(
            ValueError,
            ('RegisterMap: addressable_location_bit_width should be '
             'greater than or equal to 8.'),
            RegisterMap,
            **self.args,
        )

        self.args['addressable_location_bit_width'] = 0

        self.assertRaisesRegex(
            ValueError,
            ('RegisterMap: addressable_location_bit_width should be '
             'greater than or equal to 8.'),
            RegisterMap,
            **self.args,
        )

        self.args['addressable_location_bit_width'] = (
            random.randrange(-100, 0))

        self.assertRaisesRegex(
            ValueError,
            ('RegisterMap: addressable_location_bit_width should be '
             'greater than or equal to 8.'),
            RegisterMap,
            **self.args,
        )

    def test_non_power_of_two_addressable_location_bit_width(self):
        ''' The `RegisterMap` should raise an error if the
        `addressable_location_bit_width` is not a power of 2.
        '''

        bit_width = random.randrange(8, 129)

        if (bit_width & (bit_width-1)) == 0:
            # Bit width is a power of two so increment by 1
            bit_width += 1

        self.args['addressable_location_bit_width'] = bit_width

        self.assertRaisesRegex(
            ValueError,
            ('RegisterMap: addressable_location_bit_width should be a '
             'power of 2.'),
            RegisterMap,
            **self.args,
        )

    def test_invalid_register_definition(self):
        ''' The `RegisterMap` should raise an error if any entry in the
        `register_definitions` is not a sub-class of `RegisterDefinition`.
        '''

        # Pick a random register and set it to the wrong type
        register = random.choice(
            list(self.args['register_definitions'].keys()))
        self.args['register_definitions'][register] = random.randrange(0, 100)

        self.assertRaisesRegex(
            TypeError,
            ('RegisterMap: All registers in register_definitions '
             'should be an instance of RegisterDefinition.'),
            RegisterMap,
            **self.args,
        )

    def test_invalid_register_offset(self):
        ''' The `RegisterMap` should raise an error if a register in
        `register_definitions` contains a register with an offset which is not
        a multiple of the number of addresses per register.

        For example, if the `register_bit_width` is 32 and
        `addressable_location_bit_width` is 8 then each register occupies 4
        memory addresses. In which case, the register offsets should be
        multiples of 4.
        '''

        # Calculate how many memory addresses each register occupies
        n_addresses_per_register = ceil(
            self.args['register_bit_width']/
            self.args['addressable_location_bit_width'])

        if n_addresses_per_register == 1:
            # If n_addresses_per_register is 1 then all offsets are valid so
            # we cannot run this test.
            return None

        # Pick a random register
        register = random.choice(
            list(self.args['register_definitions'].keys()))

        # Generate random bitfield definitions
        bitfield_definitions, _expected_bitfields = (
            random_bitfield_definitions(self.args['register_bit_width'], 1))

        # Generate a random offset
        offset = random.randrange(1025)
        if offset % n_addresses_per_register == 0:
            # If the offset is a multiple of n_addresses_per_register
            # increment by 1.
            offset += 1

        # Generate a register
        self.args['register_definitions'][register] = (
            RegisterDefinition(offset, bitfield_definitions))

        self.assertRaisesRegex(
            ValueError,
            ('RegisterMap: Register offsets should be a multiple of '
             'the number of addresses occupied by each register.'),
            RegisterMap,
            **self.args,
        )

    def test_register_with_invalid_bit_length(self):
        ''' The `RegisterMap` should raise an error if a register in
        `register_definitions` contains a register with a `bit_length` which
        is greater than the `register_bit_width` specified when the
        `RegisterMap` was instantiated.
        '''

        # Pick a random register
        register = random.choice(
            list(self.args['register_definitions'].keys()))

        # Pick an invalid register bitwidth
        invalid_register_bitwidth = (
            random.randrange(
                self.args['register_bit_width']+1,
                self.args['register_bit_width']+100))

        # Generate a bitfield definition with the invalid bit length
        bitfield_definitions = {
            random_string_generator(4): (
                UintBitfield(offset=0, bit_length=invalid_register_bitwidth))}

        # Generate the register definitions
        register_offset = self.args['register_definitions'][register].offset
        self.args['register_definitions'][register] = (
            RegisterDefinition(register_offset, bitfield_definitions))

        self.assertRaisesRegex(
            ValueError,
            ('RegisterMap: Register ' + register + ' is too wide '
             'for the specified register_bit_width.'),
            RegisterMap,
            **self.args,
        )

    def test_repeated_offset(self):
        ''' The `RegisterMap` should raise an error if two registers in
        `register_definitions` have the same offset.
        '''

        # Pick two registers
        reg_0, reg_1 = random.sample(
            list(self.args['register_definitions'].keys()), 2)

        # Extract the offset from reg_0
        offset = self.args['register_definitions'][reg_0].offset

        # Generate random bitfields
        bitfield_definitions, _expected_bitfields = (
            random_bitfield_definitions(self.args['register_bit_width'], 1))

        # Update reg_1 in the register definitions with the same offset as
        # reg_0
        self.args['register_definitions'][reg_1] = (
            RegisterDefinition(offset, bitfield_definitions))

        self.assertRaisesRegex(
            ValueError,
            ('RegisterMap: Register offsets should be unique.'),
            RegisterMap,
            **self.args,
        )

    def test_register_invalid_register_name(self):
        ''' The `register` method on `RegisterMap` should raise an error if
        `register_name` is not the name of a register in the map.
        '''

        register_name = random_string_generator(4)

        self.assertRaisesRegex(
            ValueError,
            ('RegisterMap: The requested register is not included in this '
             'map.'),
            self.register_map.register,
            register_name,
        )

    def test_register(self):
        ''' The `register` method on `RegisterMap` should return the register
        specified by `register_name`.
        '''

        register_name = (
            random.choice(list(self.args['register_definitions'].keys())))

        # Use offset as the parameter to check to make sure the DUT has
        # returned the correct offset.
        dut_offset = self.register_map.register(register_name).offset
        expected_offset = (
            self.args['register_definitions'][register_name].offset)

        assert(dut_offset == expected_offset)

    def test_n_registers(self):
        ''' The `n_registers` method on `RegisterMap` should return the number
        of registers in the register map.
        '''

        dut_n_registers = self.register_map.n_registers
        expected_n_registers = len(self.args['register_definitions'])

        assert(dut_n_registers == expected_n_registers)

    def test_register_names(self):
        ''' The `register_names` method on `RegisterMap` should return a list
        containing the names of the registers in the register map.
        '''

        dut_register_names = self.register_map.register_names
        expected_register_names = (
            list(self.args['register_definitions'].keys()))

        dut_register_names.sort()
        expected_register_names.sort()

        assert(dut_register_names == expected_register_names)

    def test_register_bit_width(self):
        ''' The `register_bit_width` method on `RegisterMap` should return the
        bit width of the registers in the register map.
        '''

        dut_register_bit_width = self.register_map.register_bit_width
        expected_register_bit_width = self.args['register_bit_width']

        assert(dut_register_bit_width == expected_register_bit_width)

    def test_abutting_registers(self):
        ''' It should be possible to add abutting registers. Ie it is not
        necessary to have a gap between registers.
        '''

        # Calculate how many memory addresses each register occupies
        n_addresses_per_register = ceil(
            self.args['register_bit_width']/
            self.args['addressable_location_bit_width'])

        register_definitions = {}
        offset = 0

        for n in range(4):

            bitfield_name = random_string_generator(random.randrange(3, 12))
            bitfield_definitions = {
                bitfield_name: (
                    UintBitfield(0, self.args['register_bit_width']))}

            reg_name = random_string_generator(random.randrange(3, 12))
            register_definitions[reg_name] = (
                RegisterDefinition(
                    offset, bitfield_definitions))

            # Increment the offset
            offset += n_addresses_per_register

        self.args['register_definitions'] = register_definitions

        # Create the register map
        register_map = RegisterMap(**self.args)

        expected_offset = 0

        for register_name in list(register_definitions.keys()):
            dut_offset = register_map.register(register_name).offset

            assert(dut_offset == expected_offset)

            expected_offset += n_addresses_per_register

class TestRegisterMap(RegisterMapSimulationMixIn, KeaTestCase):
    n_registers = 16
    register_bit_width = 32
    addressable_location_bit_width = 8

class TestRandomRegisterMap(RegisterMapSimulationMixIn, KeaTestCase):
    n_registers = 16
    register_bit_width = 2**(random.randrange(8))
    addressable_location_bit_width = 2**(random.randrange(3, 8))

class TestEmptyRegisterMap(RegisterMapSimulationMixIn, KeaTestCase):
    n_registers = 0
    register_bit_width = 2**(random.randrange(8))
    addressable_location_bit_width = 2**(random.randrange(3, 8))

    @unittest.skip("Cannot run this test with an empty register defintions.")
    def test_register():
        pass

    @unittest.skip("Cannot run this test with an empty register defintions.")
    def test_repeated_offset():
        pass

    @unittest.skip("Cannot run this test with an empty register defintions.")
    def test_register_with_invalid_bit_length():
        pass

    @unittest.skip("Cannot run this test with an empty register defintions.")
    def test_invalid_register_definition():
        pass
