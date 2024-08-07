import random

from myhdl import block, Signal, intbv, always, always_comb

from kea.hdl.logic.asynchronous import not_gate
from kea.testing.test_utils import (
    KeaTestCase, KeaVivadoVHDLTestCase, KeaVivadoVerilogTestCase)

from .interfaces import NBitsTriStateBuffersIOInterface
from ._n_bit_tri_state_buffers import n_bit_tri_state_buffers

class TestNBitTriStateBuffersInterface(KeaTestCase):
    ''' The DUT should reject incompatible interfaces and arguments.
    '''

    def setUp(self):

        n_bits = 1

        self.dut_args = {
            'tri_state_write': Signal(intbv(0)[n_bits:]),
            'tri_state_read': Signal(intbv(0)[n_bits:]),
            'tri_state_control': Signal(False),
            'tri_state_io_interface': NBitsTriStateBuffersIOInterface(n_bits),
        }

    def test_invalid_tri_state_control_bitwidth(self):
        ''' The `n_bit_tri_state_buffers` block should raise an error if the
        `tri_state_control` is not 1 bit wide.
        '''
        invalid_bitwidth = random.randrange(2, 10)
        self.dut_args['tri_state_control'] = (
            Signal(intbv(0)[invalid_bitwidth:]))

        self.assertRaisesRegex(
            ValueError,
            ('n_bit_tri_state_buffers: tri_state_control should be one bit '
             'wide.'),
            n_bit_tri_state_buffers,
            **self.dut_args
            )

    def test_invalid_tri_state_io_interface(self):
        ''' The `n_bit_tri_state_buffers` block should raise an error if the
        `tri_state_io_interface` is not an instance of
        `NBitsTriStateBuffersIOInterface`.
        '''
        self.dut_args['tri_state_io_interface'] = random.randrange(1, 100)

        self.assertRaisesRegex(
            TypeError,
            ('n_bit_tri_state_buffers: tri_state_io_interface should be an '
             'instance of NBitsTriStateBuffersIOInterface'),
            n_bit_tri_state_buffers,
            **self.dut_args
            )

    def test_mismatched_tri_state_write_bitwidth(self):
        ''' The `n_bit_tri_state_buffers` block should raise an error if the
        bitwidth of `tri_state_write` is not equal to
        `tri_state_io_interface.n_bits`.
        '''
        n_bits_0, n_bits_1 = random.sample(range(1, 17), 2)
        self.dut_args['tri_state_write'] = Signal(intbv(0)[n_bits_0:])
        self.dut_args['tri_state_read'] = Signal(intbv(0)[n_bits_1:])
        self.dut_args['tri_state_io_interface'] = (
            NBitsTriStateBuffersIOInterface(n_bits_1))

        self.assertRaisesRegex(
            ValueError,
            ('n_bit_tri_state_buffers: tri_state_write should have the same '
             'number of bits as tri_state_io_interface.'),
            n_bit_tri_state_buffers,
            **self.dut_args
            )

    def test_mismatched_tri_state_read_bitwidth(self):
        ''' The `n_bit_tri_state_buffers` block should raise an error if the
        bitwidth of `tri_state_read` is not equal to
        `tri_state_io_interface.n_bits`.
        '''
        n_bits_0, n_bits_1 = random.sample(range(1, 17), 2)
        self.dut_args['tri_state_write'] = Signal(intbv(0)[n_bits_1:])
        self.dut_args['tri_state_read'] = Signal(intbv(0)[n_bits_0:])
        self.dut_args['tri_state_io_interface'] = (
            NBitsTriStateBuffersIOInterface(n_bits_1))

        self.assertRaisesRegex(
            ValueError,
            ('n_bit_tri_state_buffers: tri_state_read should have the same '
             'number of bits as tri_state_io_interface.'),
            n_bit_tri_state_buffers,
            **self.dut_args
            )

