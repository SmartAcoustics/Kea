from veriutils.tests.base_hdl_test import HDLTestCase
from veriutils import myhdl_cosimulation

from ovenbird.cosimulation import (
    vivado_vhdl_cosimulation, vivado_verilog_cosimulation)

from ovenbird import VIVADO_EXECUTABLE

import unittest
import os

VIVADO_DISABLE_REASON = ''

try:
    if os.environ['USE_VIVADO'] == '0':
        USE_VIVADO = False
        VIVADO_DISABLE_REASON = 'USE_VIVADO environment variable was set to 0'
    else:
        USE_VIVADO = True

except KeyError:
    # default to trying to use Vivado
    USE_VIVADO = True

class KeaTestCase(HDLTestCase):

    testing_using_vivado = False

    def cosimulate(self, sim_cycles, dut_factory, ref_factory, args,
                   arg_types, **kwargs):

        return myhdl_cosimulation(
            sim_cycles, dut_factory, ref_factory, args, arg_types, **kwargs)

    def tearDown(self):
        # FIXME
        # This is horrible. MyHDL should _not_ keep every historic simulation
        # in a global like this. I made a foray into fixing this at
        # https://github.com/hgomersall/myhdl/tree/globals_free_sim
        # but at the time the appetite for this was not enough to complete
        # the work properly.
        # Here we have a very clear use case: Running all the Jackdaw tests
        # causes the system to run out of memory!
        # At some point, we need to fix this properly in MyHDL. A simpler
        # fix than the previous work would be simply to allow the state to
        # be cleared using a manual call. Not very elegant but would work.
        #
        # This should work because each test is notionally standalone, so
        # there is no problem in simply clearing the simulator state between
        # each run.
        import myhdl._simulator

        myhdl._simulator._signals = []
        myhdl._simulator._blocks = []
        myhdl._simulator._siglist = []
        myhdl._simulator._futureEvents = []
        myhdl._simulator._time = 0
        myhdl._simulator._cosim = 0
        myhdl._simulator._tracing = 0
        myhdl._simulator._tf = None

class KeaVivadoVHDLTestCase(HDLTestCase):

    testing_using_vivado = True

    def cosimulate(self, sim_cycles, dut_factory, ref_factory, args,
                   arg_types, **kwargs):

        if not USE_VIVADO:
            raise unittest.SkipTest(
                'Vivado tests have been disabled: %s' % VIVADO_DISABLE_REASON)

        if VIVADO_EXECUTABLE is None:
            raise unittest.SkipTest(
                'Vivado executable not available: Running VHDL tests in '
                'Vivado requires the Vivado executable to be in the path.')

        return vivado_vhdl_cosimulation(
            sim_cycles, dut_factory, ref_factory, args, arg_types, **kwargs)

class KeaVivadoVerilogTestCase(HDLTestCase):

    testing_using_vivado = True

    def cosimulate(self, sim_cycles, dut_factory, ref_factory, args,
                   arg_types, **kwargs):

        if not USE_VIVADO:
            raise unittest.SkipTest(
                'Vivado tests have been disabled: %s' % VIVADO_DISABLE_REASON)

        if VIVADO_EXECUTABLE is None:
            raise unittest.SkipTest(
                'Vivado executable not available: Running Verilog tests in '
                'Vivado requires the Vivado executable to be in the path.')

        return vivado_verilog_cosimulation(
            sim_cycles, dut_factory, ref_factory, args, arg_types, **kwargs)
