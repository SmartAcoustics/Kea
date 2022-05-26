from myhdl import block, always, always_comb, Signal

@block
def sr_flip_flop(clock, set_output, reset_output, output):
    ''' A simple clocked SR flip flop.
    '''

    return_objects = []

    @always(clock.posedge)
    def control():

        if reset_output:
            output.next = False

        elif set_output:
            output.next = True

    return_objects.append(control)

    return return_objects
