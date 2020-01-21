from kea.axi import AxiLiteInterface, axi_lite
from ._registers import Registers, Bitfields
from myhdl import *
from math import log, ceil

@block
def ro_register_assignments(register, read_signal):
    @always_comb
    def assign():
        read_signal.next = register

    return assign

@block
def rw_register_assignments(register, read_signal, write_signal):

    @always_comb
    def assign():
        read_signal.next = write_signal
        register.next = write_signal

    return assign

@block
def wo_register_assignments(
    clock, register, read_signal, write_signal, do_write):

    zero_register = Signal(intbv(0, read_signal.min, read_signal.max))

    @always_comb
    def assign():
        if do_write:
            register.next = write_signal
        else:
            register.next = 0

    @always_comb
    def assign_zero_read():
        read_signal.next = zero_register

    @always(clock.posedge)
    def assign_zero_register():
        zero_register.next = 0

    return assign, assign_zero_read, assign_zero_register

@block
def axi_lite_handler(
    clock, axil_nreset, axi_lite_interface, registers):

    if not isinstance(axi_lite_interface, AxiLiteInterface):
        raise ValueError(
            'axi_lite_interface needs to be an instance of AxiLiteInterface')

    if not isinstance(registers, Registers):
        raise ValueError('registers need to be an instance of Registers')

    if (len(axi_lite_interface.WDATA) != len(axi_lite_interface.RDATA)):
        raise ValueError('Read and write data should be of equal width')

    if (len(axi_lite_interface.AWADDR) != len(axi_lite_interface.ARADDR)):
        raise ValueError('Read and write addresses should be of equal width')

    if len(axi_lite_interface.WDATA) not in (32, 64):
        raise ValueError('Data width must be 32 or 64 bits')

    # Need to remap the address from words to bytes to work with the
    # software on the PS
    addr_remap_ratio = len(axi_lite_interface.WDATA)//8

    # The number of bits that should be taken off the address to account for
    # the byte addressing.
    byte_to_word_shift = int(log(addr_remap_ratio, 2))

    if (len(registers.register_types) > 2**(
        len(axi_lite_interface.AWADDR)-byte_to_word_shift)):
        raise ValueError('n_registers too large for the address width')

    # This gives us the required number of bits to address all of the
    # registers.
    required_addr_width = (
        int(ceil(log(len(registers.register_types), 2))) + byte_to_word_shift)

    # Create lists of registers
    write_signals = []
    read_signals = []
    assignment_blocks = []
    do_write_signals = []

    n_registers = len(registers.register_types)

    for name in registers.register_types:

        interface_object = getattr(registers, name)

        if isinstance(interface_object, Bitfields):
            interface_register = interface_object.register
        else:
            interface_register = interface_object

        reg_initial_val = interface_register.val
        reg_type = registers.register_types[name]

        write_signal = Signal(
            intbv(reg_initial_val)[len(interface_register):])
        read_signal = Signal(
            intbv(reg_initial_val)[len(interface_register):])
        do_write = Signal(False)

        write_signals.append(write_signal)
        read_signals.append(read_signal)
        do_write_signals.append(do_write)

        if reg_type == 'axi_read_write':
            # For read write registers create the correct type of register.
            assignment_blocks.append(
                rw_register_assignments(
                    interface_register, read_signal, write_signal))

        elif reg_type == 'axi_read_only':
            # For read only registers create the correct type of register.
            assignment_blocks.append(
                ro_register_assignments(interface_register, read_signal))

        elif reg_type == 'axi_write_only':
            # For write only registers create the correct type of register.
            assignment_blocks.append(
                wo_register_assignments(
                    clock, interface_register, read_signal, write_signal, do_write))

        else:
            raise ValueError(
                'Unknown register type: \'%s\' is not defined.' % reg_type)

    t_write_state = enum(
        'IDLE', 'READY', 'ADDR_RECEIVED', 'DATA_RECEIVED', 'RESPOND')
    write_state = Signal(t_write_state.IDLE)

    t_read_state = enum('IDLE', 'READY', 'RESPOND')
    read_state = Signal(t_read_state.IDLE)

    # Create the address and data buffers
    write_address_buffer = Signal(intbv(0)[len(axi_lite_interface.AWADDR):])
    write_data_buffer = Signal(intbv(0)[len(axi_lite_interface.WDATA):])

    valid_write_address = Signal(False)
    valid_read_address = Signal(False)

    valid_write_address_buffer = Signal(False)

    # Create the internal remapped address signals
    if required_addr_width==byte_to_word_shift:
        # There is only one register.
        word_write_address = Signal(intbv(0)[1:])
        word_read_address = Signal(intbv(0)[1:])
    else:
        word_write_address = (
            Signal(intbv(0)[required_addr_width-byte_to_word_shift:]))
        word_read_address = (
            Signal(intbv(0)[required_addr_width-byte_to_word_shift:]))

    if required_addr_width==byte_to_word_shift:
        @always_comb
        def address_remap():
            '''
            Need to remap the address signals to remove the byte indexing which
            comes from software.

            We also at this point check that the address is valid, deasserting
            valid_read_address or valid_write_address flag as necessary.
            '''

            # There is only one register so address should always be zero.
            word_write_address.next = 0
            word_read_address.next = 0

            # Only write to the register if the address is zero
            if axi_lite_interface.AWADDR == 0:
                valid_write_address.next = True
            else:
                valid_write_address.next = False

            # Only read from the register if the address is zero
            if axi_lite_interface.ARADDR == 0:
                valid_read_address.next = True
            else:
                valid_read_address.next = False

    else:
        @always_comb
        def address_remap():
            '''
            Need to remap the address signals to remove the byte indexing
            which comes from software.

            We also at this point check that the address is valid, deasserting
            valid_read_address or valid_write_address flag as necessary.
            '''

            if axi_lite_interface.AWADDR[
                required_addr_width:byte_to_word_shift] < n_registers:

                word_write_address.next = (
                    axi_lite_interface.AWADDR[
                        required_addr_width:byte_to_word_shift])

                valid_write_address.next = True

            else:
                word_write_address.next = 0
                valid_write_address.next = False

            if axi_lite_interface.ARADDR[
                required_addr_width:byte_to_word_shift] < n_registers:

                word_read_address.next = (
                    axi_lite_interface.ARADDR[
                        required_addr_width:byte_to_word_shift])

                valid_read_address.next = True

            else:
                word_read_address.next = 0
                valid_read_address.next = False

    @always(clock.posedge)
    def write():

        if not axil_nreset:
            # Reset so drive control signals low and return to idle.
            axi_lite_interface.AWREADY.next = False
            axi_lite_interface.WREADY.next = False
            axi_lite_interface.BVALID.next = False
            write_state.next = t_write_state.IDLE

        else:
            if write_state == t_write_state.IDLE:
                # Ready to receive so set the ready signals.
                axi_lite_interface.AWREADY.next = True
                axi_lite_interface.WREADY.next = True
                write_state.next = t_write_state.READY

            elif write_state == t_write_state.READY:

                if (axi_lite_interface.AWVALID and
                    axi_lite_interface.WVALID):
                    # Received address and data from the master.
                    axi_lite_interface.AWREADY.next = False
                    axi_lite_interface.WREADY.next = False

                    if valid_write_address:
                        # Store the received data in the received address.
                        write_signals[word_write_address].next = (
                            axi_lite_interface.WDATA)

                        axi_lite_interface.BRESP.next = axi_lite.OKAY

                    else:
                        # We must respond with an error
                        axi_lite_interface.BRESP.next = axi_lite.SLVERR

                    # Setup the response transaction.
                    axi_lite_interface.BVALID.next = True

                    # We need to buffer the write address in order to update
                    # do_write properly
                    write_address_buffer.next = word_write_address

                    valid_write_address_buffer.next = (
                        valid_write_address)

                    write_state.next = t_write_state.RESPOND

                elif axi_lite_interface.AWVALID:
                    # Received address from the master.
                    axi_lite_interface.AWREADY.next = False
                    # Store the address in a buffer.
                    write_address_buffer.next = word_write_address
                    valid_write_address_buffer.next = (
                        valid_write_address)

                    write_state.next = t_write_state.ADDR_RECEIVED

                elif axi_lite_interface.WVALID:
                    # Received data from the master.
                    axi_lite_interface.WREADY.next = False
                    # Store the data in a buffer.
                    write_data_buffer.next = axi_lite_interface.WDATA
                    write_state.next = t_write_state.DATA_RECEIVED

            elif write_state == t_write_state.ADDR_RECEIVED:
                if axi_lite_interface.WVALID:
                    # Received data from the master.
                    axi_lite_interface.WREADY.next = False

                    if valid_write_address_buffer:
                        # Store the received data in the buffered address.
                        write_signals[write_address_buffer].next = (
                            axi_lite_interface.WDATA)

                        axi_lite_interface.BRESP.next = axi_lite.OKAY

                    else:
                        axi_lite_interface.BRESP.next = axi_lite.SLVERR

                    # Set up the response transaction.
                    axi_lite_interface.BVALID.next = True
                    write_state.next = t_write_state.RESPOND

            elif write_state == t_write_state.DATA_RECEIVED:
                if axi_lite_interface.AWVALID:
                    # Received address from the master.
                    axi_lite_interface.AWREADY.next = False

                    if valid_write_address:
                        # Store the received data in the received address.
                        write_signals[word_write_address].next = (
                            write_data_buffer)

                        axi_lite_interface.BRESP.next = axi_lite.OKAY

                    else:
                        # We must respond with an error
                        axi_lite_interface.BRESP.next = axi_lite.SLVERR

                    # Set up the response transaction.
                    axi_lite_interface.BVALID.next = True

                    # Store the address in a buffer for do_write
                    write_address_buffer.next = word_write_address

                    write_state.next = t_write_state.RESPOND

            elif write_state == t_write_state.RESPOND:
                if axi_lite_interface.BREADY:
                    # Response has been received so set the valid signal low
                    # again.
                    axi_lite_interface.BVALID.next = False
                    write_state.next = t_write_state.IDLE

    @always(clock.posedge)
    def read():

        if not axil_nreset:
            # Axi nreset so drive control signals low and return to idle.
            axi_lite_interface.ARREADY.next = False
            axi_lite_interface.RVALID.next = False
            read_state.next = t_read_state.IDLE

        else:
            if read_state == t_read_state.IDLE:
                # Ready to receive so set the ready signal.
                axi_lite_interface.ARREADY.next = True
                read_state.next = t_read_state.READY

            elif read_state == t_read_state.READY:
                if axi_lite_interface.ARVALID:
                    # Received the read address so respond with the data.
                    axi_lite_interface.ARREADY.next = False
                    axi_lite_interface.RVALID.next = True

                    if valid_read_address:
                        axi_lite_interface.RDATA.next = (
                            read_signals[word_read_address])
                        axi_lite_interface.RRESP.next = axi_lite.OKAY

                    else:
                        axi_lite_interface.RDATA.next = 0
                        axi_lite_interface.RRESP.next = axi_lite.SLVERR

                    read_state.next = t_read_state.RESPOND

            elif read_state == t_read_state.RESPOND:
                if axi_lite_interface.RREADY:
                    # Response has been received.
                    axi_lite_interface.RVALID.next = False
                    read_state.next = t_read_state.IDLE

    n_do_writes = len(do_write_signals)

    if n_do_writes > 0:
        # Ideally this should be combined into the main state machine, but
        # this way we can optionally disable the block if we don't need it.
        #
        @always(clock.posedge)
        def assign_do_writes():
            '''Sets the do_write flag if and only if a write transaction
            happens.
            '''

            if not axil_nreset:
                for n in range(n_do_writes):
                    do_write_signals[n].next = False
            else:
                if write_state == t_write_state.READY:
                    if (axi_lite_interface.AWVALID and
                        axi_lite_interface.WVALID):

                        if valid_write_address:
                            do_write_signals[word_write_address].next = True

                    else:
                        pass

                elif write_state == t_write_state.ADDR_RECEIVED:
                    if axi_lite_interface.WVALID:
                        if valid_write_address_buffer:
                            do_write_signals[write_address_buffer].next = True


                elif write_state == t_write_state.DATA_RECEIVED:
                    if axi_lite_interface.AWVALID:
                        if valid_write_address:
                            do_write_signals[word_write_address].next = True

                    else:
                        pass

                elif write_state == t_write_state.RESPOND:
                    do_write_signals[write_address_buffer].next = False

                else:
                    # defensive catch
                    do_write_signals[write_address_buffer].next = False

    else:
        assign_do_writes = []

    # Connect up the bitfields
    bitfield_connections = []
    for bitfield in registers._bitfields:
        bitfield_connections.append(
            getattr(registers, bitfield).bitfield_connector())

    return (read, write, assignment_blocks, address_remap, assign_do_writes,
            bitfield_connections)
