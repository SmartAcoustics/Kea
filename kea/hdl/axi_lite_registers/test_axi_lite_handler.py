import copy
import random
import string
import unittest

import numpy as np

from math import log
from myhdl import block, Signal, intbv, enum, always, StopSimulation, modbv

from kea.hdl.axi import axi_lite, AxiLiteInterface, AxiLiteMasterBFM
from kea.testing.test_utils import random_string_generator
from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._axi_lite_handler import (
    axi_lite_handler,
    VALID_DATA_BITWIDTHS as AXI_LITE_HANDLER_VALID_DATA_BITWIDTHS)
from ._registers import Registers
from .test_registers import create_bitfields_config

CONST_BF_TYPES = ('const-bool', 'const-uint')

try:
    import Queue as queue
except ImportError:
    import queue

def create_bitfield_initial_values(bitfield_config):
    ''' This function creates initial values for the specified bitfields.
    '''

    bitfields_initial_values = {}

    for bitfield in bitfield_config:
        if bitfield_config[bitfield]['type'] in ('bool'):
            # Boolean bitfield so pick a random initial val
            bitfields_initial_values[bitfield] = (
                bool(random.randrange(2)))

        elif bitfield_config[bitfield]['type'] in ('uint'):
            # Uint bitfield so pick a random initial val
            bitfield_bitwidth = (
                bitfield_config[bitfield]['length'])
            bitfields_initial_values[bitfield] = (
                random.randrange(2**bitfield_bitwidth))

        else:
            raise ValueError('Invalid bitfield type')

    return bitfields_initial_values

def generate_random_registers_args(
    n_registers_lower_bound, n_registers_upper_bound, register_bitwidth,
    available_register_types, random_initial_values, random_bitfields,
    include_all_register_types):
    ''' This function generates a random register_list, register_types and
    initial_values arguments for the Registers class.
    '''

    if available_register_types is None:
        available_register_types = [
            'axi_read_write', 'axi_write_only', 'axi_read_only']

    if include_all_register_types:
        # Sanity check to make sure we can definitlay include every type of
        # register
        assert(n_registers_lower_bound >= len(available_register_types))

    # Pick a random number of registers
    n_registers = (
        random.randrange(n_registers_lower_bound, n_registers_upper_bound))

    # Create a list of registers with random names
    register_list = [
        random_string_generator(random.randrange(5, 9))
        for n in range(n_registers)]

    if include_all_register_types:
        # Set up the register types list with one of each type of register
        register_types_list = copy.copy(available_register_types)

        # Calculate how many more regisrer types we need
        n_addition_register = n_registers - len(register_types_list)

        for n in range(n_addition_register):
            # Randomly choose the rest of the register types
            register_types_list.append(
                random.choice(available_register_types))

        random.shuffle(register_types_list)

    else:
        # Randomly pick the register types
        register_types_list = [
            random.choice(available_register_types)
            for n in range(n_registers)]

    # Create a register_types dict which uses the names in the list of
    # registers as keys.
    register_types = {
        reg_name: reg_type for reg_name, reg_type in
        zip(register_list, register_types_list)}

    if random_bitfields:
        # Select random registers to have bitfields
        n_registers_with_bitfields = random.randrange(1, n_registers+1)
        registers_with_bitfields = (
            random.sample(register_list, n_registers_with_bitfields))

        bitfields = {}

        for reg_name in registers_with_bitfields:

            if register_types[reg_name] == 'axi_read_only':
                # Only axi read only registers can carry constants
                include_consts = bool(random.randrange(2))

            else:
                include_consts = False

            if random.random() < 0.1:
                single_bitfield = True

            else:
                single_bitfield = False

            # Generate a random bitfield config for each register with
            # bitfields
            bitfields[reg_name], _ordered_bitfields = (
                create_bitfields_config(
                    register_bitwidth, include_consts=include_consts,
                    single_bitfield=single_bitfield))

    else:
        bitfields = None

    if random_initial_values:
        # Create a list of the read_write registers. Only read write registers
        # can have initial values.
        read_write_registers_list = []
        for reg_name in register_types:
            if register_types[reg_name] == 'axi_read_write':
                read_write_registers_list.append(reg_name)

        n_rw_registers = len(read_write_registers_list)

        # Select random registers to have initial values
        n_registers_with_initial_vals = random.randrange(1, n_rw_registers+1)
        registers_with_initial_vals = (
            random.sample(
                read_write_registers_list, n_registers_with_initial_vals))

        initial_value_upper_bound = 2**register_bitwidth

        if bitfields is None:
            # There are no bitfields so generate initial values for the
            # registers
            initial_values = {
                reg_name: random.randrange(initial_value_upper_bound)
                for reg_name in registers_with_initial_vals}

        else:

            initial_values = {}

            for reg_name in registers_with_initial_vals:

                if reg_name in bitfields:
                    # This register has bitfields so generate initial values
                    # for the bitfields.
                    initial_values[reg_name] = (
                        create_bitfield_initial_values(bitfields[reg_name]))

                else:
                    # This register doesn't have bitfields so generate an
                    # initial value for the register
                    initial_values[reg_name] = (
                        random.randrange(initial_value_upper_bound))

    else:
        initial_values = None

    return register_list, register_types, initial_values, bitfields

def test_args_setup(
    n_registers_lower_bound=1, n_registers_upper_bound=21,
    available_register_types=None, random_initial_values=False,
    random_bitfields=False, include_all_register_types=False,
    data_bitwidth=32, addr_bitwidth=8, write_count_bitwidth=32):
    ''' Generate the arguments and argument types for the DUT.
    '''

    register_list, register_types, initial_values, bitfields = (
        generate_random_registers_args(
            n_registers_lower_bound, n_registers_upper_bound,
            data_bitwidth, available_register_types,
            random_initial_values, random_bitfields,
            include_all_register_types))

    registers = (
        Registers(
            register_list, register_types, register_width=data_bitwidth,
            initial_values=initial_values, bitfields=bitfields))

    axi_lite_interface = (
        AxiLiteInterface(
            data_bitwidth, addr_bitwidth, use_AWPROT=False,
            use_ARPROT=False, use_WSTRB=False))

    args = {
        'clock': Signal(False),
        'axil_nreset': Signal(True),
        'axi_lite_interface': axi_lite_interface,
        'registers': registers,
        'last_written_reg_addr': Signal(intbv(0)[addr_bitwidth:]),
        'last_written_reg_data': Signal(intbv(0)[data_bitwidth:]),
        'write_count': Signal(intbv(0)[write_count_bitwidth:]),
    }

    axi_lite_interface_types = {
        'AWVALID': 'custom',
        'AWREADY': 'output',
        'AWADDR': 'custom',
        'WVALID': 'custom',
        'WREADY': 'output',
        'WDATA': 'custom',
        'BVALID': 'output',
        'BREADY': 'custom',
        'BRESP': 'output',
        'ARVALID': 'custom',
        'ARREADY': 'output',
        'ARADDR': 'custom',
        'RVALID': 'output',
        'RREADY': 'custom',
        'RDATA': 'output',
        'RRESP': 'output',}

    registers_interface_types = {}

    for reg_name in register_list:
        if register_types[reg_name]=='axi_read_only':
            # Default to `custom`
            registers_interface_types[reg_name] = 'custom'

            if bitfields is not None:
                # There are bitfields defined
                if reg_name in bitfields:
                    # This register has bitfields so we need to specify the
                    # types for the bitfield signals
                    reg_bitfields = bitfields[reg_name]

                    bitfield_types = {}

                    for bf_name in reg_bitfields:
                        if (reg_bitfields[bf_name]['type'] not in
                            CONST_BF_TYPES):
                            # The constant bitfields do not have a signal on
                            # the interface
                            bitfield_types[bf_name] = 'custom'

                    # A read only register with bitfields
                    registers_interface_types[reg_name] = bitfield_types

        else:
            # A read write or write only register so default to output
            registers_interface_types[reg_name] = 'output'

            if bitfields is not None:
                # There are bitfields defined
                if reg_name in bitfields:
                    # This register has bitfields so we need to specify the
                    # types for the bitfield signals
                    registers_interface_types[reg_name] = {
                        bf_name: 'output' for bf_name in bitfields[reg_name]}

    arg_types = {
        'clock': 'clock',
        'axil_nreset': 'custom',
        'axi_lite_interface': axi_lite_interface_types,
        'registers': registers_interface_types,
        'last_written_reg_addr': 'output',
        'last_written_reg_data': 'output',
        'write_count': 'output',
    }

    return args, arg_types

