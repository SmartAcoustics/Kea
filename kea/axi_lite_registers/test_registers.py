
from myhdl import Signal, intbv, block, always
import myhdl
from ._registers import Registers, Bitfields

from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)
import random
import string

class TestBitfieldsInterfaceSimulation(KeaTestCase):
    '''The `Bitfields` object should handle its arguments properly and error
    if the arguments are invalid or incompatible.
    '''

    def test_valid_bitfields(self):
        '''For valid bitfields, an interface should be created that includes
        each bitfield as a signal (correctly) and a `register` signal.
        '''

        # A case with a few vals. No need to tightly pack them
        bitfields_config = {
            'length': {'type': 'uint', 'length': 10, 'offset': 0},
            'frobinate': {'type': 'bool', 'offset': 10},
            'range': {'type': 'uint', 'length': 5, 'offset': 25}}

        bf = Bitfields(32, 'axi_read_write', bitfields_config) # OK

        assert(isinstance(bf.length, myhdl._Signal._Signal))
        assert(isinstance(bf.frobinate, myhdl._Signal._Signal))
        assert(isinstance(bf.range, myhdl._Signal._Signal))

        assert(isinstance(bf.length.val, intbv))
        assert(isinstance(bf.frobinate.val, bool))
        assert(isinstance(bf.range.val, intbv))

        assert(bf.length.min == 0)
        assert(bf.length.max == 2**10)

        assert(bf.range.min == 0)
        assert(bf.range.max == 2**5)

        # A register attribute is alwas created
        assert(isinstance(bf.register, myhdl._Signal._Signal))
        assert(isinstance(bf.register.val, intbv))
        assert(bf.register.min == 0)
        assert(bf.register.max == 2**32)

        # Check the write-only case
        bf = Bitfields(48, 'axi_write_only', bitfields_config) # OK

        assert(isinstance(bf.length, myhdl._Signal._Signal))
        assert(isinstance(bf.frobinate, myhdl._Signal._Signal))
        assert(isinstance(bf.range, myhdl._Signal._Signal))

        assert(isinstance(bf.length.val, intbv))
        assert(isinstance(bf.frobinate.val, bool))
        assert(isinstance(bf.range.val, intbv))

        assert(bf.length.min == 0)
        assert(bf.length.max == 2**10)

        assert(bf.range.min == 0)
        assert(bf.range.max == 2**5)

        # A register attribute is alwas created
        assert(isinstance(bf.register, myhdl._Signal._Signal))
        assert(isinstance(bf.register.val, intbv))
        assert(bf.register.min == 0)
        assert(bf.register.max == 2**48)

        bitfields_config['a_const'] = {
            'type': 'const-uint', 'length': 6, 'offset': 13, 'const-value': 22}
        bitfields_config['b_const'] = {
            'type': 'const-bool', 'offset': 19, 'const-value': True}

        # Must be read-only
        bf = Bitfields(32, 'axi_read_only', bitfields_config)

        assert(isinstance(bf.a_const, intbv))
        assert(isinstance(bf.b_const, bool))

        assert(bf.a_const.min == 0)
        assert(bf.a_const.max == 2**6)

        # A register attribute is alwas created
        assert(isinstance(bf.register, myhdl._Signal._Signal))
        assert(isinstance(bf.register.val, intbv))
        assert(bf.register.min == 0)
        assert(bf.register.max == 2**32)

    def test_invalid_bitfield_type(self):
        '''If a bitfield type is invalid, a `ValueError` should be raised.
        '''
        bitfields_config = {
            'length': {'type': 'int', 'length': 10, 'offset': 0}, # invalid!
            'frobinate': {'type': 'bool', 'offset': 10},
            'range': {'type': 'uint', 'length': 5, 'offset': 25}}

        self.assertRaisesRegex(
            ValueError, 'A bitfield type must be one of `uint`, `bool`, '
            '`const-uint` or `const-bool`', Bitfields, 32, 'axi_read_write',
            bitfields_config)

    def test_invalid_bitfield_name_fails(self):
        '''Bitfield names must be valid python identifiers and not begin with
        an underscore.
        '''

        bitfields_config = {
            '*': {'type': 'bool', 'offset': 10}}

        self.assertRaisesRegex(
            ValueError, 'Bitfield names must be valid python identifiers: '
            '*', Bitfields, 32, 'axi_read_write', bitfields_config)

        bitfields_config = {
            '_frobinate': {'type': 'bool', 'offset': 10}}

        self.assertRaisesRegex(
            ValueError, 'Bitfield names cannot begin with an underscore: '
            '_frobinate', Bitfields, 32, 'axi_read_write', bitfields_config)

    def test_invalid_register_type(self):
        '''If the register type is invalid, a `ValueError` should be raised.
        It should be one of `axi_read_write`, `axi_read_only` or
        `axi_write_only`.
        '''
        bitfields_config = {
            'frobinate': {'type': 'bool', 'offset': 10},
            'range': {'type': 'uint', 'length': 5, 'offset': 25}}

        self.assertRaisesRegex(
            ValueError, 'The register type must be one of `axi_read_write`, '
            '`axi_read_only` or `axi_write_only`', Bitfields, 32, 'foo',
            bitfields_config)

        self.assertRaisesRegex(
            ValueError, 'The register type must be one of `axi_read_write`, '
            '`axi_read_only` or `axi_write_only`', Bitfields, 32, None,
            bitfields_config)

    def test_overlapping_bitfield_error(self):
        '''If bitfields overlap, a `ValueError` should be raised.
        '''
        # Test a few cases
        bitfields_config = {
            'length': {'type': 'uint', 'length': 10, 'offset': 0},
            'frobinate': {'type': 'bool', 'offset': 9}}

        self.assertRaisesRegex(
            ValueError, 'Bitfield `frobinate` overlaps with bitfield `length`',
            Bitfields, 32, 'axi_read_write', bitfields_config)

        bitfields_config = {
            'length': {'type': 'uint', 'length': 10, 'offset': 10},
            'frobinate': {'type': 'uint', 'length': 10, 'offset': 5}}

        self.assertRaisesRegex(
            ValueError, 'Bitfield `frobinate` overlaps with bitfield `length`',
            Bitfields, 32, 'axi_write_only', bitfields_config)

        bitfields_config = {
            'length': {'type': 'uint', 'length': 10, 'offset': 10},
            'frobinate': {'type': 'const-uint', 'length': 10, 'offset': 5,
                          'const-value': 10}}

        self.assertRaisesRegex(
            ValueError, 'Bitfield `frobinate` overlaps with bitfield `length`',
            Bitfields, 32, 'axi_read_only', bitfields_config)


        bitfields_config = {
            'length': {'type': 'uint', 'length': 10, 'offset': 5},
            'frobinate': {'type': 'const-bool', 'offset': 5,
                          'const-value': False}}

        self.assertRaisesRegex(
            ValueError, 'Bitfield `frobinate` overlaps with bitfield `length`',
            Bitfields, 32, 'axi_read_only', bitfields_config)

    def test_empty_bitfields_error(self):
        '''If bitfields_config is empty, a ValueError would be raised.
        '''
        bitfields_config = {}

        self.assertRaisesRegex(
            ValueError, 'bitfields_config cannot be empty',
            Bitfields, 32, 'axi_read_write', bitfields_config)

    def test_bitfield_outside_register_error(self):
        '''If a bitfield is defined to be outside the width of the register,
        then a `ValueError` should be raised.
        '''
        bitfields_config = {
            'length': {'type': 'uint', 'length': 10, 'offset': 0},
            'foo': {'type': 'uint', 'length': 10, 'offset': 25}}

        self.assertRaisesRegex(
            ValueError, 'The bitfield `foo` is out of range for a register of '
            'width 32', Bitfields, 32, 'axi_read_write', bitfields_config)

        bitfields_config = {
            'foo': {'type': 'const-uint', 'length': 17, 'offset': 0,
                    'const-value': 10,}}

        self.assertRaisesRegex(
            ValueError, 'The bitfield `foo` is out of range for a register of '
            'width 16', Bitfields, 16, 'axi_read_only', bitfields_config)

        bitfields_config = {
            'foo': {'type': 'const-bool', 'offset': 16, 'const-value': True}}

        self.assertRaisesRegex(
            ValueError, 'The bitfield `foo` is out of range for a register of '
            'width 16', Bitfields, 16, 'axi_read_only', bitfields_config)

        bitfields_config = {
            'foo': {'type': 'bool', 'offset': 32}}

        self.assertRaisesRegex(
            ValueError, 'The bitfield `foo` is out of range for a register of '
            'width 32', Bitfields, 32, 'axi_write_only', bitfields_config)

    def test_const_uint_not_on_read_only_reg_error(self):
        '''A bitfield of type `const-uint` can only be defined for a register
        of type `axi_read_only`. If the register is not `axi_read_only` then
        a ValueError should be raised.
        '''
        bitfields_config = {
            'foo': {'type': 'const-uint', 'const-value': 10, 'length': 10,
                    'offset': 0}}

        Bitfields(32, 'axi_read_only', bitfields_config) # ok
        self.assertRaisesRegex(
            ValueError, 'The bitfield `foo` is of type `const-uint` which '
            'requires the register is read-only, but the register has been '
            'configured to be `axi_read_write`',
            Bitfields, 32, 'axi_read_write', bitfields_config)

        self.assertRaisesRegex(
            ValueError, 'The bitfield `foo` is of type `const-uint` which '
            'requires the register is read-only, but the register has been '
            'configured to be `axi_write_only`',
            Bitfields, 32, 'axi_write_only', bitfields_config)

    def test_invalid_const_uint_value_error(self):
        '''The const-uint parameter `const-value` should fit inside the
        bitfield. If it does not, a ValueError should be raised.
        '''
        bitfields_config = {
            'foo': {'type': 'const-uint', 'const-value': 10,
                    'length': 10, 'offset': 0}}

        Bitfields(32, 'axi_read_only', bitfields_config) # ok

        bitfields_config = {
            'foo': {'type': 'const-uint', 'const-value': '10',
                    'length': 10, 'offset': 0}}

        Bitfields(32, 'axi_read_only', bitfields_config) # ok


        bitfields_config = {
            'foo': {'type': 'const-uint', 'const-value': 2**10,
                    'length': 10, 'offset': 0}}

        self.assertRaisesRegex(
            ValueError, 'The bitfield const value, {}, is invalid for '
            'bitfield {}'.format(2**10, 'foo'),
            Bitfields, 32, 'axi_read_only', bitfields_config)

        bitfields_config = {
            'foo': {'type': 'const-uint', 'const-value': -1,
                    'length': 10, 'offset': 0}}

        self.assertRaisesRegex(
            ValueError, 'The bitfield const value, {}, is invalid for '
            'bitfield {}'.format(-1, 'foo'),
            Bitfields, 32, 'axi_read_only', bitfields_config)

        bitfields_config = {
            'foo': {'type': 'const-uint', 'const-value': None,
                    'length': 10, 'offset': 0}}

        self.assertRaises(
            TypeError, Bitfields, 32, 'axi_read_only', bitfields_config)

    def test_invalid_const_bool_value_error(self):
        '''The const-bool parameter `const-value` should fit inside the
        bitfield. If it does not, a ValueError should be raised.
        '''
        bitfields_config = {
            'foo': {'type': 'const-bool', 'const-value': True, 'offset': 0}}

        Bitfields(32, 'axi_read_only', bitfields_config) # ok

        bitfields_config = {
            'foo': {'type': 'const-bool', 'const-value': False, 'offset': 0}}

        Bitfields(32, 'axi_read_only', bitfields_config) # ok

        bitfields_config = {
            'foo': {'type': 'const-uint', 'const-value': -1,
                    'length': 10, 'offset': 0}}

        self.assertRaisesRegex(
            ValueError, 'The bitfield const value, {}, is invalid for '
            'bitfield {}'.format(-1, 'foo'),
            Bitfields, 32, 'axi_read_only', bitfields_config)

        bitfields_config = {
            'foo': {'type': 'const-uint', 'const-value': None,
                    'length': 10, 'offset': 0}}

        self.assertRaises(
            TypeError, Bitfields, 32, 'axi_read_only', bitfields_config)

    def test_const_bool_not_on_read_only_reg_error(self):
        '''A bitfield of type `const-bool` can only be defined for a register
        of type `axi_read_only`. If the register is not `axi_read_only` then
        a ValueError should be raised.
        '''
        bitfields_config = {
            'foo': {'type': 'const-bool', 'offset': 0, 'const-value': True}}

        Bitfields(32, 'axi_read_only', bitfields_config) # ok
        self.assertRaisesRegex(
            ValueError, 'The bitfield `foo` is of type `const-bool` which '
            'requires the register is read-only, but the register has been '
            'configured to be `axi_read_write`',
            Bitfields, 32, 'axi_read_write', bitfields_config)

        self.assertRaisesRegex(
            ValueError, 'The bitfield `foo` is of type `const-bool` which '
            'requires the register is read-only, but the register has been '
            'configured to be `axi_write_only`',
            Bitfields, 32, 'axi_write_only', bitfields_config)

    def test_bitfield_called_register_error(self):
        '''If a bitfield is given the name `register`, then a `ValueError`
        should be raised.
        '''
        bitfields_config = {
            'foo': {'type': 'uint', 'length': 10, 'offset': 0},
            'register': {'type': 'uint', 'length': 10, 'offset': 10}}

        self.assertRaisesRegex(
            ValueError, 'Bitfields cannot be named `register`.',
            Bitfields, 32, 'axi_read_write', bitfields_config)

    def test_initial_value_on_non_read_write_error(self):
        '''If `register_type` is not `axi_read_write`, then a ValueError should
        be raised if `initial_values` is not `None`.
        '''
        bitfields_config = {
            'foo': {'type': 'uint', 'length': 10, 'offset': 0},
            'bar': {'type': 'bool', 'offset': 10}}

        initial_values = {'foo': 10}

        Bitfields(32, 'axi_read_write', bitfields_config,
                  initial_values=initial_values) # ok

        self.assertRaisesRegex(
            ValueError, '`initial_values` must be `None` if the register type '
            'is not `axi_read_write`', Bitfields, 32, 'axi_read_only',
            bitfields_config, initial_values=initial_values)

        self.assertRaisesRegex(
            ValueError, '`initial_values` must be `None` if the register type '
            'is not `axi_read_write`', Bitfields, 32, 'axi_write_only',
            bitfields_config, initial_values=initial_values)

