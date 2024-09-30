import copy
import random

from unittest import TestCase

from kea.hdl.axi import AxiStreamInterface
from kea.testing.test_utils import random_string_generator

from .axis_utils import (
    axis_interface_attributes, check_axi_stream_interfaces_identical,
    check_axi_stream_interface_attributes)

INT_ARGS = ['bus_width']
NONE_OR_INT_ARGS = ['TID_width', 'TDEST_width', 'TUSER_width']
BOOL_ARGS = [
    'TVALID_init', 'TREADY_init', 'use_TLAST', 'use_TSTRB', 'use_TKEEP']

AXI_STREAM_INTERFACE_ARGS = INT_ARGS + NONE_OR_INT_ARGS + BOOL_ARGS

def generate_random_axi_stream_interfaces_args():
    ''' Generates random arguments for the `AxiStreamInterface`.
    '''
    args = {}

    for arg_name in AXI_STREAM_INTERFACE_ARGS:

        if arg_name in INT_ARGS:
            # Generate a random integer for the integer args
            args[arg_name] = random.randrange(1, 9)

        elif arg_name in NONE_OR_INT_ARGS:
            # Generate a random value for the none or integer vals
            args[arg_name] = random.choice([None, 1, 2, 3, 4])

        elif arg_name in BOOL_ARGS:
            # Generate a random value for the boolean args
            args[arg_name] = random.choice([False, True])

        else:
            raise ValueError('Invalid arg_name')

    return args

def generate_mismatched_axi_stream_interfaces(
    one_mismatch=False, all_mismatched=False):
    ''' Generates two mismatched AXI stream interfaces.
    '''
    if one_mismatch:
        n_mismatches = 1

    elif all_mismatched:
        n_mismatches = len(AXI_STREAM_INTERFACE_ARGS)

    else:
        n_mismatches = random.randrange(1, len(AXI_STREAM_INTERFACE_ARGS)+1)

    # Select which args to mismatch
    mismatches = random.sample(AXI_STREAM_INTERFACE_ARGS, n_mismatches)
    mismatches.sort()

    axis_0_args = {}
    axis_1_args = {}

    for arg_name in AXI_STREAM_INTERFACE_ARGS:

        if arg_name in INT_ARGS:
            # Generate 2 different random integers for the integer args
            vals = random.sample(range(1, 9), 2)

        elif arg_name in NONE_OR_INT_ARGS:
            # Generate 2 different random vals
            vals = random.sample([None, 1, 2, 3, 4], 2)

        elif arg_name in BOOL_ARGS:
            # Generate to different random vals for the boolean args
            vals = random.sample([False, True], 2)

        else:
            raise ValueError('Invalid arg_name')

        axis_0_args[arg_name] = vals[0]

        if arg_name in mismatches:
            # This argument should be mismatched so select the second val
            axis_1_args[arg_name] = vals[1]

        else:
            # This argument should match so select the same val
            axis_1_args[arg_name] = vals[0]

    axis_0 = AxiStreamInterface(**axis_0_args)
    axis_1 = AxiStreamInterface(**axis_1_args)

    return axis_0, axis_1, mismatches

def generate_mismatched_expected_attributes(
    axis_interface, n_dont_cares, n_mismatches):
    ''' This function will generate an expected_attributes with the specified
    `n_dont_cares` and `n_mismatches`.
    '''
    expected_attributes = axis_interface_attributes(axis_interface)

    assert(n_dont_cares <= len(expected_attributes))

    # Choose random attributes to make don't cares
    dont_care_attributes = (
        random.sample(list(expected_attributes.keys()), n_dont_cares))

    for dont_care_attribute in dont_care_attributes:
        # Remove the don't care attributes
        del(expected_attributes[dont_care_attribute])

    assert(n_mismatches <= len(expected_attributes))

    attribute_vals = [None, True, False, 0, 1, 2, 3, 4, 5, 6, 7, 8]

    # Choose random attributes to make mismatched
    mismatched_attributes = (
        random.sample(list(expected_attributes.keys()), n_mismatches))
    mismatched_attributes.sort()

    for mismatched_attribute in mismatched_attributes:
        # Extract the current value of the attribute
        attribute_current_val = expected_attributes[mismatched_attribute]

        # Create a list of values which will be mismatched
        mismatched_values = [
            v for v in attribute_vals if v != attribute_current_val]

        # Pick a value which will be mismatched
        expected_attributes[mismatched_attribute] = (
            random.choice(mismatched_values))

    return expected_attributes, mismatched_attributes

