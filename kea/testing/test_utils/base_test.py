from kea.testing.myhdl.tests.base_hdl_test import HDLTestCase
from kea.testing.myhdl import myhdl_cosimulation

from kea.xilinx.vivado_utils.cosimulation import (
    vivado_vhdl_cosimulation, vivado_verilog_cosimulation)

from kea.xilinx.vivado_utils import VIVADO_EXECUTABLE

import unittest
import os

import numpy as np
import random

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

    def run(self, result=None):

        try:
            numpy_seed = self.random_state[0]
            random_seed = self.random_state[1]
        except AttributeError:
            numpy_seed = random.randrange(0, 2**32-1)
            random_seed = random.randrange(0, 2**32-1)

        np.random.seed(numpy_seed)
        random.seed(random_seed)

        if result is not None:
            n_failures = len(result.failures)
            n_errors = len(result.errors)

        super(KeaTestCase, self).run(result)

        try:
            if result is not None:
                if len(result.failures) != n_failures:

                    this_failure = result.failures[-1]

                    updated_failure = (
                        this_failure[0],
                        this_failure[-1] +
                        '\nTo repeat random tests exactly, set '
                        'self.random_state on the class with:\n'
                        'random_state = (%d, %d)\n' % (
                            numpy_seed, random_seed))

                    result.failures[-1] = updated_failure

                elif len(result.errors) != n_errors:

                    this_error = result.errors[-1]

                    updated_error = (
                        this_error[0],
                        this_error[-1] +
                        '\nTo repeat random tests exactly, set '
                        'self.random_state on the class with:\n'
                        'random_state = (%d, %d)\n' % (
                            numpy_seed, random_seed))

                    result.errors[-1] = updated_error

        except IndexError:
            pass

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
