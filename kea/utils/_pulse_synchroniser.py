from myhdl import *

@block
def pulse_synchroniser(trigger_clock, output_clock, trigger, output, busy):
    ''' Implements a pulse synchroniser to allow pulses to cross clock domain
    boundaries.

    On receipt of a single cycle pulse on ``trigger`` (synchronised to
    ``trigger_clock``), this block will output a single cycle pulse on
    ``output`` (synchronised to ``output_clock``).

    Any pulses on trigger which are received when busy is high will be
    ignored.
    '''
    # This design uses multiple registers on the output side to prevent
    # metastability. It uses an extra register to detect a rising edge. The
    # output side then acknowledges receipt of the pulse.

    trigger_pulse_detected = Signal(False)

    internal_busy = Signal(False)

    # Define the number of and create the registers in the acknowledge
    # pipeline
    acknowledge_pipeline_length = 2
    acknowledge_pipeline = [
        Signal(False) for n in range(acknowledge_pipeline_length)]

    # Define the number of and create the registers in the output pipeline
    output_pipeline_length = 3
    output_pipeline = [Signal(False) for n in range(output_pipeline_length)]

    @always(trigger_clock.posedge)
    def trigger_domain_handler():

        if (acknowledge_pipeline[acknowledge_pipeline_length-1] and
            trigger_pulse_detected):
            # If the output side has acknowledged receipt of the trigger pulse
            # then set trigger_pulse_detected low.
            trigger_pulse_detected.next = False

        elif trigger and not internal_busy:
            # If a trigger is received then set trigger_pulse_detected high
            trigger_pulse_detected.next = True

        else:
            trigger_pulse_detected.next = trigger_pulse_detected

        if not internal_busy:
            # If idle, set busy in response to the trigger
            internal_busy.next = trigger

        else:
            # If busy, reset busy when the acknowlede pipeline goes low
            internal_busy.next = (
                trigger_pulse_detected or
                acknowledge_pipeline[acknowledge_pipeline_length-1])

        for n in range(acknowledge_pipeline_length-1):
            # Shift the acknowledge pipeline up one position. This buffers the
            # signal multiple times to protect against meta stability.
            acknowledge_pipeline[acknowledge_pipeline_length-n-1].next = (
                acknowledge_pipeline[acknowledge_pipeline_length-n-2])

        # Make the clock domain crossing assignment
        acknowledge_pipeline[0].next = (
            output_pipeline[output_pipeline_length-1])

    @always(output_clock.posedge)
    def output_domain_handler():

        for n in range(output_pipeline_length-1):
            # Shift the output pipeline up one position. This buffers the
            # signal multiple times to protect against meta stability.
            output_pipeline[output_pipeline_length-n-1].next = (
                output_pipeline[output_pipeline_length-n-2])

        # Make the clock domain crossing assignment
        output_pipeline[0].next = trigger_pulse_detected

        # Rising edge detection
        output.next = (
            output_pipeline[output_pipeline_length-2] and
            not output_pipeline[output_pipeline_length-1])

    @always_comb
    def busy_driver():

        busy.next = internal_busy

    return trigger_domain_handler, output_domain_handler, busy_driver
