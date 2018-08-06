#!/usr/bin/env python
# coding=utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""setuptools install script"""

from setuptools import setup

EXTRAS = {
    'test': [
        'flake8==3.5.0',
        'flake8-commas==2.0.0',
        'flake8-isort==2.5',
        'flake8-quotes==1.0.0',
        'pytest==3.7.1',
        'pytest-flake8==1.0.2',
    ],
}

if __name__ == '__main__':
    setup(
        classifiers=[
            'Intended Audience :: Developers',
            'Topic :: Software Development :: Testing',
            'Topic :: Security',
            'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
        ],
        description='Automatic bisection utility for Mozilla Firefox and SpiderMonkey',
        entry_points={
            'console_scripts': ['autobisect = autobisect.main:main'],
        },
        extras_require=EXTRAS,
        install_requires=[
              'configparser>=3.5.0',
              'fuzzfetch==0.5.7',
        ],
        keywords='fuzz fuzzing security test testing bisection',
        license='MPL 2.0',
        maintainer='Mozilla Fuzzing Team',
        maintainer_email='fuzzing@mozilla.com',
        name='autobisect',
        packages=['autobisect', 'autobisect.evaluator'],
        url='https://github.com/MozillaSecurity/autobisect',
        version='0.0.1')
