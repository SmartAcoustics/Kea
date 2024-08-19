from math import ceil
from myhdl import block, Signal, intbv, enum, always

from kea.hdl.logic.asynchronous import and_gate
from kea.hdl.signal_handling import constant_assigner, signal_assigner
from kea.xilinx.primitives.seven_series import xil_oddr

@block
def clock_forwarding_oddr(
    clock, reset, initialised, enable_clock_forwarding, forwarded_clock,
    clock_frequency, invert_clock=False):
    ''' This block instantiates an ODDR primitive and sets up the connections
    for clock forwarding.

    `enable_clock_forwarding` should not be set high until the `initialised`
    flag is set high.

    `clock_frequency` should be the frequency of `clock`.
    '''

    return_objects = []

    if invert_clock:
        # Create the required signals for the ODDR block
        oddr_data_0 = Signal(False)
        oddr_data_1 = Signal(True)

        return_objects.append(constant_assigner(False, oddr_data_0))
        return_objects.append(constant_assigner(True, oddr_data_1))

    else:
        # Create the required signals for the ODDR block
        oddr_data_0 = Signal(True)
        oddr_data_1 = Signal(False)

        return_objects.append(constant_assigner(True, oddr_data_0))
        return_objects.append(constant_assigner(False, oddr_data_1))

    # Keep a copy of initialised for internal use
    internal_initialised = Signal(False)
    return_objects.append(signal_assigner(internal_initialised, initialised))

    # Create an ODDR block to drive the forwarded_clock. This is the
    # recommended method for forwarding a clock. The ODDR block alternates
    # between oddr_data_0 and oddr_data_1 on rising and falling edges of
    # clock.
    return_objects.append(
        xil_oddr(
            clock, enable_clock_forwarding, oddr_data_0, oddr_data_1,
            forwarded_clock, reset))

    # From observation of the converted simulation, the ODDR primitive appears
    # to require an initialisation period of approximately 120ns. We give it
    # 240ns just to make sure.
    oddr_init_period = 240e-9
    oddr_init_period_n_cycles = ceil(clock_frequency*oddr_init_period)
    oddr_init_count = Signal(intbv(0, 0, oddr_init_period_n_cycles+1))

    @always(clock.posedge)
    def init_control():

        if not internal_initialised:
            if oddr_init_count >= oddr_init_period_n_cycles:
                # Initialisaiton period has passed
                internal_initialised.next = True

            else:
                # Count the initialisation period
                oddr_init_count.next = oddr_init_count + 1

    return_objects.append(init_control)

    return return_objects
