import copy
import random

from myhdl import block, Signal, intbv, enum, always, StopSimulation

from kea.hdl.shift_registers import piso_shift_register
from kea.hdl.signal_handling import signal_assigner
from kea.testing.test_utils.base_test import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)
from kea.testing.test_utils import generate_value

from ._synchronous_sipo_follower import synchronous_sipo_follower

def dut_args_setup(parallel_data_bitwidth):
    ''' Generate the arguments and argument types for the DUT.
    '''

    assert(parallel_data_bitwidth > 0)

    dut_args = {
        'clock': Signal(False),
        'serial_clock': Signal(False),
        'shift_reg_nreset': Signal(False),
        'parallel_out_nreset': Signal(False),
        'serial_data': Signal(False),
        'latch': Signal(False),
        'parallel_data': Signal(intbv(0)[parallel_data_bitwidth:]),
    }

    dut_arg_types = {
        'clock': 'clock',
        'serial_clock': 'custom',
        'shift_reg_nreset': 'custom',
        'parallel_out_nreset': 'custom',
        'serial_data': 'custom',
        'latch': 'custom',
        'parallel_data': 'output',
    }

    return dut_args, dut_arg_types

class TestSynchronousSipoFollowerInterface(KeaTestCase):

    def setUp(self):
        parallel_data_bitwidth = 16
        self.dut_args, _dut_arg_types = dut_args_setup(parallel_data_bitwidth)

    def test_parallel_data_bitwidth_of_one(self):
        ''' The `synchronous_sipo_follower` should raise an error if
        `parallel_data` is less than 2 bits wide.
        '''
        dut_args, _dut_arg_types = dut_args_setup(1)

        self.assertRaisesRegex(
            ValueError,
            ('synchronous_sipo_follower: parallel_data should be greater '
             'than 1 bit wide.'),
            synchronous_sipo_follower,
            **dut_args,
        )

