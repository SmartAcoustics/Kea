import random

from kea.test_utils import KeaTestCase

from .test_bitfield_map import random_bitfield_definitions
from .register_definition import RegisterDefinition

class TestRegisterDefinition(KeaTestCase):

    def setUp(self):

        n_available_bits = 32
        n_bitfields = 6

        bitfield_definitions, self.expected_bitfields = (
            random_bitfield_definitions(n_available_bits, n_bitfields))

        self.args = {
            'offset': random.randrange(2**32),
            'bitfield_definitions': bitfield_definitions,
        }

        # Create the bitfield map
        self.register = RegisterDefinition(**self.args)

    def test_negative_offset(self):
        ''' The `RegisterDefinition` should raise an error if the `offset` is
        less than 0.
        '''

        self.args['offset'] = random.randrange(-100, 0)

        self.assertRaisesRegex(
            ValueError,
            ('RegisterDefinition: offset should not be negative.'),
            RegisterDefinition,
            **self.args,
        )

    def test_offset(self):
        ''' The `offset` property on a `RegisterDefinition` should return the
        offset specified at initialisation of that `RegisterDefinition`.
        '''

        assert(self.register.offset == self.args['offset'])
