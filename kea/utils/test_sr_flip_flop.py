import random

from myhdl import block, always, Signal

from jackdaw.test_utils.base_test import (
    JackdawTestCase, JackdawVivadoVHDLTestCase, JackdawVivadoVerilogTestCase)

from ._sr_flip_flop import sr_flip_flop

class TestSRFlipFlopSimulation(JackdawTestCase):

    def setUp(self):
        self.clock = Signal(False)
        self.set_output = Signal(False)
        self.reset_output = Signal(False)
        self.output = Signal(False)

        self.args = {
            'clock': self.clock,
            'set_output': self.set_output,
            'reset_output': self.reset_output,
            'output': self.output,
        }

        self.arg_types = {
            'clock': 'clock',
            'set_output': 'custom',
            'reset_output': 'custom',
            'output': 'output',
        }

    @block
    def check_sr_flip_flop(self, clock, set_output, reset_output, output):
        ''' This block checks the behaviour of the SR flip flop.
        '''

        return_objects = []

        expected_output = Signal(False)

        @always(clock.posedge)
        def stim_check():

            ########
            # Stim #
            ########

            if not reset_output:
                if random.random() < 0.02:
                    reset_output.next = True

            else:
                if random.random() < 0.3:
                    reset_output.next = False

            if not set_output:
                if random.random() < 0.02:
                    set_output.next = True

            else:
                if random.random() < 0.3:
                    set_output.next = False

            #########
            # Check #
            #########

            assert(output == expected_output)

            if reset_output:
                expected_output.next = False

            elif set_output:
                expected_output.next = True

        return_objects.append(stim_check)

        return return_objects

    def test_sr_flip_flop(self):
        ''' When `reset` is set high the `sr_flip_flop` should set the output
        low.

        When `set` is high, the `sr_flip_flip` should set the output high.

        At all other times the output should maintain its state.
        '''

        cycles = 5000

        @block
        def test(clock, set_output, reset_output, output):

            return_objects = []

            return_objects.append(
                self.check_sr_flip_flop(
                    clock, set_output, reset_output, output))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, sr_flip_flop, sr_flip_flop, self.args, self.arg_types,
            custom_sources=[(test, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestSRFlipFlopVivadoVhdlSimulation(
    JackdawVivadoVHDLTestCase, TestSRFlipFlopSimulation):
    pass

class TestSRFlipFlopVivadoVerilogSimulation(
    JackdawVivadoVerilogTestCase, TestSRFlipFlopSimulation):
    pass