class TestSynchronousSipoFollower(KeaTestCase):

    def setUp(self):
        self.test_count = 0
        self.tests_complete = False

    @block
    def end_tests(self, n_tests_to_run, **dut_args):

        clock = dut_args['clock']

        return_objects = []

        stop_simulation = Signal(False)

        @always(clock.posedge)
        def check():

            if self.test_count >= n_tests_to_run:
                # Give the DUT one more cycle before raising StopSimulation
                stop_simulation.next = True

            if stop_simulation:
                self.tests_complete = True
                raise StopSimulation

        return_objects.append(check)

        return return_objects

    @block
    def data_stim(
        self, ready, send_data, send_n_bits, parallel_stim_data,
        **dut_args):
        ''' A block to stim the serial_clock, serial_data and latch lines.
        '''

        clock = dut_args['clock']
        serial_clock = dut_args['serial_clock']
        shift_reg_nreset = dut_args['shift_reg_nreset']
        parallel_out_nreset = dut_args['parallel_out_nreset']
        serial_data = dut_args['serial_data']
        latch = dut_args['latch']

        return_objects = []

        parallel_data_bitwidth = len(parallel_stim_data)
        bit_count = Signal(intbv(0, 0, parallel_data_bitwidth+1))
        n_bits = Signal(intbv(0, 0, parallel_data_bitwidth+1))

        buffer = Signal(intbv(0)[parallel_data_bitwidth:])

        t_state = enum('IDLE', 'DATA', 'CLOCK_RISE', 'LATCH', 'COMPLETE')
        state = Signal(t_state.IDLE)

        @always(clock.posedge)
        def stim():

            if state == t_state.IDLE:
                if send_data and (send_n_bits > 0):
                    ready.next = False
                    n_bits.next = send_n_bits
                    buffer.next = parallel_stim_data
                    bit_count.next = 0
                    state.next = t_state.DATA

            elif state == t_state.DATA:
                serial_clock.next = False
                serial_data.next = buffer[parallel_data_bitwidth-bit_count-1]
                bit_count.next = bit_count + 1
                state.next = t_state.CLOCK_RISE

            elif state == t_state.CLOCK_RISE:
                serial_clock.next = True

                if bit_count >= n_bits:
                    state.next = t_state.LATCH

                else:
                    state.next = t_state.DATA

            elif state == t_state.LATCH:
                if not parallel_out_nreset:
                    # If parallel_out_nreset is low then we should not latch
                    # the data.
                    pass

                else:
                    serial_clock.next = False
                    latch.next = True
                    state.next = t_state.COMPLETE

            elif state == t_state.COMPLETE:
                latch.next = False
                ready.next = True
                state.next = t_state.IDLE

            if not shift_reg_nreset:
                serial_clock.next = False
                latch.next = False
                ready.next = True
                state.next = t_state.IDLE

        return_objects.append(stim)

        return return_objects

    @block
    def reset_stim(self, send_random_resets, **dut_args):
        ''' A block to stim shift_reg_nreset, parallel_out_nreset.
        '''

        clock = dut_args['clock']
        shift_reg_nreset = dut_args['shift_reg_nreset']
        parallel_out_nreset = dut_args['parallel_out_nreset']

        return_objects = []

        t_state = enum('INIT', 'STIM', 'IDLE')
        state = Signal(t_state.INIT)

        @always(clock.posedge)
        def stim():

            if state == t_state.INIT:
                shift_reg_nreset.next = True
                parallel_out_nreset.next = True

                if send_random_resets:
                    state.next = t_state.STIM

                else:
                    state.next = t_state.IDLE

            elif state == t_state.STIM:
                shift_reg_nreset.next = True

                if random.random() < 0.03:
                    shift_reg_nreset.next = False

                parallel_out_nreset.next = True

                if random.random() < 0.03:
                    parallel_out_nreset.next = False

            elif state == t_state.IDLE:
                pass

        return_objects.append(stim)

        return return_objects

    @block
    def stim_check(self, **dut_args):
        ''' Check the outputs of the DUT.
        '''

        clock = dut_args['clock']
        shift_reg_nreset = dut_args['shift_reg_nreset']
        parallel_out_nreset = dut_args['parallel_out_nreset']
        latch = dut_args['latch']
        parallel_data = dut_args['parallel_data']

        return_objects = []

        parallel_data_bitwidth = len(parallel_data)
        parallel_data_upper_bound = 2**parallel_data_bitwidth
        parallel_data_mask = parallel_data_upper_bound - 1
        send_n_bits_upper_bound = parallel_data_bitwidth+1

        data_stim_ready = Signal(False)
        send_data = Signal(False)
        send_n_bits = Signal(intbv(0, 0, parallel_data_bitwidth+1))
        parallel_stim_data = Signal(intbv(0)[parallel_data_bitwidth:])

        return_objects.append(
            self.data_stim(
                data_stim_ready, send_data, send_n_bits,
                parallel_stim_data, **dut_args))

        pending_parallel_data = Signal(intbv(0)[parallel_data_bitwidth:])
        expected_parallel_data = Signal(intbv(0)[parallel_data_bitwidth:])

        t_state = enum('IDLE', 'PROPAGATION', 'AWAIT_STIM_COMPLETE')
        state = Signal(t_state.IDLE)

        @always(clock.posedge)
        def check():

            assert(parallel_data == expected_parallel_data)

            if not parallel_out_nreset:
                # Not parallel_out_nreset should set parallel_data to 0
                expected_parallel_data.next = 0

            elif latch:
                # The shift register should be latched onto parallel_data
                expected_parallel_data.next = pending_parallel_data

            if state == t_state.IDLE:
                if random.random() < 0.05:
                    # Generate random stim_data
                    stim_data = random.randrange(parallel_data_upper_bound)
                    n_bits = (
                        generate_value(
                            1, send_n_bits_upper_bound, 0.1, 0.25))

                    send_data.next = True
                    parallel_stim_data.next = stim_data
                    send_n_bits.next = n_bits

                    n_old_bits = parallel_data_bitwidth-n_bits

                    if n_old_bits <= 0:
                        # All data in the shift register will up updated
                        pending_parallel_data.next = stim_data

                    else:
                        # There will be some old data remaining in the shift
                        # register. Shift the old data up and add the new data
                        # in at the bottom.
                        pending_parallel_data.next[:n_bits] = (
                            pending_parallel_data[n_old_bits:])
                        pending_parallel_data.next[n_bits:] = (
                            (stim_data >> n_old_bits) & (2**n_bits-1))

                    state.next = t_state.PROPAGATION

            elif state == t_state.PROPAGATION:
                send_data.next = False
                state.next = t_state.AWAIT_STIM_COMPLETE

            elif state == t_state.AWAIT_STIM_COMPLETE:
                if data_stim_ready:
                    self.test_count += 1
                    state.next = t_state.IDLE

            if not shift_reg_nreset:
                # The shift register should be reset to 0
                pending_parallel_data.next = 0
                send_data.next = False
                state.next = t_state.IDLE

        return_objects.append(check)

        return return_objects

    def base_test(self, parallel_data_bitwidth, send_random_resets):

        dut_args, dut_arg_types = dut_args_setup(parallel_data_bitwidth)

        cycles = 5000
        n_tests = 50

        @block
        def stimulate_check(**dut_args):

            return_objects = []

            return_objects.append(self.stim_check(**dut_args))
            return_objects.append(
                self.reset_stim(send_random_resets, **dut_args))
            return_objects.append(self.end_tests(n_tests, **dut_args))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, synchronous_sipo_follower, synchronous_sipo_follower,
            dut_args, dut_arg_types,
            custom_sources=[(stimulate_check, (), dut_args)])

        self.assertTrue(self.tests_complete)
        self.assertEqual(dut_outputs, ref_outputs)

    def test_data(self):
        ''' On rising edges of `serial_clock` the
        `synchronous_sipo_follower` should shift the data in the shift
        register up one bit and load `serial_data` into the first bit.

        When `latch` is set high, it should latch the data in the shift
        register on to `parallel_data`.
        '''
        self.base_test(
            parallel_data_bitwidth=16,
            send_random_resets=False)

    def test_random_bitwidth(self):
        ''' The `synchronous_sipo_follower` should work correctly with any
        `parallel_data` bitwidth.
        '''
        self.base_test(
            parallel_data_bitwidth=random.randrange(2, 33),
            send_random_resets=False)

    def test_bitwidth_of_two(self):
        ''' The `synchronous_sipo_follower` should work correctly with a
        `parallel_data` bitwidth of 2.
        '''
        self.base_test(
            parallel_data_bitwidth=2,
            send_random_resets=False)

    def test_resets(self):
        ''' On falling edges of `shift_reg_nreset` the
        `synchronous_sipo_follower` should set the every bit in the shift
        register low.

        On falling edges of `parallel_out_nreset` the
        `synchronous_sipo_follower` should set `parallel_data` to zero.
        '''
        self.base_test(
            parallel_data_bitwidth=16,
            send_random_resets=True)

    def test_resets_bitwidth_of_two(self):
        ''' The resets should function correctly with a `parallel_data`
        bitwidth of 2.
        '''
        self.base_test(
            parallel_data_bitwidth=2,
            send_random_resets=True)


