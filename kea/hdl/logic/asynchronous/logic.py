from myhdl import block, always_comb

@block
def and_gate(signal_in_0, signal_in_1, signal_out):
    ''' Two input AND gate.
    '''

    @always_comb
    def logic():

        signal_out.next = signal_in_0 and signal_in_1

    return logic

@block
def or_gate(signal_in_0, signal_in_1, signal_out):
    ''' Two input OR gate.
    '''

    @always_comb
    def logic():

        signal_out.next = signal_in_0 or signal_in_1

    return logic

@block
def not_gate(signal_in, signal_out):
    ''' Basic NOT gate.
    '''

    @always_comb
    def logic():

        signal_out.next = not signal_in

    return logic

@block
def nand_gate(signal_in_0, signal_in_1, signal_out):
    ''' Two input NAND gate.
    '''

    @always_comb
    def logic():

        signal_out.next = not (signal_in_0 and signal_in_1)

    return logic

@block
def nor_gate(signal_in_0, signal_in_1, signal_out):
    ''' Two input NOR gate.
    '''

    @always_comb
    def logic():

        signal_out.next = not (signal_in_0 or signal_in_1)

    return logic

@block
def exor_gate(signal_in_0, signal_in_1, signal_out):
    ''' Two input EXOR gate.
    '''

    @always_comb
    def logic():

        signal_out.next = (
            (signal_in_0 and not signal_in_1) or
            (not signal_in_0 and signal_in_1))

    return logic

@block
def exnor_gate(signal_in_0, signal_in_1, signal_out):
    ''' Two input EXNOR gate.
    '''

    @always_comb
    def logic():

        signal_out.next = (
            (signal_in_0 and signal_in_1) or
            (not signal_in_0 and not signal_in_1))

    return logic
