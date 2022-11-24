VALID_BOOLEAN_VALUES = [True, False, 1, 0]

def overlapping_ranges(range_0, range_1):
    ''' Returns True if the ranges are overlapping and False if they are not
    overlapping.
    '''

    assert(isinstance(range_0, range))
    assert(isinstance(range_1, range))

    if max(range_0.start, range_1.start) < min(range_0.stop, range_1.stop):
        # There is an overlap
        return True

    else:
        # There is no overlap
        return False
