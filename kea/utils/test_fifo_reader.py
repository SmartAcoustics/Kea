from ._fifo_reader import fifo_reader

from jackdaw.test_utils.base_test import (
    JackdawTestCase, JackdawVivadoVHDLTestCase, JackdawVivadoVerilogTestCase)

import random
import copy

from myhdl import *

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    data_width = 112

    clock = Signal(False)
    data_in = Signal(intbv(0)[data_width:])
    data_in_valid = Signal(False)
    fifo_empty = Signal(True)
    fifo_read_enable = Signal(False)
    data_out = Signal(intbv(0)[data_width:])
    n_cycles_per_word = 2
    buffer_n_words = 4

    args = {
        'clock': clock,
        'data_in': data_in,
        'data_in_valid': data_in_valid,
        'fifo_empty': fifo_empty,
        'fifo_read_enable': fifo_read_enable,
        'data_out': data_out,
        'n_cycles_per_word': n_cycles_per_word,
        'buffer_n_words': buffer_n_words,
    }

    arg_types = {
        'clock': 'clock',
        'data_in': 'custom',
        'data_in_valid': 'custom',
        'fifo_empty': 'custom',
        'fifo_read_enable': 'output',
        'data_out': 'output',
        'n_cycles_per_word': 'non-signal',
        'buffer_n_words': 'non-signal',
    }

    return args, arg_types

class TestFifoReaderInterface(JackdawTestCase):

    def setUp(self):

        self.args, self.arg_types = test_args_setup()

    def test_mismatched_data_widths(self):
        ''' The `fifo_reader` should raise an error if the `data_in` and
        `data_out` signals are not the same width.
        '''

        # Generate to different widths
        m, n = random.sample([n for n in range(2, 100)], 2)

        self.args['data_in'] = Signal(intbv(0)[m:])
        self.args['data_out'] = Signal(intbv(0)[n:])

        self.assertRaisesRegex(
            ValueError,
            ('fifo_reader: data_in and data_out should be the same width.'),
            fifo_reader,
            **self.args,
        )

    def test_zero_n_cycles_per_word(self):
        ''' The `fifo_reader` should raise an error if `n_cycles_per_word` is
        zero.
        '''

        self.args['n_cycles_per_word'] = 0

        self.assertRaisesRegex(
            ValueError,
            ('fifo_reader: n_cycles_per_word should be greater than 0.'),
            fifo_reader,
            **self.args,
        )

    def test_negative_n_cycles_per_word(self):
        ''' The `fifo_reader` should raise an error if `n_cycles_per_word` is
        negative.
        '''

        self.args['n_cycles_per_word'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('fifo_reader: n_cycles_per_word should be greater than 0.'),
            fifo_reader,
            **self.args,
        )

    def test_negative_buffer_n_words(self):
        ''' The `fifo_reader` should raise an error if `buffer_n_words` is
        negative.
        '''

        self.args['buffer_n_words'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('fifo_reader: buffer_n_words should be greater than or equal '
             'to 0.'),
            fifo_reader,
            **self.args,
        )

    def test_large_buffer_n_words(self):
        ''' The `fifo_reader` should raise an error if `buffer_n_words` is
        greater than 8.
        '''

        self.args['buffer_n_words'] = random.randrange(9, 100)

        self.assertRaisesRegex(
            ValueError,
            ('fifo_reader: buffer_n_words is intended as a small buffer to '
            'overcome slight phase alignment discrepancies between the write '
            'and read clocks. If the buffer_n_words is too large for the '
            'FIFO then data will be lost. We limit buffer_n_words to 8 to '
            'protect against that data loss.'),
            fifo_reader,
            **self.args,
        )

