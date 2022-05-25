
from myhdl import *
from myhdl import ToVerilogWarning, ToVHDLWarning

import random
import warnings

from jackdaw.test_utils.base_test import (
    JackdawTestCase, JackdawVivadoVHDLTestCase, JackdawVivadoVerilogTestCase)
from kea.axi import AxiStreamInterface

from .axis_transaction_count import (
    axis_count_valid_transactions, axis_count_sink_not_ready_transactions,
    axis_count_source_not_valid_transactions)

# This works around a bug in myhdl in which block objects placed as a property
# of a class are assumed to be bound. This method puts a reference to the
# block instead
transaction_count_methods = {
    'axis_count_valid_transactions': axis_count_valid_transactions,
    'axis_count_sink_not_ready': axis_count_sink_not_ready_transactions,
    'axis_count_source_not_valid': axis_count_source_not_valid_transactions}

'''There should be a series of transparent blocks that monitor transactions
on an AXI stream bus.
'''

class TestAxisCountTransactionsInterfaceMixin(object):

    counter_block_name = None

    def setUp(self):

        self.clock = Signal(False)
        self.reset = Signal(False)
        self.axis_interface = AxiStreamInterface(4, use_TLAST=False)
        self.count = Signal(intbv(0)[32:])

        self.default_args = {
            'clock': self.clock,
            'reset': self.reset,
            'axis_interface': self.axis_interface,
            'count': self.count}

    def test_axis_interface_interface(self):
        '''The axis_interface port should be an instance of
        ``kea.axi.AxiStreamInterface``.

        Anything else should raise a ValueError.
        '''

        args = self.default_args.copy()
        args['axis_interface'] = 'not a valid interface'

        counter_block = transaction_count_methods[self.counter_block_name]

        self.assertRaisesRegex(
            ValueError, 'Invalid axis_interface port',
            counter_block, **args)


class TestAxisCountTransactionsMixin(object):

    counter_block_name = None

    @block
    def count_definition(self, axis_interface, do_count):
        raise NotImplementedError

    def setUp(self):

        self.clock = Signal(False)
        self.reset = Signal(False)
        self.axis_interface = AxiStreamInterface(4, use_TLAST=False)
        self.count = Signal(intbv(0)[32:])

        # With in TVALID and out TREADY set to random, about 25% of the
        # time we will have a transaction
        # We make TDATA an output because it is not used so we can just
        # driver it low
        axis_interface_signal_types = {
            'TDATA': 'custom',
            'TVALID': 'random',
            'TREADY': 'random'}

        self.default_args = {
            'clock': self.clock,
            'reset': self.reset,
            'axis_interface': self.axis_interface,
            'count': self.count}

        self.default_arg_types = {
            'clock': 'clock',
            'reset': 'custom',
            'axis_interface': axis_interface_signal_types,
            'count': 'output'}

    def test_transaction_count(self):
        '''Whenever a valid transaction occurs when reset it no asserted, the
        output of count should be incremented.
        '''

        counter_block = transaction_count_methods[self.counter_block_name]

        @block
        def counter_ref(clock, axis_interface, count):

            do_count = Signal(False)

            count_def = self.count_definition(axis_interface, do_count)

            internal_count = Signal(intbv(0, min=count.min, max=count.max))

            @always(clock.posedge)
            def transaction_counter():
                if do_count:
                    internal_count.next = internal_count + 1

                assert internal_count == count

            return transaction_counter, count_def

        custom_sources = [
            (counter_ref,
             (self.clock, self.axis_interface, self.count), {})]

        samples = 500

        dut_results, ref_results = self.cosimulate(
            samples, counter_block, counter_block,
            self.default_args, self.default_arg_types,
            custom_sources=custom_sources)

        self.assertTrue(dut_results == ref_results)


    def test_range_limit(self):
        '''If the range limit of the count register is reached, no further
        transactions are recorded and the count register remains at its limit.
        '''
        counter_block = transaction_count_methods[self.counter_block_name]

        max_count_val = random.randrange(10, 64)

        count = Signal(intbv(0, min=0, max=max_count_val))
        self.default_args['count'] = count

        @block
        def counter_ref(clock, axis_interface, count):

            do_count = Signal(False)

            count_def = self.count_definition(axis_interface, do_count)

            internal_count = Signal(intbv(0, min=count.min, max=count.max))

            @always(clock.posedge)
            def transaction_counter():

                if do_count:
                    if internal_count < max_count_val-1:
                        internal_count.next = internal_count + 1

                assert internal_count == count

            return transaction_counter, count_def

        custom_sources = [
            (counter_ref,
             (self.clock, self.axis_interface, count), {})]

        samples = 500

        dut_results, ref_results = self.cosimulate(
            samples, counter_block, counter_block,
            self.default_args, self.default_arg_types,
            custom_sources=custom_sources)

        self.assertTrue(dut_results == ref_results)


    def test_reset(self):
        '''On a reset, the counter should be cleared
        '''
        counter_block = transaction_count_methods[self.counter_block_name]

        max_count_val = random.randrange(10, 64)

        count = Signal(intbv(0, min=0, max=max_count_val))
        self.default_args['count'] = count

        reset_probability = 0.05
        reset_clear_probability = 0.5

        @block
        def counter_ref(clock, reset, axis_interface, count):

            do_count = Signal(False)

            count_def = self.count_definition(axis_interface, do_count)

            internal_count = Signal(intbv(0, min=count.min, max=count.max))

            @always(clock.posedge)
            def reset_driver():
                if not reset:
                    if random.random() < reset_probability:
                        reset.next = True

                else:
                    if random.random() < reset_clear_probability:
                        reset.next = False


            @always(clock.posedge)
            def transaction_counter():

                if reset:
                    internal_count.next = 0

                else:
                    if do_count:
                        if internal_count < max_count_val-1:
                            internal_count.next = internal_count + 1

                    assert internal_count == count

            return transaction_counter, count_def, reset_driver

        custom_sources = [
            (counter_ref, (), self.default_args)]

        samples = 500

        dut_results, ref_results = self.cosimulate(
            samples, counter_block, counter_block,
            self.default_args, self.default_arg_types,
            custom_sources=custom_sources)

        self.assertTrue(dut_results == ref_results)


