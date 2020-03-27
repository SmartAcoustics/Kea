from kea.axi_lite_registers import Registers, axi_lite_handler
from kea.axi import AxiLiteInterface, AxiLiteMasterBFM

import random

from myhdl import *
import myhdl

try:
    import queue
except ImportError:
    import Queue as queue

# This is a simple list giving the names of the registers.
# The order is the index of the register, so 'control' is index 0 and
# 'system_id' is index 3, and the byte address should be derived from that
# index (see the test driver).
register_names = [
        'control', 'counter_reset_value', 'status', 'system_id']

# bitfields is a description of the bitfield layout of each register
# It is optional for each register, with the key for a given register given
# by its name.
# For RO registers, if a bitfield is set on that register, then the register
# will be driven by the bitfield, so it will likely be an error to drive the
# register itself as well. That is, you should then drive the bitfields
# individually.
# See the documentation for Bitfields in axi_lite_registers/_registers.py for
# the correct form of a bitfields definition.
# Here we show the const-uint type being used, which is intended as a means
# to convey build-time information to software, but can be used for whatever
# you want (the signal will be connected up and driven by the constant value).
bitfields = {
    'control': {'go': {'type': 'bool', 'offset': 0}},
    'system_id': {'device_type': {'type': 'const-uint',
                                  'length': 8,
                                  'offset': 0,
                                  'const-value': 0x5},
                  'system_config_id': {'type': 'const-uint',
                                       'length': 8,
                                       'offset': 8,
                                       'const-value': 0x3}
                 }}

@block
def counter_block(clock, axil_resetn, axi_lite_bus):

    # Missing registers in register_types default to read-write.
    register_types = {
        'control': 'axi_write_only',
        'counter_reset_value': 'axi_read_write',
        'status': 'axi_read_only',
        'system_id': 'axi_read_only'}

    # Initial_values only make sense for RW registers and it's an error to
    # use them on RO or WO registers.
    # Missing initial values default to zero. In the case in which bitfields
    # are set on the register, the value in this dict can be itself a dict
    # to bitfield initial values (with keys given by the bitfield names).
    register_initial_values = {
        'counter_reset_value': 100}

    registers = Registers(
        register_names, register_types,
        initial_values=register_initial_values,
        bitfields=bitfields)

    counter = Signal(intbv(0)[32:])

    @always(clock.posedge)
    def do_counter():

        # Look, we access the go field directly!
        if registers.control.go:
            # Reset
            counter.next = 0

        elif counter >= registers.counter_reset_value:
            counter.next = 0

        else:
            counter.next = counter + 1

    @always_comb
    def status_connector():
        registers.status.next = counter

    register_handler = axi_lite_handler(
        clock, axil_resetn, axi_lite_bus, registers)

    return do_counter, status_connector, register_handler

@block
def clock_source(clock, period):

    if not isinstance(clock, myhdl._Signal._Signal):
        raise ValueError('The passed clock signal is not a signal')

    even_period = period//2
    odd_period = period - even_period

    start_val = int(clock.val)
    not_start_val = int(not clock.val)

    clock_state = Signal(clock.val)

    @instance
    def clockgen():

        while True:
            yield(delay(even_period))
            clock.next = not clock_state
            clock_state.next = not clock_state
            yield(delay(odd_period))
            clock.next = not clock_state
            clock_state.next = not clock_state

    return clockgen