class TestNBitTriStateBuffers(KeaTestCase):

    @block
    def two_dut_wrapper(self, **test_args):
        ''' This block instantiates two `n_bit_tri_state_buffers` connected
        by their IO signals.

        This is necessary because the testing framework cannot handle in-out
        signals on the interface of the DUT.
        '''

        tri_state_control = test_args['tri_state_control']
        tri_state_write_0 = test_args['tri_state_write_0']
        tri_state_read_0 = test_args['tri_state_read_0']
        tri_state_write_1 = test_args['tri_state_write_1']
        tri_state_read_1 = test_args['tri_state_read_1']

        n_bits = len(tri_state_write_0)
        assert(len(tri_state_control) == 1)
        assert(len(tri_state_write_1) == n_bits)
        assert(len(tri_state_read_0) == n_bits)
        assert(len(tri_state_read_1) == n_bits)

        return_objects = []

        tri_state_io_interface = NBitsTriStateBuffersIOInterface(n_bits)

        # Invert tri_state_control for one of the n_bit_tri_state_buffers
        not_tri_state_control = Signal(True)
        return_objects.append(
            not_gate(tri_state_control, not_tri_state_control))

        return_objects.append(
            n_bit_tri_state_buffers(
                tri_state_write_0, tri_state_read_0, tri_state_control,
                tri_state_io_interface))

        return_objects.append(
            n_bit_tri_state_buffers(
                tri_state_write_1, tri_state_read_1, not_tri_state_control,
                tri_state_io_interface))

        return return_objects

    @block
    def dut_stim_check(self, **test_args):

        clock = test_args['clock']
        tri_state_control = test_args['tri_state_control']
        tri_state_write_0 = test_args['tri_state_write_0']
        tri_state_read_0 = test_args['tri_state_read_0']
        tri_state_write_1 = test_args['tri_state_write_1']
        tri_state_read_1 = test_args['tri_state_read_1']

        n_bits = len(tri_state_write_0)
        assert(len(tri_state_control) == 1)
        assert(len(tri_state_write_1) == n_bits)
        assert(len(tri_state_read_0) == n_bits)
        assert(len(tri_state_read_1) == n_bits)

        return_objects = []

        stim_upper_bound = 2**n_bits

        @always(clock.posedge)
        def stim_check():

            # Randomly drive the write signals
            tri_state_write_0.next = random.randrange(stim_upper_bound)
            tri_state_write_1.next = random.randrange(stim_upper_bound)

            if tri_state_control:
                assert(tri_state_read_0 == tri_state_write_1)

                if random.random() < 0.02:
                    # Randomly switch the direction
                    tri_state_control.next = False

            else:
                assert(tri_state_read_1 == tri_state_write_0)

                if random.random() < 0.02:
                    # Randomly switch the direction
                    tri_state_control.next = True

        return_objects.append(stim_check)

        return return_objects

    def base_test(self, n_bits):

        if not self.testing_using_vivado:
            cycles = 5000
        else:
            cycles = 1000

        test_args = {
            'clock': Signal(False),
            'tri_state_control': Signal(False),
            'tri_state_write_0': Signal(intbv(0)[n_bits:]),
            'tri_state_read_0': Signal(intbv(0)[n_bits:]),
            'tri_state_write_1': Signal(intbv(0)[n_bits:]),
            'tri_state_read_1': Signal(intbv(0)[n_bits:]),
        }

        test_arg_types = {
            'clock': 'clock',
            'tri_state_control': 'custom',
            'tri_state_write_0': 'custom',
            'tri_state_read_0': 'output',
            'tri_state_write_1': 'custom',
            'tri_state_read_1': 'output',
        }

        @block
        def stimulate_check(**test_args):

            return_objects = []

            return_objects.append(self.dut_stim_check(**test_args))

            return return_objects

        dut_outputs, ref_outputs = self.cosimulate(
            cycles, self.two_dut_wrapper, self.two_dut_wrapper, test_args,
            test_arg_types, custom_sources=[(stimulate_check, (), test_args)])

        self.assertEqual(dut_outputs, ref_outputs)

    def test_n_bits(self):
        ''' The `n_bit_tri_state_buffers` should instantiate one `xil_iobuf`
        for each bit on the `tri_state_io_interface`.

        All of the `xil_iobuf` should have the same `tri_state_control`
        signal connected to their `ts_t` input.

        Bit n of the `tri_state_write` signal should be connected to
        `xil_iobuf` n.

        Bit n of the `tri_state_read` signal should be connected to
        `xil_iobuf` n.

        Bit n of the `tri_state_io_interface` should be connected to
        `xil_iobuf` n.
        '''
        self.base_test(n_bits=8)

    def test_random_n_bits(self):
        ''' The `n_bit_tri_state_buffers` should function correctly for any
        value of `tri_state_io_interface.n_bits`.
        '''
        n_bits = random.randrange(3, 17)
        self.base_test(n_bits=n_bits)

    def test_two_bits(self):
        ''' The `n_bit_tri_state_buffers` should function correctly when
        `tri_state_io_interface.n_bits` is 2.
        '''
        self.base_test(n_bits=2)

    def test_one_bit(self):
        ''' The `n_bit_tri_state_buffers` should function correctly when
        `tri_state_io_interface.n_bits` is 1.
        '''
        self.base_test(n_bits=1)

# NOTE: Myhdl cannot currently convert blocks with internal tri-state signals
# to VHDL. I have raised the issue on the myhdl repository. When we update to
# a version of myhdl with a fix included, we can enable the VHDL tests again.
#
# The `two_dut_wrapper` in `TestNBitTriStateBuffers` uses internal tri-state
# signals because the testing framework cannot handle in-out signals on the
# interface of the DUT.
#
# The Verilog conversion tests verify the Xilinx primitives work as expected.
#
#class TestNBitTriStateBuffersVivadoVhdl(
#    KeaVivadoVHDLTestCase, TestNBitTriStateBuffers):
#    pass

class TestNBitTriStateBuffersVivadoVerilog(
    KeaVivadoVerilogTestCase, TestNBitTriStateBuffers):
    pass
