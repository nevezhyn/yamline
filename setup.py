from distutils.core import setup

setup(
    name='yamline',
    version='0.0.1',
    packages=['test.strategies', 'test.strategies.testdb',
              'test.strategies.testdb.engines',
              'test.strategies.testdb.engines.tests',
              'test.strategies.testdb.schemes', 'yamline', 'strategies',
              'strategies.testdb', 'strategies.testdb.engines',
              'strategies.testdb.engines.tests', 'strategies.testdb.schemes'],
    package_dir={'': 'test'},
    url='https://github.com/nevezhyn/yamline',
    license='GPL',
    author='Roman Nevezhyn',
    author_email='roman@nevezhyn.com',
    description=''
)
