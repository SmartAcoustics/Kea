from myhdl import block, always

@block
def synchronous_and_gate(clock, signal_in_0, signal_in_1, signal_out):
    ''' Two input AND gate.
    '''

    @always(clock.posedge)
    def logic():

        signal_out.next = signal_in_0 and signal_in_1

    return logic

@block
def synchronous_or_gate(clock, signal_in_0, signal_in_1, signal_out):
    ''' Two input OR gate.
    '''

    @always(clock.posedge)
    def logic():

        signal_out.next = signal_in_0 or signal_in_1

    return logic

@block
def synchronous_not_gate(clock, signal_in, signal_out):
    ''' Basic NOT gate.
    '''

    @always(clock.posedge)
    def logic():

        signal_out.next = not signal_in

    return logic

@block
def synchronous_nand_gate(clock, signal_in_0, signal_in_1, signal_out):
    ''' Two input NAND gate.
    '''

    @always(clock.posedge)
    def logic():

        signal_out.next = not (signal_in_0 and signal_in_1)

    return logic

@block
def synchronous_nor_gate(clock, signal_in_0, signal_in_1, signal_out):
    ''' Two input NOR gate.
    '''

    @always(clock.posedge)
    def logic():

        signal_out.next = not (signal_in_0 or signal_in_1)

    return logic

@block
def synchronous_exor_gate(clock, signal_in_0, signal_in_1, signal_out):
    ''' Two input EXOR gate.
    '''

    @always(clock.posedge)
    def logic():

        signal_out.next = (
            (signal_in_0 and not signal_in_1) or
            (not signal_in_0 and signal_in_1))

    return logic

@block
def synchronous_exnor_gate(clock, signal_in_0, signal_in_1, signal_out):
    ''' Two input EXNOR gate.
    '''

    @always(clock.posedge)
    def logic():

        signal_out.next = (
            (signal_in_0 and signal_in_1) or
            (not signal_in_0 and not signal_in_1))

    return logic
