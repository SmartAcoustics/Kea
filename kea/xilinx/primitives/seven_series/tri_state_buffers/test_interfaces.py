import random

from kea.testing.test_utils.base_test import KeaTestCase

from .interfaces import NBitsTriStateBuffersIOInterface

class TestNBitsTriStateBuffersIOInterface(KeaTestCase):
    ''' The downmix_control block should reject incompatible interfaces and
    arguments.
    '''

    def test_zero_n_bits(self):
        ''' The `NBitsTriStateBuffersIOInterface` should raise an error if
        `n_bits` is 0.
        '''

        n_bits = 0

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('NBitsTriStateBuffersIOInterface: n_bits should be greater '
             'than 0.'),
            NBitsTriStateBuffersIOInterface,
            n_bits,
        )

    def test_negative_n_bits(self):
        ''' The `NBitsTriStateBuffersIOInterface` should raise an error if
        `n_bits` is negative.
        '''

        n_bits = random.randrange(-100, 0)

        # Check that the system errors
        self.assertRaisesRegex(
            ValueError,
            ('NBitsTriStateBuffersIOInterface: n_bits should be greater '
             'than 0.'),
            NBitsTriStateBuffersIOInterface,
            n_bits,
        )
