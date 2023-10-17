# Kea

Some useful HDL blocks.

The usage documentation is within the python modules and the spec is tightly
defined (see the relevant test code for how it should work).

Check out the `examples` directory for how to use kea, which includes quite
a few explanatory comments. The various functions and classes are documented
as well.

## Testing

To run tests in the correct environment, use:

```
pdm sync --clean
pdm run python -m unittest <tests to run>
``
