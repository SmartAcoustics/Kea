import versioneer
from setuptools import setup, find_packages

setup(
    name='Kea',
    version=versioneer.get_version(),
    packages=find_packages(),
    cmdclass=versioneer.get_cmdclass(),
)