class TestAxisCountValidTransactionsInterface(
    TestAxisCountTransactionsInterfaceMixin, JackdawTestCase):

    counter_block_name = 'axis_count_valid_transactions'

class TestAxisCountSinkNotReadyTransactionsInterface(
    TestAxisCountTransactionsInterfaceMixin, JackdawTestCase):

    counter_block_name = 'axis_count_sink_not_ready'

class TestAxisCountSourceNotValidTransactionsInterface(
    TestAxisCountTransactionsInterfaceMixin, JackdawTestCase):

    counter_block_name = 'axis_count_source_not_valid'

class TestAxisCountValidTransactionsSimulation(
    TestAxisCountTransactionsMixin, JackdawTestCase):

    counter_block_name = 'axis_count_valid_transactions'

    @block
    def count_definition(self, axis_interface, do_count):

        @always_comb
        def define_count():
            do_count.next = axis_interface.TVALID and axis_interface.TREADY

        return define_count

class TestAxisCountSinkNotReadyTransactionsSimulation(
    TestAxisCountTransactionsMixin, JackdawTestCase):

    counter_block_name = 'axis_count_sink_not_ready'

    @block
    def count_definition(self, axis_interface, do_count):

        @always_comb
        def define_count():
            do_count.next = axis_interface.TVALID and not axis_interface.TREADY

        return define_count

class TestAxisCountSourceNotValidTransactionsSimulation(
    TestAxisCountTransactionsMixin, JackdawTestCase):

    counter_block_name = 'axis_count_source_not_valid'

    @block
    def count_definition(self, axis_interface, do_count):

        @always_comb
        def define_count():
            do_count.next = not axis_interface.TVALID and axis_interface.TREADY

        return define_count

class SupressConversionWarningsMixin(object):

    def cosimulate(self, *args, **kwargs):

        with warnings.catch_warnings():
            warnings.filterwarnings(
                'ignore',
                message='Signal is driven but not read: axis_interface_TDATA',
                category=ToVHDLWarning)

            warnings.filterwarnings(
                'ignore',
                message='Signal is driven but not read: axis_interface_TDATA',
                category=ToVerilogWarning)

            return super(SupressConversionWarningsMixin, self).cosimulate(
                *args, **kwargs)

class TestAxisCountValidTransactionsVivadoVHDLSimulation(
    SupressConversionWarningsMixin, JackdawVivadoVHDLTestCase,
    TestAxisCountValidTransactionsSimulation):
    pass

class TestAxisCountSinkNotReadyTransactionsVivadoVHDLSimulation(
    SupressConversionWarningsMixin, JackdawVivadoVHDLTestCase,
    TestAxisCountSinkNotReadyTransactionsSimulation):
    pass

class TestAxisCountSourceNotValidTransactionsVivadoVHDLSimulation(
    SupressConversionWarningsMixin, JackdawVivadoVHDLTestCase,
    TestAxisCountSourceNotValidTransactionsSimulation):
    pass

class TestAxisCountValidTransactionsVivadoVerilogSimulation(
    SupressConversionWarningsMixin,
    JackdawVivadoVerilogTestCase, TestAxisCountValidTransactionsSimulation):
    pass

class TestAxisCountSinkNotReadyTransactionsVivadoVerilogSimulation(
    SupressConversionWarningsMixin, JackdawVivadoVerilogTestCase,
    TestAxisCountSinkNotReadyTransactionsSimulation):
    pass

class TestAxisCountSourceNotValidTransactionsVivadoVerilogSimulation(
    SupressConversionWarningsMixin, JackdawVivadoVerilogTestCase,
    TestAxisCountSourceNotValidTransactionsSimulation):
    pass


