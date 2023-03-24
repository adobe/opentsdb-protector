#  Copyright 2019 Adobe
#  All Rights Reserved.
#
#  NOTICE: Adobe permits you to use, modify, and distribute this file in
#  accordance with the terms of the Adobe license agreement accompanying
#  it. If you have received this file from a source other than Adobe,
#  then your use, modification, or distribution of it requires the prior
#  written permission of Adobe.
#

from setuptools import setup, find_packages

# Pull version from source without importing
# since we can't import something we haven't built yet :)
exec (open('protector/version.py').read())

# Create reStructuredText README file for PyPi
# http://stackoverflow.com/a/26737672/270334
try:
    import pypandoc

    long_description = pypandoc.convert('README.md', 'rst')
except(IOError, ImportError):
    long_description = open('README.md').read()

requires = [
    "daemonocle==1.0.1",
    "psutil>=5.6.6",
    "pbr",
    "python-dateutil",
    "PyYAML>=4.2b1",
    "result==0.3.0",
    "prometheus_client==0.7.1",
    "redis==3.2.1",
    "wheel==0.33.4",
    "setuptools==41.0.1",
    "typing-extensions==3.10.0.2"
]

test_requires = [
    "coverage",
    "freezegun",
    "mock",
    'nose',
    'nose-cover3',
    "six"
]

setup(name='opentsdb-protector',
      version=__version__,
      description='Circuit breaker and analytics tool for OpenTSDB queries',
      long_description=long_description,
      classifiers=[
          'Development Status :: 4 - Beta',
          'License :: OSI Approved :: BSD License',
          'Topic :: Utilities',
          "Programming Language :: Python",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: Implementation :: PyPy",
      ],
      keywords='opentsdb query proxy circuit-breaker',
      url='https://git.corp.adobe.com/rojco/opentsdb-protector',
      author='Valentin Rojco',
      author_email='rojco@adobe.com',
      license='BSD',
      packages=find_packages(),
      install_requires=requires,
      test_suite='nose.collector',
      tests_require=test_requires,
      entry_points={
          'console_scripts': ['opentsdb-protector=protector.__main__:main'],
      },
      include_package_data=True,
      zip_safe=False)
