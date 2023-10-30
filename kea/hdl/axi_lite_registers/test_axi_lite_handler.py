import unittest
import random
import string
import copy

from ._registers import Registers
from ._axi_lite_handler import axi_lite_handler
from .test_registers import create_bitfields_config
from kea.hdl.axi import axi_lite, AxiLiteInterface, AxiLiteMasterBFM
from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from myhdl import *
from math import log
import numpy as np

try:
    import Queue as queue
except ImportError:
    import queue


class TestAxiLiteHandlerInterfaceSimulation(KeaTestCase):
    ''' The block should implement various bits of functionality that should
    be verifiable through simulation.
    '''

    def setUp(self):

        self.available_register_types = [
            'axi_read_write', 'axi_write_only', 'axi_read_only']

        self.clock = Signal(bool(0))
        self.axil_nreset = Signal(bool(0))


    def test_single_register(self):
        ''' The system should create a single register.
        '''

        data_width = 32
        addr_width = 4

        n_registers = 1
        register_list = []

        # Create a list of registers with random names of 5 character length.
        for i in range(n_registers):
            register_list.append(
                ''.join(random.choice(string.ascii_lowercase)
                        for i in range(5)))

        # Create the registers without passing a dict of register types
        registers = Registers(register_list)

        # Create a valid axi lite interface.
        axi_lite_interface = AxiLiteInterface(data_width, addr_width)

        axi_lite_registers = axi_lite_handler(
            self.clock, self.axil_nreset, axi_lite_interface, registers)

    def test_non_AxiLiteInterface(self):
        ''' The system should raise a ValueError if the ``axi_lite_interface``
        argument of ``axi_lite_handler`` is not an instance of
        ``AxiLiteInterface``.
        '''

        n_registers = 20
        register_list = []

        # Create a list of registers with random names of 5 character length.
        for i in range(n_registers):
            register_list.append(
                ''.join(random.choice(string.ascii_lowercase)
                        for i in range(5)))

        # Create the registers.
        registers = Registers(register_list)

        # Create a variable which is not an instance of AxiLiteInterface.
        non_axi_lite_interface = random.randint(0, 100)

        # Check that the system errors when axi_lite_interface is not an
        # instance of AxiLiteInterface
        self.assertRaisesRegex(ValueError,
                               ('axi_lite_interface needs to be an instance '
                               'of AxiLiteInterface'),
                               axi_lite_handler, self.clock, self.axil_nreset,
                               non_axi_lite_interface, registers)

    def test_non_registers(self):
        ''' The system should raise a ValueError if the ``registers`` argument
        of ``axi_lite_handler`` is not an instance of ``Registers``.
        '''
        data_width = 32
        addr_width = 4

        # Create a valid axi lite interface.
        axi_lite_interface = AxiLiteInterface(data_width, addr_width)

        # Create a variable which is not an instance of Registers.
        non_registers = random.randint(0, 100)

        # Check that the system errors when registers is not an instance of
        # Registers
        self.assertRaisesRegex(ValueError,
                               ('registers need to be an instance of '
                                'Registers'),
                               axi_lite_handler, self.clock, self.axil_nreset,
                               axi_lite_interface, non_registers)

    def test_n_registers_exceeds_addr_space(self):
        ''' The system should error if the number of registers being created
        exceeds the address space.
        '''

        data_width = 32
        addr_width = 4

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

        # Create a valid axi lite interface.
        axi_lite_interface = AxiLiteInterface(data_width, addr_width)

        # Check that the system errors when the number of registers exceeds
        # the available address space
        self.assertRaisesRegex(ValueError,
                               ('n_registers too large for the address width'),
                               axi_lite_handler, self.clock, self.axil_nreset,
                               axi_lite_interface, registers)

@block
def rw_testbench(
    test_class, clock, axil_nreset, axi_lite_interface, registers,
    test_checks, initial_values=None):

    axi_lite_bfm = AxiLiteMasterBFM()
    master_bfm = axi_lite_bfm.model(clock, axil_nreset, axi_lite_interface)

    add_write_transaction_prob = 0.05
    add_read_transaction_prob = 0.05

    t_check_state = enum(
        'IDLE','ADD_WRITE', 'ADD_READ', 'AWAIT_WRITE_TRANSACTION',
        'AWAIT_READ_TRANSACTION', 'CHECK_WRITE_TRANSACTION',
        'CHECK_READ_TRANSACTION')
    check_state = Signal(t_check_state.IDLE)

    test_data = {'wr_address': 0,
                 'wr_address_received': False,
                 'wr_data': 0,
                 'wr_data_received': False,
                 'write_response': None,
                 'rd_address': 0,
                 'expected_rd_data': 0,
                 'read_response': None,}

    if initial_values is None:
        initial_values = {}

    # Create an expected_register_values dict which uses the names in
    # the list of registers as keys.
    expected_register_values = {
        key: initial_values[key] if key in initial_values else 0
        for key in test_class.register_list}

    @always(clock.posedge)
    def stimulate_check():

        # Check the register values every clock cycle.
        for register_key in test_class.register_list:
            assert(expected_register_values[register_key] ==
                   getattr(registers, register_key))

        if check_state == t_check_state.IDLE:
            if random.random() < add_write_transaction_prob:
                check_state.next = t_check_state.ADD_WRITE

            elif random.random() < add_read_transaction_prob:
                check_state.next = t_check_state.ADD_READ

        # Write transaction sequence
        # --------------------------

        if check_state == t_check_state.ADD_WRITE:
            # At a random time set up an axi lite write
            # transaction
            test_data['wr_address'] = random.choice(
                test_class.read_write_registers_indices)
            test_data['wr_data'] = random.randint(
                0, 2**test_class.data_width-1)

            # Add the write transaction to the queue.
            axi_lite_bfm.add_write_transaction(
                write_address=(
                    test_class.addr_remap_ratio*test_data['wr_address']),
                write_data=test_data['wr_data'],
                write_strobes=None,
                write_protection=None,
                address_delay=random.randint(0, 15),
                data_delay=random.randint(0, 15),
                response_ready_delay=random.randint(10, 25))

            check_state.next = t_check_state.AWAIT_WRITE_TRANSACTION

        elif check_state == t_check_state.AWAIT_WRITE_TRANSACTION:

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
                # Both data and address received so update the
                # expected register value
                expected_register_values[
                    test_class.register_list[test_data['wr_address']]] = (
                        test_data['wr_data'])

            if (axi_lite_interface.BVALID and
                axi_lite_interface.BREADY):
                # Response has been received.
                check_state.next = (
                    t_check_state.CHECK_WRITE_TRANSACTION)

        elif check_state == t_check_state.CHECK_WRITE_TRANSACTION:
            try:
                # Try to get the response from the responses Queue.
                # Include a timeout to prevent the system hanging if
                # queue is empty.
                test_data['write_response'] = (
                    axi_lite_bfm.write_responses.get(True, 3))
            except queue.Empty:
                raise AssertionError(
                    'axi_lite_handler has failed to respond correctly')

            test_checks['test_run'] = True

            # Check that the write response is not an error.
            assert(test_data['write_response']['wr_resp']==0)

            test_data['wr_address_received'] = False
            test_data['wr_data_received'] = False

            check_state.next = t_check_state.IDLE

        # Read transaction sequence
        # -------------------------

        elif check_state == t_check_state.ADD_READ:
            # At random times set up an axi lite read transaction
            test_data['rd_address'] = random.choice(
                    test_class.read_write_registers_indices)

            # Get the register value.
            test_data['expected_rd_data'] = copy.copy(getattr(
                registers,test_class.register_list[
                    test_data['rd_address']]).val)

            # Add the read transaction to the queue.
            axi_lite_bfm.add_read_transaction(
                read_address=(
                    test_class.addr_remap_ratio*test_data['rd_address']),
                read_protection=None,
                address_delay=random.randint(0, 15),
                data_delay=random.randint(0, 15))

            check_state.next = t_check_state.AWAIT_READ_TRANSACTION

        elif check_state == t_check_state.AWAIT_READ_TRANSACTION:
            if (axi_lite_interface.RVALID and
                axi_lite_interface.RREADY):
                # Response has been received.
                check_state.next = (
                    t_check_state.CHECK_READ_TRANSACTION)

        elif check_state == t_check_state.CHECK_READ_TRANSACTION:
            try:
                # Try to get the response from the responses Queue.
                # Include a timeout to prevent the system hanging if
                # queue is empty.
                test_data['read_response'] = (
                    axi_lite_bfm.read_responses.get(True, 3))
            except queue.Empty:
                raise AssertionError(
                    'axi_lite_handler has failed to respond correctly')

            test_checks['test_run'] = True

            # Check that the read responds with the correct data.
            assert(test_data['read_response']['rd_data']==
                   test_data['expected_rd_data'])
            # Check that the read response is not an error.
            assert(test_data['read_response']['rd_resp']==0)

            check_state.next = t_check_state.IDLE

    return stimulate_check, master_bfm


