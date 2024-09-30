def axis_interface_attributes(axis_interface):
    ''' Extracts the attributes on the `axis_interface`.
    '''

    attributes = {
        'bus_width': axis_interface.bus_width,
        'TID_width': axis_interface.TID_width,
        'TDEST_width': axis_interface.TDEST_width,
        'TUSER_width': axis_interface.TUSER_width,
        'TVALID_init': axis_interface.TVALID._init,
        'TREADY_init': axis_interface.TREADY._init,
        'use_TLAST': hasattr(axis_interface, 'TLAST'),
        'use_TSTRB': hasattr(axis_interface, 'TSTRB'),
        'use_TKEEP': hasattr(axis_interface, 'TKEEP'),
    }

    return attributes

def check_axi_stream_interfaces_identical(axis_0, axis_1):
    ''' Raises an error if the axis interfaces do not match.
    '''

    axis_0_attributes = axis_interface_attributes(axis_0)
    axis_1_attributes = axis_interface_attributes(axis_1)

    assert(axis_0_attributes.keys() == axis_1_attributes.keys())

    mismatches = []

    for attribute in axis_0_attributes:
        if axis_0_attributes[attribute] != axis_1_attributes[attribute]:
            mismatches.append(attribute)

    mismatches.sort()

    if len(mismatches) != 0:
        raise ValueError(
            'The following mismatches were detected on the AXI stream '
            'interfaces:' + ', '.join(mismatches))

def check_axi_stream_interface_attributes(
    expected_attributes, axis_interface):
    ''' This function checks the attributes of the `axis_interface`.

    The `expected_attributes` argument should be a dictionary in which the
    keys are attributes on the `axis_interface`. Note, the attributes that
    this function checks are the arguments passed to `AxiStreamInterface`.

    If you don't care what value an attribute takes, then do not include it in
    the `expected_attributes` dictionary.

    If you do care, then include it in the `expected_attributes` dictionary
    with the desired value.
    '''

    axis_attributes = axis_interface_attributes(axis_interface)

    mismatches = []

    for attribute in expected_attributes:

        if attribute not in axis_attributes:
            raise ValueError(
                'check_axi_stream_interface_attributes: ' + str(attribute) +
                ' is invalid.')

        if axis_attributes[attribute] != expected_attributes[attribute]:
            mismatches.append(attribute)

    mismatches.sort()

    if len(mismatches) != 0:
        raise ValueError(
            'The following attributes on the axis_interface did not match '
            'the expected_attributes: ' + ', '.join(mismatches))