def create_bitfields_config(
    reg_len, include_consts=False, single_bitfield=False):
    '''single_bitfield implies a single full-width bitfield
    '''
    if single_bitfield:
        # We can only use uint types to have a single bitfield
        if include_consts:
            bf_type = random.choice(('uint', 'const-uint'))
        else:
            bf_type = 'uint'

        bitfields_config = {'a': {
            'type': bf_type,
            'length': reg_len,
            'offset': 0}}

        if bf_type == 'const-uint':
            bitfields_config['a']['const-value'] = random.randrange(0, 2**reg_len)

        return bitfields_config, ['a']

    offset = 0
    i = 0
    bitfields_config = {}
    ordered_bitfields = []

    while offset < reg_len:
        if include_consts:
            bf_type = random.choice(
                ('uint', 'bool', 'const-uint', 'const-bool', 'padding'))
        else:
            bf_type = random.choice(('uint', 'bool', 'padding'))

        if bf_type in ('bool'):
            length = 1
        else:
            length = random.randrange(1, min(8, (reg_len - offset) + 1))

        if bf_type == 'uint':
            bitfields_config[string.ascii_lowercase[i]] = {
                'type': 'uint',
                'length': length,
                'offset': offset}

            ordered_bitfields.append(string.ascii_lowercase[i])

            i += 1


        elif bf_type == 'bool':
            bitfields_config[string.ascii_lowercase[i]] = {
                'type': 'bool',
                'offset': offset}
            ordered_bitfields.append(string.ascii_lowercase[i])

            i += 1

        elif bf_type == 'const-uint':
            bitfields_config[string.ascii_lowercase[i]] = {
                'type': 'const-uint',
                'length': length,
                'offset': offset,
                'const-value': random.randrange(0, 2**length)}

            ordered_bitfields.append(string.ascii_lowercase[i])

            i += 1


        elif bf_type == 'const-bool':
            bitfields_config[string.ascii_lowercase[i]] = {
                'type': 'const-bool',
                'offset': offset,
                'const-value': random.choice((True, False))}
            ordered_bitfields.append(string.ascii_lowercase[i])

            i += 1

        elif bf_type == 'padding':
            pass


        offset += length

    return bitfields_config, ordered_bitfields


