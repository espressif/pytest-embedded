import codecs
import os

import setuptools
from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding='utf-8').read()


VERSION = '0.1.0'
AUTHOR = 'Fu Hanxi'
EMAIL = 'fuhanxi@espressif.com'
NAME = 'pytest-embedded-jtag'
SHORT_DESCRIPTION = 'ESP-IDF test plugin'
LICENSE = 'Apache License 2.0'
URL = 'https://espressif.com'
REQUIRES = [
    'pytest>=3.5.0',
    # 'pytest-embedded',
]
ENTRY_POINTS = {
    'pytest11': [
        'pytest_embedded_jtag = pytest_embedded_jtag.plugin',
    ],
}

setup(
    name=NAME,
    version=VERSION,
    author=AUTHOR,
    author_email=EMAIL,
    license=LICENSE,
    url=URL,
    description=SHORT_DESCRIPTION,
    long_description=read('README.md'),
    packages=setuptools.find_packages(exclude='tests'),
    python_requires='>=3.6',
    install_requires=REQUIRES,
    classifiers=[
        'Framework :: Pytest',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: Apache Software License',
    ],
    entry_points=ENTRY_POINTS,
)
