import random

from kea.testing.test_utils.base_test import KeaTestCase

from .interfaces import DoubleBufferArrayInterface

def test_args_setup():
    ''' Generate the arguments and argument types for the DUT.
    '''

    n_signals = 16

    args = {
        'n_signals': n_signals,
        'init_val': False,
    }

    return args

class TestDoubleBufferArrayInterface(KeaTestCase):
    ''' The DUT should reject incompatible interfaces and arguments.
    '''

    def setUp(self):
        self.args = test_args_setup()

    def test_zero_n_signals(self):
        ''' The `DoubleBufferArrayInterface` should raise an error if
        `n_signals` is 0.
        '''

        self.args['n_signals'] = 0

        self.assertRaisesRegex(
            ValueError,
            ('DoubleBufferArrayInterface: n_signals should be greater '
             'than zero.'),
            DoubleBufferArrayInterface,
            **self.args,
        )

    def test_negative_n_signals(self):
        ''' The `DoubleBufferArrayInterface` should raise an error if
        `n_signals` is less then 0.
        '''

        self.args['n_signals'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('DoubleBufferArrayInterface: n_signals should be greater '
             'than zero.'),
            DoubleBufferArrayInterface,
            **self.args,
        )

    def test_non_boolean_init_val(self):
        ''' The `DoubleBufferArrayInterface` should raise an error if
        `init_val` is not a boolean.
        '''

        self.args['init_val'] = random.randrange(0, 100)

        self.assertRaisesRegex(
            TypeError,
            ('DoubleBufferArrayInterface: init_val should be a bool.'),
            DoubleBufferArrayInterface,
            **self.args,
        )