def extract_bitfield_values(value, bitfields_config):
    ''' For a given value this function extracts the bitfield values.
    '''

    bitfield_vals = {}

    for bitfield in bitfields_config:
        # Extract the bitfield type and offset.
        bitfield_type = bitfields_config[bitfield]['type']
        bitfield_offset = bitfields_config[bitfield]['offset']

        if bitfield_type in ('bool', 'const-bool'):
            # The bitfield is a bool so it is 1 bit
            bitfield_vals[bitfield] = (value >> bitfield_offset) & 1

        elif bitfield_type in ('uint', 'const-uint'):
            # This bitfield is a uint so it extract the length and calculate
            # the mask
            bitfield_length = bitfields_config[bitfield]['length']
            mask = 2**bitfield_length - 1

            # Extract the bitfield value
            bitfield_vals[bitfield] = (value >> bitfield_offset) & mask

        else:
            raise ValueError('Invalid bitfield type')

    return bitfield_vals

class TestAxiLiteHandlerInterface(KeaTestCase):
    ''' The block should implement various bits of functionality that should
    be verifiable through simulation.
    '''

    def setUp(self):
        self.args, _arg_types = test_args_setup()

    def test_invalid_axi_lite_interface(self):
        ''' The system should raise a error if the `axi_lite_interface`
        argument is not an instance of `AxiLiteInterface`.
        '''

        self.args['axi_lite_interface'] = random.randint(0, 100)

        self.assertRaisesRegex(
            ValueError,
            ('axi_lite_handler: axi_lite_interface needs to be an instance '
             'of AxiLiteInterface'),
            axi_lite_handler,
            **self.args,)

    def test_invalid_registers(self):
        ''' The system should raise a error if the `registers` argument is not
        an instance of `Registers`.
        '''

        self.args['registers'] = random.randint(0, 100)

        self.assertRaisesRegex(
            ValueError,
            ('axi_lite_handler: registers need to be an instance of '
             'Registers'),
            axi_lite_handler,
            **self.args)

    def test_mismatched_data_widths(self):
        ''' The system should raise a error if the `WDATA` and `RDATA` signals
        on the `axi_lite_interface` are not the same bitwidth.
        '''

        wdata_bitwidth, rdata_bitwidth = random.sample(range(1, 33), 2)

        self.args['axi_lite_interface'].WDATA = (
            Signal(intbv(0)[wdata_bitwidth:]))
        self.args['axi_lite_interface'].RDATA = (
            Signal(intbv(0)[rdata_bitwidth:]))

        self.assertRaisesRegex(
            ValueError,
            ('axi_lite_handler: Read and write data should be of equal '
             'width'),
            axi_lite_handler,
            **self.args)

    def test_mismatched_address_widths(self):
        ''' The system should raise a error if the `AWDATA` and `ARDATA`
        signals on the `axi_lite_interface` are not the same bitwidth.
        '''

        awaddr_bitwidth, araddr_bitwidth = random.sample(range(1, 33), 2)

        self.args['axi_lite_interface'].AWADDR = (
            Signal(intbv(0)[awaddr_bitwidth:]))
        self.args['axi_lite_interface'].ARADDR = (
            Signal(intbv(0)[araddr_bitwidth:]))

        self.assertRaisesRegex(
            ValueError,
            ('axi_lite_handler: Read and write addresses should be of equal '
             'width'),
            axi_lite_handler,
            **self.args)

    def test_invalid_data_bitwidth(self):
        ''' The system should raise a error if the bitwidth of the `WDATA` and
        `RDATA` signals on the `axi_lite_interface` is not a valid bitwidth.
        The valid bitwidths are defined in
        `._axi_lite_handler.VALID_DATA_BITWIDTHS`.
        '''

        data_bitwidth = (
            random.choice([
                n for n in range(1, 33)
                if n not in AXI_LITE_HANDLER_VALID_DATA_BITWIDTHS]))

        # Set up the axi lite interface with an invalid data bitwidth
        self.args['axi_lite_interface'].WDATA = (
            Signal(intbv(0)[data_bitwidth:]))
        self.args['axi_lite_interface'].RDATA = (
            Signal(intbv(0)[data_bitwidth:]))

        self.assertRaisesRegex(
            ValueError,
            ('axi_lite_handler: Data width must be 32 or 64 bits'),
            axi_lite_handler,
            **self.args)

    def test_invalid_register_type(self):
        ''' The system should error if the `registers` contains an invalid
        register type.
        '''

        invalid_register_type = random_string_generator(5)
        available_register_types = [invalid_register_type]

        self.args, _arg_types = (
            test_args_setup(
                n_registers_lower_bound=1,
                n_registers_upper_bound=2,
                available_register_types=available_register_types))

        self.assertRaisesRegex(
            ValueError,
            ('axi_lite_handler: Unknown register type: \'%s\' is not '
             'defined.' % invalid_register_type),
            axi_lite_handler,
            **self.args)

    def test_axi_lite_interface_includes_awprot(self):
        ''' The system should error if the `axi_lite_interface` includes an
        `AWPROT` signal.
        '''

        data_bitwidth = len(self.args['axi_lite_interface'].WDATA)
        addr_bitwidth = len(self.args['axi_lite_interface'].AWADDR)

        self.args['axi_lite_interface'] = (
            AxiLiteInterface(
                data_bitwidth, addr_bitwidth, use_AWPROT=True,
                use_ARPROT=False, use_WSTRB=False))

        self.assertRaisesRegex(
            TypeError,
            ('axi_lite_handler: The axi_lite_interface includes AWPROT but '
             'the axi_lite_handler does not support AWPROT'),
            axi_lite_handler,
            **self.args)

    def test_axi_lite_interface_includes_arprot(self):
        ''' The system should error if the `axi_lite_interface` includes an
        `ARPROT` signal.
        '''

        data_bitwidth = len(self.args['axi_lite_interface'].WDATA)
        addr_bitwidth = len(self.args['axi_lite_interface'].AWADDR)

        self.args['axi_lite_interface'] = (
            AxiLiteInterface(
                data_bitwidth, addr_bitwidth, use_AWPROT=False,
                use_ARPROT=True, use_WSTRB=False))

        self.assertRaisesRegex(
            TypeError,
            ('axi_lite_handler: The axi_lite_interface includes ARPROT but '
             'the axi_lite_handler does not support ARPROT'),
            axi_lite_handler,
            **self.args)

    def test_axi_lite_interface_includes_wstrb(self):
        ''' The system should error if the `axi_lite_interface` includes an
        `WSTRB` signal.
        '''

        data_bitwidth = len(self.args['axi_lite_interface'].WDATA)
        addr_bitwidth = len(self.args['axi_lite_interface'].AWADDR)

        self.args['axi_lite_interface'] = (
            AxiLiteInterface(
                data_bitwidth, addr_bitwidth, use_AWPROT=False,
                use_ARPROT=False, use_WSTRB=True))

        self.assertRaisesRegex(
            TypeError,
            ('axi_lite_handler: The axi_lite_interface includes WSTRB but '
             'the axi_lite_handler does not support WSTRB'),
            axi_lite_handler,
            **self.args)

    def test_mismatched_registers_bitwidth(self):
        ''' The system should error if the bitwidth of the
        `axi_lite_interface.WDATA` and `axi_lite_interface.RDATA` do not match
        the `registers.register_width`.
        '''

        data_bitwidth = random.randrange(1, 32)

        register_types = self.args['registers'].register_types
        register_list = list(register_types.keys())

        self.args['registers'] = (
            Registers(
                register_list, register_types, register_width=data_bitwidth))

        self.assertRaisesRegex(
            TypeError,
            ('axi_lite_handler: The axi_lite_interface data width should be '
             'the same as the register bitwidth'),
            axi_lite_handler,
            **self.args)

    def test_mismatched_last_written_reg_data_bitwidth(self):
        ''' The system should error if the bitwidth of the
        `axi_lite_interface.WDATA` and `axi_lite_interface.RDATA` do not match
        the bitwidth of `last_written_reg_data`.
        '''

        data_bitwidth = random.randrange(1, 32)

        self.args['last_written_reg_data'] = Signal(intbv(0)[data_bitwidth:])

        self.assertRaisesRegex(
            TypeError,
            ('axi_lite_handler: the bitwidth of last_written_reg_data should '
            'be equal to the bitwidths of the data signals on the '
            'axi_lite_interface'),
            axi_lite_handler,
            **self.args)

    def test_mismatched_last_written_reg_addr_bitwidth(self):
        ''' The system should error if the bitwidth of the
        `axi_lite_interface.AWADDR` and `axi_lite_interface.ARADDR` do not
        match the bitwidth of `last_written_reg_addr`.
        '''

        addr_bitwidth = random.randrange(1, 32)

        self.args['last_written_reg_addr'] = Signal(intbv(0)[addr_bitwidth:])

        self.assertRaisesRegex(
            TypeError,
            ('axi_lite_handler: the bitwidth of last_written_reg_addr should '
            'be equal to the bitwidths of the address signals on the '
            'axi_lite_interface'),
            axi_lite_handler,
            **self.args)

    def test_write_count_non_zero_init_val(self):
        ''' The system should error if the `write_count` has a non zero
        initial value.
        '''

        bitwidth = 4
        init_val = random.randrange(1, 2**bitwidth)

        self.args['write_count'] = Signal(intbv(init_val)[bitwidth:])

        self.assertRaisesRegex(
            ValueError,
            ('axi_lite_handler: The write_count should initialise with 0'),
            axi_lite_handler,
            **self.args)

    def test_n_registers_exceeds_addr_space(self):
        ''' The system should error if the number of registers being created
        exceeds the address space.
        '''

        data_bitwidth = 32
        addr_bitwidth = random.randrange(3, 7)

        # Need to remap the address from words to bytes to work with the
        # software on the PS
        addr_remap_ratio = data_bitwidth//8
        byte_to_word_shift = int(log(addr_remap_ratio, 2))

        # Calculate the maximum number of registers we can address
        n_reg_addresses = 2**(addr_bitwidth - byte_to_word_shift)

        self.args, _arg_types = (
            test_args_setup(
                n_registers_lower_bound=n_reg_addresses+1,
                n_registers_upper_bound=n_reg_addresses+10,
                data_bitwidth=data_bitwidth,
                addr_bitwidth=addr_bitwidth))

        self.assertRaisesRegex(
            ValueError,
            ('axi_lite_handler: n_registers too large for the address width'),
            axi_lite_handler,
            **self.args)

