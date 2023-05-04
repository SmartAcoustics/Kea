from math import ceil

from myhdl import block, enum, Signal, always

from kea.axi import AxiStreamInterface

# The flow control section of the PG074 Aurora 64B/66B LogiCORE IP Product
# Guide is not very clear when it describes the flow control words. From
# inspection of the signals in an ILA the following seem to work.
AURORA_NFC_OFF_WORD = 1 << 8
AURORA_NFC_ON_WORD = 0

@block
def aurora_64b_66b_flow_control(
    clock, reset, fifo_count, axis_aurora_nfc, fifo_depth):
    ''' This block can perform flow control for the Aurora 64B/66B block.
    The following requirements must be met for this block to function
    correctly:

        - This block should control a single Aurora block.
        - That Aurora block should contain a single lane.
        - The Aurora block should output data to a FIFO.
        - The FIFO should provide the word count to this block.
        - The FIFO should be 64 bits wide (the same as the Aurora 64B/66B data
          output).
        - The optical fibre should not be longer than 100m.

    reset should be the same signal driving the aurora reset_pb signal.

    It is recommended to also use the reset signal to clear the FIFO.
    '''

    if not isinstance(axis_aurora_nfc, AxiStreamInterface):
        raise TypeError(
            'aurora_64b_66b_flow_control: axis_aurora_nfc should be an '
            'instance of AxiStreamInterface.')

    fifo_count_upper_bound = 2**len(fifo_count)
    if fifo_count_upper_bound <= fifo_depth:
        raise ValueError(
            'aurora_64b_66b_flow_control: The fifo_count should be able to '
            'carry a value equal to the fifo_depth.')

    speed_of_light = 3e8
    speed_of_light_in_fibre = 2/3 * speed_of_light

    aurora_data_bit_width = 64
    aurora_latency = 55
    # A single lane of the aurora bus has a max data rate of 12 Gbps.
    aurora_lane_max_data_rate = 12e9

    # Set a maximum fibre length of 100m
    max_fibre_length = 100

    # Calculate the time for a bit to traverse the fibre
    bit_fibre_flight_time = max_fibre_length/speed_of_light_in_fibre

    # Calculate the maximum number of bits and words in the fibre
    max_n_bits_in_flight_in_fibre = (
        aurora_lane_max_data_rate * bit_fibre_flight_time)
    max_n_words_in_flight_in_fibre = (
        ceil(max_n_bits_in_flight_in_fibre/aurora_data_bit_width))

    # Calculate the maximum number of words we need to be able to handle
    # before flow control takes effect. We assume there are
    # (max_n_words_in_flight_in_fibre + aurora_latency) words within the
    # aurora system. By the time the flow control signal has arrived at the tx
    # end another (max_n_words_in_flightin_fibre + aurora_latency) words will
    # have entered the aurora system.
    max_n_words_during_flow_control_propagation = (
        2*(max_n_words_in_flight_in_fibre + aurora_latency))

    # Calculate the flow start and flow stop thresholds
    flow_on_threshold = max_n_words_during_flow_control_propagation
    flow_off_threshold = (
        fifo_depth - max_n_words_during_flow_control_propagation)

    # The FIFO needs to be able to accomodate the flow on threshold and the
    # flow off threshold.
    min_fifo_depth = (
        flow_on_threshold + max_n_words_during_flow_control_propagation)

    if flow_on_threshold > flow_off_threshold:
        raise ValueError(
            'aurora_64b_66b_flow_control: The fifo_depth should be at least '
            + str(min_fifo_depth) + '.')

    return_objects = []

    # Extract the signals from the axis_aurora_nfc interface
    tvalid = axis_aurora_nfc.TVALID
    tready = axis_aurora_nfc.TREADY
    tdata = axis_aurora_nfc.TDATA

    t_state = enum(
        'INIT', 'AWAIT_FLOW_OFF_ACK', 'FLOW_OFF',
        'TURN_FLOW_ON', 'AWAIT_FLOW_ON_ACK', 'FLOW_ON')
    state = Signal(t_state.INIT)

    @always(clock.posedge)
    def control():

        if state == t_state.INIT:
            # If the fifo_count falls between the thresholds then we will wait
            # until it either drains or fills to a threshold before acting to
            # turn the flow on or off.
            if fifo_count >= flow_off_threshold:
                # Send the word to turn the flow off
                tvalid.next = True
                tdata.next = AURORA_NFC_OFF_WORD
                state.next = t_state.AWAIT_FLOW_OFF_ACK

            elif fifo_count < flow_on_threshold:
                # Send the word to turn the flow on
                tvalid.next = True
                tdata.next = AURORA_NFC_ON_WORD
                state.next = t_state.AWAIT_FLOW_ON_ACK

        elif state == t_state.AWAIT_FLOW_OFF_ACK:
            if tready:
                # The Aurora has received the off word
                tvalid.next = False
                state.next = t_state.FLOW_OFF

        elif state == t_state.FLOW_OFF:
            if fifo_count < flow_on_threshold:
                # FIFO has drained to a low enough level that we can turn the
                # aurora bus on.
                tvalid.next = True
                tdata.next = AURORA_NFC_ON_WORD
                state.next = t_state.AWAIT_FLOW_ON_ACK

        elif state == t_state.AWAIT_FLOW_ON_ACK:
            if tready:
                # The Aurora has received the on word
                tvalid.next = False
                state.next = t_state.FLOW_ON

        elif state == t_state.FLOW_ON:
            if fifo_count >= flow_off_threshold:
                # FIFO has filled to such a high level that we need to turn
                # the aurora bus off to prevent potential data loss.
                tvalid.next = True
                tdata.next = AURORA_NFC_OFF_WORD
                state.next = t_state.AWAIT_FLOW_OFF_ACK

        if reset:
            tvalid.next = False
            state.next = t_state.INIT

    return_objects.append(control)

    return return_objects
