# Vivado Verification toolkit #

A tool for merging the MyHDL workflow with Vivado (and possibly other tools
further down the line).

The emphasis at this stage is on extending the `kea.testing.myhdl` toolkit to
support Vivado.

This involves two core features:

1. The `vivado_vhdl_cosimulation` and `vivado_verilog_cosimulation` functions.
These are functionally equivalent to `kea.testing.myhdl.myhdl_cosimulation`
(albeit with a couple of extra arguments), but run the device under test
inside the Vivado simulator.

2. The VivadoIP block. This allows Vivado IP blocks (notably encrypted IP) 
to be included and controlled in a MyHDL hierarchy, with 
`vivado_*_cosimulation` using the correct IP block. Encrypted IP is not
functionally accessible inside MyHDL, so it is necessary to reimplement the
functionality of the block for MyHDL simulation. This is not as serious 
a drawback as one might initially imagine as the MyHDL implementation does
not need to be convertible and typically the IP blocks can be easily 
implemented using the full power of Python (and all the libraries available) - 
indeed, in implementing the Python model of the IP block, you'll understand
it properly.

The best way of understanding how to use the tool is by looking at the 
examples in the `examples` directory, which also serve as a test bench.

The examples demonstrate using Vivado with an IP block integrated with MyHDL,
both standalone (`dsp48e1.py`) and as part of a hierarchy 
(`simple_wrapper.py`).

In order to use Vivado, it is necessary to set up your environment. Under
linux, this is something like:

    source /opt/Xilinx/Vivado/2019.2/settings64.sh

I imagine there's something similar under Windows (though I've not tested it).

If the executable is not in the path, the relevant tests will be skipped, or
if you try to use the Vivado cosimulation, an `EnvironmentError` will be 
raised.

Again, to use the Vivado capability, it is necessary to have a
`kea-testing.cfg` file in the current working directory to configure the part
being used. An example one is provided. The need for `kea-testing.cfg` will
likely be  removed in subsequent releases (much of the need for it has been
removed in the seperation of the vivado verification toolkit).

This Vivado verification toolkit depends on the MyHDL initial value support,
which is now part of MyHDL master.

The code is released under the BSD 3 clause license. See License.txt for the 
text of this.