class TestAxisInterfaceAttributes(TestCase):

    def test_random(self):
        ''' The `axis_interface_attributes` function should return a dict
        containing the current attributes of the `axis_interface`. The
        attributes should be in the same form as the `AxiStreamInterface`
        arguments.
        '''

        for n in range(20):
            args = generate_random_axi_stream_interfaces_args()

            axis_interface = AxiStreamInterface(**args)

            dut_output = axis_interface_attributes(axis_interface)

            assert(dut_output == args)

class TestCheckAxiStreamInterfacesIdentical(TestCase):

    def test_random_n_mismatch(self):
        ''' The `check_axi_stream_interfaces_identical` function should raise
        an error if the AXI stream interfaces passed to it are not identical.
        '''

        args = {}

        args['axis_0'], args['axis_1'], expected_mismatches = (
            generate_mismatched_axi_stream_interfaces())

        self.assertRaisesRegex(
            ValueError,
            ('The following mismatches were detected on the AXI stream '
             'interfaces:' + ', '.join(expected_mismatches)),
            check_axi_stream_interfaces_identical,
            **args,
        )

    def test_one_mismatch(self):
        ''' The `check_axi_stream_interfaces_identical` function should raise
        an error if the AXI stream interfaces has one mismatched parameter.
        '''

        args = {}

        args['axis_0'], args['axis_1'], expected_mismatches = (
            generate_mismatched_axi_stream_interfaces(one_mismatch=True))

        self.assertRaisesRegex(
            ValueError,
            ('The following mismatches were detected on the AXI stream '
             'interfaces:' + ', '.join(expected_mismatches)),
            check_axi_stream_interfaces_identical,
            **args,
        )

    def test_all_mismatched(self):
        ''' The `check_axi_stream_interfaces_identical` function should raise
        an error if none of the parameters on the AXI stream interfaces match.
        '''

        args = {}

        args['axis_0'], args['axis_1'], expected_mismatches = (
            generate_mismatched_axi_stream_interfaces(all_mismatched=True))

        self.assertRaisesRegex(
            ValueError,
            ('The following mismatches were detected on the AXI stream '
             'interfaces:' + ', '.join(expected_mismatches)),
            check_axi_stream_interfaces_identical,
            **args,
        )

    def test_pass(self):
        ''' The `check_axi_stream_interfaces_identical` function should not
        raise an error if the parameters on the AXI stream interfaces match.
        '''

        args = {}

        args['axis_0'], _mismatched, expected_mismatches = (
            generate_mismatched_axi_stream_interfaces(all_mismatched=True))

        args['axis_1'] = copy.copy(args['axis_0'])

        check_axi_stream_interfaces_identical(**args)

