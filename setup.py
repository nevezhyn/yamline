from distutils.core import setup

from yamline import __version__

setup(
    name='yamline',
    version=__version__,
    packages=['yamline'],
    url='https://github.com/nevezhyn/yamline',
    license='',
    author='Roman Nevezhyn',
    author_email='',
    description='YAML Pipeline semantics language and executor',
    install_requires=['pyyaml']
)