@block
def top():
    '''A simple test example that controls a counter through a register
    interface, using the BFM.

    With some probability, the counter is either reset, the value is changed
    or the counter is read.
    '''
    data_width = 32
    addr_width = 4

    # Allows a nice way to do AxiLite stuff.
    # The transactions and responses are handled through a thread-safe Queue
    # which means you should be able to handle it all asynchronously nice and
    # safely (assuming you use the proper interface).
    bfm = AxiLiteMasterBFM()

    axi_lite_interface = AxiLiteInterface(
        data_width, addr_width, use_AWPROT=False, use_ARPROT=False,
        use_WSTRB=False)

    axil_resetn = Signal(True)
    clock = Signal(False)

    period = 10
    clock_gen = clock_source(clock, period)
    counter = counter_block(clock, axil_resetn, axi_lite_interface)

    bfm_inst = bfm.model(clock, axil_resetn, axi_lite_interface)

    t_test_states = enum('INIT', 'IDLE', 'READING', 'WRITING')
    test_state = Signal(t_test_states.INIT)

    @always(clock.posedge)
    def test_driver():

        if test_state == t_test_states.INIT:
            print('Reading the system id')
            bfm.add_read_transaction(register_names.index('system_id') * 4)
            test_state.next = t_test_states.READING

        elif test_state == t_test_states.IDLE:
            random_val = random.random()

            # Remember, the list index should be multiplied by 4 to get the
            # byte address
            if random_val < 0.1:
                # Reset the counter
                print('Resetting the counter')
                bfm.add_write_transaction(
                    register_names.index('control') * 4, 1)

                test_state.next = t_test_states.WRITING

            elif random_val < 0.2:
                upper_val = random.randrange(40, 150)
                # change the counter upper value
                print('Changing the upper value to %d' % upper_val)
                bfm.add_write_transaction(
                    register_names.index('counter_reset_value') * 4,
                    upper_val)
                test_state.next = t_test_states.WRITING

            elif random_val < 0.6:
                print('Reading the current counter value')
                bfm.add_read_transaction(register_names.index('status') * 4)
                test_state.next = t_test_states.READING

        elif test_state == t_test_states.WRITING:

            try:
                response = bfm.write_responses.get(block=False)
                print('Response: %d' % response['wr_resp'])
                test_state.next = t_test_states.IDLE

            except queue.Empty:
                # no response yet
                pass

        elif test_state == t_test_states.READING:
            try:
                response = bfm.read_responses.get(block=False)
                print('Response: %d' % response['rd_data'])
                test_state.next = t_test_states.IDLE

            except queue.Empty:
                # no response yet
                pass


    return clock_gen, counter, bfm_inst, test_driver

def runner():

    top_inst = top()
    top_inst.run_sim()


def register_converter():
    '''An example that is independent of the counter example that simply
    creates a register set and converts it. It shows a minimal useful example
    of using the registers.
    '''

    data_width = 32
    addr_width = 4

    register_types = {
        'control': 'axi_write_only',
        'counter_reset_value': 'axi_read_write',
        'status': 'axi_read_only',
        'system_id': 'axi_read_only'}

    register_initial_values = {
        'counter_reset_value': 100}

    # register_initial_values and bitfields are both optional, but provide
    # some useful functionality.
    # Registers is reasonably well documented in
    # axi_lite_registers/_registers.py
    # The correct types and fields for the bitfields object are described
    # in the Bitfields class in that same file (it's the bitfields_config
    # argument to Bitfields, which is passed straight through by Registers).
    registers = Registers(
        register_names, register_types,
        initial_values=register_initial_values,
        bitfields=bitfields)

    # We need to creat the axi-lite bus
    axi_lite_interface = AxiLiteInterface(
        data_width, addr_width, use_AWPROT=False, use_ARPROT=False,
        use_WSTRB=False)

    axil_resetn = Signal(True)
    clock = Signal(False)

    # axi_lite_handler does all the cleverness in joining up the registers
    # correctly to the axi-lite bus.
    # * Writeable registers (RW and WO) are driven by this block.
    # * Read only registers are only read and the signal is expected to be
    # driven elsewhere within your code (though obviously it will still work
    # if not, just it won't do very much).
    register_handler = axi_lite_handler(
        clock, axil_resetn, axi_lite_interface, registers)

    # Needed to use the register initial values stuff reliably
    # (alternatively, use myhdl.toVHDL.initial_values)
    myhdl.toVerilog.initial_values = True

    register_handler.convert()


if __name__ == '__main__':
    # Convert an example (because we can)
    register_converter()

    # Separately, run an example
    runner()
