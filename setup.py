import versioneer
from distutils.core import setup

setup(
    name='Kea',
    version=versioneer.get_version(),
    packages=['kea',],
    cmdclass=versioneer.get_cmdclass(),
)
