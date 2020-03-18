from myhdl import Signal, intbv, block, always_comb, ConcatSignal
import myhdl
from collections import OrderedDict

import keyword

def _is_valid_name(ident: str) -> bool:
    '''Determine if ident is a valid register or bitfield name.
    '''

    if not isinstance(ident, str):
        raise TypeError("expected str, but got {!r}".format(type(ident)))

    if not ident.isidentifier():
        return False

    if keyword.iskeyword(ident):
        return False

    return True

@block
def assign_bitfield_from_register(reg, bitfield, offset):

    if isinstance(bitfield.val, bool):
        @always_comb
        def assignment():
            bitfield.next = reg[offset]

    else:
        start = offset
        stop = offset + len(bitfield)

        @always_comb
        def assignment():
            bitfield.next = reg[stop:start]


    return assignment

class Bitfields:

    def __eq__(self, other):

        if not ((self._bitfields_config == other._bitfields_config) and
                (self._initial_values == other._initial_values) and
                (self._register_width == other._register_width) and
                (self._reg_type == other._reg_type)):
            return False

        else:
            # The values also need to be the same
            for bf_name in self._bitfields_config:
                if getattr(self, bf_name) != getattr(other, bf_name):
                    return False

            if self.register != other.register:
                return False

        return True


    def __init__(
        self, register_width, register_type, bitfields_config,
        initial_values=None):
        '''
        Creates a MyHDL interface representing a series of bitfields.

        `register_width` is the width of the register that the bitfields sit
        on top of.

        `register_type` is one of `axi_read_write`, `axi_read_only` or
        `axi_write_only`.

        `initial_values` is an optional lookup for each bitfield when the
        register type is `axis_read_write`. If a bitfield
        has an initial value set, then, assuming the register_type is
        `axis_read_write`, the bitfield will be set to the initial value. If
        the register type is not `axis_read_write`, then a ValueError will be
        raised if this argument is not `None`.

        `bitfields_config` is a dictionary that provides the configuration
        for each bitfield on a register. The keys are the names of the
        bitfields and each key should point to a configuration dict.
        Each configution should have the `type` key, which should have data
        which is one of:
            - `uint`
            - `bool`
            - `const-uint`
            - `const-bool`

        In addition, it should also have keys which depend on the type, as
        follows:
            - `uint`:
                - `length` giving the length in bits of the uint
                - `offset` giving the offset of the bitfield.
            - `bool`:
                - `offset` giving the offset of the boolean value.
            - `const-uint`:
                - `length` giving the length in bits of the uint
                - `offset` giving the offset of the bitfield.
                - `const-value` giving the value of the constant.
            - `const-bool`:
                - `offset` giving the offset of the boolean balue.
                - `const-value` giving the value of the constant.

        Extra keys are ignored.

        Other constraints are enforced and will cause an error:
            - All bitfields must fit within the register width.
            - A `const-uint` and `const-bool` can only be set on a read-only
            register.
            - Overlapping bitfields are invalid.
            - No bitfield can be called 'register'. This is reserved for the
            full register representation.
            - Only read-write registers can have an initial value.

        An example bitfield entry might look something like:
            {'foo':{'type': 'uint',
                    'length': 6,
                    'offset': 0},
             'bar': {'type': 'bool',
                     'offset': 6},
             'baz': {'type': 'const-uint',
                     'length': 5,
                     'offset': 7,
                     'const-value': 15}}

        '''

        if len(bitfields_config) == 0:
            raise ValueError('bitfields_config cannot be empty')

        if register_type not in (
            'axi_read_write', 'axi_read_only', 'axi_write_only'):
            raise ValueError(
                'The register type must be one of `axi_read_write`, '
                '`axi_read_only` or `axi_write_only`')

        if initial_values != None and register_type != 'axi_read_write':
            raise ValueError(
                '`initial_values` must be `None` if the register type '
                'is not `axi_read_write`')

        if initial_values is None:
            initial_values = {}

        # We always create a register attribute
        register_initial_val = 0
        for bitfield in bitfields_config:
            offset = bitfields_config[bitfield]['offset']
            try:
                init_val = initial_values[bitfield]
            except KeyError:
                init_val = 0

            register_initial_val += init_val << offset

        self._reg_type = register_type
        self._register_width = register_width
        self._bitfields_config = bitfields_config
        self._initial_values = initial_values

        bitfield_masks = {}

        bitfield_starts = {}
        bitfield_stops = {}
        self._constant_vals = {}

        for bitfield in bitfields_config:

            if not _is_valid_name(bitfield):
                raise ValueError(
                    'Bitfield names must be valid python identifiers: '
                    '{}'.format(bitfield))

            if bitfield[0] == '_':
                raise ValueError(
                    'Bitfield names cannot begin with an underscore: '
                    '{}'.format(bitfield))

            if bitfield == 'register':
                raise ValueError('Bitfields cannot be named `register`.')

            if bitfields_config[bitfield]['type'] == 'uint':
                length = bitfields_config[bitfield]['length']
                offset = bitfields_config[bitfield]['offset']

                bf_signal = Signal(intbv(0)[length:])

                mask = (2**length - 1) << offset

                bitfield_starts[offset] = bitfield
                bitfield_stops[bitfield] = offset + length

            elif bitfields_config[bitfield]['type'] == 'bool':
                offset = bitfields_config[bitfield]['offset']

                bf_signal = Signal(False)
                mask = 1 << offset

                bitfield_starts[offset] = bitfield
                bitfield_stops[bitfield] = offset + 1

            elif bitfields_config[bitfield]['type'] == 'const-uint':

                if register_type != 'axi_read_only':
                    raise ValueError(
                        'The bitfield `{}` is of type `const-uint` which '
                        'requires the register is read-only, but the register '
                        'has been configured to be `{}`'.format(
                            bitfield, register_type))

                length = bitfields_config[bitfield]['length']
                offset = bitfields_config[bitfield]['offset']
                const_val = int(bitfields_config[bitfield]['const-value'])

                if (const_val >= 2**length or const_val < 0):
                    raise ValueError(
                        'The bitfield const value, {}, is invalid for '
                        'bitfield {}'.format(const_val, bitfield))

                bf_signal = intbv(const_val)[length:]
                self._constant_vals[bitfield] = const_val

                # We also set the initial value for constants
                register_initial_val += const_val << offset

                mask = (2**length - 1) << offset

                bitfield_starts[offset] = bitfield
                bitfield_stops[bitfield] = offset + length

            elif bitfields_config[bitfield]['type'] == 'const-bool':

                if register_type != 'axi_read_only':
                    raise ValueError(
                        'The bitfield `{}` is of type `const-bool` which '
                        'requires the register is read-only, but the register '
                        'has been configured to be `{}`'.format(
                            bitfield, register_type))

                offset = bitfields_config[bitfield]['offset']
                const_val = bitfields_config[bitfield]['const-value']

                if not isinstance(const_val, bool):
                    raise ValueError(
                        'The bitfield const value, {}, is invalid for '
                        'bitfield {}'.format(const_val, bitfield))

                bf_signal = const_val
                self._constant_vals[bitfield] = const_val

                # We also set the initial value for constants
                register_initial_val += const_val << offset

                mask = 1 << offset

                bitfield_starts[offset] = bitfield
                bitfield_stops[bitfield] = offset + 1

            else:
                raise ValueError('A bitfield type must be one of `uint`, '
                                 '`bool`, `const-uint` or `const-bool`: '
                                 '{}'.format(bitfield))

            if mask >= 2**register_width:
                raise ValueError(
                    'The bitfield `{}` is out of range for a register of '
                    'width {}'.format(bitfield, register_width))

            # Check the bitfield doesn't overlap with any others
            for other_bf in bitfield_masks:
                if (bitfield_masks[other_bf] & mask) != 0:
                    raise ValueError(
                        'Bitfield `{}` overlaps with bitfield `{}`'.format(
                            bitfield, other_bf))

            bitfield_masks[bitfield] = mask
            setattr(self, bitfield, bf_signal)

        # We now need to construct the packed version of the bitfields,
        # including padding.
        rev_concat_list = []
        bitfield_starts_list = list(bitfield_starts.keys())
        bitfield_starts_list.sort()

        if bitfield_starts_list[0] != 0:
            padding = intbv(0)[bitfield_starts_list[0]:]
            rev_concat_list.append(padding)

        for i, start in enumerate(bitfield_starts_list):

            bitfield = bitfield_starts[start]
            rev_concat_list.append(getattr(self, bitfield))

            try:
                next_start = bitfield_starts_list[i + 1]

                # The higher up checks make sure padding_len should never be
                # negative.
                padding_len = next_start - bitfield_stops[bitfield]
                if padding_len > 0:
                    padding = intbv(0)[padding_len:]
                    rev_concat_list.append(padding)

            except IndexError:
                if bitfield_stops[bitfield] < register_width:
                    padding = intbv(0)[
                        register_width - bitfield_stops[bitfield]:]
                    rev_concat_list.append(padding)

        self.register = Signal(intbv(register_initial_val)[register_width:])

        self._concat_list = rev_concat_list[::-1]
        self._bitfield_starts = bitfield_starts
        self._bitfield_masks = bitfield_masks

    @block
    def bitfield_connector(self):

        if self._reg_type in ('axi_read_write', 'axi_write_only'):

            instances = []

            for bitfield_start in self._bitfield_starts:
                bitfield = getattr(self, self._bitfield_starts[bitfield_start])
                instances.append(
                    assign_bitfield_from_register(
                        self.register, bitfield, bitfield_start))

            return instances

        elif self._reg_type in ('axi_read_only'):

            if len(self._concat_list) == 1:
                # This is a hack to allow a concat signal to work in
                # all cases. An alternative would be to special case single
                # signals, but that doesn't work well with constants, which
                # themselves would require a special case, and some hackery to
                # have the constant read (and requiring initial_values to be
                # turned on).
                keep = Signal(True)
                keep.driven = True

                reg_signal = ConcatSignal(keep, self._concat_list[0])

            else:
                reg_signal = ConcatSignal(*self._concat_list)

            @always_comb
            def assign_register():
                self.register.next = reg_signal[self._register_width:]

            return assign_register

