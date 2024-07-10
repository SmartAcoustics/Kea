from myhdl import Signal, intbv

def integer_constant_signal(constant_value):
    ''' Pseudo constant. The conversion to VHDL breaks in certain situations
    (eg comparisons) if the constant is more than 32 bits (signed). This is a
    work around.

    The returned signal can be used in place of a constant.

    Note: The conversion appears to work as expected when we assign a constant
    which is greater than 32 bits so this function is not necessary for
    assignments.
    '''

    constant_min = constant_value
    constant_max = constant_value + 1

    constant_signal = (
        Signal(intbv(constant_value, min=constant_min, max=constant_max)))

    # Use 'reg' here so the conversion to verilog works correctly.
    constant_signal.driven = 'reg'

    return constant_signal
