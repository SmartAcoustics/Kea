import myhdl
from myhdl.conversion._toVHDL import _shortversion

_global_toVHDL_libraries = set()
_global_toVHDL_use_clauses = set(['work.pck_myhdl_%s.all' % (_shortversion)])

def update(library=None, use_clauses=None):

    if library is not None:
        # If an extra library is required add it to the set. Note: sets only
        # contain unique values.
        _global_toVHDL_libraries.add(library)

    if use_clauses is not None:
        # If an extra use clause is required add it to the set. Note: sets
        # only contain unique values.
        _global_toVHDL_use_clauses.add(use_clauses)

    if len(_global_toVHDL_libraries) == 0:
        # If update is run when the libraries set is empty we need to keep
        # the libraries value as work
        myhdl.toVHDL.library = 'work'

    else:
        # Add library to toVHDL so that they get written into the header of
        # the converted VHDL file
        myhdl.toVHDL.library = ', '.join(_global_toVHDL_libraries)

    # Add use_clauses to toVHDL so that they get written into the header of
    # the converted VHDL file
    myhdl.toVHDL.use_clauses = (
        'use ' + ', '.join(_global_toVHDL_use_clauses) + ';')

update()