class TestAxiLiteHandler(KeaTestCase):
    ''' The axi lite handler is used for communication between the PS and the
    PL. AXI lite can be used to read/write single words from/to the PL. The
    handler should create registers with an axi interface and a parallel
    interface. These registers can take any of the following forms:

        writable from axi - The parallel interface is read only in the PL.
        Readable from axi - The parallel interface is write only in the PL.
        Read-write from axi - The parallel interface is read only in the PL.

    The registers will store any value written to them until it is
    overwritten.
    '''

    def setUp(self):

        self.test_count = 0
        self.tests_complete = False

    @block
    def end_tests(self, n_tests_to_run, **dut_args):
        ''' Waits until enough tests have run and then ends the tests.
        '''

        clock = dut_args['clock']

        return_objects = []

        stop_simulation = Signal(False)

        @always(clock.posedge)
        def check():

            if self.test_count >= n_tests_to_run:
                # Give the DUT one more cycle before raising StopSimulation
                stop_simulation.next = True

            if stop_simulation:
                self.tests_complete = True
                raise StopSimulation

        return_objects.append(check)

        return return_objects

    @block
    def stim_reset(self, stim_random_resets, **dut_args):
        ''' Stims the `axil_nreset` signal.
        '''

        clock = dut_args['clock']
        axil_nreset = dut_args['axil_nreset']

        return_objects = []

        @always(clock.posedge)
        def stim():

            if stim_random_resets:
                if axil_nreset:
                    if random.random() < 0.005:
                        # Randomly set axil_nreset low
                        axil_nreset.next = False

                else:
                    if random.random() < 0.3:
                        # Randomly set axil_nreset high again
                        axil_nreset.next = True

        return_objects.append(stim)

        return return_objects

    @block
    def randomise_signal(self, signal_to_drive, **dut_args):
        ''' Drives `signal_to_drive` with random values.
        '''

        clock = dut_args['clock']

        return_objects = []

        upper_bound = 2**len(signal_to_drive)

        @always(clock.posedge)
        def stim():

            # Drive signal_to_drive with a random value every cycle
            signal_to_drive.next = random.randrange(upper_bound)

        return_objects.append(stim)

        return return_objects

    @block
    def axi_lite_handler_stim_check(
        self, stim_invalid_reads, stim_invalid_writes, stim_invalid_addresses,
        stim_non_word_aligned_addresses, **dut_args):
        ''' Stimulate and check the `axi_lite_handler`.

        If `stim_invalid_reads` is True then this block will occasionally
        attempt to read from a write only register.

        If `stim_invalid_writes` is True then this block will occasionally
        attempt to write to a read only register.

        It `stim_invalid_addresses` is True then this block will occasionally
        attempt to read from or write to an invalid address (for example, if
        we have 10 registers, it will attempt to read from or write to an
        address which is greater than or equal to 10).
        '''

        clock = dut_args['clock']
        axil_nreset = dut_args['axil_nreset']
        axi_lite_interface = dut_args['axi_lite_interface']
        registers = dut_args['registers']
        last_written_reg_addr = dut_args['last_written_reg_addr']
        last_written_reg_data = dut_args['last_written_reg_data']
        write_count = dut_args['write_count']

        return_objects = []

        assert(len(axi_lite_interface.WDATA)==len(axi_lite_interface.RDATA))
        data_bitwidth = len(axi_lite_interface.WDATA)

        assert(len(axi_lite_interface.AWADDR)==len(axi_lite_interface.ARADDR))
        addr_bitwidth = len(axi_lite_interface.AWADDR)

        axi_lite_bfm = AxiLiteMasterBFM()
        return_objects.append(
            axi_lite_bfm.model(clock, axil_nreset, axi_lite_interface))

        transaction_prob = 0.05

        test_data = {
            'wr_address_received': False,
            'wr_data_received': False,
        }

        initial_values = registers.initial_values
        n_registers = len(registers.register_types)

        # Need to remap the address from words to bytes to work with the
        # software on the PS
        addr_remap_ratio = data_bitwidth//8

        reg_offset_upper_bound = 2**addr_bitwidth//addr_remap_ratio
        byte_offset_upper_bound = addr_remap_ratio

        register_list = [None for n in range(n_registers)]

        register_types = registers.register_types
        bitfields = registers.bitfields

        # Keep a record of readable and writable register indices
        readable_registers_indices = []
        writable_registers_indices = []

        # Keep a record of not readable and not writable register indices
        not_readable_registers_indices = []
        not_writable_registers_indices = []

        for reg_name in register_types:

            # Extract the offest for this register
            register_offset = registers.register_offset(reg_name)

            # Set up the register names at the correct offset
            register_list[register_offset] = reg_name

            if registers.register_types[reg_name]=='axi_read_write':
                # The register is readable and writable so add the index to
                # both the writable and readable registers list.
                readable_registers_indices.append(register_offset)
                writable_registers_indices.append(register_offset)

            elif registers.register_types[reg_name]=='axi_read_only':
                # The register is read only so add the index to the readable
                # registers list and the not writable registers list
                readable_registers_indices.append(register_offset)
                not_writable_registers_indices.append(register_offset)

            elif registers.register_types[reg_name]=='axi_write_only':
                # The register is write only so add the index to the writable
                # registers list and the not readable registers list
                writable_registers_indices.append(register_offset)
                not_readable_registers_indices.append(register_offset)

        n_writable_registers = len(writable_registers_indices)
        n_readable_registers = len(readable_registers_indices)
        n_not_writable_registers = len(not_writable_registers_indices)
        n_not_readable_registers = len(not_readable_registers_indices)

        # Sanity check to make sure we've overwritten all of the Nones that we
        # used to set up the register_list
        assert(None not in register_list)

        # Sanity check to make sure we have at least one readable or writable
        # register
        assert(n_writable_registers > 0 or n_readable_registers > 0)

        available_transactions = []

        if n_writable_registers > 0:
            available_transactions.append('write')

        if n_readable_registers > 0:
            available_transactions.append('read')

        if stim_invalid_writes:
            # If stim_invalid_writes is True, check we actually have registers
            # which are read only
            assert(n_not_writable_registers > 0)
            available_transactions.append('invalid_write')

        if stim_invalid_reads:
            # If stim_invalid_reads is True, check we actually have registers
            # which are write only
            assert(n_not_readable_registers > 0)
            available_transactions.append('invalid_read')

        if stim_invalid_addresses:
            # If stim invalid addresses is true, check we actually have
            # addresses in the address space which aren't assigned to a
            # register
            assert(reg_offset_upper_bound > n_registers)
            available_transactions.append('invalid_address_write')
            available_transactions.append('invalid_address_read')

        if stim_non_word_aligned_addresses:
            # Sanity check to make sure we can stim addresses which are not
            # word aligned
            assert(addr_remap_ratio > 1)
            available_transactions.append('non_word_aligned_address_write')
            available_transactions.append('non_word_aligned_address_read')

        update_wr_status = Signal(False)
        update_register = Signal(False)

        pending_wr_reg_offset = Signal(intbv(0)[addr_bitwidth:])
        pending_wr_data = Signal(intbv(0)[data_bitwidth:])
        expected_wr_response = (
            Signal(intbv(0)[len(axi_lite_interface.BRESP):]))

        valid_read = Signal(False)
        pending_rd_reg_offset = Signal(intbv(0)[addr_bitwidth:])
        expected_rd_data = Signal(intbv(0)[data_bitwidth:])
        expected_rd_response = (
            Signal(intbv(0)[len(axi_lite_interface.RRESP):]))

        pending_byte_offset = Signal(intbv(0, 0, byte_offset_upper_bound))

        expected_last_written_reg_addr = Signal(intbv(0)[addr_bitwidth:])
        expected_last_written_reg_data = Signal(intbv(0)[data_bitwidth:])
        expected_write_count = Signal(modbv(0, 0, 2**len(write_count)))

        expected_writable_register_values = {}

        for reg_name in register_list:
            if register_types[reg_name] == 'axi_read_write':
                if reg_name in initial_values:

                    if reg_name in bitfields:
                        # Extract the bitfields config for this register
                        register_bitfields = bitfields[reg_name]

                        initial_val = 0

                        for bf_name in register_bitfields:
                            # Extract the initial value for each bitfield
                            bf_init_val = initial_values[reg_name][bf_name]

                            # Shift each bitfield init val into the correct
                            # location in the initial value.
                            initial_val |= (
                                bf_init_val <<
                                register_bitfields[bf_name]['offset'])

                        expected_writable_register_values[reg_name] = (
                            initial_val)

                    else:
                        # There is an initial value specified for this
                        # register so use it
                        expected_writable_register_values[reg_name] = (
                            initial_values[reg_name])

                else:
                    # There are no initial values set for this register so use
                    # 0
                    expected_writable_register_values[reg_name] = 0

            elif register_types[reg_name] == 'axi_write_only':
                # Set the expected value for the write only registers
                expected_writable_register_values[reg_name] = 0

            elif register_types[reg_name] == 'axi_read_only':
                register = getattr(registers, reg_name)

                if reg_name in bitfields:
                    register_bitfields = bitfields[reg_name]

                    for bf_name in register_bitfields:
                        bf_type = register_bitfields[bf_name]['type']
                        if bf_type not in CONST_BF_TYPES:
                            # If the bitfield is not a constant then randomly
                            # drive it
                            dut_bitfield = getattr(register, bf_name)
                            return_objects.append(
                                self.randomise_signal(
                                    dut_bitfield, **dut_args))

                else:
                    # Randomly drive the register
                    return_objects.append(
                        self.randomise_signal(register, **dut_args))

            else:
                raise ValueError('Invalid register type')

        t_state = enum(
            'IDLE','ADD_WRITE', 'AWAIT_WRITE_DATA', 'AWAIT_WRITE_RESPONSE',
            'CHECK_WRITE_TRANSACTION', 'ADD_READ', 'GET_EXPECTED_DATA',
            'AWAIT_READ_RESPONSE', 'CHECK_READ_TRANSACTION', 'RESET')
        state = Signal(t_state.IDLE)

        @always(clock.posedge)
        def stimulate_check():

            assert(last_written_reg_addr == expected_last_written_reg_addr)
            assert(last_written_reg_data == expected_last_written_reg_data)
            assert(write_count == expected_write_count)

            # Register checks
            # ---------------

            for reg_name in register_list:

                if register_types[reg_name] in [
                    'axi_read_write', 'axi_write_only']:

                    # Check that the writable registers are correct
                    dut_register = getattr(registers, reg_name)
                    expected_register_val = (
                        expected_writable_register_values[reg_name])

                    if reg_name in bitfields:
                        # When the register has bitfields the combined value
                        # is stored on the bitfields object as register
                        assert(dut_register.register == expected_register_val)

                        # Calculate the expected bitfield values
                        expected_bitfield_vals = (
                            extract_bitfield_values(
                                expected_register_val,
                                bitfields[reg_name]))

                        for bf_name in expected_bitfield_vals:
                            # Check that the registers are connected to the
                            # bitfields correctly
                            dut_bitfield = getattr(dut_register, bf_name)
                            expected_bitfield_val = (
                                expected_bitfield_vals[bf_name])
                            assert(dut_bitfield == expected_bitfield_val)

                    else:
                        # When the register does not have bitfields the
                        # register signal is stored on registers
                        assert(dut_register == expected_register_val)

                    if register_types[reg_name]=='axi_write_only':
                        # Write only registers should pulse the written value
                        # for 1 cycle.
                        expected_writable_register_values[reg_name] = 0

                elif registers.register_types[reg_name]=='axi_read_only':

                    if reg_name in bitfields:
                        # If the register has bitfields then we need to check
                        # that the bitfields are connected to the register
                        # correctly
                        dut_register = getattr(registers, reg_name)

                        # Extract the bitfields config for this register
                        reg_bitfields = bitfields[reg_name]

                        expected_register_val = 0

                        for bf_name in reg_bitfields:

                            bf_type = reg_bitfields[bf_name]['type']

                            if bf_type in CONST_BF_TYPES:
                                # The bitfield is a constant so get the
                                # constant value
                                bitfield_val = (
                                    reg_bitfields[bf_name]['const-value'])

                            else:
                                # Extract the input value on each bitfield
                                dut_bitfield = getattr(dut_register, bf_name)
                                bitfield_val = dut_bitfield.val

                            # Shift each bitfield val into the correct
                            # location in the expected register value.
                            expected_register_val |= (
                                bitfield_val <<
                                reg_bitfields[bf_name]['offset'])

                        # Check that the input bitfields are connected to the
                        # register correctly
                        assert(dut_register.register == expected_register_val)

                else:
                    raise ValueError('Invalid register type')

            # Idle
            # ----

            if state == t_state.IDLE:
                if random.random() < transaction_prob:
                    # Select a transaction
                    transaction = random.choice(available_transactions)

                    pending_byte_offset.next = 0

                    if transaction == 'write':
                        # Setup a valid write transaction
                        update_wr_status.next = True
                        update_register.next = True
                        pending_wr_reg_offset.next = (
                            random.choice(writable_registers_indices))
                        pending_wr_data.next = (
                            random.randrange(2**data_bitwidth))
                        expected_wr_response.next = axi_lite.OKAY

                        state.next = t_state.ADD_WRITE

                    elif transaction == 'invalid_write':
                        # Set up a write to a read only register
                        update_wr_status.next = True
                        update_register.next = False
                        pending_wr_reg_offset.next = (
                            random.choice(not_writable_registers_indices))
                        pending_wr_data.next = (
                            random.randrange(2**data_bitwidth))
                        expected_wr_response.next = axi_lite.OKAY

                        state.next = t_state.ADD_WRITE

                    elif transaction == 'invalid_address_write':
                        # Set up a write to an invalid address
                        update_wr_status.next = False
                        update_register.next = False
                        pending_wr_reg_offset.next = (
                            random.randrange(
                                n_registers, reg_offset_upper_bound))
                        pending_wr_data.next = (
                            random.randrange(2**data_bitwidth))
                        expected_wr_response.next = axi_lite.SLVERR

                        state.next = t_state.ADD_WRITE

                    elif transaction == 'non_word_aligned_address_write':
                        # Set up a write with an address which is not word
                        # aligned
                        update_wr_status.next = False
                        update_register.next = False
                        pending_wr_reg_offset.next = (
                            random.randrange(
                                n_registers, reg_offset_upper_bound))
                        pending_byte_offset.next = (
                            random.randrange(1, byte_offset_upper_bound))
                        pending_wr_data.next = (
                            random.randrange(2**data_bitwidth))
                        expected_wr_response.next = axi_lite.SLVERR

                        state.next = t_state.ADD_WRITE

                    elif transaction == 'read':
                        # Set up a read from a valid address.
                        valid_read.next = True
                        pending_rd_reg_offset.next = (
                            random.choice(readable_registers_indices))
                        expected_rd_response.next = axi_lite.OKAY

                        state.next = t_state.ADD_READ

                    elif transaction == 'invalid_read':
                        # Set up a read from a write only register.
                        valid_read.next = False
                        pending_rd_reg_offset.next = (
                            random.choice(not_readable_registers_indices))
                        expected_rd_response.next = axi_lite.OKAY

                        state.next = t_state.ADD_READ

                    elif transaction == 'invalid_address_read':
                        # Set up a read from an invalid address.
                        valid_read.next = False
                        pending_rd_reg_offset.next = (
                            random.randrange(
                                n_registers, reg_offset_upper_bound))
                        expected_rd_response.next = axi_lite.SLVERR

                        state.next = t_state.ADD_READ

                    elif transaction == 'non_word_aligned_address_read':
                        # Set up a read with an address which is not word
                        # aligned
                        valid_read.next = False
                        pending_rd_reg_offset.next = (
                            random.randrange(
                                n_registers, reg_offset_upper_bound))
                        pending_byte_offset.next = (
                            random.randrange(1, byte_offset_upper_bound))
                        expected_rd_response.next = axi_lite.SLVERR

                        state.next = t_state.ADD_READ

                    else:
                        raise ValueError('Invalid transaction')

            # Write transaction sequence
            # --------------------------

            if state == t_state.ADD_WRITE:
                # Set up the test framework to wait for the address and data
                test_data['wr_address_received'] = False
                test_data['wr_data_received'] = False

                wr_reg_offset = copy.copy(pending_wr_reg_offset.val)
                wr_byte_offset = copy.copy(pending_byte_offset.val)
                wr_data = copy.copy(pending_wr_data.val)

                wr_addr = addr_remap_ratio*wr_reg_offset + wr_byte_offset

                # Add the write transaction to the queue.
                axi_lite_bfm.add_write_transaction(
                    write_address=wr_addr,
                    write_data=wr_data,
                    write_strobes=None,
                    write_protection=None,
                    address_delay=random.randint(0, 15),
                    data_delay=random.randint(0, 15),
                    response_ready_delay=random.randint(10, 25))

                state.next = t_state.AWAIT_WRITE_DATA

            elif state == t_state.AWAIT_WRITE_DATA:

                if update_wr_status or update_register:
                    # Valid write so monitor the AXI signals to get the timing
                    # correct for updating the expected register value.

                    if (axi_lite_interface.AWVALID and
                        axi_lite_interface.AWREADY):
                        # Write address handshake has occurred.
                        test_data['wr_address_received'] = True

                    if (axi_lite_interface.WVALID and
                        axi_lite_interface.WREADY):
                        # Write data handshake has occurred.
                        test_data['wr_data_received'] = True

                    if (test_data['wr_address_received'] and
                        test_data['wr_data_received']):
                        # Data and address have been received and we expect a
                        # write so update the expected register value
                        reg_offset = pending_wr_reg_offset.val
                        reg_name = register_list[reg_offset]
                        wr_data = copy.copy(pending_wr_data.val)

                        if update_register:
                            expected_writable_register_values[reg_name] = (
                                wr_data)

                        if update_wr_status:
                            # Update the expected last written signals and
                            # write count
                            expected_last_written_reg_addr.next = (
                                reg_offset*addr_remap_ratio)
                            expected_last_written_reg_data.next = wr_data
                            expected_write_count.next = (
                                expected_write_count + 1)

                        state.next = t_state.AWAIT_WRITE_RESPONSE

                else:
                    # Not a valid write to move on immediately to wait for the
                    # response
                    state.next = t_state.AWAIT_WRITE_RESPONSE

            elif state == t_state.AWAIT_WRITE_RESPONSE:
                if axi_lite_interface.BVALID and axi_lite_interface.BREADY:
                    # Response has been received.
                    state.next = t_state.CHECK_WRITE_TRANSACTION

            elif state == t_state.CHECK_WRITE_TRANSACTION:
                try:
                    # Try to get the response from the responses Queue.
                    # Include a timeout to prevent the system hanging if
                    # queue is empty.
                    received_response = (
                        axi_lite_bfm.write_responses.get(True, 3))

                except queue.Empty:
                    raise AssertionError(
                        'axi_lite_handler has failed to respond correctly')

                # Check that the write response is correct
                assert(received_response['wr_resp'] == expected_wr_response)

                self.test_count += 1

                state.next = t_state.IDLE

            # Read transaction sequence
            # -------------------------

            elif state == t_state.ADD_READ:
                rd_reg_offset = copy.copy(pending_rd_reg_offset.val)
                rd_byte_offset = copy.copy(pending_byte_offset.val)

                rd_addr = addr_remap_ratio*rd_reg_offset + rd_byte_offset

                # Add the read transaction to the queue.
                axi_lite_bfm.add_read_transaction(
                    read_address=rd_addr,
                    read_protection=None,
                    address_delay=random.randint(0, 15),
                    data_delay=random.randint(0, 15))

                state.next = t_state.GET_EXPECTED_DATA

            elif state == t_state.GET_EXPECTED_DATA:
                if axi_lite_interface.ARVALID and axi_lite_interface.ARREADY:
                    if valid_read:
                        # Get the register name
                        reg_name = register_list[pending_rd_reg_offset.val]

                        reg_object = getattr(registers, reg_name)

                        if reg_name in bitfields:
                            # We check above that the register signal is
                            # carrying the bitfields concatenated correctly so
                            # we can just use the register value
                            register = getattr(reg_object, 'register')
                            expected_rd_data.next = register.val

                        else:
                            # Get the register value
                            expected_rd_data.next = reg_object.val

                    else:
                        # An invalid read so read data should be 0
                        expected_rd_data.next = 0

                    state.next = t_state.AWAIT_READ_RESPONSE

            elif state == t_state.AWAIT_READ_RESPONSE:
                if axi_lite_interface.RVALID and axi_lite_interface.RREADY:
                    # Response has been received.
                    state.next = t_state.CHECK_READ_TRANSACTION

            elif state == t_state.CHECK_READ_TRANSACTION:
                try:
                    # Try to get the response from the responses Queue.
                    # Include a timeout to prevent the system hanging if
                    # queue is empty.
                    received_response = (
                        axi_lite_bfm.read_responses.get(True, 3))

                except queue.Empty:
                    raise AssertionError(
                        'axi_lite_handler has failed to respond correctly')

                # Check that the dut came back with the correct read response
                # and data.
                assert(received_response['rd_resp'] == expected_rd_response)
                assert(received_response['rd_data'] == expected_rd_data)

                self.test_count += 1

                state.next = t_state.IDLE

            elif state == t_state.RESET:
                # Clear any write responses in the axi_lite_bfm
                while not axi_lite_bfm.write_responses.empty():
                    try:
                        axi_lite_bfm.write_responses.get(block=False)
                    except Empty:
                        continue

                # Clear any read responses in the axi_lite_bfm
                while not axi_lite_bfm.read_responses.empty():
                    try:
                        axi_lite_bfm.read_responses.get(block=False)
                    except Empty:
                        continue

                state.next = t_state.IDLE

            if not axil_nreset:
                # Clear any write transactions in the axi_lite_bfm
                while not axi_lite_bfm.write_transactions.empty():
                    try:
                        axi_lite_bfm.write_transactions.get(block=False)
                    except Empty:
                        continue

                # Clear any read transactions in the axi_lite_bfm
                while not axi_lite_bfm.read_transactions.empty():
                    try:
                        axi_lite_bfm.read_transactions.get(block=False)
                    except Empty:
                        continue

                state.next = t_state.RESET

        return_objects.append(stimulate_check)

        return return_objects

    def base_test(
        self, n_registers_lower_bound=1, n_registers_upper_bound=21,
        data_bitwidth=32, addr_bitwidth=8, write_count_bitwidth=32,
        available_register_types=None, random_initial_values=False,
        random_bitfields=False, stim_random_resets=False,
        stim_invalid_reads=False, stim_invalid_writes=False,
        stim_invalid_addresses=False, stim_non_word_aligned_addresses=False,
        include_all_register_types=False):

        dut_args, dut_arg_types = (
            test_args_setup(
                n_registers_lower_bound=n_registers_lower_bound,
                n_registers_upper_bound=n_registers_upper_bound,
                available_register_types=available_register_types,
                random_initial_values=random_initial_values,
                random_bitfields=random_bitfields,
                include_all_register_types=include_all_register_types,
                data_bitwidth=data_bitwidth, addr_bitwidth=addr_bitwidth,
                write_count_bitwidth=write_count_bitwidth))

        if not self.testing_using_vivado:
            cycles = 100000
            n_tests = 60
        else:
            cycles = 50000
            n_tests = 20

        @block
        def stimulate_check(**dut_args):

            return_objects = []

            return_objects.append(self.end_tests(n_tests, **dut_args))
            return_objects.append(
                self.stim_reset(stim_random_resets, **dut_args))
            return_objects.append(
                self.axi_lite_handler_stim_check(
                    stim_invalid_reads, stim_invalid_writes,
                    stim_invalid_addresses, stim_non_word_aligned_addresses,
                    **dut_args))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, dut_args,
            dut_arg_types, custom_sources=[(stimulate_check, (), dut_args)])

        self.assertTrue(self.tests_complete)

        self.assertEqual(dut_outputs, ref_outputs)

    def test_single_read_write_register(self):
        ''' It should be possible to write to and read from AXI read-write
        registers.

        When an AXI write transaction addresses an AXI read-write register,
        the `axi_lite_handler` should write the data to the register at the
        specified address. The register should retain this data until it is
        overwritten by another write to that address.

        If the data arrives before the address, the `axi_lite_handler` should
        buffer the data until the address arrives. On receipt of the address,
        it should then write to the appropriate register.

        The `axi_lite_handler` should respond with a
        `kea.hdl.axi.axi_lite.OKAY`.

        When an AXI read transaction addresses an AXI read-write register,
        the `axi_lite_handler` should respond with the data stored in the
        register at the specified address and a `kea.hdl.axi.axi_lite.OKAY`.

        When the `axi_lite_handler` writes to an AXI read-write register it
        should also update the `last_written_reg_addr` to the address of the
        register, update `last_written_reg_data` to the data written to the
        register and increment the `write_count`.
        '''
        self.base_test(
            n_registers_lower_bound=1,
            n_registers_upper_bound=2,
            available_register_types=['axi_read_write'])

    def test_single_write_only_register(self):
        ''' It should be possible to write to an AXI write-only register.

        When an AXI write transaction addresses an AXI write-only register,
        the `axi_lite_handler` should write the data to the register at the
        specified address. The register should retain this data for one cycle
        and then return to 0.

        If the data arrives before the address, the `axi_lite_handler` should
        buffer the data until the address arrives. On receipt of the address,
        it should then write to the appropriate register.

        The `axi_lite_handler` should respond with a
        `kea.hdl.axi.axi_lite.OKAY`.

        When the `axi_lite_handler` writes to an AXI read-write register it
        should also update the `last_written_reg_addr` to the address of the
        register, update `last_written_reg_data` to the data written to the
        register and increment the `write_count`.
        '''
        self.base_test(
            n_registers_lower_bound=1,
            n_registers_upper_bound=2,
            available_register_types=['axi_write_only'])

    def test_single_read_only_register(self):
        ''' It should be possible to read from an AXI read-only register.

        When an AXI read transaction addresses an AXI read-only register,
        the `axi_lite_handler` should respond with the data stored in the
        register at the specified address and a `kea.hdl.axi.axi_lite.OKAY`.

        This register is read only from the perspective of the AXIS master.
        The returned read data should be the value on the register signal when
        `axi_lite_interface.ARREADY` and `axi_lite_interface.ARVALID` are both
        high.
        '''
        self.base_test(
            n_registers_lower_bound=1,
            n_registers_upper_bound=2,
            available_register_types=['axi_read_only'])

    def test_multiple_read_write_registers(self):
        ''' The `axi_lite_handler` should function correctly when `registers`
        contains multiple AXI read-write registers.
        '''
        self.base_test(
            n_registers_lower_bound=2,
            n_registers_upper_bound=21,
            available_register_types=['axi_read_write'])

    def test_multiple_write_only_registers(self):
        ''' The `axi_lite_handler` should function correctly when `registers`
        contains multiple AXI write-only registers.
        '''
        self.base_test(
            n_registers_lower_bound=2,
            n_registers_upper_bound=21,
            available_register_types=['axi_write_only'])

    def test_multiple_read_only_registers(self):
        ''' The `axi_lite_handler` should function correctly when `registers`
        contains multiple AXI read-only registers.
        '''
        self.base_test(
            n_registers_lower_bound=2,
            n_registers_upper_bound=21,
            available_register_types=['axi_read_only'])

    def test_random_register_types(self):
        ''' The `axi_lite_handler` should function correctly when `registers`
        contains multiple registers of varying types.
        '''
        self.base_test(
            n_registers_lower_bound=5,
            n_registers_upper_bound=41)

    def test_invalid_writes(self):
        ''' When an AXI write transaction addresses an AXI read-only register,
        the `axi_lite_handler` should not update the register signal and
        should respond with `axi_lite_interface.BRESP` set to
        `kea.hdl.axi.axi_lite.OKAY`.

        When the `axi_lite_handler` receives an AXI transaction which attempts
        to write to an AXI read-only register it should update the
        `last_written_reg_addr` to the address of the register, update
        `last_written_reg_data` to the data in the AXI lite transaction and
        increment the `write_count`.
        '''
        self.base_test(
            n_registers_lower_bound=5,
            n_registers_upper_bound=21,
            available_register_types=['axi_read_only'],
            stim_invalid_writes=True)

    def test_invalid_reads(self):
        ''' When an AXI read transaction addresses an AXI write-only register,
        the `axi_lite_handler` should respond with `axi_lite_interface.RDATA`
        set to 0 and the `axi_lite_interface.RRESP` set to
        `kea.hdl.axi.axi_lite.OKAY`.
        '''
        self.base_test(
            n_registers_lower_bound=5,
            n_registers_upper_bound=21,
            available_register_types=['axi_write_only'],
            stim_invalid_reads=True)

    def test_invalid_addresses(self):
        ''' When an AXI write transaction specifies an address which is not a
        register (if the address is greater than the number of registers
        specified by `registers`), the `axi_lite_handler` should respond with
        `axi_lite_interface.BRESP` set to `kea.hdl.axi.axi_lite.SLVERR`.

        When an AXI read transaction specifies an address which is not a
        register (if the address is greater than the number of registers
        specified by `registers`), the `axi_lite_handler` should respond with
        `axi_lite_interface.RDATA` set to 0 and the `axi_lite_interface.RRESP`
        set to `kea.hdl.axi.axi_lite.SLVERR`.

        When an AXI write transaction specifies an address which is not a
        register the `axi_lite_handler` should not update the
        `last_written_reg_addr`, `last_written_reg_data` or the `write_count`.
        '''
        self.base_test(
            n_registers_lower_bound=5,
            n_registers_upper_bound=21,
            stim_invalid_addresses=True)

    def test_non_word_aligned_addresses(self):
        ''' The `axi_lite_handler` should store the data in registers which
        are `registers.register_width` bits wide.

        The AXI lite interface addresses are byte aligned. The
        `axi_lite_handler` should translate from the byte aligned addresses
        to word aligned addresses. The `axi_lite_handler` requires that the
        register bit width is a power of 2, is a multiple of 8 and is greater
        than 8. This means that we can translate from byte to word alignment
        by stripping n least significant bits of the AXI lite address.

        For example:

            - Register bitwidth: 32 bits
            - 32 / 8 = 4
            - log2(4) = 2 bits
            - The 2 least significant bits of the address specify the byte
            within the word.

        When an AXI write transaction specifies an address which is not
        word aligned (the byte offset bits are not 0), the `axi_lite_handler`
        should respond with `axi_lite_interface.BRESP` set to
        `kea.hdl.axi.axi_lite.SLVERR`.

        When an AXI read transaction specifies an address which is not word
        aligned (the byte offset bits are not 0), the `axi_lite_handler`
        should respond with `axi_lite_interface.RDATA` set to 0 and the
        `axi_lite_interface.RRESP` set to `kea.hdl.axi.axi_lite.SLVERR`.

        When an AXI write transaction specifies an address which is not word
        aligned the `axi_lite_handler` should not update the
        `last_written_reg_addr`, `last_written_reg_data` or the `write_count`.
        '''
        self.base_test(
            n_registers_lower_bound=5,
            n_registers_upper_bound=21,
            stim_non_word_aligned_addresses=True)

    def test_initial_values(self):
        ''' The `registers` argument can optionally have been set up with
        initial values. If provided, these initial values will have been used
        by `registers` when creating the register signals. Only
        `axi_read_write` registers can have initial values.

        The `axi_lite_handler` should not update the register values from the
        initial value until it receives a transaction that writes to that
        address.
        '''
        self.base_test(
            n_registers_lower_bound=5,
            n_registers_upper_bound=21,
            available_register_types=['axi_read_write'],
            random_initial_values=True)

    def test_bitfields(self):
        ''' The `registers` argument can optionally have been set up with
        `bitfields`. If provided, this `bitfields` argument defines the
        bitfields in the specified register and the `registers` will create
        connectors performing the following:

            - `axi_read_write`: The bitfields should be directly connected to
            and driven by the register bits specified in the `bitfields`
            argument.
            - `axi_write_only`: The bitfields should be directly connected to
            and driven by the register bits specified in the `bitfields`
            argument.
            - `axi_read_only`: The bitfields should be directly connected to
            and should drive the register bits specified in the `bitfields`
            argument. Note: `axi_read_only` registers can have bitfields which
            are constants (`const-bool or `const-uint`). These constant
            bitfields should be held at the `const-value` specified by
            `bitfields`.

        The `axi_lite_handler` should instantiate these connectors so the
        specified `bitfields` are driven correctly.
        '''
        self.base_test(
            n_registers_lower_bound=10,
            n_registers_upper_bound=21,
            random_bitfields=True,
            include_all_register_types=True)

    def test_bitfields_and_initial_values(self):
        ''' When set, the initial value on an `axi_read_write` register should
        correctly drive any bitfields on the register.
        '''
        self.base_test(
            n_registers_lower_bound=5,
            n_registers_upper_bound=21,
            available_register_types=['axi_read_write'],
            random_initial_values=True,
            random_bitfields=True)

    def test_random_combination(self):
        ''' The `axi_lite_handler` should function correctly when instantiated
        with a random combination of register properties.
        '''

        self.base_test(
            n_registers_lower_bound=10,
            n_registers_upper_bound=31,
            random_initial_values=True,
            random_bitfields=True,
            stim_invalid_reads=True,
            stim_invalid_writes=True,
            stim_invalid_addresses=True,
            stim_non_word_aligned_addresses=True,
            include_all_register_types=True)

    def test_random_address_bitwidth(self):
        ''' The `axi_lite_handler` should function correctly with any
        bitwidth of `axi_lite_interface.AWADDR` and
        `axi_lite_interface.ARADDR`.
        '''
        data_bitwidth = 32
        addr_remap_ratio = data_bitwidth//8
        byte_to_word_shift = int(log(addr_remap_ratio, 2))
        addr_bitwidth = (
            random.randrange(byte_to_word_shift+1, byte_to_word_shift+5))
        n_registers_upper_bound = 2**(addr_bitwidth-byte_to_word_shift)
        n_registers = random.randrange(1, n_registers_upper_bound)

        self.base_test(
            n_registers_lower_bound=n_registers,
            n_registers_upper_bound=n_registers+1,
            data_bitwidth=data_bitwidth,
            addr_bitwidth=addr_bitwidth)

    def test_sixty_four_bit_data(self):
        ''' The `axi_lite_handler` should function correctly when the bitwidth
        of `axi_lite_interface.WDATA` and `axi_lite_interface.RDATA` is set to
        64 bits.
        '''
        self.base_test(data_bitwidth=64)

    def test_write_count_wrapping(self):
        ''' The `write_count` should wrap around when it reaches it's maximum
        value.
        '''
        self.base_test(write_count_bitwidth=3)

    def test_axil_nreset(self):
        ''' When `axil_nreset` is set low the `axi_lite_handler` should
        set:

            - `axi_lite_interface.AWREADY` low.
            - `axi_lite_interface.WREADY` low.
            - `axi_lite_interface.BVALID` low.
            - `axi_lite_interface.ARREADY` low.
            - `axi_lite_interface.RVALID` low.

        The `axi_lite_handler` should return to idle and await the next AXI
        transaction.

        It may only drive these signals high again after after the
        `axil_nreset` signal goes high.

        The reset should have no effect on the data stored on the registers.

        If the `axil_nreset` signal is set low in the middle of an AXI
        transaction then the transaction should be dropped (the register
        should not be updated in the case of a write and the data should not
        be returned in the case of a read).
        '''

        self.base_test(
            n_registers_lower_bound=5,
            n_registers_upper_bound=31,
            random_initial_values=True,
            random_bitfields=True,
            stim_random_resets=True,
            stim_invalid_reads=True,
            stim_invalid_writes=True,
            stim_invalid_addresses=True,
            stim_non_word_aligned_addresses=True,
            include_all_register_types=True)

class TestAxiLiteHandlerVivadoVhdl(
    KeaVivadoVHDLTestCase, TestAxiLiteHandler):
    pass

class TestAxiLiteHandlerVivadoVerilog(
    KeaVivadoVerilogTestCase, TestAxiLiteHandler):
    pass
