from math import log, ceil
from myhdl import block, Signal, intbv, always, enum, modbv

from kea.hdl.axi import AxiLiteInterface, axi_lite
from kea.hdl.signal_handling.asynchronous import (
    signal_assigner, signal_slicer)

from ._registers import Registers, Bitfields

VALID_DATA_BITWIDTHS = (32, 64)

@block
def axi_lite_handler(
    clock, axil_nreset, axi_lite_interface, registers, last_written_reg_addr,
    last_written_reg_data, write_count):

    if not isinstance(axi_lite_interface, AxiLiteInterface):
        raise ValueError(
            'axi_lite_handler: axi_lite_interface needs to be an instance of '
            'AxiLiteInterface')

    if not isinstance(registers, Registers):
        raise ValueError(
            'axi_lite_handler: registers need to be an instance of Registers')

    if (len(axi_lite_interface.WDATA) != len(axi_lite_interface.RDATA)):
        raise ValueError(
            'axi_lite_handler: Read and write data should be of equal width')

    data_bitwidth = len(axi_lite_interface.WDATA)

    if (len(axi_lite_interface.AWADDR) != len(axi_lite_interface.ARADDR)):
        raise ValueError(
            'axi_lite_handler: Read and write addresses should be of equal '
            'width')

    addr_bitwidth = len(axi_lite_interface.AWADDR)

    for n in VALID_DATA_BITWIDTHS:
        # Sanity check to make sure all valid data bitwidths are a power of 2,
        # are a multiple of 8 and are greater than 8.
        assert((n & (n-1) == 0) and (n % 8 == 0) and (n > 8))

    if data_bitwidth not in VALID_DATA_BITWIDTHS:
        raise ValueError('axi_lite_handler: Data width must be 32 or 64 bits')

    if hasattr(axi_lite_interface, 'AWPROT'):
        raise TypeError(
            'axi_lite_handler: The axi_lite_interface includes AWPROT but '
            'the axi_lite_handler does not support AWPROT')

    if hasattr(axi_lite_interface, 'ARPROT'):
        raise TypeError(
            'axi_lite_handler: The axi_lite_interface includes ARPROT but '
            'the axi_lite_handler does not support ARPROT')

    if hasattr(axi_lite_interface, 'WSTRB'):
        raise TypeError(
            'axi_lite_handler: The axi_lite_interface includes WSTRB but '
            'the axi_lite_handler does not support WSTRB')

    if registers.register_width != data_bitwidth:
        raise TypeError(
            'axi_lite_handler: The axi_lite_interface data width should be '
            'the same as the register bitwidth')

    if len(last_written_reg_data) != data_bitwidth:
        raise TypeError(
            'axi_lite_handler: the bitwidth of last_written_reg_data should '
            'be equal to the bitwidths of the data signals on the '
            'axi_lite_interface')

    if len(last_written_reg_addr) != addr_bitwidth:
        raise TypeError(
            'axi_lite_handler: the bitwidth of last_written_reg_addr should '
            'be equal to the bitwidths of the address signals on the '
            'axi_lite_interface')

    if write_count.val != 0:
        raise ValueError(
            'axi_lite_handler: The write_count should initialise with 0')

    return_objects = []

    # This block addresses in words and the AXI addresses are in bytes so we
    # need to remap the AXIS address from bytes to words. Calculate the number
    # of bits that address the bytes and the number of bits which address the
    # word.
    byte_addr_bitwidth = int(log(data_bitwidth//8, 2))
    word_addr_bitwidth = addr_bitwidth - byte_addr_bitwidth

    n_registers = len(registers.register_types)

    if n_registers > 2**word_addr_bitwidth:
        raise ValueError(
            'axi_lite_handler: n_registers too large for the address width')

    # Connect up the bitfields
    for reg_name in registers.bitfields:
        bitfields = getattr(registers, reg_name)
        return_objects.append(bitfields.bitfield_connector())

    # Create lists of registers
    write_signals = [None for n in range(n_registers)]
    read_signals = [None for n in range(n_registers)]
    wo_registers = [None for n in range(n_registers)]

    for name in registers.register_types:

        interface_object = getattr(registers, name)

        if isinstance(interface_object, Bitfields):
            interface_register = interface_object.register
        else:
            interface_register = interface_object

        reg_initial_val = interface_register.val
        reg_offset = registers.register_offset(name)
        reg_type = registers.register_types[name]

        write_signal = Signal(intbv(reg_initial_val)[data_bitwidth:])
        read_signal = Signal(intbv(reg_initial_val)[data_bitwidth:])

        write_signals[reg_offset] = write_signal
        read_signals[reg_offset] = read_signal

        if reg_type == 'axi_read_write':
            # The register should be written by this block in response to AXI
            # write transactions.
            return_objects.append(
                signal_assigner(write_signal, interface_register))

            # The register should be read by this block in response to AXI
            # read transactions. The read signal should track the write
            # signal.
            return_objects.append(signal_assigner(write_signal, read_signal))

            # I tried multiple techniques to record which registers are write
            # only (using a ROM, Signal(False) etc). This specific combination
            # of a list of 1 bit intbv signals was the only one that worked
            # when converted to VHDL and Verilog.
            wo_registers[reg_offset] = Signal(intbv(0)[1:])
            wo_registers[reg_offset].driven = 'reg'

        elif reg_type == 'axi_read_only':
            # The write signal should be ignored
            write_signal.read = True

            # The register should be read by this block in response to AXI
            # read transactions. The read signal should track the register.
            return_objects.append(
                signal_assigner(interface_register, read_signal))

            # I tried multiple techniques to record which registers are write
            # only (using a ROM, Signal(False) etc). This specific combination
            # of a list of 1 bit intbv signals was the only one that worked
            # when converted to VHDL and Verilog.
            wo_registers[reg_offset] = Signal(intbv(0)[1:])
            wo_registers[reg_offset].driven = 'reg'

        elif reg_type == 'axi_write_only':
            # The register should be written by this block in response to AXI
            # write transactions.
            return_objects.append(
                signal_assigner(write_signal, interface_register))

            # The read signal should not be used. Set driven to `reg` to
            # supress the Myhdl conversion warning that the signal is not
            # driven
            read_signal.driven = 'reg'

            # I tried multiple techniques to record which registers are write
            # only (using a ROM, Signal(False) etc). This specific combination
            # of a list of 1 bit intbv signals was the only one that worked
            # when converted to VHDL and Verilog.
            wo_registers[reg_offset] = Signal(intbv(1)[1:])
            wo_registers[reg_offset].driven = 'reg'

        else:
            raise ValueError(
                'axi_lite_handler: Unknown register type: \'%s\' is not '
                'defined.' % reg_type)

    # Check that all the register signals have been set correctly
    assert(None not in write_signals)
    assert(None not in read_signals)
    assert(None not in wo_registers)

    pending_write_count = Signal(modbv(1)[len(write_count):])

    # Create the address and data buffers
    wr_addr_buffer = Signal(intbv(0)[addr_bitwidth:])
    wr_data_buffer = Signal(intbv(0)[data_bitwidth:])

    # Extract the byte address from the AWADDR signal
    wr_byte_addr = Signal(intbv(0)[byte_addr_bitwidth:])
    return_objects.append(
        signal_slicer(
            axi_lite_interface.AWADDR, 0, byte_addr_bitwidth,
            wr_byte_addr))

    # Extract the word address from the AWADDR signal
    wr_word_addr = Signal(intbv(0)[word_addr_bitwidth:])
    return_objects.append(
        signal_slicer(
            axi_lite_interface.AWADDR, byte_addr_bitwidth, word_addr_bitwidth,
            wr_word_addr))

    # Extract the byte address from the wr_addr_buffer
    wr_byte_addr_buffer = Signal(intbv(0)[byte_addr_bitwidth:])
    return_objects.append(
        signal_slicer(
            wr_addr_buffer, 0, byte_addr_bitwidth, wr_byte_addr_buffer))

    # Extract the word address from the wr_addr_buffer
    wr_word_addr_buffer = Signal(intbv(0)[word_addr_bitwidth:])
    return_objects.append(
        signal_slicer(
            wr_addr_buffer, byte_addr_bitwidth, word_addr_bitwidth,
            wr_word_addr_buffer))

    # Extract the byte address from the ARADDR signal
    rd_byte_addr = Signal(intbv(0)[byte_addr_bitwidth:])
    return_objects.append(
        signal_slicer(
            axi_lite_interface.ARADDR, 0, byte_addr_bitwidth,
            rd_byte_addr))

    # Extract the word address from the ARADDR signal
    rd_word_addr = Signal(intbv(0)[word_addr_bitwidth:])
    return_objects.append(
        signal_slicer(
            axi_lite_interface.ARADDR, byte_addr_bitwidth, word_addr_bitwidth,
            rd_word_addr))

    t_wr_state = enum(
        'IDLE', 'READY', 'ADDR_RECEIVED', 'DATA_RECEIVED', 'RESPOND')
    wr_state = Signal(t_wr_state.IDLE)

    @always(clock.posedge)
    def write():

        for n in range(n_registers):
            if wo_registers[n]:
                # Iterate over all write signals and if they are write only
                # set them low. The write only registers should pulse for one
                # cycle.
                write_signals[n].next = 0

        if wr_state == t_wr_state.IDLE:
            # Ready to receive so set the ready signals.
            axi_lite_interface.AWREADY.next = True
            axi_lite_interface.WREADY.next = True
            wr_state.next = t_wr_state.READY

        elif wr_state == t_wr_state.READY:

            if (axi_lite_interface.AWVALID and
                axi_lite_interface.WVALID):
                # Received address and data from the master.
                axi_lite_interface.AWREADY.next = False
                axi_lite_interface.WREADY.next = False

                if wr_byte_addr == 0 and wr_word_addr < n_registers:
                    # Check that the address is word aligned and specifies a
                    # register. If so, store the received data in the received
                    # address.
                    write_signals[wr_word_addr].next = (
                        axi_lite_interface.WDATA)

                    # Increment the write_count
                    write_count.next = pending_write_count
                    pending_write_count.next = pending_write_count + 1

                    # Update the last written address and data signals
                    last_written_reg_addr.next = axi_lite_interface.AWADDR
                    last_written_reg_data.next = axi_lite_interface.WDATA

                    axi_lite_interface.BRESP.next = axi_lite.OKAY

                else:
                    # Otherwise respond with an error
                    axi_lite_interface.BRESP.next = axi_lite.SLVERR

                # Setup the response transaction.
                axi_lite_interface.BVALID.next = True

                wr_state.next = t_wr_state.RESPOND

            elif axi_lite_interface.AWVALID:
                # Received address from the master
                axi_lite_interface.AWREADY.next = False
                wr_addr_buffer.next = axi_lite_interface.AWADDR
                wr_state.next = t_wr_state.ADDR_RECEIVED

            elif axi_lite_interface.WVALID:
                # Received data from the master.
                axi_lite_interface.WREADY.next = False
                wr_data_buffer.next = axi_lite_interface.WDATA
                wr_state.next = t_wr_state.DATA_RECEIVED

        elif wr_state == t_wr_state.ADDR_RECEIVED:
            if axi_lite_interface.WVALID:
                # Received data from the master.
                axi_lite_interface.WREADY.next = False

                if (wr_byte_addr_buffer == 0 and
                    wr_word_addr_buffer < n_registers):
                    # Store the received data in the buffered address.
                    write_signals[wr_word_addr_buffer].next = (
                        axi_lite_interface.WDATA)

                    # Increment the write_count
                    write_count.next = pending_write_count
                    pending_write_count.next = pending_write_count + 1

                    # Update the last written address and data signals
                    last_written_reg_addr.next = wr_addr_buffer
                    last_written_reg_data.next = axi_lite_interface.WDATA

                    axi_lite_interface.BRESP.next = axi_lite.OKAY

                else:
                    # Otherwise the address is invalid
                    axi_lite_interface.BRESP.next = axi_lite.SLVERR

                # Set up the response transaction.
                axi_lite_interface.BVALID.next = True
                wr_state.next = t_wr_state.RESPOND

        elif wr_state == t_wr_state.DATA_RECEIVED:
            if axi_lite_interface.AWVALID:
                # Received address from the master.
                axi_lite_interface.AWREADY.next = False

                if wr_byte_addr == 0 and wr_word_addr < n_registers:
                    # Check that the address is word aligned and specifies a
                    # register. Is so, store the received data in the received
                    # address.
                    write_signals[wr_word_addr].next = wr_data_buffer

                    # Increment the write_count
                    write_count.next = pending_write_count
                    pending_write_count.next = pending_write_count + 1

                    # Update the last written address and data signals
                    last_written_reg_addr.next = axi_lite_interface.AWADDR
                    last_written_reg_data.next = wr_data_buffer

                    axi_lite_interface.BRESP.next = axi_lite.OKAY

                else:
                    # Otherwise the address is invalid
                    axi_lite_interface.BRESP.next = axi_lite.SLVERR

                # Set up the response transaction.
                axi_lite_interface.BVALID.next = True

                wr_state.next = t_wr_state.RESPOND

        elif wr_state == t_wr_state.RESPOND:
            if axi_lite_interface.BREADY:
                # Response has been received so set the valid signal low
                # again.
                axi_lite_interface.BVALID.next = False
                wr_state.next = t_wr_state.IDLE

        if not axil_nreset:
            # Reset so drive control signals low and return to idle.
            axi_lite_interface.AWREADY.next = False
            axi_lite_interface.WREADY.next = False
            axi_lite_interface.BVALID.next = False
            wr_state.next = t_wr_state.IDLE

    return_objects.append(write)

    t_rd_state = enum('IDLE', 'READY', 'RESPOND')
    rd_state = Signal(t_rd_state.IDLE)

    @always(clock.posedge)
    def read():

        if rd_state == t_rd_state.IDLE:
            # Ready to receive so set the ready signal.
            axi_lite_interface.ARREADY.next = True
            rd_state.next = t_rd_state.READY

        elif rd_state == t_rd_state.READY:
            if axi_lite_interface.ARVALID:
                # Received the read address so respond with the data.
                axi_lite_interface.ARREADY.next = False
                axi_lite_interface.RVALID.next = True

                if rd_byte_addr == 0 and rd_word_addr < n_registers:
                    # Check that the address is word aligned and specifies a
                    # register. Is so, store the received data in the received
                    # address.
                    axi_lite_interface.RDATA.next = read_signals[rd_word_addr]
                    axi_lite_interface.RRESP.next = axi_lite.OKAY

                else:
                    axi_lite_interface.RDATA.next = 0
                    axi_lite_interface.RRESP.next = axi_lite.SLVERR

                rd_state.next = t_rd_state.RESPOND

        elif rd_state == t_rd_state.RESPOND:
            if axi_lite_interface.RREADY:
                # Response has been received.
                axi_lite_interface.RVALID.next = False
                rd_state.next = t_rd_state.IDLE

        if not axil_nreset:
            # Axi nreset so drive control signals low and return to idle.
            axi_lite_interface.ARREADY.next = False
            axi_lite_interface.RVALID.next = False
            rd_state.next = t_rd_state.IDLE

    return_objects.append(read)

    return return_objects