class TestBitfieldsRegisterAssignments(KeaTestCase):
    '''The bitfield_connector method should connect up the bitfield signals
    and the register signals in the correct direction according to the
    register type.
    '''

    def setUp(self):
        pass
        #seed = random.randrange(2**32)
        #random.seed(seed)

    def do_ps_write_test(
        self, reg_type, reg_len, use_initial_values=False,
        single_bitfield=False):
        ''' A common test implementation for axi_write_only and axi_read_write
        register types.
        '''

        # Make sure we never construct an empty bitfields_config
        bitfields_config = {}
        while bitfields_config == {}:
            bitfields_config, ordered_bitfields = (
                create_bitfields_config(
                    reg_len, single_bitfield=single_bitfield))

        initial_reg_val = 0
        if use_initial_values:
            assert reg_type == 'axi_read_write'

            init_vals = {}
            for bitfield in ordered_bitfields:
                # We choose randomly whether we provide an initial value
                # to the bitfield
                if random.choice((True, False)):
                    bf_type = bitfields_config[bitfield]['type']

                    if bf_type in ('bool'):
                        init_val = random.choice((0, 1))
                    else:
                        length = bitfields_config[bitfield]['length']
                        init_val = random.randrange(0, 2**length)

                    offset = bitfields_config[bitfield]['offset']
                    initial_reg_val += (init_val << offset)

                else:
                    init_val = 0

                init_vals[bitfield] = init_val

            bitfields = Bitfields(
                reg_len, reg_type, bitfields_config, initial_values=init_vals)

        else:
            init_vals = {bitfield: 0 for bitfield in bitfields_config}
            bitfields = Bitfields(reg_len, reg_type, bitfields_config)

        self.assertEqual(bitfields.register._val, initial_reg_val)
        self.assertEqual(bitfields.register._init, initial_reg_val)

        init_vals_checked = [False]

        @block
        def assignment_wrapper(clock, bitfields):
            return bitfields.bitfield_connector()

        @block
        def testbench(clock, bitfields):

            @always(clock.posedge)
            def stimulate_and_check():
                bitfields.register.next = random.randrange(0, 2**reg_len)

                for i, bitfield in enumerate(ordered_bitfields):

                    bf_type = bitfields_config[bitfield]['type']
                    if bf_type in ('bool'):
                        length = 1
                    else:
                        length = bitfields_config[bitfield]['length']

                    offset = bitfields_config[bitfield]['offset']

                    bitfield_name = string.ascii_lowercase[i]
                    expected_val = bitfields.register[offset+length:offset]

                    self.assertTrue(
                        getattr(bitfields, bitfield_name) == expected_val)

                    if not init_vals_checked[0]:
                        self.assertEqual(
                            expected_val, init_vals[bitfield_name])

                if not init_vals_checked[0]:
                    # Do it once
                    init_vals_checked[0] = True

            return stimulate_and_check

        cycles = 100

        clock = Signal(False)
        default_args = {
            'clock': clock,
            'bitfields': bitfields}

        bitfield_types = {'register': 'custom'}
        for bitfield in bitfields_config:
            bitfield_types[bitfield] = 'output'

        default_arg_types = {
            'clock': 'clock',
            'bitfields': bitfield_types}

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, assignment_wrapper, assignment_wrapper, default_args,
            default_arg_types,
            custom_sources=[(testbench, (), default_args)])

        self.assertTrue(dut_outputs == ref_outputs)

    def do_ps_read_only_test(
        self, reg_len, use_consts=False, single_bitfield=False):
        ''' A common test implementation for axi_read_only registers.
        '''
        reg_type = 'axi_read_only'

        # Make sure we never construct an empty bitfields_config
        bitfields_config = {}
        while bitfields_config == {}:
            bitfields_config, ordered_bitfields = (
                create_bitfields_config(
                    reg_len, include_consts=use_consts,
                    single_bitfield=single_bitfield))

        bitfields = Bitfields(reg_len, reg_type, bitfields_config)

        reg_initial_value = 0
        for bitfield in bitfields_config:
            if bitfields_config[bitfield]['type'] in (
                'const-uint', 'const-bool'):
                offset = bitfields_config[bitfield]['offset']
                const_val = bitfields_config[bitfield]['const-value']
                reg_initial_value += const_val << offset

        @block
        def assignment_wrapper(clock, bitfields):
            return bitfields.bitfield_connector()

        @block
        def testbench(clock, bitfields):

            reg_check = Signal(intbv(reg_initial_value)[reg_len:])

            @always(clock.posedge)
            def stimulate_and_check():

                expected_reg_val = 0

                for i, bitfield in enumerate(ordered_bitfields):

                    bf_type = bitfields_config[bitfield]['type']

                    if bf_type == 'bool':
                        write_val = random.choice((True, False))

                    elif bf_type == 'uint':
                        length = bitfields_config[bitfield]['length']
                        write_val = random.randrange(0, 2**length)

                    elif bf_type in ('const-uint', 'const-bool'):
                        const_val = bitfields_config[bitfield]['const-value']

                    offset = bitfields_config[bitfield]['offset']

                    bitfield_name = string.ascii_lowercase[i]

                    if bf_type in ('bool', 'uint'):
                        getattr(bitfields, bitfield_name).next = write_val
                        expected_reg_val += (write_val << offset)

                    elif bf_type in ('const-uint', 'const-bool'):
                        expected_reg_val += (const_val << offset)

                    else:
                        # Defensive check
                        raise RuntimeError(
                            'Unknown bitfield type: {}'.format(bf_type))

                # Use the intermediate signal because we check the val on
                # the next cycle.
                reg_check.next = expected_reg_val
                self.assertTrue(bitfields.register == reg_check)

            return stimulate_and_check

        cycles = 100

        clock = Signal(False)
        default_args = {
            'clock': clock,
            'bitfields': bitfields}

        bitfield_types = {'register': 'output'}
        for bitfield in bitfields_config:
            bf_type = bitfields_config[bitfield]['type']

            if bf_type in ('const-uint', 'const-bool'):
                bitfield_types[bitfield] = 'non-signal'
            else:
                bitfield_types[bitfield] = 'custom'

        default_arg_types = {
            'clock': 'clock',
            'bitfields': bitfield_types}

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, assignment_wrapper, assignment_wrapper, default_args,
            default_arg_types,
            custom_sources=[(testbench, (), default_args)])

        self.assertTrue(dut_outputs == ref_outputs)


    def test_axi_read_write_assignments(self):
        '''The bitfields should be correctly written from the internal
        register when the register type is `axi_read_write`.
        '''
        self.do_ps_write_test('axi_read_write', 32)
        # Do a strange register length too...
        self.do_ps_write_test('axi_read_write', 18)

    def test_axi_read_write_initial_values(self):
        '''If an initial values argument is set for the bitfields when the
        register type is `axi_read_write`, the initial values of all the
        bitfields should be set correctly.
        '''
        self.do_ps_write_test('axi_read_write', 32, use_initial_values=True)

    def test_axi_write_only_assignments(self):
        '''The bitfields should be correctly written from the internal
        register when the register type is `axi_write_only`.
        '''
        self.do_ps_write_test('axi_write_only', 32)
        # Do a strange register length too...
        self.do_ps_write_test('axi_write_only', 18)

    def test_axi_read_only_assignments(self):
        '''The bitfields should be correctly drive the internal
        register when the register type is `axi_read_only`.
        '''
        self.do_ps_read_only_test(32)
        # Do a strange register length too...
        self.do_ps_read_only_test(18)

    def test_axi_read_only_constants(self):
        '''When a bitfield is a constant type ('const-bool' or 'const-uint',
        its value should always be the constant value that has been set
        '''
        self.do_ps_read_only_test(32, use_consts=True)
        # Do a strange register length too...
        self.do_ps_read_only_test(65, use_consts=True)

    def test_axi_read_write_assignments_single_bitfield(self):
        '''A register containing a single bitfield should be correctly written
        from the internal register when the register type is `axi_read_write`.
        '''
        self.do_ps_write_test('axi_read_write', 32, single_bitfield=True)

    def test_axi_write_only_assignments_single_bitfield(self):
        '''A register containing a single bitfield should be correctly written
        from the internal register when the register type is `axi_write_only`.
        '''
        self.do_ps_write_test('axi_write_only', 32, single_bitfield=True)

    def test_axi_read_only_assignments_single_bitfield(self):
        '''A register containing a single bitfield should be correctly drive
        the internal register when the register type is `axi_read_only`.
        '''
        self.do_ps_read_only_test(32, use_consts=False, single_bitfield=True)