class TestFifoReader(JackdawTestCase):

    def setUp(self):

        self.test_count = 0
        self.tests_run = False

        self.args, self.arg_types = test_args_setup()

    @block
    def count_tests(self, clock, n_tests):

        @always(clock.posedge)
        def counter():

            if self.test_count >= n_tests:
                # Check that all the tests are run
                self.tests_run = True

                raise StopSimulation

        return counter

    @block
    def fifo_bfm(
        self, clock, data, data_valid, fifo_empty, read_enable,
        probability_fifo_drains):
        ''' This block models the behaviour of the FIFO.
        '''

        return_objects = []

        t_state = enum('EMPTY', 'DATA_AVAILABLE', 'DRAINING')
        state = Signal(t_state.EMPTY)

        data_max_val = 2**len(data)

        @always(clock.posedge)
        def stim():

            # Set data_valid in response to read_enable. Randomly drive the
            # data signal
            data_valid.next = read_enable
            data.next = random.randrange(data_max_val)

            if state == t_state.EMPTY:
                if random.random() < 0.01:
                    # Randomly set FIFO empty low
                    fifo_empty.next = False
                    state.next = t_state.DATA_AVAILABLE

            elif state == t_state.DATA_AVAILABLE:
                if random.random() < probability_fifo_drains:
                    state.next = t_state.DRAINING

            elif state == t_state.DRAINING:
                if random.random() < 0.05:
                    # Randomly set FIFO empty
                    fifo_empty.next = True
                    state.next = t_state.EMPTY

        return_objects.append(stim)

        return return_objects

    @block
    def fifo_reader_check(
        self, clock, data_in, data_in_valid, fifo_empty,
        fifo_read_enable, data_out, n_cycles_per_word, buffer_n_words,
        probability_fifo_drains=0):

        return_objects = []

        return_objects.append(
            self.fifo_bfm(
                clock, data_in, data_in_valid, fifo_empty,
                fifo_read_enable, probability_fifo_drains))

        expected_data_out = Signal(intbv(0)[len(data_in):])
        expected_fifo_read_enable = Signal(False)

        count = Signal(intbv(0, 0, n_cycles_per_word+1))

        buffer_n_cycles = buffer_n_words * n_cycles_per_word
        buffer_count = Signal(intbv(0, 0, buffer_n_cycles+1))

        @always(clock.posedge)
        def check():

            assert(data_out == expected_data_out)
            assert(fifo_read_enable == expected_fifo_read_enable)

            if fifo_empty:
                # The fifo reader should turn off if the fifo is empty
                count.next = 0
                buffer_count.next = 0
                expected_fifo_read_enable.next = False

            elif buffer_count < buffer_n_cycles - 1:
                buffer_count.next = buffer_count + 1

            else:

                if count < n_cycles_per_word - 1:
                    # Count the number of cycles for each word read from the
                    # FIFO
                    count.next = count + 1
                else:
                    count.next = 0

                if count == 0:
                    # fifo reader should read every n_cycles_per_word
                    expected_fifo_read_enable.next = True
                else:
                    expected_fifo_read_enable.next = False

            if data_in_valid:
                # Data should be read in on data_in_valid. data_in_valid will
                # be set in response to fifo_read_enable which we also check.
                expected_data_out.next = data_in

                # Count the words
                self.test_count += 1

        return_objects.append(check)

        return return_objects

    def test_fifo_reader(self):
        ''' The `fifo_reader` should remain idle and wait until the
        `fifo_empty` signal goes low. It should then wait `buffer_n_cycles` to
        allow some data to build up in the FIFO. Once `buffer_n_cycles` has
        passed the `fifo_reader` should set `fifo_read_enable` high for one
        clock cycle every `n_cycles_per_word`. This reads one word out of the
        FIFO.

        ``buffer_n_cycles = buffer_n_words * n_cycles_per_word``

        The `fifo_reader` should continue reading words out of the FIFO in
        this manner until `fifo_empty` goes high. It should then stop
        reading (hold `fifo_read_enable` low) until `fifo_empty` goes low
        again and another buffer period has passed.

        This strategy means we build up a buffer of data in the FIFO. This
        means the data rate out of the FIFO can be maintained even if the
        phase alignment between the write and read clock isn't perfect.

        Note: it is still necessary for the data rate into the FIFO to equal
        the data rate out of the FIFO.

        When `data_in_valid` is set high the `fifo_reader` should forward the
        value on `data_in` to `data_out`.
        '''

        if not self.testing_using_vivado:
            cycles = 15000
            n_tests = 3000

        else:
            cycles = 3000
            n_tests = 600

        @block
        def test(
            clock, data_in, data_in_valid, fifo_empty, fifo_read_enable,
            data_out, n_cycles_per_word, buffer_n_words):

            return_objects = []

            return_objects.append(
                self.fifo_reader_check(
                    clock, data_in, data_in_valid, fifo_empty,
                    fifo_read_enable, data_out, n_cycles_per_word,
                    buffer_n_words, probability_fifo_drains=0))

            return_objects.append(self.count_tests(clock, n_tests))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, fifo_reader, fifo_reader, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertTrue(self.tests_run)
        self.assertTrue(dut_outputs == ref_outputs)

    def test_random_data_width(self):
        ''' The `fifo_reader` should be able to handle any arbitrary data
        width. Ie `data_in` and `data_out` can be any width as long as they
        the same width.
        '''

        if not self.testing_using_vivado:
            cycles = 15000
            n_tests = 3000

        else:
            cycles = 3000
            n_tests = 600

        data_width = random.randrange(1, 257)
        self.args['data_in'] = Signal(intbv(0)[data_width:])
        self.args['data_out'] = Signal(intbv(0)[data_width:])

        @block
        def test(
            clock, data_in, data_in_valid, fifo_empty, fifo_read_enable,
            data_out, n_cycles_per_word, buffer_n_words):

            return_objects = []

            return_objects.append(
                self.fifo_reader_check(
                    clock, data_in, data_in_valid, fifo_empty,
                    fifo_read_enable, data_out, n_cycles_per_word,
                    buffer_n_words, probability_fifo_drains=0))

            return_objects.append(self.count_tests(clock, n_tests))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, fifo_reader, fifo_reader, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertTrue(self.tests_run)
        self.assertTrue(dut_outputs == ref_outputs)

    def test_single_cycle_per_word(self):
        ''' The `fifo_reader` should be able to handle an `n_cycles_per_word`
        of 1.
        '''

        if not self.testing_using_vivado:
            cycles = 15000
            n_tests = 3000

        else:
            cycles = 3000
            n_tests = 600

        self.args['n_cycles_per_word'] = 1

        @block
        def test(
            clock, data_in, data_in_valid, fifo_empty, fifo_read_enable,
            data_out, n_cycles_per_word, buffer_n_words):

            return_objects = []

            return_objects.append(
                self.fifo_reader_check(
                    clock, data_in, data_in_valid, fifo_empty,
                    fifo_read_enable, data_out, n_cycles_per_word,
                    buffer_n_words, probability_fifo_drains=0))

            return_objects.append(self.count_tests(clock, n_tests))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, fifo_reader, fifo_reader, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertTrue(self.tests_run)
        self.assertTrue(dut_outputs == ref_outputs)

    def test_random_n_cycles_per_word(self):
        ''' The `fifo_reader` should be able to handle any `n_cycles_per_word`
        which is greater than 0.
        '''

        if not self.testing_using_vivado:
            cycles = 15000
            n_tests = 600

        else:
            cycles = 3000
            n_tests = 125

        self.args['n_cycles_per_word'] = random.randrange(3, 10)

        @block
        def test(
            clock, data_in, data_in_valid, fifo_empty, fifo_read_enable,
            data_out, n_cycles_per_word, buffer_n_words):

            return_objects = []

            return_objects.append(
                self.fifo_reader_check(
                    clock, data_in, data_in_valid, fifo_empty,
                    fifo_read_enable, data_out, n_cycles_per_word,
                    buffer_n_words, probability_fifo_drains=0))

            return_objects.append(self.count_tests(clock, n_tests))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, fifo_reader, fifo_reader, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertTrue(self.tests_run)
        self.assertTrue(dut_outputs == ref_outputs)

    def test_zero_buffer_n_words(self):
        ''' The `fifo_reader` should be able to handle a `buffer_n_words` of
        0.
        '''

        if not self.testing_using_vivado:
            cycles = 3000
            n_tests = 300

        else:
            cycles = 1000
            n_tests = 60

        self.args['buffer_n_words'] = 0

        @block
        def test(
            clock, data_in, data_in_valid, fifo_empty, fifo_read_enable,
            data_out, n_cycles_per_word, buffer_n_words):

            return_objects = []

            return_objects.append(
                self.fifo_reader_check(
                    clock, data_in, data_in_valid, fifo_empty,
                    fifo_read_enable, data_out, n_cycles_per_word,
                    buffer_n_words, probability_fifo_drains=0))

            return_objects.append(self.count_tests(clock, n_tests))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, fifo_reader, fifo_reader, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertTrue(self.tests_run)
        self.assertTrue(dut_outputs == ref_outputs)

    def test_random_buffer_n_words(self):
        ''' The `fifo_reader` should be able to handle any `buffer_n_words`
        which is in the range:

            0 <= buffer_n_words <= 8
        '''

        if not self.testing_using_vivado:
            cycles = 6000
            n_tests = 300

        else:
            cycles = 2000
            n_tests = 60

        self.args['buffer_n_words'] = random.randrange(1, 9)

        @block
        def test(
            clock, data_in, data_in_valid, fifo_empty, fifo_read_enable,
            data_out, n_cycles_per_word, buffer_n_words):

            return_objects = []

            return_objects.append(
                self.fifo_reader_check(
                    clock, data_in, data_in_valid, fifo_empty,
                    fifo_read_enable, data_out, n_cycles_per_word,
                    buffer_n_words, probability_fifo_drains=0))

            return_objects.append(self.count_tests(clock, n_tests))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, fifo_reader, fifo_reader, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertTrue(self.tests_run)
        self.assertTrue(dut_outputs == ref_outputs)

    def test_fifo_empty(self):
        ''' Once the `fifo_empty` signal has gone high and `buffer_n_cycles`
        has passed the `fifo_reader` should keep reading the FIFO until the
        `fifo_empty` signal goes high.
        '''

        if not self.testing_using_vivado:
            cycles = 30000
            n_tests = 600

        else:
            cycles = 6000
            n_tests = 125

        @block
        def test(
            clock, data_in, data_in_valid, fifo_empty, fifo_read_enable,
            data_out, n_cycles_per_word, buffer_n_words):

            return_objects = []

            return_objects.append(
                self.fifo_reader_check(
                    clock, data_in, data_in_valid, fifo_empty,
                    fifo_read_enable, data_out, n_cycles_per_word,
                    buffer_n_words, probability_fifo_drains=0.01))

            return_objects.append(self.count_tests(clock, n_tests))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, fifo_reader, fifo_reader, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertTrue(self.tests_run)
        self.assertTrue(dut_outputs == ref_outputs)

    def test_fifo_empty_zero_buffer_n_words(self):
        ''' If the `buffer_n_words` is 0, the `fifo_reader` should start
        reading from the FIFO as soon as `fifo_empty` goes low.
        '''

        if not self.testing_using_vivado:
            cycles = 30000
            n_tests = 600

        else:
            cycles = 6000
            n_tests = 125

        self.args['buffer_n_words'] = 0

        @block
        def test(
            clock, data_in, data_in_valid, fifo_empty, fifo_read_enable,
            data_out, n_cycles_per_word, buffer_n_words):

            return_objects = []

            return_objects.append(
                self.fifo_reader_check(
                    clock, data_in, data_in_valid, fifo_empty,
                    fifo_read_enable, data_out, n_cycles_per_word,
                    buffer_n_words, probability_fifo_drains=0.01))

            return_objects.append(self.count_tests(clock, n_tests))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, fifo_reader, fifo_reader, self.args,
            self.arg_types, custom_sources=[(test, (), self.args)])

        self.assertTrue(self.tests_run)
        self.assertTrue(dut_outputs == ref_outputs)

class TestFifoReaderVivadoVhdl(
    JackdawVivadoVHDLTestCase, TestFifoReader):
    pass

class TestFifoReaderVivadoVerilog(
    JackdawVivadoVerilogTestCase, TestFifoReader):
    pass
