import codecs
import os
import re

import setuptools
from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding='utf-8').read()


def get_version():
    regex = re.compile(r'version = "(.+)"')
    return regex.findall(read(os.path.join('..', 'pyproject.toml')))[0]


AUTHOR = 'Fu Hanxi'
EMAIL = 'fuhanxi@espressif.com'
NAME = 'pytest-embedded-serial-esp'
SHORT_DESCRIPTION = 'pytest embedded plugin for testing espressif boards via serial ports'
LICENSE = 'MIT'
URL = 'https://docs.espressif.com/projects/pytest-embedded/en/latest/'
VERSION = get_version()
REQUIRES = [
    f'pytest-embedded-serial~={VERSION}',
    'esptool~=3.1',
]
ENTRY_POINTS = {}

setup(
    name=NAME,
    version=get_version(),
    author=AUTHOR,
    author_email=EMAIL,
    license=LICENSE,
    url=URL,
    description=SHORT_DESCRIPTION,
    long_description=read('README.md'),
    packages=setuptools.find_packages(exclude='tests'),
    python_requires='>=3.7',
    install_requires=REQUIRES,
    classifiers=[
        'Framework :: Pytest',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3 :: Only',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: MIT License',
    ],
    entry_points=ENTRY_POINTS,
)
