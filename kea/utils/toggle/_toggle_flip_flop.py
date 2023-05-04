from myhdl import block, always, Signal

@block
def toggle_flip_flop(clock, toggle, output):
    ''' A simple clocked toggle flip flop.
    '''

    if len(toggle) != 1:
        raise TypeError('toggle_flip_flop: toggle should be 1 bit wide.')

    if len(output) != 1:
        raise TypeError('toggle_flip_flop: output should be 1 bit wide.')

    return_objects = []

    next_output_init_state = not output.val
    next_output = Signal(next_output_init_state)

    @always(clock.posedge)
    def control():

        if toggle:
            # Toggle the output
            output.next = next_output
            next_output.next = not next_output

    return_objects.append(control)

    return return_objects