class TestPisoToSynchronousSipoFollower(TestSynchronousSipoFollower):
    ''' A test class to verify the `synchronous_sipo_follower` works with the
    `piso_shift_register`.
    '''

    @block
    def reset_stim(self, send_random_resets, **dut_args):
        ''' Overwrite the reset_stim block as the `piso_shift_register` will
        drive the reset signals.
        '''

        clock = dut_args['clock']

        return_objects = []

        @always(clock.posedge)
        def stim():
            pass

        return_objects.append(stim)

        return return_objects

    @block
    def stim_check(self, **dut_args):
        ''' Check the outputs of the DUT when driven by the
        `piso_shift_register`.
        '''

        clock = dut_args['clock']
        serial_clock = dut_args['serial_clock']
        shift_reg_nreset = dut_args['shift_reg_nreset']
        parallel_out_nreset = dut_args['parallel_out_nreset']
        serial_data = dut_args['serial_data']
        latch = dut_args['latch']
        parallel_data = dut_args['parallel_data']

        return_objects = []

        parallel_data_bitwidth = len(parallel_data)
        parallel_data_upper_bound = 2**parallel_data_bitwidth

        data_stim_ready = Signal(True)
        parallel_stim_data = Signal(intbv(0)[parallel_data_bitwidth:])

        piso_data_out_nframe_sync = Signal(False)
        piso_data_out_nreset = Signal(False)
        external_register_value = Signal(intbv(0)[parallel_data_bitwidth:])

        return_objects.append(
            piso_shift_register(
                clock, False, parallel_stim_data, serial_data, serial_clock,
                latch, piso_data_out_nframe_sync, piso_data_out_nreset,
                external_register_value, clock_out_period=2,
                post_frame_delay=0, ready=data_stim_ready))

        # Connect piso_data_out_nreset to shift_reg_nreset and
        # parallel_out_nreset
        return_objects.append(
            signal_assigner(piso_data_out_nreset, shift_reg_nreset))
        return_objects.append(
            signal_assigner(piso_data_out_nreset, parallel_out_nreset))

        pending_parallel_data = Signal(intbv(0)[parallel_data_bitwidth:])
        expected_parallel_data = Signal(intbv(0)[parallel_data_bitwidth:])

        t_state = enum('INIT', 'IDLE', 'PROPAGATION', 'AWAIT_STIM_COMPLETE')
        state = Signal(t_state.INIT)

        @always(clock.posedge)
        def check():

            assert(parallel_data == expected_parallel_data)

            if not parallel_out_nreset:
                # Not parallel_out_nreset should set parallel_data to 0
                expected_parallel_data.next = 0

            elif latch:
                # The shift register should be latched onto parallel_data
                expected_parallel_data.next = pending_parallel_data

            if state == t_state.INIT:
                if data_stim_ready:
                    # The piso_shift_register performs an initial write. Wait
                    # for it to complete.
                    state.next = t_state.IDLE

            elif state == t_state.IDLE:
                if random.random() < 0.05:
                    # Generate random stim_data
                    stim_data = random.randrange(parallel_data_upper_bound)

                    parallel_stim_data.next = stim_data
                    pending_parallel_data.next = stim_data

                    state.next = t_state.PROPAGATION

            elif state == t_state.PROPAGATION:
                state.next = t_state.AWAIT_STIM_COMPLETE

            elif state == t_state.AWAIT_STIM_COMPLETE:
                if data_stim_ready:
                    self.test_count += 1
                    state.next = t_state.IDLE

            if not shift_reg_nreset:
                # The shift register should be reset to 0
                parallel_stim_data.next = 0
                pending_parallel_data.next = 0
                state.next = t_state.INIT

        return_objects.append(check)

        return return_objects

class TestSynchronousSipoFollowerVivadoVHDL(
    KeaVivadoVHDLTestCase, TestSynchronousSipoFollower):
    pass

class TestSynchronousSipoFollowerVivadoVerilog(
    KeaVivadoVerilogTestCase, TestSynchronousSipoFollower):
    pass
