def axi_stream_types_generator(
    sink=False, TID_width=None, TDEST_width=None, TUSER_width=None,
    use_TLAST=True, use_TSTRB=False, use_TKEEP=False):
    ''' Generates the types for the AXIS interface. If sink is False then it
    is assumed to be a source interface.

    Note source/sink is from the perspective of the DUT. A source AXIS means
    data flows into the DUT. A sink AXIS means data flows out of the DUT
    '''

    if sink:
        types = {
            'TDATA': 'output',
            'TVALID': 'output',
            'TREADY': 'custom',}

        if TID_width is not None:
            types['TID'] = 'output'

        if TDEST_width is not None:
            types['TDEST'] = 'output'

        if TUSER_width is not None:
            types['TUSER'] = 'output'

        if use_TLAST:
            types['TLAST'] = 'output'

        if use_TSTRB:
            types['TSTRB'] = 'output'

        if use_TKEEP:
            types['TKEEP'] = 'output'

    else:
        types = {
            'TDATA': 'custom',
            'TVALID': 'custom',
            'TREADY': 'output',}

        if TID_width is not None:
            types['TID'] = 'custom'

        if TDEST_width is not None:
            types['TDEST'] = 'custom'

        if TUSER_width is not None:
            types['TUSER'] = 'custom'

        if use_TLAST:
            types['TLAST'] = 'custom'

        if use_TSTRB:
            types['TSTRB'] = 'custom'

        if use_TKEEP:
            types['TKEEP'] = 'custom'

    return types
