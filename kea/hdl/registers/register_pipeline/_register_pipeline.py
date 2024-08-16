from myhdl import block, Signal, intbv, always

@block
def stage(clock, reset, enable, source_data, sink_data):
    ''' A single stage in the `register_pipeline`.
    '''
    assert(sink_data.max >= source_data.max)
    assert(sink_data.min <= source_data.min)

    # Check that we can assign 0 on reset
    assert(sink_data.max > 0)
    assert(sink_data.min <= 0)

    return_objects = []

    @always(clock.posedge)
    def assigner():

        if enable:
            sink_data.next = source_data

        if reset:
            sink_data.next = 0

    return_objects.append(assigner)

    return return_objects

@block
def register_pipeline(
    clock, reset, enable, source_data, sink_data, n_stages):
    ''' A simple register pipeline of `n_stages`.

    When `reset` is set high all registers in the pipeline will be reset to 0.

    When `enable` is set high, data will shift through the registers in the
    pipeline.
    '''

    if n_stages <= 0:
        raise ValueError(
            'register_pipeline: n_stages should be greater than 0.')

    if sink_data.max < source_data.max:
        raise ValueError(
            'register_pipeline: sink_data.max should be greater than or '
            'equal to source_data.max.')

    if sink_data.min > source_data.min:
        raise ValueError(
            'register_pipeline: sink_data.min should be less than or '
            'equal to source_data.min.')

    return_objects = []

    data_bitwidth = len(source_data)

    register_sink_datas = []

    for n in range(n_stages):
        if n == 0:
            register_source_data = source_data

        else:
            register_source_data = register_sink_datas[n-1]

        if n == n_stages-1:
            register_sink_data = sink_data

        else:
            register_sink_datas.append(
                Signal(intbv(0, min=source_data.min, max=source_data.max)))
            register_sink_data = register_sink_datas[n]

        return_objects.append(
            stage(
                clock, reset, enable, register_source_data,
                register_sink_data))

    return return_objects
