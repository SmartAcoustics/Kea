from myhdl import *

import veriutils
import random

from ._pulse_synchroniser import pulse_synchroniser

from kea.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

class TestPulseSynchroniserSimulation(KeaTestCase):

    def setUp(self):

        self.trigger_clock = Signal(False)
        self.output_clock = Signal(False)
        self.trigger = Signal(False)
        self.synchronised_pulse_output = Signal(False)
        self.busy = Signal(False)

        self.default_args = {
            'trigger_clock': self.trigger_clock,
            'output_clock': self.output_clock,
            'trigger': self.trigger,
            'output': self.synchronised_pulse_output,
            'busy': self.busy,
        }

        self.default_arg_types = {
            'trigger_clock': 'clock',
            'output_clock': 'output',
            'trigger': 'custom',
            'output': 'output',
            'busy': 'output',
        }

    def test_high_to_low_freq_cdc(self):
        ''' When the ``trigger`` signal pulses high for one ``trigger_clock``
        cycle, the system should output one high pulse on the ``output`` for
        one ``output_clock`` cycle.

        The system should set busy high and ignore any pulses on trigger
        whilst it is performing the pulse synchronisation.

        The above is encapsulated in the following timing diagram
        (defined in Wavedrom):

        { "signal": [
          { "name": "trigger clock",
           "wave": "p..................."},

          { "name": "output clock",
           "wave": "p.........",
           "period": 2 },

          { "name": "trigger",
           "wave": "010................." },

          { "name": "trigger pulse detected",
           "wave": "0.1........0........" },

          { "name": "output pipeline 0",
           "wave": "0.1...0...",
           "period": 2  },

          { "name": "output pipeline 1",
           "wave": "0..1...0..",
           "period": 2  },

          { "name": "output pipeline 2",
           "wave": "0...1...0.",
           "period": 2  },

          { "name": "acknowledge pipeline 0",
           "wave": "0........1.......0.." },

          { "name": "acknowledge pipeline 1",
           "wave": "0.........1.......0." },

          { "name": "busy",
           "wave": "0.1...............0.",},

          { "name": "output",
           "wave": "0...10....",
           "period": 2,},
        ]}
        '''

        args = self.default_args.copy()
        arg_types = self.default_arg_types.copy()

        cycles = 5000

        test_confirmation = {'tests_run': 0}

        # Set the output clock period making sure it is longer than the
        # trigger clock period
        trigger_clock_period = veriutils.cosimulation.PERIOD
        output_clock_period = random.randrange(
            trigger_clock_period+1, 2*trigger_clock_period)

        @block
        def dut_wrapper(trigger_clock, output_clock, trigger, output, busy):

            # Create the output clock source
            output_clock_source = veriutils.clock_source(
                output_clock, output_clock_period)

            # Create the DUT
            pulse_cdc_block = pulse_synchroniser(
                trigger_clock, output_clock, trigger, output, busy)

            return output_clock_source, pulse_cdc_block

        @block
        def test():

            test_data = {'expected_output_pipeline': [False, False],
                         'expected_output': False,}

            trigger_sent = Signal(False)
            trigger_sent_d0 = Signal(False)

            @always(self.trigger_clock.posedge)
            def trigger_driver():

                # Randomly pulse the trigger signal
                if self.trigger:
                    self.trigger.next = False

                    if not self.busy:
                        # If the system is not busy then we should get a pulse
                        # on the output so set up a check.
                        trigger_sent.next = True

                        test_confirmation['tests_run'] += 1

                elif random.random() < 0.1:
                    self.trigger.next = True

            @always(self.output_clock.posedge)
            def check():

                trigger_sent_d0.next = trigger_sent

                if trigger_sent_d0:
                    # A trigger has been sent so we expect to see a pulse on
                    # the output
                    trigger_sent.next = False
                    trigger_sent_d0.next = False
                    test_data['expected_output_pipeline'].append(True)

                else:
                    test_data['expected_output_pipeline'].append(False)

                test_data['expected_output'] = (
                    test_data['expected_output_pipeline'].pop(0))

                # Check the output
                self.assertTrue(
                    test_data['expected_output']==
                    self.synchronised_pulse_output)

                #NOTE The busy signal is checked implicitly as we only add a
                # pulse to the expected output if busy is low.

            return trigger_driver, check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, dut_wrapper, dut_wrapper, args, arg_types,
            custom_sources=[(test, (),{})])

        assert(test_confirmation['tests_run'] >= 5)

        self.assertTrue(dut_outputs == ref_outputs)

    def test_low_to_high_freq_cdc(self):
        ''' When the ``trigger`` signal pulses high for one ``trigger_clock``
        cycle, the system should output one high pulse on the ``output`` for
        one ``output_clock`` cycle.

        The system should set busy high and ignore any pulses on trigger
        whilst it is performing the pulse synchronisation.

        The above is encapsulated in the following timing diagram
        (defined in Wavedrom):

        { "signal": [
           { "name": "trigger clock",
           "wave": "p..........",
           "period": 2 },

          { "name": "output clock",
           "wave": "p....................."},

          { "name": "trigger",
           "wave": "010........",
           "period": 2 },

          { "name": "trigger pulse detected",
           "wave": "0.1...0....",
           "period": 2 },

          { "name": "output pipeline 0",
           "wave": "0....1.......0........" },

          { "name": "output pipeline 1",
           "wave": "0.....1.......0......." },

          { "name": "output pipeline 2",
           "wave": "0......1.......0......" },

          { "name": "acknowledge pipeline 0",
           "wave": "0...1...0..",
           "period": 2  },

          { "name": "acknowledge pipeline 1",
           "wave": "0....1...0.",
           "period": 2  },

          { "name": "busy",
           "wave": "0.1......0.",
           "period": 2},

          { "name": "output",
           "wave": "0......10............."},
        ]}
        '''

        args = self.default_args.copy()
        arg_types = self.default_arg_types.copy()

        cycles = 5000

        test_confirmation = {'tests_run': 0}

        # Set the output clock period making sure it is shorter than the
        # trigger clock period
        trigger_clock_period = veriutils.cosimulation.PERIOD
        output_clock_period = random.randrange(1, trigger_clock_period)

        @block
        def dut_wrapper(trigger_clock, output_clock, trigger, output, busy):

            # Create the output clock source
            output_clock_source = veriutils.clock_source(
                output_clock, output_clock_period)

            # Create the DUT
            pulse_cdc_block = pulse_synchroniser(
                trigger_clock, output_clock, trigger, output, busy)

            return output_clock_source, pulse_cdc_block

        @block
        def test():

            test_data = {'expected_output_pipeline': [False, False],
                         'expected_output': False,}

            trigger_sent = Signal(False)
            trigger_sent_d0 = Signal(False)

            @always(self.trigger_clock.posedge)
            def trigger_driver():

                # Randomly pulse the trigger signal
                if self.trigger:
                    self.trigger.next = False

                    if not self.busy:
                        # If the system is not busy then we should get a pulse
                        # on the output so set up a check.
                        trigger_sent.next = True

                        test_confirmation['tests_run'] += 1

                elif random.random() < 0.1:
                    self.trigger.next = True

            @always(self.output_clock.posedge)
            def check():

                trigger_sent_d0.next = trigger_sent

                if trigger_sent_d0:
                    # A trigger has been sent so we expect to see a pulse on
                    # the output
                    trigger_sent.next = False
                    trigger_sent_d0.next = False
                    test_data['expected_output_pipeline'].append(True)

                else:
                    test_data['expected_output_pipeline'].append(False)

                test_data['expected_output'] = (
                    test_data['expected_output_pipeline'].pop(0))

                # Check the output
                self.assertTrue(
                    test_data['expected_output']==
                    self.synchronised_pulse_output)

                #NOTE The busy signal is checked implicitly as we only add a
                # pulse to the expected output if busy is low.

            return trigger_driver, check

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, dut_wrapper, dut_wrapper, args, arg_types,
            custom_sources=[(test, (),{})])

        assert(test_confirmation['tests_run'] >= 5)

        self.assertTrue(dut_outputs == ref_outputs)

class TestPulseSynchroniserVivadoVhdlSimulation(
    KeaVivadoVHDLTestCase, TestPulseSynchroniserSimulation):
    pass

class TestPulseSynchroniserVivadoVerilogSimulation(
    KeaVivadoVerilogTestCase, TestPulseSynchroniserSimulation):
    pass

