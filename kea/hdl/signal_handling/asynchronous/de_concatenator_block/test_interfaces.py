import random

from kea.testing.test_utils.base_test import KeaTestCase

from .interfaces import DeConcatenatorOutputInterface

class TestDeConcatenatorOutputInterface(KeaTestCase):

    def setUp(self):

        self.args = {
            'n_signals': 1,
            'signal_bitwidth': 1,
        }

    def test_zero_n_signals(self):
        ''' The `DeConcatenatorOutputInterface` should raise an error if
        `n_signals` is 0.
        '''

        self.args['n_signals'] = 0

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('DeConcatenatorOutputInterface: n_signals should be greater '
             'than 0.'),
            DeConcatenatorOutputInterface,
            **self.args,
        )

    def test_negative_n_signals(self):
        ''' The `DeConcatenatorOutputInterface` should raise an error if
        `n_signals` is less than 0.
        '''

        self.args['n_signals'] = random.randrange(-100, 0)

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('DeConcatenatorOutputInterface: n_signals should be greater '
             'than 0.'),
            DeConcatenatorOutputInterface,
            **self.args,
        )

    def test_zero_signal_bitwidth(self):
        ''' The `DeConcatenatorOutputInterface` should raise an error if
        `signal_bitwidth` is 0.
        '''

        self.args['signal_bitwidth'] = 0

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('DeConcatenatorOutputInterface: signal_bitwidth should be '
             'greater than 0.'),
            DeConcatenatorOutputInterface,
            **self.args,
        )

    def test_negative_signal_bitwidth(self):
        ''' The `DeConcatenatorOutputInterface` should raise an error if
        `signal_bitwidth` is less than 0.
        '''

        self.args['signal_bitwidth'] = random.randrange(-100, 0)

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('DeConcatenatorOutputInterface: signal_bitwidth should be '
             'greater than 0.'),
            DeConcatenatorOutputInterface,
            **self.args,
        )

