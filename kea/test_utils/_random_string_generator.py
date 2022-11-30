import string
import random

def random_string_generator(length=4):
    ''' This function generates a random string of length characters.
    '''

    letters = string.ascii_lowercase
    generated_string = ''.join(random.choice(letters) for i in range(length))

    return generated_string
