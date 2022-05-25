from ._falling_edge_detector import falling_edge_detector

from jackdaw.test_utils.base_test import (
    JackdawTestCase, JackdawVivadoVHDLTestCase, JackdawVivadoVerilogTestCase)

import random
import copy

from myhdl import *

class TestFallingEdgeDetectorSimulation(JackdawTestCase):

    def setUp(self):

        self.clock = Signal(False)
        self.reset = Signal(False)
        self.trigger = Signal(False)
        self.edge_detected_output = Signal(False)

        self.args = {
            'clock': self.clock,
            'reset': self.reset,
            'trigger': self.trigger,
            'output': self.edge_detected_output,
            'buffer_trigger': False,
        }

        self.arg_types = {
            'clock': 'clock',
            'reset': 'custom',
            'trigger': 'custom',
            'output': 'output',
            'buffer_trigger': 'non-signal',
        }

    @block
    def stimulator(self, clock, reset, trigger):
        ''' A block to drive the reset and trigger inputs.
        '''

        @always(clock.posedge)
        def stim():

            # Randomly drive the reset
            if not reset:
                if random.random() < 0.05:
                    reset.next = True

            else:
                if random.random() < 0.2:
                    reset.next = False

            # Drive the trigger signal with pulses of random lengths
            if not trigger:
                if random.random() < 0.05:
                    trigger.next = True

            else:
                if random.random() < 0.2:
                    trigger.next = False

        return stim

    def test_falling_edge_detection(self):
        ''' On a falling edge of the trigger input the system should output a
        single cycle pulse.

        A reset should set the output low and any edges that had been received
        but not yet signalled on the output should never be output.

        The above is encapsulated in the following timing diagram
        (defined in Wavedrom):

        { "signal": [
          { "name": "clock",
           "wave": "p......|.|....|.......|....|..." },

          { "name": "reset",
           "wave": "0......|.|....|.......|1..0|.10" },

          { "name": "trigger",
           "wave": "0.10...|1|0...|1010...|.10.|10.",},

          { "name": "output pulse",
           "wave": "0...10.|.|.10.|..1010.|....|...",},
        ]}
        '''

        cycles = 4000

        @block
        def stimulate_and_check(
            clock, reset, trigger, output, buffer_trigger):

            return_objects = []

            return_objects.append(self.stimulator(clock, reset, trigger))

            trigger_d0 = Signal(False)
            falling_edge_detected = Signal(False)

            @always(clock.posedge)
            def check():

                trigger_d0.next = trigger

                if not trigger and trigger_d0:
                    # Detect falling edges on trigger
                    falling_edge_detected.next = True

                else:
                    falling_edge_detected.next = False

                if reset:
                    # Reset the test signals
                    trigger_d0.next = False
                    falling_edge_detected.next = False

                    # On reset output should be set low
                    self.assertFalse(output)

                elif falling_edge_detected:
                    # Check the output is as expected
                    self.assertTrue(output)

                else:
                    # At all other times the output should be set low
                    self.assertFalse(output)

            return_objects.append(check)

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, falling_edge_detector, falling_edge_detector, self.args,
            self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_buffered_falling_edge_detection(self):
        ''' On a falling edge of the trigger input the system should output a
        single cycle pulse.

        When the `buffer_trigger` argument is set true, this block should
        buffer the input. This amounts to a double buffer before the logic to
        protect against meta stability. It also allows the tools to place the
        trigger input close to the pin.

        A reset should set the output low and any edges that had been received
        but not yet signalled on the output should never be output.

        The above is encapsulated in the following timing diagram
        (defined in Wavedrom):

        { "signal": [
          { "name": "clock",
           "wave": "p......|.|....|.......|....|..." },

          { "name": "reset",
           "wave": "0......|.|....|.......|1..0|.10" },

          { "name": "trigger",
           "wave": "0.10...|1|0...|1010...|.10.|10.",},

          { "name": "output pulse",
           "wave": "0....10|.|..10|...1010|....|...",},
        ]}
        '''

        cycles = 4000

        self.args['buffer_trigger'] = True

        @block
        def stimulate_and_check(
            clock, reset, trigger, output, buffer_trigger):

            return_objects = []

            return_objects.append(self.stimulator(clock, reset, trigger))

            trigger_d0 = Signal(False)
            trigger_d1 = Signal(False)
            falling_edge_detected = Signal(False)

            @always(clock.posedge)
            def check():

                trigger_d0.next = trigger
                trigger_d1.next = trigger_d0

                if not trigger_d0 and trigger_d1:
                    # Detect falling edges on trigger
                    falling_edge_detected.next = True

                else:
                    falling_edge_detected.next = False

                if reset:
                    # Reset the test signals
                    trigger_d1.next = False
                    falling_edge_detected.next = False

                    # On reset output should be set low
                    self.assertFalse(output)

                elif falling_edge_detected:
                    # Check the output is as expected
                    self.assertTrue(output)

                else:
                    # At all other times the output should be set low
                    self.assertFalse(output)

            return_objects.append(check)

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, falling_edge_detector, falling_edge_detector, self.args,
            self.arg_types,
            custom_sources=[(stimulate_and_check, (), self.args)])

        self.assertEqual(dut_outputs, ref_outputs)

class TestFallingEdgeDetectorVivadoVhdlSimulation(
    JackdawVivadoVHDLTestCase, TestFallingEdgeDetectorSimulation):
    pass

class TestFallingEdgeDetectorVivadoVerilogSimulation(
    JackdawVivadoVerilogTestCase, TestFallingEdgeDetectorSimulation):
    pass
