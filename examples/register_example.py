from kea.axi_lite_registers import Registers, axi_lite_handler
from kea.axi import AxiLiteInterface, AxiLiteMasterBFM

import random

from myhdl import *
import myhdl

try:
    import queue
except ImportError:
    import Queue as queue

register_names = [
        'control', 'counter_reset_value', 'status']

@block
def counter_block(clock, axil_resetn, axi_lite_bus):

    register_types = {
        'control': 'axi_write_only',
        'counter_reset_value': 'axi_read_write',
        'status': 'axi_read_only'}

    register_initial_values = {
        'counter_reset_value': 100}

    registers = Registers(
        register_names, register_types,
        initial_values=register_initial_values)

    counter = Signal(intbv(0)[32:])

    @always(clock.posedge)
    def do_counter():

        if registers.control[0]:
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

    t_test_states = enum('IDLE', 'READING', 'WRITING')
    test_state = Signal(t_test_states.IDLE)

    @always(clock.posedge)
    def test_driver():

        if test_state == t_test_states.IDLE:
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
                pass

        elif test_state == t_test_states.READING:
            try:
                response = bfm.read_responses.get(block=False)
                print('Response: %d' % response['rd_data'])
                test_state.next = t_test_states.IDLE

            except queue.Empty:
                pass


    return clock_gen, counter, bfm_inst, test_driver

def runner():

    top_inst = top()
    top_inst.run_sim()

if __name__ == '__main__':
    runner()
