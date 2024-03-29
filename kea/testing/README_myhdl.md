# MyHDL Verification toolkit #

`kea.testing.myhdl` is a collection of utilities for verification of HDL
designs created using MyHDL.

Here is an example usage:

```python
from myhdl import Signal, always, block, intbv
from kea.testing.myhdl import myhdl_cosimulation
import random

@block
def dut(clock, data_in, data_out, data_control):

    # We have a data_hold so we don't have outputs also driving internally.
    data_hold = Signal(intbv(0)[len(data_out):])

    @always(clock.posedge)
    def simple_driver():

        if data_control:
            data_out.next = data_in
            data_hold.next = data_in
        else:
            data_out.next = data_hold
            data_hold.next = data_hold

    return simple_driver


@block
def test_driver(clock, data_control, dut_data_in, dut_data_out):
    '''This block drives data_control. It also takes `dut_data_in` and
    `dut_data_out` as part of it's signature which are both inputs. This allows
    the block to check that signals are correct. The checker and the driver
    can be in separate blocks with no problem. We just put them together here
    for brevity.
    '''

    expected_data_out = Signal(intbv(0)[len(dut_data_out):])

    @always(clock.posedge)
    def drive_data_control():
        # We just randomly flick the control line
        data_control.next = random.choice([True, False])

    @always(clock.posedge)
    def set_expected_data_out():
        # This drives out checking signal
        if data_control:
            expected_data_out.next = dut_data_in
        else:
            expected_data_out.next = dut_data_out

    @always(clock.posedge)
    def check_data_out():
        # In a testing framework, say unittest, you can use the unittest
        # asserts here. Typically this driver would live inside the test itself

        # We print something out, otherwise you don't see very much happening
        print(data_control, dut_data_in, dut_data_out, expected_data_out)
        assert dut_data_out == expected_data_out

    return drive_data_control, set_expected_data_out, check_data_out

def do_test():

    clock = Signal(False)
    data_in_top = Signal(intbv(0)[5:])
    data_out_top = Signal(intbv(0)[5:])
    data_ctrl = Signal(False)

    args = {'clock': clock,
            'data_in': data_in_top,
            'data_out': data_out_top,
            'data_control': data_ctrl}

    arg_types = {'clock': 'clock',
                 'data_in': 'random',
                 'data_out': 'output',
                 'data_control': 'custom'}

    # In this case, we set both the dut and the ref to by `dut`, this is
    # because we want to check the results online. The alternative usage
    # model (which can be used at the same time) is to have a reference
    # different to the dut. In this case, typically you'd intend the dut to be
    # convertible, but the ref can contain whatever you want it to contain.
    # It's generally much easier to write HDL if you have access to the full
    # power of python, and that is what the ref allows.
    #
    # custom_sources is a bit of a misnomer, as it can be used for checking
    # code too. It's called custom_sources for legacy reasons.
    #
    # We also output a VCD file of the data (which can be viewed with GTKWave).
    # This was useful in debugging this example!
    myhdl_cosimulation(
        30, dut, dut, args, arg_types,
        custom_sources=[
            (test_driver, (clock, data_ctrl, data_in_top, data_out_top), {})],
        vcd_name='vcd_test_out',)

if __name__ == '__main__':
    do_test()
```

Until more complete docs are available, I suggest looking at the test code
for a full description of the capabilities and how to use it (the doc strings
for each test describe well the behaviour tested by that test).

## Additional legacy information from Veriutils README

It seems to be necessary to install with pip from a source distribution 
(otherwise the source is not installed and so the code inspection breaks):

    python setup.py sdist
    cd dist
    sudo pip install Veriutils-0.9.tar.gz

The Vivado specific code has now been moved out into its own project 
called [Ovenbird](https://github.com/hgomersall/Ovenbird), which works
with Veriutils to provide (among other things) Vivado cosimulation 
capabilities.
