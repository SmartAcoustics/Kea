from .bitfield_map import BitfieldMap

class RegisterDefinition(BitfieldMap):
    ''' A register definition.
    '''

    def __init__(self, offset, bitfield_definitions):
        ''' offset = Offset of the register.
        '''

        if offset < 0:
            raise ValueError(
                'RegisterDefinition: offset should not be negative.')

        super(RegisterDefinition, self).__init__(bitfield_definitions)

        self._offset = offset

    @property
    def offset(self):
        ''' Returns the offset of the register.
        '''
        return self._offset
