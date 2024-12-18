import random

def generate_value(lower_bound, upper_bound, p_lower_bound, p_max_value):
    ''' Generates a value between the inclusive `lower_bound` and the
    exclusive `upper_bound`.

    It will generate the corner cases of `lower_bound` and `max_value` more
    frequently than a random generator.

    `max_value` = `upper_bound` - 1

    The probability of returning the `lower_bound` can be set by
    `p_lower_bound`.

    The probability of returning the `max_value` can be set by `p_max_value`.

    Note: If `upper_bound` - `lower_bound` = 1 then `lower_bound` is the only
    valid value in the specified range. Therefore this function will always
    return `lower_bound` regardless of `p_lower_bound`.

    Note: If `upper_bound` - `lower_bound` = 2 then `lower_bound` and
    `max_value` are the only valid values in the specified range. Therefore
    this function will always return `lower_bound` or `max_value` regardless
    of `p_lower_bound` and `p_max_value`.
    '''

    assert(upper_bound > lower_bound)

    assert(p_lower_bound + p_max_value <= 1)

    random_val = random.random()

    if random_val < p_lower_bound:
        # Lowest value
        val = lower_bound

    elif random_val < p_lower_bound + p_max_value:
        # Max value
        val = upper_bound - 1

    else:
        if upper_bound - lower_bound <= 2:
            # There are only are only two options in the range (upper_bound or
            # max_value)
            val = random.randrange(lower_bound, upper_bound)

        else:
            # Random val
            val = random.randrange(lower_bound+1, upper_bound-1)

    return val

def generate_value_with_preferences(
    lower_bound, upper_bound, preferences, p_preferences):
    ''' Generates a value between the inclusive `lower_bound` and the
    exclusive `upper_bound`.

    `preferences` should be a list of values within the range `lower_bound` to
    `upper_bound`.

    It will generate one of the of `preferences` with a probability
    `p_preferences`.

    Note: If `upper_bound` - `lower_bound` = 1 then `lower_bound` is the only
    valid value in the specified range. Therefore this function will always
    return `lower_bound`.

    Note: If `upper_bound` - `lower_bound` = 2 then `lower_bound` and
    `max_value` are the only valid values in the specified range. Therefore
    this function will always return `lower_bound` or `max_value`.
    '''

    assert(upper_bound > lower_bound)

    assert(all(i > lower_bound for i in preferences))
    assert(all(i < upper_bound for i in preferences))

    assert(p_preferences <= 1)

    random_val = random.random()

    if random_val < p_preferences:
        # Pick one of the preferences
        val = random.choice(preferences)

    else:
        # Random val
        val = random.randrange(lower_bound, upper_bound)

    return val
