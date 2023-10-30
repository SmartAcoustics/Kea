from distutils import spawn as _spawn
import subprocess as _subprocess
import myhdl as _myhdl

VIVADO_EXECUTABLE = _spawn.find_executable('vivado')

if VIVADO_EXECUTABLE is not None:
    vivado_version_exe = _subprocess.Popen(
        [VIVADO_EXECUTABLE, '-version'], stdin=_subprocess.PIPE,
        stdout=_subprocess.PIPE, stderr=_subprocess.PIPE)

    try:
        out, err = vivado_version_exe.communicate()
        VIVADO_VERSION = (out.split()[1][1:]).decode('utf8')
    except IndexError:
        VIVADO_VERSION = None

else:
    VIVADO_VERSION = None

class KeaConversionError(_myhdl.ConversionError):
    pass
