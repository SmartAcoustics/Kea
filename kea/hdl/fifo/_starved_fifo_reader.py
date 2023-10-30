from myhdl import *

@block
def starved_fifo_reader(
    clock, data_in, data_in_valid, fifo_empty, fifo_read_enable, data_out,
    n_cycles_per_word, buffer_n_words):
    ''' This block is intended to serve as a reader of a FIFO which has a
    slower write clock than read clock.

    This block will wait until fifo_empty goes low and then wait for
    buffer_n_words*n_cycles_per_word cycles before starting to read words from
    the FIFO. It will read one word every n_cycles_per_word.

    This block will continue reading data from the FIFO until fifo_empty goes
    high.

    When fifo_empty is high this block will stop reading the FIFO and hold
    read_enable low.

    This strategy means we build up a buffer of data in the FIFO. This means
    the data rate out of the FIFO can be maintained even if the phase
    alignment between the write and read clock isn't perfect.

    This block will register the valid data from the FIFO and hold it until
    the next valid data word arrives.
    '''
    # Note: The Vivado FIFO generator does not require a reset and this block
    # does not currently provide one. If a reset is required in future the
    # FIFO generator documentation recommends a asynchronous reset is set high
    # for 3 clock cycles and there is a minimum 6 cycles between resets. These
    # are both cycles of the slowest clock speed (read clock or write clock).
    # read enable and write enable should be low during a reset. See PG057 for
    # more information.

    if len(data_in) != len(data_out):
        raise ValueError(
            'starved_fifo_reader: data_in and data_out should be the same '
            'width.')

    if n_cycles_per_word < 1:
        raise ValueError(
            'starved_fifo_reader: n_cycles_per_word should be greater than '
            '0.')

    if buffer_n_words < 0:
        raise ValueError(
            'starved_fifo_reader: buffer_n_words should be greater than or '
            'equal to 0.')

    if buffer_n_words > 8:
        raise ValueError(
            'starved_fifo_reader: buffer_n_words is intended as a small '
            'buffer to overcome slight phase alignment discrepancies between '
            'the write and read clocks. If the buffer_n_words is too large '
            'for the FIFO then data will be lost. We limit buffer_n_words to '
            '8 to protect against that data loss.')

    return_objects = []

    buffer_n_cycles = buffer_n_words * n_cycles_per_word

    count = Signal(intbv(0, 0, n_cycles_per_word+1))
    buffer_count = Signal(intbv(0, 0, buffer_n_cycles+1))

    t_state = enum('AWAITING_BUFFER', 'READ')

    # Define the state that the reader should reside in whilst the FIFO is
    # empty
    if buffer_n_cycles == 0:
        # No buffer required so reside in READ and wait for FIFO empty to go
        # low
        fifo_empty_state = t_state.READ

    else:
        # Buffer is required so reside in AWAITING_BUFFER and wait for FIFO
        # empty to go low
        fifo_empty_state = t_state.AWAITING_BUFFER

    state = Signal(fifo_empty_state)

    @always(clock.posedge)
    def reader():

        if data_in_valid:
            # Forward the data_in to data_out
            data_out.next = data_in

        if state == t_state.AWAITING_BUFFER:
            if buffer_count >= buffer_n_cycles-2:
                count.next = 0
                state.next = t_state.READ

            else:
                buffer_count.next = buffer_count + 1

        elif state == t_state.READ:
            if count >= n_cycles_per_word-1:
                # Count the number of cycles for each word read
                count.next = 0
            else:
                count.next = count + 1

            if count == 0:
                # EVery n_cycles_per_word read a word out of the FIFO
                fifo_read_enable.next = True
            else:
                fifo_read_enable.next = False

        if fifo_empty:
            # FIFO is empty so stop reading the FIFO
            fifo_read_enable.next = False

            buffer_count.next = 0
            count.next = 0

            state.next = fifo_empty_state

    return_objects.append(reader)

    return return_objects