class RegisterSet(object):
    pass

class Registers(object):
    ''' A general purpose register definition.
    '''

    @property
    def register_types(self):
        return self._register_types

    def __eq__(self, other):
        return (self._bitfields == other._bitfields and
                self._register_types == other._register_types and
                self._register_width == other._register_width)


    def __init__(
        self, register_list, register_types=None, register_width=32,
        initial_values=None, bitfields=None):
        '''
        Constructs a MyHDL interface that encapsulates each register name
        given in `register_list`. The order of the registers in the list is
        kept.

        If `register_types` is set, it should be a dictionary like object
        that provides data of the form `axi_read_write`, `axi_read_only` or
        `axi_write_only` for the register name given by its key. If a register
        name is missing from `register_types`, then the register type defaults
        to `axi_read_write`. If `register_types` is `None`, then all the
        registers are `axi_read_write`.

        `register_width` gives the width in bits of each register that is
        created, defaulting to 32.

        `initial_values` is an optional dictionary that sets the initial
        value of a read-write register. A `ValueError` will be raised if an
        initial value is set for a non read-write register. The default is
        for the initial values to be zero. If a register has bitfields set
        (see below), then the dictionary entry should itself be a dictionary
        to the initial values for each bitfield.

        `bitfields` is an optional dictionary argument in which each register
        that is included in the dictionary is populated as a Bitfield interface
        rather than a signal. Each data in bitfields is passed directly as the
        second argument to the initialisation of a `Bitfield` class. See the
        documentation for that class to see what form the data should be.
        '''

        for name in register_list:
            if not _is_valid_name(name):
                raise ValueError('Invalid register name: {}'.format(name))

        if register_types is None:
            # Create a register types dictionary so that the system can handle
            # an empty register types argument.
            register_types = {}

        self._register_width = register_width

        # Create an ordered dictionary
        self._register_types = OrderedDict()

        for each in register_types:
            if each not in register_list:
                # Check that the register types have a corresponding register
                # in the register list. If not error.
                raise ValueError(
                    'Invalid register in register_types: %s' % each)

        if initial_values is None:
            initial_values = {}

        if bitfields is None:
            bitfields = {}

        for initial_val_key in initial_values:

            if (register_types.get(initial_val_key, 'axi_read_write') !=
                'axi_read_write'):

                raise ValueError(
                    'Only read-write registers can take initial values: %s' %
                    initial_val_key + ': ' +
                    str(register_types[initial_val_key]))

        for name in register_list:
            register_type = register_types.get(name, 'axi_read_write')

            if name in bitfields:
                initial_vals = initial_values.get(name, None)
                setattr(
                    self, name,
                    Bitfields(register_width, register_type, bitfields[name],
                              initial_values=initial_vals))

            else:
                # Create the registers
                setattr(self, name, Signal(
                    intbv(initial_values.get(name, 0))[register_width:]))

            # Populate the ordered dictionary with the appropriate
            # register types, defaulting to 'axi_read_write'
            self._register_types[name] = (
                register_types.get(name, 'axi_read_write'))

        self._bitfields = bitfields

