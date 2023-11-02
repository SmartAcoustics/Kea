import random
import copy

from myhdl import (
    Signal, block, always, always_comb, intbv, enum, StopSimulation)

from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from ._spi_slave import spi_slave

def test_args_setup(data_word_length: int):
    ''' Generate the arguments and argument types for the DUT.
    '''
    clock = Signal(False)
    parallel_out = Signal(intbv(0)[data_word_length:])
    data_valid = Signal(False)
    spi_sclk = Signal(False)
    spi_mosi = Signal(False)
    spi_ncs = Signal(False)

    args = {
        'clock': clock,
        'parallel_out': parallel_out,
        'data_valid': data_valid,
        'spi_sclk': spi_sclk,
        'spi_ncs': spi_ncs,
        'spi_mosi': spi_mosi,
    }

    arg_types = {
        'clock': 'clock',
        'parallel_out': 'output',
        'data_valid': 'output',
        'spi_sclk': 'custom',
        'spi_ncs': 'custom',
        'spi_mosi': 'custom'
    }

    return args, arg_types

class TestSpiSlave(KeaTestCase):
    '''The SPI slave should read in as many bits as are determined by the
    length of a provided parallel out signal, with each bit set on a rising
    clock edge.
    '''
    @block
    def spi_master(
        self, reset, write_data_ready, write_data_valid, write_data,
        sclk_half_period, **dut_args,
    ):

        assert sclk_half_period > 1

        clock = dut_args['clock']
        spi_ncs = dut_args['spi_ncs']
        spi_mosi = dut_args['spi_mosi']
        spi_sclk = dut_args['spi_sclk']
        data_valid = dut_args['data_valid']

        data_buffer = Signal(intbv(0)[len(write_data):])

        new_data_available = Signal(False)
        parallel_store = Signal(intbv(0)[len(write_data):])

        bitwidth = len(write_data)

        bit_count = Signal(intbv(0, min=0, max=bitwidth))

        states = enum(
            'INIT', 'AWAITING_DATA', 'NEW_DATA_HOLD', 'SET_MOSI', 'SCLK_LOW_HOLD',
            'CLOCK_OUT', 'SCLK_HIGH_HOLD', 'COMPLETION_HOLD')
        state = Signal(states.INIT)

        NCS_HOLD_CYCLES = sclk_half_period

        ncs_hold_count = Signal(intbv(0, min=0, max=NCS_HOLD_CYCLES))
        sclk_hold_count = Signal(intbv(0, min=0, max=sclk_half_period))
        completion_hold_count = Signal(intbv(0, min=0, max=sclk_half_period))

        last_sclk = Signal(False)

        checker_states = enum('INIT', 'RUNNING')
        checker_state = Signal(checker_states.INIT)

        @always(clock.posedge)
        def spi_checker():
            '''A instance that just checks some spi invariants
            '''
            last_sclk.next = spi_sclk

            if checker_state == checker_states.INIT:
                last_sclk.next = True
                checker_state.next = checker_states.RUNNING

            elif checker_state == checker_states.RUNNING:
                if spi_sclk and not last_sclk:
                    assert spi_ncs == False

            if reset:
                checker_state.next = checker_states.INIT

        @always(clock.posedge)
        def spi_driver():

            if write_data_valid and write_data_ready:
                data_buffer.next = write_data
                write_data_ready.next = False
                new_data_available.next = True

            if state == states.INIT:
                spi_ncs.next = True
                spi_sclk.next = True
                write_data_ready.next = True
                new_data_available.next = False
                state.next = states.AWAITING_DATA

            elif state == states.AWAITING_DATA:
                if new_data_available:
                    parallel_store.next = data_buffer
                    new_data_available.next = False
                    write_data_ready.next = True
                    spi_ncs.next = False
                    bit_count.next = 0

                    ncs_hold_count.next = 1
                    state.next = states.SET_MOSI

            elif state == states.NEW_DATA_HOLD:
                if ncs_hold_count == NCS_HOLD_CYCLES - 1:
                    state.next = states.SET_MOSI
                else:
                    ncs_hold_count.next = ncs_hold_count + 1

            elif state == states.SET_MOSI:
                spi_sclk.next = False
                spi_mosi.next = parallel_store[bitwidth-1]
                parallel_store.next[bitwidth:1] = parallel_store[bitwidth-1:0]

                sclk_hold_count.next = 1
                state.next = states.SCLK_LOW_HOLD

            elif state == states.SCLK_LOW_HOLD:
                if sclk_hold_count == sclk_half_period - 1:
                    state.next = states.CLOCK_OUT
                else:
                    sclk_hold_count.next = sclk_hold_count + 1
                    state.next = states.SCLK_LOW_HOLD

            elif state == states.CLOCK_OUT:
                spi_sclk.next = True
                sclk_hold_count.next = 1
                state.next = states.SCLK_HIGH_HOLD

            elif state == states.SCLK_HIGH_HOLD:
                if sclk_hold_count == sclk_half_period - 1:
                    if bit_count == bitwidth - 1:
                        if new_data_available:
                            parallel_store.next = data_buffer
                            new_data_available.next = False
                            write_data_ready.next = True
                            bit_count.next = 0

                            state.next = states.SET_MOSI

                        else:
                            state.next = states.COMPLETION_HOLD

                    else:
                        bit_count.next = bit_count + 1
                        state.next = states.SET_MOSI
                else:
                    sclk_hold_count.next = sclk_hold_count + 1
                    state.next = states.SCLK_HIGH_HOLD

            elif state == states.COMPLETION_HOLD:
                if completion_hold_count == sclk_half_period - 1:
                    completion_hold_count.next = 0

                    spi_ncs.next = True
                    state.next = states.AWAITING_DATA

                else:
                    completion_hold_count.next = completion_hold_count + 1

            if reset:
                state.next = states.INIT

        return spi_driver, spi_checker

    @block
    def check(self, **dut_args):
        clock = dut_args['clock']
        spi_sclk = dut_args['spi_sclk']
        spi_mosi = dut_args['spi_mosi']
        spi_ncs = dut_args['spi_ncs']
        data_valid = dut_args['data_valid']
        parallel_out = dut_args['parallel_out']

        bitwidth = len(parallel_out)

        last_spi_sclk = Signal(False)
        bit_counter = Signal(intbv(0, min=0, max=bitwidth))
        store_word = Signal(intbv(0)[bitwidth:])

        check_data_valid = Signal(False)
        check_word = Signal(intbv(0)[bitwidth:])

        @always(clock.posedge)
        def check_inner():
            last_spi_sclk.next = spi_sclk

            if not spi_ncs:
                if spi_sclk and not last_spi_sclk:
                    last_store_word = int(store_word)

                    # We fill up an integer from lsb first which is simpler,
                    # then we will reverse it to check
                    next_store_word = (
                        last_store_word | (spi_mosi << bit_counter))

                    if bit_counter == bitwidth - 1:
                        # The word is complete
                        store_word.next = 0
                        bit_counter.next = 0
                        check_data_valid.next = True

                        # Reverse the string bitwise to get it in the right
                        # order.
                        store_word_str = '{:0{width}b}'.format(
                            int(next_store_word), width=bitwidth)
                        check_word.next = int(store_word_str[::-1], 2)

                    else:
                        bit_counter.next = bit_counter + 1
                        store_word.next = next_store_word
            else:
                bit_counter.next = 0
                store_word.next = 0

            if check_data_valid:
                assert data_valid
                assert check_word == parallel_out
                check_data_valid.next = False

        return check_inner

    @block
    def stimulate_and_check(
        self, word_length, sclk_half_period, delay_between_words=False,
        word_cancellation_probability=0.0,
        **dut_args):

        clock = dut_args['clock']
        output_data_valid = dut_args['data_valid']

        min_word_delay = 0
        max_word_delay = 100

        # This is approximately the probability that a reset should be sent
        # on any given clock edge.
        reset_master_probability = word_cancellation_probability/(
            2 * sclk_half_period * (word_length + 1))

        new_data = Signal(intbv(0)[word_length:])

        master_data_valid = Signal(False)
        master_data_ready = Signal(False)

        reset_master = Signal(False)

        spi_master_inst = self.spi_master(
            reset_master,
            master_data_ready, master_data_valid, new_data, sclk_half_period,
            **dut_args)

        ready_for_next_word = Signal(False)

        check_inst = self.check(**dut_args)

        delay_count = Signal(intbv(0, min=min_word_delay, max=max_word_delay))
        next_delay = Signal(intbv(0, min=min_word_delay, max=max_word_delay))

        states = enum('INIT', 'RUNNING')
        state = Signal(states.INIT)

        @always(clock.posedge)
        def inner_stimulate():
            if state == states.INIT:
                ready_for_next_word.next = True
                new_data.next = random.randrange(0, 2**word_length)
                next_delay.next = random.randrange(
                    min_word_delay, max_word_delay)

                state.next = states.RUNNING

            elif state == states.RUNNING:
                if ready_for_next_word:
                    if delay_count >= next_delay:
                        master_data_valid.next = True
                        ready_for_next_word.next = False
                        delay_count.next = 0
                    else:
                        delay_count.next = delay_count + 1

                if output_data_valid:
                    ready_for_next_word.next = True

                if master_data_valid and master_data_ready:
                    new_data.next = random.randrange(0, 2**word_length)

                    if not delay_between_words:
                        next_delay.next = 0
                        ready_for_next_word.next = True

                    else:
                        next_delay_val = random.randrange(
                            min_word_delay, max_word_delay)

                        if next_delay_val == 0:
                            ready_for_next_word.next = True

                        next_delay.next = next_delay_val

                    master_data_valid.next = False

            if random.random() < reset_master_probability:
                reset_master.next = True
                state.next = states.INIT
            else:
                reset_master.next = False

        return inner_stimulate, spi_master_inst, check_inst

    def generic_test(
        self, sclk_half_period, delay_between_words,
        word_cancellation_probability=0.0):

        word_length = random.randrange(2, 40)
        dut_args, arg_types = test_args_setup(word_length)

        if self.testing_using_vivado:
            max_cycles = 3000
        else:
            max_cycles = 15000

        custom_sources_args = (
            word_length, sclk_half_period, delay_between_words,
            word_cancellation_probability
        )

        dut_outputs, ref_outputs = self.cosimulate(
            max_cycles, spi_slave, spi_slave, dut_args, arg_types,
            custom_sources=[
                (self.stimulate_and_check, custom_sources_args, dut_args),
            ],
        )

        self.assertEqual(dut_outputs, ref_outputs)

    def test_single_words_written_minimal_spi_clock_period(self):
        '''Writing single words to the `spi_slave` over spi should result in a
        single cycle data_valid flag being raised for each word with each
        single word being presented on the `parallel_out` signal.

        The spi slave should read in as many bits as are determined by the
        length of the parallel out signal, with each bit set on a rising
        edge of the spi clock, `spi_sclk` (distinct from signal `clock`).

        It can be assumed that the spi signals are sensibly within the clock
        domain of `clock`.

        The data should be read in most-significant bit first.

        Once all the data has been read in, `data_valid` should be set high for
        one clock cycle at which point the data can be read from `parallel_out`
        on the next rising edge of `clock`.

        The following timing diagram can be viewed in wavedrom
        (https://wavedrom.com/editor.html):

        ```wavedrom
        { "signal": [
          { "name": "spi_sclk",
          "wave": "xhlhlhlhlh|lhlhlhlhx|." },
          { "name": "spi_ncs",
          "wave": "hl........|........h.." },
          { "name": "spi_mosi",
          "wave": "x.=.=.=.=.|=.=.=.=.x|.",
          "data":["DN", "DN-1", "DN-2", "",  "D3", "D2", "D1", "D0"] },
          {"name": "clock",
          "wave": "p.........|..........."},
          { "name": "data_valid",
          "wave": "l.........|.......hl.."},
          { "name": "parallel_out",
          "wave": "x.........|.......=...",
          "data": 'D[N,N-1,N-2,..,3,2,1,0]' }
        ]}
        ```

        It can be expected that `spi_ncs` is low for the whole transaction.

        The above should work with the minimum SPI clock period of 4 clock
        cycles
        '''
        self.generic_test(sclk_half_period=2, delay_between_words=True)

    def test_single_words_written_longer_spi_clock_period(self):
        '''The block should work as specified in
        `single_words_written_minimal_spi_clock_period`, but with a longer
        SPI clock period.
        '''
        self.generic_test(sclk_half_period=8, delay_between_words=True)

    def test_contiguous_words_written_minimal_spi_clock_period(self):
        '''
        If multiple sequence words are written with `spi_ncs` not going high,
        the data should still be written out as expected on each completed
        word:

        ```wavedrom
        { "signal": [
          { "name": "spi_sclk",
          "wave": "lhlhlhlhlh|lhlhlhx|.." },
          { "name": "spi_ncs",
          "wave": "l.........|......h..." },
          { "name": "spi_mosi",
          "wave": "=.=.=.=.=.|=.=.=.x...",
          "data":["A1", "A0", "BN-1", "BN-2",  "", "B2", "B1", "B0"] },
          {"name": "clock",
          "wave": "p.........|.........."},
          { "name": "data_valid",
          "wave": "l..hl.....|.....hl..."},
          { "name": "parallel_out",
          "wave": "x..=......|.....=....",
          "data": ["A[N,N-1,N-2,..,3,2,1,0]", "B[N,N-1,N-2,..,3,2,1,0]"] }
        ]}
        ```
        The above should work with the minimum SPI clock period of 4 clock
        cycles
        '''
        self.generic_test(sclk_half_period=2, delay_between_words=False)

    def test_contiguous_words_written_longer_spi_clock_period(self):
        '''The block should work as specified in
        `contiguous_words_written_minimal_spi_clock_period`, but with a longer
        SPI clock period.
        '''
        self.generic_test(sclk_half_period=10, delay_between_words=False)

    def test_truncated_serial_data_produces_no_output(self):
        '''If spi_ncs goes high before all the data is clocked in, then
        `data_valid` should not be set for that word.
        '''
        # A word cancellation probability of 0.5 should result in a
        # cancellation sufficiently often to make sure the test is reliable
        self.generic_test(
            sclk_half_period=2, delay_between_words=True,
            word_cancellation_probability=0.5
        )


class TestDoubleBufferArrayVivadoVhdl(
    KeaVivadoVHDLTestCase, TestSpiSlave):
    pass

class TestDoubleBufferArrayVivadoVerilog(
    KeaVivadoVerilogTestCase, TestSpiSlave):
    pass