class TestAxiLiteHandlerBehaviouralSimulation(KeaTestCase):
    ''' The axi lite handler is used for communication between the PS and the
    PL. AXI lite can be used to read/write single words from/to the PL. The
    handler should create registers with an axi interface and a parallel
    interface. These registers can take any of the following forms:

        Writeable from axi - The parallel interface is read only in the PL.
        Readable from axi - The parallel interface is write only in the PL.
        Read-write from axi - The parallel interface is read only in the PL.

    The registers will store any value written to them until it is
    overwritten.
    '''

    def setUp(self):

        self.available_register_types = [
            'axi_read_write', 'axi_write_only', 'axi_read_only']

        self.clock = Signal(bool(0))
        self.axil_nreset = Signal(bool(1))

        self.data_width = 32
        self.addr_width = 7

        # Need to remap the address from words to bytes to work with the
        # software on the PS
        self.addr_remap_ratio = self.data_width//8

        byte_to_word_shift = int(log(self.addr_remap_ratio, 2))

        self.n_registers = 17
        self.register_list = []

        max_addressable = 2**(self.addr_width - byte_to_word_shift)

        self.valid_addresses = list(set(range(self.n_registers)))
        self.invalid_addresses = list(
            set(range(max_addressable)).difference(self.valid_addresses))

        # Create a list of registers with random names of 5 character length.
        for i in range(self.n_registers):
            self.register_list.append(
                ''.join(random.choice(string.ascii_lowercase)
                        for i in range(5)))

        # Create a register_types dict which uses the names in the list of
        # registers as keys.
        # We firstly make sure that at least one of each type is created.
        self.register_types = {
            key: reg_type for key, reg_type in zip(
                self.register_list, self.available_register_types)}

        # Now use a random choice for the rest
        self.register_types.update({
            key: random.choice(self.available_register_types) for key in
            self.register_list[len(self.available_register_types):]})

        self.axi_lite_interface = AxiLiteInterface(
            self.data_width, self.addr_width, use_AWPROT=False,
            use_ARPROT=False, use_WSTRB=False)
        self.registers = Registers(
            self.register_list, self.register_types,
            register_width=self.data_width)

        # Create lists of register_list indices to show which registers are
        # readable and which are writeable.
        self.writeable_registers_indices = []
        self.readable_registers_indices = []
        self.read_only_registers_indices = []
        self.write_only_registers_indices = []
        self.read_write_registers_indices = []

        for n, value in enumerate(self.register_list):
            if self.registers.register_types[value]=='axi_read_write':
                # The register is readable and writeable so add the index to
                # both the writeable and readable registers list.
                self.writeable_registers_indices.append(n)
                self.readable_registers_indices.append(n)
                self.read_write_registers_indices.append(n)

            elif self.registers.register_types[value]=='axi_write_only':
                # The register is writeable only so add the index to just the
                # writeable registers list.
                self.writeable_registers_indices.append(n)
                self.write_only_registers_indices.append(n)

            elif self.registers.register_types[value]=='axi_read_only':
                # The register is readable only so add the index to just the
                # readable registers list.
                self.readable_registers_indices.append(n)
                self.read_only_registers_indices.append(n)

        self.writeable_registers = [
            self.register_list[n] for n in self.writeable_registers_indices]
        self.readable_registers = [
            self.register_list[n] for n in self.readable_registers_indices]
        self.read_only_registers = [
            self.register_list[n] for n in self.read_only_registers_indices]
        self.write_only_registers = [
            self.register_list[n] for n in self.write_only_registers_indices]
        self.read_write_registers = [
            self.register_list[n] for n in self.read_write_registers_indices]

        self.default_args = {
            'clock': self.clock,
            'axil_nreset': self.axil_nreset,
            'axi_lite_interface': self.axi_lite_interface,
            'registers': self.registers,}

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

        registers_interface_types = {
            key: ('custom' if (
                self.registers.register_types[key]=='axi_read_only') else (
                    'output')) for key in self.register_list}

        self.default_arg_types = {
            'clock': 'clock',
            'axil_nreset': 'custom',
            'axi_lite_interface': axi_lite_interface_types,
            'registers': registers_interface_types,}


    def test_axil_nreset(self):
        ''' On axil_nreset the system should drive RVALID and BVALID low.

        It may only next drive the valid signals one rising edge after the
        axil_nreset signal goes high.

        We do not care about the other signals.
        '''

        cycles = 4000

        @block
        def testbench(clock, axil_nreset, axi_lite_interface, registers):

            axi_lite_bfm = AxiLiteMasterBFM()
            master_bfm = axi_lite_bfm.model(
                self.clock, self.axil_nreset, self.axi_lite_interface)

            axil_nreset_low_prob = 0.05
            axil_nreset_high_prob = 0.1
            add_write_transaction_prob = 0.05
            add_read_transaction_prob = 0.05

            t_check_state = enum('IDLE', 'CHECK_RESET')
            check_state = Signal(t_check_state.IDLE)

            @always(clock.posedge)
            def stimulate():

                # Randomly wiggle the axil_nreset line.
                if not self.axil_nreset and (
                    random.random() < axil_nreset_high_prob):
                    self.axil_nreset.next = True
                elif self.axil_nreset and (
                    random.random() < axil_nreset_low_prob):
                    self.axil_nreset.next = False

                if random.random() < add_write_transaction_prob:
                    # At random times set up an axi lite write transaction
                    axi_lite_bfm.add_write_transaction(
                        write_address=self.addr_remap_ratio*random.choice(
                            self.writeable_registers_indices),
                        write_data=random.randint(0, 2**self.data_width-1),
                        write_strobes=None,
                        write_protection=None,
                        address_delay=random.randint(0, 15),
                        data_delay=random.randint(0, 15),
                        response_ready_delay=random.randint(10, 25))

                if random.random() < add_read_transaction_prob:
                    # At random times set up an axi lite read transaction
                    axi_lite_bfm.add_read_transaction(
                        read_address=self.addr_remap_ratio*random.choice(
                            self.readable_registers_indices),
                        read_protection=None,
                        address_delay=random.randint(0, 15),
                        data_delay=random.randint(0, 15))

                try:
                    # Try to remove any responses from the responses Queue.
                    # In this test we are not actually interested in the
                    # response but we want to prevent the queue from filling
                    # up
                    axi_lite_bfm.write_responses.get(False)
                except queue.Empty:
                    pass

                try:
                    # Try to remove any responses from the responses Queue.
                    # In this test we are not actually interested in the
                    # response but we want to prevent the queue from filling
                    # up
                    axi_lite_bfm.read_responses.get(False)
                except queue.Empty:
                    pass

            @always(clock.posedge)
            def check():

                if check_state == t_check_state.IDLE:
                    if not self.axil_nreset:
                        # Reset has been received so move onto the
                        # check_axil_nreset state.
                        check_state.next = t_check_state.CHECK_RESET

                elif check_state == t_check_state.CHECK_RESET:
                    assert(
                        self.axi_lite_interface.RVALID==False)
                    assert(
                        self.axi_lite_interface.BVALID==False)

                    if self.axil_nreset:
                        # No longer being reset so return to IDLE
                        check_state.next = t_check_state.IDLE

            return stimulate, check, master_bfm

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, self.default_args,
            self.default_arg_types,
            custom_sources=[(testbench, (), self.default_args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_successful_write_to_read_write_register(self):
        ''' On receipt of an axi write to an axi read-write register the
        axi_lite_handler should write the packet to that register.

        If the master, sends the data before the address, the axi_lite_handler
        should buffer the data whilst it waits for the address. On receipt
        of the address, it should then write to the appropriate register.
        '''

        cycles = 4000

        test_checks = {'test_run': False}

        @block
        def testbench(clock, axil_nreset, axi_lite_interface, registers):

            axi_lite_bfm = AxiLiteMasterBFM()
            master_bfm = axi_lite_bfm.model(clock, axil_nreset, axi_lite_interface)

            add_write_transaction_prob = 0.05

            t_check_state = enum(
                'IDLE','AWAIT_TRANSACTION', 'CHECK_TRANSACTION')
            check_state = Signal(t_check_state.IDLE)

            test_data = {'address': 0,
                         'address_received': False,
                         'data': 0,
                         'data_received': False,
                         'write_response': None,}

            # Create an expected_register_values dict which uses the names in
            # the list of registers as keys.
            expected_register_values = {
                key: 0 for key in self.register_list}

            @always(clock.posedge)
            def stimulate_check():

                # Check the register values every clock cycle.
                for register_key in self.read_write_registers:
                    assert(expected_register_values[register_key]==
                           getattr(self.registers, register_key))

                if check_state == t_check_state.IDLE:
                    if random.random() < add_write_transaction_prob:
                        # At a random time set up an axi lite write
                        # transaction
                        test_data['address'] = random.choice(
                                self.read_write_registers_indices)
                        test_data['data'] = random.randint(
                                0, 2**self.data_width-1)

                        # Add the write transaction to the queue.
                        axi_lite_bfm.add_write_transaction(
                            write_address=(
                                self.addr_remap_ratio*test_data['address']),
                            write_data=test_data['data'],
                            write_strobes=None,
                            write_protection=None,
                            address_delay=random.randint(0, 15),
                            data_delay=random.randint(0, 15),
                            response_ready_delay=random.randint(10, 25))

                        check_state.next = t_check_state.AWAIT_TRANSACTION

                elif check_state == t_check_state.AWAIT_TRANSACTION:

                    if (axi_lite_interface.AWVALID and
                        axi_lite_interface.AWREADY):
                        # Write address handshake has occurred.
                        test_data['address_received'] = True

                    if (axi_lite_interface.WVALID and
                        axi_lite_interface.WREADY):
                        # Write data handshake has occurred.
                        test_data['data_received'] = True

                    if (test_data['address_received'] and
                        test_data['data_received']):
                        # Both data and address received so update the
                        # expected register value
                        expected_register_values[
                            self.register_list[test_data['address']]] = (
                                test_data['data'])

                    if (axi_lite_interface.BVALID and
                        axi_lite_interface.BREADY):
                        # Response has been received.
                        check_state.next = t_check_state.CHECK_TRANSACTION

                elif check_state == t_check_state.CHECK_TRANSACTION:
                    try:
                        # Try to get the response from the responses Queue.
                        # Include a timeout to prevent the system hanging if
                        # queue is empty.
                        test_data['write_response'] = (
                            axi_lite_bfm.write_responses.get(True, 3))
                    except queue.Empty:
                        raise AssertionError(
                            'axi_lite_handler has failed to respond correctly')

                    test_checks['test_run'] = True

                    # Check that the write response is not an error.
                    assert(test_data['write_response']['wr_resp']==0)

                    test_data['address_received'] = False
                    test_data['data_received'] = False

                    check_state.next = t_check_state.IDLE

            return stimulate_check, master_bfm

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, self.default_args,
            self.default_arg_types,
            custom_sources=[(testbench, (), self.default_args)])

        assert(test_checks['test_run'])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_successful_write_to_single_read_write_register(self):
        ''' The axi_lite_handler should be able to write to the register when
        a single read_write register is defined.
        '''

        # Create a new registers list and register type dict for a single
        # read write register
        register_list = [self.register_list[0]]
        register_types = {register_list[0]: 'axi_read_write'}
        registers = Registers(
            register_list, register_types, register_width=self.data_width)

        args = self.default_args
        arg_types = self.default_arg_types

        # Modify the args to take the registers created within this test
        args['registers'] = registers
        arg_types['registers'] = {register_list[0]: 'output'}

        cycles = 4000

        test_checks = {'test_run': False}

        @block
        def testbench(clock, axil_nreset, axi_lite_interface, registers):

            axi_lite_bfm = AxiLiteMasterBFM()
            master_bfm = axi_lite_bfm.model(clock, axil_nreset, axi_lite_interface)

            add_write_transaction_prob = 0.05

            t_check_state = enum(
                'IDLE','AWAIT_TRANSACTION', 'CHECK_TRANSACTION')
            check_state = Signal(t_check_state.IDLE)

            test_data = {'address': 0,
                         'address_received': False,
                         'data': 0,
                         'data_received': False,
                         'write_response': None,}

            # Create an expected_register_values dict which uses the names in
            # the list of registers as keys.
            expected_register_values = {
                key: 0 for key in register_list}

            @always(clock.posedge)
            def stimulate_check():

                # Check the register values every clock cycle.
                for register_key in register_list:

                    assert(expected_register_values[register_key]==
                           getattr(registers, register_key))

                if check_state == t_check_state.IDLE:
                    if random.random() < add_write_transaction_prob:
                        # At a random time set up an axi lite write
                        # transaction
                        test_data['address'] = 0
                        test_data['data'] = random.randint(
                                0, 2**self.data_width-1)

                        # Add the write transaction to the queue.
                        axi_lite_bfm.add_write_transaction(
                            write_address=(
                                self.addr_remap_ratio*test_data['address']),
                            write_data=test_data['data'],
                            write_strobes=None,
                            write_protection=None,
                            address_delay=random.randint(0, 15),
                            data_delay=random.randint(0, 15),
                            response_ready_delay=random.randint(10, 25))

                        check_state.next = t_check_state.AWAIT_TRANSACTION

                elif check_state == t_check_state.AWAIT_TRANSACTION:

                    if (axi_lite_interface.AWVALID and
                        axi_lite_interface.AWREADY):
                        # Write address handshake has occurred.
                        test_data['address_received'] = True

                    if (axi_lite_interface.WVALID and
                        axi_lite_interface.WREADY):
                        # Write data handshake has occurred.
                        test_data['data_received'] = True

                    if (test_data['address_received'] and
                        test_data['data_received']):
                        # Both data and address received so update the
                        # expected register value
                        expected_register_values[
                            register_list[test_data['address']]] = (
                                test_data['data'])

                    if (axi_lite_interface.BVALID and
                        axi_lite_interface.BREADY):
                        # Response has been received.
                        check_state.next = t_check_state.CHECK_TRANSACTION

                elif check_state == t_check_state.CHECK_TRANSACTION:
                    try:
                        # Try to get the response from the responses Queue.
                        # Include a timeout to prevent the system hanging if
                        # queue is empty.
                        test_data['write_response'] = (
                            axi_lite_bfm.write_responses.get(True, 3))
                    except queue.Empty:
                        raise AssertionError(
                            'axi_lite_handler has failed to respond correctly')

                    test_checks['test_run'] = True

                    # Check that the write response is not an error.
                    assert(test_data['write_response']['wr_resp']==0)

                    test_data['address_received'] = False
                    test_data['data_received'] = False

                    check_state.next = t_check_state.IDLE

            return stimulate_check, master_bfm

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, args, arg_types,
            custom_sources=[(testbench, (), args)])

        assert(test_checks['test_run'])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_successful_write_to_write_only_register(self):
        ''' On receipt of an axi write to an axi write-only register the
        axi_lite_handler should write the packet to that register, which
        should maintain the value for one cycle only (before reverting to
        all zeros). That is, the write only register will pulse for one
        cycle with the written value.

        If the master sends the data before the address, the axi_lite_handler
        should buffer the data whilst it waits for the address. On receipt
        of the address, it should then write to the appropriate register.
        '''

        cycles = 4000

        test_checks = {'test_run': False}

        @block
        def testbench(clock, axil_nreset, axi_lite_interface, registers):

            axi_lite_bfm = AxiLiteMasterBFM()
            master_bfm = axi_lite_bfm.model(clock, axil_nreset, axi_lite_interface)

            add_write_transaction_prob = 0.05

            t_check_state = enum(
                'IDLE','AWAIT_TRANSACTION', 'AWAIT_RESPONSE',
                'CHECK_TRANSACTION')
            check_state = Signal(t_check_state.IDLE)

            test_data = {'address': 0,
                         'address_received': False,
                         'data': 0,
                         'data_received': False,
                         'write_response': None,}

            # Create an expected_register_values dict which uses the names in
            # the list of registers as keys.
            expected_register_values = {
                key: 0 for key in self.register_list}

            # Set up a valid start value (for the case when we re-use the
            # previous value)
            test_data['address'] = random.choice(
                self.write_only_registers_indices)
            test_data['data'] = random.randint(0, 2**self.data_width-1)

            @always(clock.posedge)
            def stimulate_check():

                # Check the register values every clock cycle.
                for register_key in self.write_only_registers:

                    assert(expected_register_values[register_key] ==
                           getattr(self.registers, register_key))

                # Now zero all the expected values before the next check
                # (since the register is only set for a cycle)

                for key in expected_register_values:
                    expected_register_values[key] = 0

                if check_state == t_check_state.IDLE:
                    if random.random() < add_write_transaction_prob:

                        if random.random() < 0.5:
                            # About half the time we setup a new address and
                            # data
                            test_data['address'] = random.choice(
                                self.write_only_registers_indices)
                            test_data['data'] = random.randint(
                                0, 2**self.data_width-1)
                        else:
                            # The rest of the time we use the previous values
                            pass

                        # Add the write transaction to the queue.
                        axi_lite_bfm.add_write_transaction(
                            write_address=(
                                self.addr_remap_ratio*test_data['address']),
                            write_data=test_data['data'],
                            write_strobes=None,
                            write_protection=None,
                            address_delay=random.randint(0, 15),
                            data_delay=random.randint(0, 15),
                            response_ready_delay=random.randint(10, 25))

                        check_state.next = t_check_state.AWAIT_TRANSACTION

                elif check_state == t_check_state.AWAIT_TRANSACTION:

                    if (axi_lite_interface.AWVALID and
                        axi_lite_interface.AWREADY):
                        # Write address handshake has occurred.
                        test_data['address_received'] = True

                    if (axi_lite_interface.WVALID and
                        axi_lite_interface.WREADY):
                        # Write data handshake has occurred.
                        test_data['data_received'] = True

                    if (test_data['address_received'] and
                        test_data['data_received']):
                        # Both data and address received so update the
                        # expected register value
                        expected_register_values[
                            self.register_list[test_data['address']]] = (
                                test_data['data'])

                        if (axi_lite_interface.BVALID and
                            axi_lite_interface.BREADY):
                            # Response has been received.
                            check_state.next = t_check_state.CHECK_TRANSACTION

                        else:
                            check_state.next = t_check_state.AWAIT_RESPONSE

                elif check_state == t_check_state.AWAIT_RESPONSE:
                    # In this state, we don't write to the expected value
                    # at all
                    if (axi_lite_interface.BVALID and
                        axi_lite_interface.BREADY):
                        # Response has been received.
                        check_state.next = t_check_state.CHECK_TRANSACTION

                elif check_state == t_check_state.CHECK_TRANSACTION:
                    try:
                        # Try to get the response from the responses Queue.
                        # Include a timeout to prevent the system hanging if
                        # queue is empty.
                        test_data['write_response'] = (
                            axi_lite_bfm.write_responses.get(True, 3))
                    except queue.Empty:
                        raise AssertionError(
                            'axi_lite_handler has failed to respond correctly')

                    test_checks['test_run'] = True

                    # Check that the write response is not an error.
                    assert(test_data['write_response']['wr_resp']==0)

                    test_data['address_received'] = False
                    test_data['data_received'] = False

                    check_state.next = t_check_state.IDLE

            return stimulate_check, master_bfm

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, self.default_args,
            self.default_arg_types,
            custom_sources=[(testbench, (), self.default_args)])

        assert(test_checks['test_run'])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_successful_write_to_single_write_only_register(self):
        ''' The axi_lite_handler should be able to write to the register when
        a single write_only register is defined.
        '''

        # Create a new registers list and register type dict for a single
        # read write register
        register_list = [self.register_list[0]]
        register_types = {register_list[0]: 'axi_write_only',}
        registers = Registers(
            register_list, register_types, register_width=self.data_width)

        args = self.default_args
        arg_types = self.default_arg_types

        # Modify the args to take the registers created within this test
        args['registers'] = registers
        arg_types['registers'] = {register_list[0]: 'output',}

        cycles = 4000

        test_checks = {'test_run': False}

        @block
        def testbench(clock, axil_nreset, axi_lite_interface, registers):

            axi_lite_bfm = AxiLiteMasterBFM()
            master_bfm = axi_lite_bfm.model(clock, axil_nreset, axi_lite_interface)

            add_write_transaction_prob = 0.05

            t_check_state = enum(
                'IDLE','AWAIT_TRANSACTION', 'AWAIT_RESPONSE',
                'CHECK_TRANSACTION')
            check_state = Signal(t_check_state.IDLE)

            test_data = {'address': 0,
                         'address_received': False,
                         'data': 0,
                         'data_received': False,
                         'write_response': None,}

            # Create an expected_register_values dict which uses the names in
            # the list of registers as keys.
            expected_register_values = {
                key: 0 for key in register_list}

            # Set up a valid start value (for the case when we re-use the
            # previous value)
            test_data['address'] = 0
            test_data['data'] = random.randint(0, 2**self.data_width-1)

            @always(clock.posedge)
            def stimulate_check():

                # Check the register values every clock cycle.
                for register_key in register_list:

                    assert(expected_register_values[register_key] ==
                           getattr(registers, register_key))

                # Now zero all the expected values before the next check
                # (since the register is only set for a cycle)

                for key in expected_register_values:
                    expected_register_values[key] = 0

                if check_state == t_check_state.IDLE:
                    if random.random() < add_write_transaction_prob:

                        if random.random() < 0.5:
                            # About half the time we setup a new address and
                            # data
                            test_data['address'] = 0
                            test_data['data'] = random.randint(
                                0, 2**self.data_width-1)
                        else:
                            # The rest of the time we use the previous values
                            pass

                        # Add the write transaction to the queue.
                        axi_lite_bfm.add_write_transaction(
                            write_address=(
                                self.addr_remap_ratio*test_data['address']),
                            write_data=test_data['data'],
                            write_strobes=None,
                            write_protection=None,
                            address_delay=random.randint(0, 15),
                            data_delay=random.randint(0, 15),
                            response_ready_delay=random.randint(10, 25))

                        check_state.next = t_check_state.AWAIT_TRANSACTION

                elif check_state == t_check_state.AWAIT_TRANSACTION:

                    if (axi_lite_interface.AWVALID and
                        axi_lite_interface.AWREADY):
                        # Write address handshake has occurred.
                        test_data['address_received'] = True

                    if (axi_lite_interface.WVALID and
                        axi_lite_interface.WREADY):
                        # Write data handshake has occurred.
                        test_data['data_received'] = True

                    if (test_data['address_received'] and
                        test_data['data_received']):
                        # Both data and address received so update the
                        # expected register value
                        expected_register_values[
                            register_list[test_data['address']]] = (
                                test_data['data'])

                        if (axi_lite_interface.BVALID and
                            axi_lite_interface.BREADY):
                            # Response has been received.
                            check_state.next = t_check_state.CHECK_TRANSACTION

                        else:
                            check_state.next = t_check_state.AWAIT_RESPONSE

                elif check_state == t_check_state.AWAIT_RESPONSE:
                    # In this state, we don't write to the expected value
                    # at all
                    if (axi_lite_interface.BVALID and
                        axi_lite_interface.BREADY):
                        # Response has been received.
                        check_state.next = t_check_state.CHECK_TRANSACTION

                elif check_state == t_check_state.CHECK_TRANSACTION:
                    try:
                        # Try to get the response from the responses Queue.
                        # Include a timeout to prevent the system hanging if
                        # queue is empty.
                        test_data['write_response'] = (
                            axi_lite_bfm.write_responses.get(True, 3))
                    except queue.Empty:
                        raise AssertionError(
                            'axi_lite_handler has failed to respond correctly')

                    test_checks['test_run'] = True

                    # Check that the write response is not an error.
                    assert(test_data['write_response']['wr_resp']==0)

                    test_data['address_received'] = False
                    test_data['data_received'] = False

                    check_state.next = t_check_state.IDLE

            return stimulate_check, master_bfm

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, args, arg_types,
            custom_sources=[(testbench, (), args)])

        assert(test_checks['test_run'])

        self.assertEqual(dut_outputs, ref_outputs)


    def test_successful_read(self):
        ''' On receipt of an axi read from an axi readable register the
        axi_lite_handler should send the data from that register.
        '''

        cycles = 4000

        test_checks = {'test_run': False}

        @block
        def testbench(clock, axil_nreset, axi_lite_interface, registers):

            axi_lite_bfm = AxiLiteMasterBFM()
            master_bfm = axi_lite_bfm.model(
                self.clock, self.axil_nreset, self.axi_lite_interface)

            add_read_transaction_prob = 0.05

            test_data = {'address': 0,
                         'expected_data': 0,
                         'read_response': None,
                         'signal_to_update': None,}

            t_check_state = enum(
                'IDLE', 'AWAIT_RESPONSE', 'CHECK_TRANSACTION')
            check_state = Signal(t_check_state.IDLE)

            @always(clock.posedge)
            def stimulate_check():

                if check_state == t_check_state.IDLE:
                    if random.random() < add_read_transaction_prob:
                        # At random times set up an axi lite read transaction
                        test_data['address'] = random.choice(
                                self.read_only_registers_indices)
                        test_data['expected_data'] = random.randint(
                                0, 2**self.data_width-1)

                        # Set the register value.
                        test_data['signal_to_update'] = (
                            getattr(registers,
                                    self.register_list[test_data['address']]))
                        test_data['signal_to_update'].next = (
                            test_data['expected_data'])

                        # Add the read transaction to the queue.
                        axi_lite_bfm.add_read_transaction(
                            read_address=(
                                self.addr_remap_ratio*test_data['address']),
                            read_protection=None,
                            address_delay=random.randint(0, 15),
                            data_delay=random.randint(0, 15))

                        check_state.next = t_check_state.AWAIT_RESPONSE

                elif check_state == t_check_state.AWAIT_RESPONSE:
                    if (axi_lite_interface.RVALID and
                        axi_lite_interface.RREADY):
                        # Response has been received.
                        check_state.next = t_check_state.CHECK_TRANSACTION

                elif check_state == t_check_state.CHECK_TRANSACTION:
                    try:
                        # Try to get the response from the responses Queue.
                        # Include a timeout to prevent the system hanging if
                        # queue is empty.
                        test_data['read_response'] = (
                            axi_lite_bfm.read_responses.get(True, 3))
                    except queue.Empty:
                        raise AssertionError(
                            'axi_lite_handler has failed to respond correctly')

                    test_checks['test_run'] = True

                    # Check that the read responds with the correct data.
                    assert(test_data['read_response']['rd_data']==
                           test_data['expected_data'])
                    # Check that the read response is not an error.
                    assert(test_data['read_response']['rd_resp']==0)

                    check_state.next = t_check_state.IDLE

            return stimulate_check, master_bfm

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, self.default_args,
            self.default_arg_types,
            custom_sources=[(testbench, (), self.default_args)])

        assert(test_checks['test_run'])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_successful_read_single_register(self):
        ''' The axi_lite_handler should be able to read from the register when
        a single read_only register is defined.
        '''

        # Create a new registers list and register type dict for a single
        # read write register
        register_list = [self.register_list[0],]
        register_types = {register_list[0]: 'axi_read_only',}
        registers = Registers(
            register_list, register_types, register_width=self.data_width)

        args = self.default_args
        arg_types = self.default_arg_types

        # Modify the args to take the registers created within this test
        args['registers'] = registers
        arg_types['registers'] = {register_list[0]: 'custom',}

        cycles = 4000

        test_checks = {'test_run': False}

        @block
        def testbench(clock, axil_nreset, axi_lite_interface, registers):

            axi_lite_bfm = AxiLiteMasterBFM()
            master_bfm = axi_lite_bfm.model(
                self.clock, self.axil_nreset, self.axi_lite_interface)

            add_read_transaction_prob = 0.05

            test_data = {'address': 0,
                         'expected_data': 0,
                         'read_response': None,
                         'signal_to_update': None,}

            t_check_state = enum(
                'IDLE', 'AWAIT_RESPONSE', 'CHECK_TRANSACTION')
            check_state = Signal(t_check_state.IDLE)

            @always(clock.posedge)
            def stimulate_check():

                if check_state == t_check_state.IDLE:
                    if random.random() < add_read_transaction_prob:
                        # At random times set up an axi lite read transaction
                        test_data['address'] = 0
                        test_data['expected_data'] = random.randint(
                                0, 2**self.data_width-1)

                        # Set the register value.
                        test_data['signal_to_update'] = (
                            getattr(registers,
                                    register_list[test_data['address']]))
                        test_data['signal_to_update'].next = (
                            test_data['expected_data'])

                        # Add the read transaction to the queue.
                        axi_lite_bfm.add_read_transaction(
                            read_address=(
                                self.addr_remap_ratio*test_data['address']),
                            read_protection=None,
                            address_delay=random.randint(0, 15),
                            data_delay=random.randint(0, 15))

                        check_state.next = t_check_state.AWAIT_RESPONSE

                elif check_state == t_check_state.AWAIT_RESPONSE:
                    if (axi_lite_interface.RVALID and
                        axi_lite_interface.RREADY):
                        # Response has been received.
                        check_state.next = t_check_state.CHECK_TRANSACTION

                elif check_state == t_check_state.CHECK_TRANSACTION:
                    try:
                        # Try to get the response from the responses Queue.
                        # Include a timeout to prevent the system hanging if
                        # queue is empty.
                        test_data['read_response'] = (
                            axi_lite_bfm.read_responses.get(True, 3))
                    except queue.Empty:
                        raise AssertionError(
                            'axi_lite_handler has failed to respond correctly')

                    test_checks['test_run'] = True

                    # Check that the read responds with the correct data.
                    assert(test_data['read_response']['rd_data']==
                           test_data['expected_data'])
                    # Check that the read response is not an error.
                    assert(test_data['read_response']['rd_resp']==0)

                    check_state.next = t_check_state.IDLE

            return stimulate_check, master_bfm

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, args, arg_types,
            custom_sources=[(testbench, (), args)])

        assert(test_checks['test_run'])

        self.assertTrue(dut_outputs == ref_outputs)

    def test_read_write_registers(self):
        ''' The read write registers should store the value on a write and
        return the value on a read.
        '''

        cycles = 4000

        test_checks = {'test_run': False}

        test_bench_args = self.default_args.copy()
        test_bench_args['test_class'] = self
        test_bench_args['test_checks'] = test_checks

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, self.default_args,
            self.default_arg_types,
            custom_sources=[(rw_testbench, (), test_bench_args)])

        assert(test_checks['test_run'])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_write_to_read_only_register(self):
        ''' On receipt of an axi write to a register which is not axi
        writeable the axi_lite_handler should complete the axi transaction
        but should not write the data to the register.

        If the master, sends the data before the address, the axi_lite_handler
        should buffer the data whilst it waits for the address. On receipt
        of the non writeable address it should respond as if the transaction
        was a success but without writing the data to the requested register.
        '''
        cycles = 4000

        test_checks = {'test_run': False}

        @block
        def testbench(clock, axil_nreset, axi_lite_interface, registers):

            axi_lite_bfm = AxiLiteMasterBFM()
            master_bfm = axi_lite_bfm.model(
                self.clock, self.axil_nreset, self.axi_lite_interface)

            add_write_transaction_prob = 0.05

            t_check_state = enum(
                'IDLE', 'CHECK_TRANSACTION', 'AWAIT_RESPONSE')
            check_state = Signal(t_check_state.IDLE)

            test_data = {'address': 0,
                         'write_response': None,}

            @always(clock.posedge)
            def stimulate_check():

                # Check the register values every clock cycle to ensure they
                # do not change.
                for register_key in self.register_list:
                    assert(getattr(self.registers, register_key)==0)

                if check_state == t_check_state.IDLE:
                    if random.random() < add_write_transaction_prob:
                        # At a random time set up an axi lite write
                        # transaction with an address which is read only.
                        test_data['address'] = random.choice(
                                self.read_only_registers_indices)
                        test_data['data'] = random.randint(
                                0, 2**self.data_width-1)

                        # Add the write transaction to the queue.
                        axi_lite_bfm.add_write_transaction(
                            write_address=(
                                self.addr_remap_ratio*test_data['address']),
                            write_data=test_data['data'],
                            write_strobes=None,
                            write_protection=None,
                            address_delay=random.randint(0, 15),
                            data_delay=random.randint(0, 15),
                            response_ready_delay=random.randint(10, 25))

                        check_state.next = t_check_state.AWAIT_RESPONSE

                elif check_state == t_check_state.AWAIT_RESPONSE:
                    if (axi_lite_interface.BVALID and
                        axi_lite_interface.BREADY):
                        # Response has been received.
                        check_state.next = t_check_state.CHECK_TRANSACTION

                elif check_state == t_check_state.CHECK_TRANSACTION:
                    try:
                        # Try to get the response from the responses Queue.
                        # Include a timeout to prevent the system hanging if
                        # queue is empty.
                        test_data['write_response'] = (
                            axi_lite_bfm.write_responses.get(True, 3))
                    except queue.Empty:
                        raise AssertionError(
                            'axi_lite_handler has failed to respond correctly')

                    test_checks['test_run'] = True

                    # Check that the write response is not an error.
                    assert(test_data['write_response']['wr_resp']==0)

                    check_state.next = t_check_state.IDLE

            return stimulate_check, master_bfm

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, self.default_args,
            self.default_arg_types,
            custom_sources=[(testbench, (), self.default_args)])

        assert(test_checks['test_run'])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_read_from_write_only_register(self):
        ''' On receipt of an axi read from a register which is not axi
        readable the axi_lite_handler should send zeros.
        '''

        cycles = 4000

        test_checks = {'test_run': False}

        @block
        def testbench(clock, axil_nreset, axi_lite_interface, registers):

            axi_lite_bfm = AxiLiteMasterBFM()
            master_bfm = axi_lite_bfm.model(
                self.clock, self.axil_nreset, self.axi_lite_interface)

            add_read_transaction_prob = 0.05

            test_data = {'address': 0,
                         'read_response': None,
                         'signal_to_update': None,}

            t_check_state = enum(
                'IDLE', 'AWAIT_RESPONSE', 'CHECK_TRANSACTION')
            check_state = Signal(t_check_state.IDLE)

            @always(clock.posedge)
            def stimulate_check():

                if check_state == t_check_state.IDLE:
                    if random.random() < add_read_transaction_prob:
                        # At random times set up an axi lite read transaction
                        test_data['address'] = random.choice(
                                self.write_only_registers_indices)
                        test_data['expected_data'] = random.randint(
                                0, 2**self.data_width-1)

                        # Set the register value.
                        test_data['signal_to_update'] = (
                            getattr(registers,
                                    self.register_list[test_data['address']]))
                        test_data['signal_to_update'].next = (
                            test_data['expected_data'])

                        # Add the read transaction to the queue.
                        axi_lite_bfm.add_read_transaction(
                            read_address=(
                                self.addr_remap_ratio*test_data['address']),
                            read_protection=None,
                            address_delay=random.randint(0, 15),
                            data_delay=random.randint(0, 15))

                        check_state.next = t_check_state.AWAIT_RESPONSE

                elif check_state == t_check_state.AWAIT_RESPONSE:
                    if (axi_lite_interface.RVALID and
                        axi_lite_interface.RREADY):
                        # Response has been received.
                        check_state.next = t_check_state.CHECK_TRANSACTION

                elif check_state == t_check_state.CHECK_TRANSACTION:
                    try:
                        # Try to get the response from the responses Queue.
                        # Include a timeout to prevent the system hanging if
                        # queue is empty.
                        test_data['read_response'] = (
                            axi_lite_bfm.read_responses.get(True, 3))
                    except queue.Empty:
                        raise AssertionError(
                            'axi_lite_handler has failed to respond correctly')

                    test_checks['test_run'] = True

                    # Check that the read responds with the correct data.
                    assert(test_data['read_response']['rd_data']==0)
                    # Check that the read response is not an error.
                    assert(test_data['read_response']['rd_resp']==0)

                    check_state.next = t_check_state.IDLE

            return stimulate_check, master_bfm

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, self.default_args,
            self.default_arg_types,
            custom_sources=[(testbench, (), self.default_args)])

        assert(test_checks['test_run'])

        all_equal = True
        for a, b in zip(dut_outputs['axi_lite_interface'], ref_outputs['axi_lite_interface']):
            all_equal = all_equal and (a == b)

        self.assertEqual(
            dut_outputs['axi_lite_interface'],
            ref_outputs['axi_lite_interface'])
        self.assertEqual(
            dut_outputs['axil_nreset'],
            ref_outputs['axil_nreset'])

    def test_write_to_single_invalid_register(self):
        ''' The axi_lite_handler should respond with a SLVERR if the there is
        an attempt to write to an invalid register when when a single
        write_only register is defined.
        '''

        # Create a new registers list and register type dict for a single
        # read write register
        register_list = [self.register_list[0]]
        register_types = {register_list[0]: 'axi_read_write',}
        registers = Registers(
            register_list, register_types, register_width=self.data_width)

        args = self.default_args
        arg_types = self.default_arg_types

        # Modify the args to take the registers created within this test
        args['registers'] = registers
        arg_types['registers'] = {register_list[0]: 'output',}

        cycles = 4000

        test_checks = {'test_run': False}

        @block
        def testbench(clock, axil_nreset, axi_lite_interface, registers):

            axi_lite_bfm = AxiLiteMasterBFM()
            master_bfm = axi_lite_bfm.model(clock, axil_nreset, axi_lite_interface)

            add_write_transaction_prob = 0.1

            t_check_state = enum(
                'IDLE','AWAIT_TRANSACTION', 'CHECK_TRANSACTION')
            check_state = Signal(t_check_state.IDLE)

            test_data = {'address': 0,
                         'invalid_address': False,
                         'address_received': False,
                         'data': 0,
                         'data_received': False,
                         'write_response': None,
                         'last_write_invalid': False}

            # Create an expected_register_values dict which uses the names in
            # the list of registers as keys.
            expected_register_values = {
                key: 0 for key in register_list}

            expected_values = {}

            expected_values.update(
                {key: 0 for key in register_list})

            @always(clock.posedge)
            def stimulate_check():

                if test_data['last_write_invalid']:
                    for key in expected_values:
                        assert(getattr(registers, key) ==
                               expected_values[key])

                    test_data['last_write_invalid'] = False
                else:
                    # Otherwise we just keep the expected values tracking
                    # the registers
                    expected_values.update(
                        {key: getattr(registers, key) for
                         key in register_list})

                if check_state == t_check_state.IDLE:
                    if random.random() < add_write_transaction_prob:
                        # At a random time set up an axi lite write
                        # transaction

                        # 50% of the time select an invalid address
                        if random.random() < 0.5:
                            # The only valid address in this case is 0 so
                            # pick another value
                            test_data['address'] = random.randrange(
                                1, 2**self.addr_width//self.addr_remap_ratio)

                            test_data['invalid_address'] = True
                            test_data['last_write_invalid'] = True

                        else:
                            test_data['address'] = 0
                            test_data['invalid_address'] = False

                        test_data['data'] = random.randint(
                                0, 2**self.data_width-1)

                        # Add the write transaction to the queue.
                        axi_lite_bfm.add_write_transaction(
                            write_address=(
                                self.addr_remap_ratio*test_data['address']),
                            write_data=test_data['data'],
                            write_strobes=None,
                            write_protection=None,
                            address_delay=random.randint(0, 15),
                            data_delay=random.randint(0, 15),
                            response_ready_delay=random.randint(10, 25))

                        check_state.next = t_check_state.AWAIT_TRANSACTION

                elif check_state == t_check_state.AWAIT_TRANSACTION:

                    if (axi_lite_interface.AWVALID and
                        axi_lite_interface.AWREADY):
                        # Write address handshake has occurred.
                        test_data['address_received'] = True

                    if (axi_lite_interface.WVALID and
                        axi_lite_interface.WREADY):
                        # Write data handshake has occurred.
                        test_data['data_received'] = True

                    if (test_data['address_received'] and
                        test_data['data_received']):
                        # Both data and address received so update the
                        # expected register value
                        pass

                    if (axi_lite_interface.BVALID and
                        axi_lite_interface.BREADY):

                        # Quick sanity check that a transaction has happened.
                        assert (test_data['address_received'] and
                                test_data['data_received'])

                        # Response has been received.
                        check_state.next = t_check_state.CHECK_TRANSACTION

                elif check_state == t_check_state.CHECK_TRANSACTION:
                    try:
                        # Try to get the response from the responses Queue.
                        # Include a timeout to prevent the system hanging if
                        # queue is empty.
                        test_data['write_response'] = (
                            axi_lite_bfm.write_responses.get(True, 3))
                    except queue.Empty:
                        raise AssertionError(
                            'axi_lite_handler has failed to respond correctly')

                    test_checks['test_run'] = True

                    if test_data['invalid_address']:
                        # Check that the write response is not an error.
                        assert(test_data['write_response']['wr_resp']
                               == axi_lite.SLVERR)

                    # The queue should be empty now
                    assert axi_lite_bfm.write_responses.empty()

                    test_data['address_received'] = False
                    test_data['data_received'] = False
                    test_data['invalid_address'] = False

                    check_state.next = t_check_state.IDLE

            return stimulate_check, master_bfm

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, args, arg_types,
            custom_sources=[(testbench, (), args)])

        assert(test_checks['test_run'])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_write_to_invalid_register(self):
        ''' If a write is requested to a register that is not defined,
        the transaction should complete but the response should be
        SLVERR (0b10).

        No other registers should be affected during the attempted write.
        '''

        cycles = 4000

        test_checks = {'test_run': False}

        @block
        def testbench(clock, axil_nreset, axi_lite_interface, registers):

            axi_lite_bfm = AxiLiteMasterBFM()
            master_bfm = axi_lite_bfm.model(clock, axil_nreset, axi_lite_interface)

            add_write_transaction_prob = 0.1

            t_check_state = enum(
                'IDLE','AWAIT_TRANSACTION', 'CHECK_TRANSACTION')
            check_state = Signal(t_check_state.IDLE)

            test_data = {'address': 0,
                         'invalid_address': False,
                         'address_received': False,
                         'data': 0,
                         'data_received': False,
                         'write_response': None,
                         'last_write_invalid': False}

            # Create an expected_register_values dict which uses the names in
            # the list of registers as keys.
            expected_register_values = {
                key: 0 for key in self.register_list}

            self.write_only_registers
            self.read_write_registers

            expected_values = {}

            expected_values.update(
                {key: 0 for key in self.write_only_registers})
            expected_values.update(
                {key: getattr(self.registers, key) for
                 key in self.read_write_registers})


            @always(clock.posedge)
            def stimulate_check():

                if test_data['last_write_invalid']:
                    for key in expected_values:
                        assert(getattr(self.registers, key) ==
                               expected_values[key])

                    test_data['last_write_invalid'] = False
                else:
                    # Otherwise we just keep the expected values tracking
                    # the registers
                    expected_values.update(
                        {key: getattr(self.registers, key) for
                         key in self.read_write_registers})

                if check_state == t_check_state.IDLE:
                    if random.random() < add_write_transaction_prob:
                        # At a random time set up an axi lite write
                        # transaction

                        # 50% of the time select an invalid address
                        if random.random() < 0.5:
                            test_data['address'] = random.choice(
                                self.invalid_addresses)

                            test_data['invalid_address'] = True
                            test_data['last_write_invalid'] = True

                        else:
                            test_data['address'] = random.choice(
                                self.valid_addresses)

                            test_data['invalid_address'] = False

                        test_data['data'] = random.randint(
                                0, 2**self.data_width-1)

                        # Add the write transaction to the queue.
                        axi_lite_bfm.add_write_transaction(
                            write_address=(
                                self.addr_remap_ratio*test_data['address']),
                            write_data=test_data['data'],
                            write_strobes=None,
                            write_protection=None,
                            address_delay=random.randint(0, 15),
                            data_delay=random.randint(0, 15),
                            response_ready_delay=random.randint(10, 25))

                        check_state.next = t_check_state.AWAIT_TRANSACTION

                elif check_state == t_check_state.AWAIT_TRANSACTION:

                    if (axi_lite_interface.AWVALID and
                        axi_lite_interface.AWREADY):
                        # Write address handshake has occurred.
                        test_data['address_received'] = True

                    if (axi_lite_interface.WVALID and
                        axi_lite_interface.WREADY):
                        # Write data handshake has occurred.
                        test_data['data_received'] = True

                    if (test_data['address_received'] and
                        test_data['data_received']):
                        # Both data and address received so update the
                        # expected register value
                        pass

                    if (axi_lite_interface.BVALID and
                        axi_lite_interface.BREADY):

                        # Quick sanity check that a transaction has happened.
                        assert (test_data['address_received'] and
                                test_data['data_received'])

                        # Response has been received.
                        check_state.next = t_check_state.CHECK_TRANSACTION

                elif check_state == t_check_state.CHECK_TRANSACTION:
                    try:
                        # Try to get the response from the responses Queue.
                        # Include a timeout to prevent the system hanging if
                        # queue is empty.
                        test_data['write_response'] = (
                            axi_lite_bfm.write_responses.get(True, 3))
                    except queue.Empty:
                        raise AssertionError(
                            'axi_lite_handler has failed to respond correctly')

                    test_checks['test_run'] = True

                    if test_data['invalid_address']:
                        # Check that the write response is not an error.
                        assert(test_data['write_response']['wr_resp']
                               == axi_lite.SLVERR)

                    # The queue should be empty now
                    assert axi_lite_bfm.write_responses.empty()

                    test_data['address_received'] = False
                    test_data['data_received'] = False
                    test_data['invalid_address'] = False

                    check_state.next = t_check_state.IDLE

            return stimulate_check, master_bfm

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, self.default_args,
            self.default_arg_types,
            custom_sources=[(testbench, (), self.default_args)])

        assert(test_checks['test_run'])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_read_from_invalid_register(self):
        ''' If a read is requested from a register that is not defined,
        the transaction should complete but the data should be
        returned as zero and the response should be SLVERR (0b10).
        '''

        cycles = 4000

        test_checks = {'test_run': False}

        @block
        def testbench(clock, axil_nreset, axi_lite_interface, registers):

            axi_lite_bfm = AxiLiteMasterBFM()
            master_bfm = axi_lite_bfm.model(
                self.clock, self.axil_nreset, self.axi_lite_interface)

            add_read_transaction_prob = 0.1

            test_data = {'address': 0,
                         'expected_data': 0,
                         'read_response': None,
                         'signal_to_update': None,}

            t_check_state = enum(
                'IDLE', 'AWAIT_RESPONSE', 'CHECK_TRANSACTION')
            check_state = Signal(t_check_state.IDLE)

            @always(clock.posedge)
            def stimulate_check():

                if check_state == t_check_state.IDLE:
                    if random.random() < add_read_transaction_prob:

                        # 50% of the time select an invalid address
                        if random.random() < 0.5:
                            test_data['address'] = random.choice(
                                self.invalid_addresses)

                            test_data['invalid_address'] = True

                        else:
                            test_data['address'] = random.choice(
                                self.valid_addresses)

                            test_data['invalid_address'] = False

                        # Add the read transaction to the queue.
                        axi_lite_bfm.add_read_transaction(
                            read_address=(
                                self.addr_remap_ratio*test_data['address']),
                            read_protection=None,
                            address_delay=random.randint(0, 15),
                            data_delay=random.randint(0, 15))

                        check_state.next = t_check_state.AWAIT_RESPONSE

                elif check_state == t_check_state.AWAIT_RESPONSE:
                    if (axi_lite_interface.RVALID and
                        axi_lite_interface.RREADY):
                        # Response has been received.
                        check_state.next = t_check_state.CHECK_TRANSACTION

                elif check_state == t_check_state.CHECK_TRANSACTION:
                    try:
                        # Try to get the response from the responses Queue.
                        # Include a timeout to prevent the system hanging if
                        # queue is empty.
                        test_data['read_response'] = (
                            axi_lite_bfm.read_responses.get(True, 3))
                    except queue.Empty:
                        raise AssertionError(
                            'axi_lite_handler has failed to respond correctly')

                    test_checks['test_run'] = True

                    if test_data['invalid_address']:
                        # Check that the write response is not an error.
                        assert(test_data['read_response']['rd_resp']
                               == axi_lite.SLVERR)

                    # The queue should be empty now
                    assert axi_lite_bfm.write_responses.empty()

                    test_data['invalid_address'] = False

                    check_state.next = t_check_state.IDLE

            return stimulate_check, master_bfm

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, self.default_args,
            self.default_arg_types,
            custom_sources=[(testbench, (), self.default_args)])

        assert(test_checks['test_run'])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_read_from_single_invalid_register(self):
        ''' If a read is requested from a register that is not defined,
        the transaction should complete but the data should be
        returned as zero and the response should be SLVERR (0b10).

        This should be the case when only a single register is defined
        '''

        # Create a new registers list and register type dict for a single
        # read write register
        register_list = [self.register_list[0],]
        register_types = {register_list[0]: 'axi_read_only',}
        registers = Registers(
            register_list, register_types, register_width=self.data_width)

        args = self.default_args
        arg_types = self.default_arg_types

        # Modify the args to take the registers created within this test
        args['registers'] = registers
        arg_types['registers'] = {register_list[0]: 'custom',}

        cycles = 4000

        test_checks = {'test_run': False}

        @block
        def testbench(clock, axil_nreset, axi_lite_interface, registers):

            axi_lite_bfm = AxiLiteMasterBFM()
            master_bfm = axi_lite_bfm.model(
                self.clock, self.axil_nreset, self.axi_lite_interface)

            add_read_transaction_prob = 0.1

            test_data = {'address': 0,
                         'expected_data': 0,
                         'read_response': None,
                         'signal_to_update': None,}

            t_check_state = enum(
                'IDLE', 'AWAIT_RESPONSE', 'CHECK_TRANSACTION')
            check_state = Signal(t_check_state.IDLE)

            @always(clock.posedge)
            def stimulate_check():

                if check_state == t_check_state.IDLE:
                    if random.random() < add_read_transaction_prob:

                        # 50% of the time select an invalid address
                        if random.random() < 0.5:
                            test_data['address'] = random.randrange(
                                1, 2**self.addr_width//self.addr_remap_ratio)
                            test_data['invalid_address'] = True

                        else:
                            test_data['address'] = 0

                            test_data['invalid_address'] = False

                        # Add the read transaction to the queue.
                        axi_lite_bfm.add_read_transaction(
                            read_address=(
                                self.addr_remap_ratio*test_data['address']),
                            read_protection=None,
                            address_delay=random.randint(0, 15),
                            data_delay=random.randint(0, 15))

                        check_state.next = t_check_state.AWAIT_RESPONSE

                elif check_state == t_check_state.AWAIT_RESPONSE:
                    if (axi_lite_interface.RVALID and
                        axi_lite_interface.RREADY):
                        # Response has been received.
                        check_state.next = t_check_state.CHECK_TRANSACTION

                elif check_state == t_check_state.CHECK_TRANSACTION:
                    try:
                        # Try to get the response from the responses Queue.
                        # Include a timeout to prevent the system hanging if
                        # queue is empty.
                        test_data['read_response'] = (
                            axi_lite_bfm.read_responses.get(True, 3))
                    except queue.Empty:
                        raise AssertionError(
                            'axi_lite_handler has failed to respond correctly')

                    test_checks['test_run'] = True

                    if test_data['invalid_address']:
                        # Check that the write response is not an error.
                        assert(test_data['read_response']['rd_resp']
                               == axi_lite.SLVERR)

                    # The queue should be empty now
                    assert axi_lite_bfm.write_responses.empty()

                    test_data['invalid_address'] = False

                    check_state.next = t_check_state.IDLE

            return stimulate_check, master_bfm

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, args, arg_types,
            custom_sources=[(testbench, (), args)])

        assert(test_checks['test_run'])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_initial_values(self):
        ''' It should be possible to set initial values to the register
        '''

        cycles = 4000

        test_checks = {'test_run': False}

        initial_vals = {key: random.randrange(
            0xFFFFFFFF) for key in self.read_write_registers if (
                random.random() < 0.5)}

        initial_val_registers = Registers(
            self.register_list, self.register_types,
            register_width=self.data_width, initial_values=initial_vals)

        self.default_args['registers'] = initial_val_registers

        test_bench_args = self.default_args.copy()
        test_bench_args['test_class'] = self
        test_bench_args['test_checks'] = test_checks
        test_bench_args['initial_values'] = initial_vals

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, self.default_args,
            self.default_arg_types,
            custom_sources=[(rw_testbench, (), test_bench_args)])

        assert(test_checks['test_run'])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_write_to_register_with_bitfield(self):
        ''' On writing a register that contains a bitfield, the values on the
        bitfields should be updated directly from the register value.
        '''
        cycles = 4000

        test_checks = {'test_run': False, 'check_done': False}

        def check_bitfield(expected_reg_val, bitfields):

            self.assertEqual(expected_reg_val, bitfields.register)

            for name in bitfields._bitfields_config:
                offset = bitfields._bitfields_config[name]['offset']
                mask = bitfields._bitfield_masks[name]
                expected_val = (mask & expected_reg_val) >> offset

                self.assertEqual(getattr(bitfields, name).val, expected_val)


        @block
        def testbench(clock, axil_nreset, axi_lite_interface, registers):

            axi_lite_bfm = AxiLiteMasterBFM()
            master_bfm = axi_lite_bfm.model(
                self.clock, self.axil_nreset, self.axi_lite_interface)

            add_write_transaction_prob = 0.05

            t_check_state = enum(
                'IDLE', 'AWAIT_RESPONSE')
            check_state = Signal(t_check_state.IDLE)

            test_data = {'address': 0,
                         'write_response': None,}

            register_lookup = {
                n: name for n, name in enumerate(registers._register_types)}

            # Init val is 0 for them all
            expected_reg_values = {
                reg_name: 0 for reg_name in registers._register_types}

            @always(clock.posedge)
            def stimulate_check():

                if axi_lite_interface.BVALID:
                    this_reg_name = register_lookup[test_data['address']]

                    reg_type = registers._register_types[this_reg_name]

                    # We ignore writes to read-only registers:
                    if reg_type in ('axi_read_write', 'axi_write_only'):
                        expected_reg_values[this_reg_name] = test_data['data']

                    for register_name in expected_reg_values:
                        expected_val = expected_reg_values[register_name]

                        if register_name in bitfields_configs:
                            bitfields = getattr(registers, register_name)
                            check_bitfield(expected_val, bitfields)
                        else:
                            self.assertEqual(
                                getattr(registers, register_name),
                                expected_val)

                        # We've done at least one check
                        test_checks['check_done'] = True

                    # We need to reset the expected value for write only
                    # registers
                    if reg_type == 'axi_write_only':
                        expected_reg_values[this_reg_name] = 0

                if check_state == t_check_state.IDLE:
                    if random.random() < add_write_transaction_prob:
                        # At a random time set up an axi lite write
                        # transaction with some address.
                        test_data['address'] = random.choice(
                            self.valid_addresses)
                        test_data['data'] = random.randint(
                            0, 2**self.data_width-1)

                        # Add the write transaction to the queue.
                        axi_lite_bfm.add_write_transaction(
                            write_address=(
                                self.addr_remap_ratio*test_data['address']),
                            write_data=test_data['data'])

                        check_state.next = t_check_state.AWAIT_RESPONSE

                elif check_state == t_check_state.AWAIT_RESPONSE:
                    try:
                        # Try to get the response from the responses Queue.
                        # Quietly continue if it's not there yet by branching
                        # to the exception handler
                        write_resp = axi_lite_bfm.write_responses.get(False)

                        # Check that the write response is not an error.
                        assert(write_resp['wr_resp']==0)

                        # We've done at least one check
                        test_checks['test_run'] = True

                        check_state.next = t_check_state.IDLE

                    except queue.Empty:
                        pass

            return stimulate_check, master_bfm

        bitfields_configs = {
            key: create_bitfields_config(self.data_width)[0]
            for key in self.writeable_registers if random.random() < 0.5}

        registers = Registers(
            self.register_list, self.register_types,
            register_width=self.data_width, bitfields=bitfields_configs)

        self.default_args['registers'] = registers

        for reg_name in bitfields_configs:
            assert registers.register_types[reg_name] != 'axi_read_only'

            bitfield_interface_types = {
                name: 'output' for name in bitfields_configs[reg_name]}

            bitfield_interface_types['register'] = 'output'

            self.default_arg_types['registers'][reg_name] = (
                bitfield_interface_types)


        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, self.default_args,
            self.default_arg_types,
            custom_sources=[(testbench, (), self.default_args)])

        assert(test_checks['test_run'])
        assert(test_checks['check_done'])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_read_from_register_with_bitfield(self):
        ''' On reading a register that contains a bitfield, the value read
        should be the concatenation of the bitfields.
        '''
        cycles = 4000

        test_checks = {'test_run': False, 'check_done': False}

        def check_bitfield(expected_reg_val, bitfields):

            self.assertEqual(expected_reg_val, bitfields.register)

            for name in bitfields._bitfields_config:
                offset = bitfields._bitfields_config[name]['offset']
                mask = bitfields._bitfield_masks[name]
                expected_val = (mask & expected_reg_val) >> offset

                self.assertEqual(getattr(bitfields, name).val, expected_val)


        # FIXME need to set the RW registers in the test.

        @block
        def testbench(clock, axil_nreset, axi_lite_interface, registers):

            axi_lite_bfm = AxiLiteMasterBFM()
            master_bfm = axi_lite_bfm.model(
                self.clock, self.axil_nreset, self.axi_lite_interface)

            add_write_transaction_prob = 0.05

            t_check_state = enum(
                'IDLE', 'DO_READ', 'AWAIT_RESPONSE')
            check_state = Signal(t_check_state.IDLE)

            test_data = {'address': 0,
                         'write_response': None,}

            register_lookup = {
                n: name for n, name in enumerate(registers._register_types)}

            expected_reg_val = [0]

            def randomise_bitfields(register):
                packed_reg_val = 0

                for bf_name in register._bitfields_config:
                    bitfield = getattr(register, bf_name)

                    offset = register._bitfields_config[bf_name]['offset']
                    bf_type = register._bitfields_config[bf_name]['type']

                    if bf_type == 'bool':
                        val = random.choice((True, False))

                    else:
                        length = register._bitfields_config[bf_name]['length']
                        val = random.randrange(0, 2**length)

                    bitfield.next = val
                    packed_reg_val += val << offset

                return packed_reg_val


            @always(clock.posedge)
            def stimulate_check():

                if check_state == t_check_state.IDLE:
                    if random.random() < add_write_transaction_prob:

                        test_data['address'] = random.choice(
                            self.read_only_registers_indices)

                        reg_name = register_lookup[test_data['address']]

                        # Randomise all the read only bitfields
                        register = getattr(registers, reg_name)

                        if reg_name in bitfields_configs:
                            expected_reg_val[0] = randomise_bitfields(register)
                        else:
                            expected_reg_val[0] = random.randrange(0, 2**32)
                            register.next = expected_reg_val[0]

                        check_state.next = t_check_state.DO_READ

                elif check_state == t_check_state.DO_READ:
                    # We wait a cycle to do the read, so the bitfields are
                    # set up properly

                    # Add the write transaction to the queue.
                    axi_lite_bfm.add_read_transaction(
                        read_address=(
                            self.addr_remap_ratio*test_data['address']))

                    check_state.next = t_check_state.AWAIT_RESPONSE

                elif check_state == t_check_state.AWAIT_RESPONSE:
                    try:
                        # Try to get the response from the responses Queue.
                        # Quietly continue if it's not there yet by branching
                        # to the exception handler
                        read_resp = axi_lite_bfm.read_responses.get(False)

                        # Check that the read response is not an error.
                        assert(read_resp['rd_resp']==0)
                        self.assertEqual(
                            read_resp['rd_data'], expected_reg_val[0])

                        # We've done at least one check
                        test_checks['test_run'] = True

                        check_state.next = t_check_state.IDLE

                    except queue.Empty:
                        pass

            return stimulate_check, master_bfm

        bitfields_configs = {
            key: create_bitfields_config(self.data_width)[0]
            for key in self.readable_registers if random.random() < 0.5}

        registers = Registers(
            self.register_list, self.register_types,
            register_width=self.data_width, bitfields=bitfields_configs)

        self.default_args['registers'] = registers

        for reg_name in bitfields_configs:
            assert registers.register_types[reg_name] in (
                'axi_read_only', 'axi_read_write')

            if registers.register_types[reg_name] == 'axi_read_only':
                bitfield_interface_types = {
                    name: 'custom' for name in bitfields_configs[reg_name]}

                # registers are always outputs since they are built from
                # the signals.
                bitfield_interface_types['register'] = 'output'
                self.default_arg_types['registers'][reg_name] = (
                    bitfield_interface_types)

            else:
                bitfield_interface_types = {
                    name: 'output' for name in bitfields_configs[reg_name]}

                bitfield_interface_types['register'] = 'output'
                self.default_arg_types['registers'][reg_name] = (
                    bitfield_interface_types)


        dut_outputs, ref_outputs = self.cosimulate(
            cycles, axi_lite_handler, axi_lite_handler, self.default_args,
            self.default_arg_types,
            custom_sources=[(testbench, (), self.default_args)])

        assert(test_checks['test_run'])

        self.assertEqual(dut_outputs, ref_outputs)


class TestAxiLiteHandlerBehaviouralVivadoVhdlSimulation(
    KeaVivadoVHDLTestCase, TestAxiLiteHandlerBehaviouralSimulation):
    pass

class TestAxiLiteHandlerBehaviouralVivadoVerilogSimulation(
    KeaVivadoVerilogTestCase, TestAxiLiteHandlerBehaviouralSimulation):
    pass
