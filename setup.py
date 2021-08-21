#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [ 
    'docopt',
    'pandas',
    'plotly',
    'geopandas',
    'geopy',    
]

test_requirements = [ ]

setup(
    author="tim-fan",
    author_email='tim.fanselow@gmail.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Compare Google location history to COVID locations of interest",
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='location_of_interest_checker',
    name='location_of_interest_checker',
    packages=find_packages(include=['location_of_interest_checker', 'location_of_interest_checker.*']),
    entry_points = {
        'console_scripts': ['location_of_interest_checker=location_of_interest_checker.location_of_interest_checker:main'],
    },
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/tim-fan/location_of_interest_checker',
    version='0.1.0',
    zip_safe=False,
)