from math import floor

def factors(value):
    ''' Generates a list containing the factors of value.
    '''

    value_factors = []

    # We want to check up to an including the square root of value. Each value
    # of n which is a factor also gives us a second factor (the multiplier).
    #
    # For example:
    #
    #     If value = 12.
    #     n = 1 and the multiplier is 12 (another factor)
    #     n = 2 and the multiplier is 6 (another factor)
    #     n = 3 and the multiplier is 4 (another factor)
    #
    # There is no point checking higher than the square root as all factors
    # greater than the square root must be paired with another factor which is
    # less than the square root and we have already found these (and their
    # corresponding multiplier).
    for n in range(1, int(floor(value**0.5))+1):
        if value % n == 0:
            value_factors.append(n)
            value_factors.append(int(value/n))

    # We convert value_factors to a set and back to a list in order to remove
    # repeated factors. Eg if value is the square of an integer.
    return list(set(value_factors))