class TestCheckAxiStreamInterfacesAttributes(TestCase):

    def test_invalid_attribute(self):
        ''' The `check_axi_stream_interface_attributes` function should raise
        an error if the `expected_attributes` argument contains a key which
        does not match an argument used to create the `AxiStreamInterface`.
        '''

        args = generate_random_axi_stream_interfaces_args()
        axis_interface = AxiStreamInterface(**args)

        invalid_attribute = random_string_generator()

        invalid_expected_attributes = copy.copy(args)
        invalid_expected_attributes[invalid_attribute] = (
            random.randrange(0, 9))

        self.assertRaisesRegex(
            ValueError,
            ('check_axi_stream_interface_attributes: ' +
             str(invalid_attribute) + ' is invalid.'),
            check_axi_stream_interface_attributes,
            invalid_expected_attributes,
            axis_interface,
        )

    def test_random_n_mismatches(self):
        ''' The `check_axi_stream_interface_attributes` function should raise
        an error if the attributes on the `axis_interface` do not match the
        attributes in the `expected_attributes` dictionary.
        '''

        args = generate_random_axi_stream_interfaces_args()
        axis_interface = AxiStreamInterface(**args)

        n_attributes_upper_bound = len(AXI_STREAM_INTERFACE_ARGS) + 1
        n_mismatches = random.randrange(1, n_attributes_upper_bound)

        mismatched_expected_attributes, mismatched_attributes = (
            generate_mismatched_expected_attributes(
                axis_interface, 0, n_mismatches))

        self.assertRaisesRegex(
            ValueError,
            ('The following attributes on the axis_interface did not match '
             'the expected_attributes: ' + ', '.join(mismatched_attributes)),
            check_axi_stream_interface_attributes,
            mismatched_expected_attributes,
            axis_interface,
        )

    def test_one_mismatch(self):
        ''' The `check_axi_stream_interface_attributes` function should
        function correctly if there is one mismatch between the
        `axis_interface` and the `expected_attributes` dictionary.
        '''

        args = generate_random_axi_stream_interfaces_args()
        axis_interface = AxiStreamInterface(**args)

        n_mismatches = 1

        mismatched_expected_attributes, mismatched_attributes = (
            generate_mismatched_expected_attributes(
                axis_interface, 0, n_mismatches))

        self.assertRaisesRegex(
            ValueError,
            ('The following attributes on the axis_interface did not match '
             'the expected_attributes: ' + ', '.join(mismatched_attributes)),
            check_axi_stream_interface_attributes,
            mismatched_expected_attributes,
            axis_interface,
        )

    def test_all_mismatched(self):
        ''' The `check_axi_stream_interface_attributes` function should
        function correctly if all attributes are mismatched.
        '''

        args = generate_random_axi_stream_interfaces_args()
        axis_interface = AxiStreamInterface(**args)

        n_mismatches = len(AXI_STREAM_INTERFACE_ARGS)

        mismatched_expected_attributes, mismatched_attributes = (
            generate_mismatched_expected_attributes(
                axis_interface, 0, n_mismatches))

        self.assertRaisesRegex(
            ValueError,
            ('The following attributes on the axis_interface did not match '
             'the expected_attributes: ' + ', '.join(mismatched_attributes)),
            check_axi_stream_interface_attributes,
            mismatched_expected_attributes,
            axis_interface,
        )

    def test_random_dont_cares(self):
        ''' The `check_axi_stream_interface_attributes` function should only
        check values that are included in the `expected_attributes` argument.
        '''

        args = generate_random_axi_stream_interfaces_args()
        axis_interface = AxiStreamInterface(**args)

        n_dont_cares_upper_bound = len(AXI_STREAM_INTERFACE_ARGS)
        n_dont_cares = random.randrange(1, n_dont_cares_upper_bound)
        n_mismatches = 1

        mismatched_expected_attributes, mismatched_attributes = (
            generate_mismatched_expected_attributes(
                axis_interface, n_dont_cares, n_mismatches))

        self.assertRaisesRegex(
            ValueError,
            ('The following attributes on the axis_interface did not match '
             'the expected_attributes: ' + ', '.join(mismatched_attributes)),
            check_axi_stream_interface_attributes,
            mismatched_expected_attributes,
            axis_interface,
        )

    def test_one_dont_care(self):
        ''' The `check_axi_stream_interface_attributes` function should
        function correctly if one of the attributes has been left out of the
        `expected_attributes` dictionary.
        '''

        args = generate_random_axi_stream_interfaces_args()
        axis_interface = AxiStreamInterface(**args)

        n_dont_cares = 1
        n_mismatches = 1

        mismatched_expected_attributes, mismatched_attributes = (
            generate_mismatched_expected_attributes(
                axis_interface, n_dont_cares, n_mismatches))

        self.assertRaisesRegex(
            ValueError,
            ('The following attributes on the axis_interface did not match '
             'the expected_attributes: ' + ', '.join(mismatched_attributes)),
            check_axi_stream_interface_attributes,
            mismatched_expected_attributes,
            axis_interface,
        )

    def test_all_dont_care(self):
        ''' The `check_axi_stream_interface_attributes` function should
        not raise an error if the `expected_attributes` dict is empty.
        '''

        args = generate_random_axi_stream_interfaces_args()
        axis_interface = AxiStreamInterface(**args)

        expected_attributes = {}

        check_axi_stream_interface_attributes(
            expected_attributes, axis_interface)

    def test_all_correct(self):
        ''' The `check_axi_stream_interface_attributes` function should
        not raise an error if the `expected_attributes` dict matches the
        `axis_interface`.
        '''

        args = generate_random_axi_stream_interfaces_args()
        axis_interface = AxiStreamInterface(**args)

        check_axi_stream_interface_attributes(args, axis_interface)
