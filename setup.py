#!/usr/bin/python
from __future__ import unicode_literals
from setuptools import setup, find_packages
import sys
if sys.version_info[0]==2:
    sys.exit('Sorry, python2 support is currently broken. Use python3!')
setup(
    name='textbeat',
    version='0.1.0',
    description='text music sequencer and midi shell',
    url='https://github.com/filpcoder/textbeat',
    author='Grady O\'Connell',
    author_email='flipcoder@gmail.com',
    license='MIT',
    packages=['textbeat','textbeat.def','textbeat.presets'],
    include_package_data=True,
    install_requires=[
        'pygame','colorama','prompt_toolkit','appdirs','pyyaml','docopt','future','shutilwhich','mido'
    ],
    entry_points='''
        [console_scripts]
        textbeat=textbeat.__main__:main
        txbt=textbeat.__main__:main
    ''',
    zip_safe=False
)