class TestBitfieldsRegisterAssignmentsVivadoVhdlSimulation(
    KeaVivadoVHDLTestCase, TestBitfieldsRegisterAssignments):
    pass

class TestBitfieldsRegisterAssignmentsVivadoVerilogSimulation(
    KeaVivadoVerilogTestCase, TestBitfieldsRegisterAssignments):
    pass

class TestRegisterInterfaceSimulation(KeaTestCase):
    '''The `Register` object should handle its arguments properly and error
    if the arguments are invalid or incompatible.
    '''

    def setUp(self):
        self.available_register_types = [
            'axi_read_write', 'axi_write_only', 'axi_read_only']

    def test_invalid_register_name(self):
        '''Register names should be a valid python identifier. A ValueError
        will be raised if not.
        '''
        register_list = ['*.']

        self.assertRaisesRegex(ValueError, 'Invalid register name: *.',
                               Registers, register_list)

    def test_invalid_register_types(self):
        ''' The system should error if the register_types dict includes a key
        which does not correspond to any name in the register_list
        '''

        n_registers = 5
        register_list = []

        # Create a list of registers with random names of 5 character length.
        for i in range(n_registers):
            register_list.append(
                ''.join(random.choice(string.ascii_lowercase)
                        for i in range(5)))

        # Create a register_types dict which contains a key which cannot be in
        # the list of registers. I have made sure it cannot be in the list of
        # registers by setting the length to 10 characters.
        register_types = {
            ''.join(random.choice(string.ascii_lowercase)
                    for i in range(10)): (
                random.choice(self.available_register_types))}

        # Check that the system errors when register_types contains an invalid
        # key.
        self.assertRaisesRegex(ValueError,
                               'Invalid register in register_types',
                               Registers, register_list, register_types)

    def test_default_register_types(self):
        ''' The system should treat any registers which do not have an entry
        in the register_types dict as axi_read_write.
        '''

        n_registers = 20
        register_list = []

        # Create a list of registers with random names of 5 character length.
        for i in range(n_registers):
            register_list.append(
                ''.join(random.choice(string.ascii_lowercase)
                        for i in range(5)))

        # Create a register_types dict which uses a random number of the names
        # in the list of registers as keys.
        register_types = {key: random.choice(
            self.available_register_types) for key in register_list if (
                random.random() < 0.25)}

        # Create the registers
        registers = Registers(register_list, register_types)

        # Check that any registers which don't appear in the register types
        # list are set to the default axi_read_write. All others should be the
        # type specified in the register_types.
        for name in register_list:
            if name not in register_types:
                assert(registers.register_types[name]=='axi_read_write')
            else:
                assert(registers.register_types[name]==register_types[name])

    def test_rw_initial_values_argument(self):
        ''' If the initial_values argument is not None, it should be a dict
        that provides optional initial values to read-write registers.

        If a RW register is not present in the initial_values dict, it
        should default to 0.

        If a RO or WO register is included in the initial_values dict, a
        ``ValueError`` should be raised.
        '''

        n_registers = 30
        register_list = []

        # Create a list of registers with random names of 5 character length.
        for i in range(n_registers):
            register_list.append(
                ''.join(random.choice(string.ascii_lowercase)
                        for i in range(5)))


        # Create a register_types dict which uses a random number of the names
        # in the list of registers as keys.
        register_types = {key: random.choice(
            self.available_register_types) for key in register_list if (
                random.random() < 0.5)}

        rw_registers = []
        non_rw_registers = []

        for key in register_list:
            if key in register_types:
                if register_types[key] == 'axi_read_write':
                    rw_registers.append(key)
                else:
                    non_rw_registers.append(key)

            else:
                # Also read-write
                rw_registers.append(key)

        initial_values = {
            key: random.randrange(0xFFFFFFFF) for key in rw_registers if (
                random.random() < 0.5)}

        registers = Registers(
            register_list, register_types, initial_values=initial_values)

        for key in rw_registers:
            if key in initial_values:
                self.assertEqual(getattr(registers, key), initial_values[key])

            else:
                self.assertEqual(getattr(registers, key), 0)

        # Force one read- or write-only
        invalid_type_reg = random.choice(register_list)
        register_types[invalid_type_reg] = random.choice(
            ['axi_read_only', 'axi_write_only'])

        invalid_initial_values = initial_values.copy()
        invalid_initial_values[invalid_type_reg] = 20

        self.assertRaisesRegex(ValueError,
                               ('Only read-write registers can take '
                                'initial values'),
                               Registers, register_list, register_types,
                               initial_values=invalid_initial_values)


    def test_no_register_types(self):
        ''' The system should handle a lack of register types dict gracefully
         and return all registers in the register list as axi read write.
        '''

        n_registers = 20
        register_list = []

        # Create a list of registers with random names of 5 character length.
        for i in range(n_registers):
            register_list.append(
                ''.join(random.choice(string.ascii_lowercase)
                        for i in range(5)))

        # Create the registers without passing a dict of register types
        registers = Registers(register_list)

        # All registers should be set to axi_read_write
        for name in register_list:
            assert(registers.register_types[name]=='axi_read_write')


    def test_bitfields(self):
        '''If a bitfields argument is supplied, this should be used to
        construct a bitfield object in place of a register signal.
        '''
        n_registers = 20
        register_list = []
        register_width = 32

        # Create a list of registers with random names of 5 character length.
        for i in range(n_registers):
            register_list.append(
                ''.join(random.choice(string.ascii_lowercase)
                        for i in range(5)))

        register_types = {key: random.choice(
            self.available_register_types) for key in register_list if (
                random.random() < 0.25)}

        bitfields = {}
        bitfields_configs = {}
        initial_vals = {}

        for register_name in register_list:
            bitfields_config, ordered_bitfields = (
                create_bitfields_config(register_width))

            bitfields_configs[register_name] = bitfields_config

            try:
                reg_type = register_types[register_name]
            except KeyError:
                reg_type = 'axi_read_write'


            read_write_reg = (reg_type == 'axi_read_write')

            if read_write_reg and random.choice((True, False)):

                bf_initial_vals = {}

                for bitfield in ordered_bitfields:
                    # We choose randomly whether we provide an initial value
                    # to the bitfield
                    if random.choice((True, False)):
                        bf_type = bitfields_config[bitfield]['type']

                        if bf_type in ('bool'):
                            init_val = random.choice((0, 1))
                        else:
                            length = bitfields_config[bitfield]['length']
                            init_val = random.randrange(0, 2**length)

                        bf_initial_vals[bitfield] = init_val

                initial_vals[register_name] = bf_initial_vals

            else:
                bf_initial_vals = None

            bitfields[register_name] = (
                Bitfields(register_width, reg_type, bitfields_config,
                          initial_values=bf_initial_vals))

        # Create the registers
        registers = Registers(
            register_list, register_types, register_width,
            initial_values=initial_vals, bitfields=bitfields_configs)

        for reg_name in bitfields:

            self.assertEqual(
                getattr(registers, reg_name), bitfields[reg_name])
