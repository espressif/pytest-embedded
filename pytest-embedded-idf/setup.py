import codecs
import os

import setuptools
from pytest_embedded_idf import __version__
from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding='utf-8').read()


AUTHOR = 'Fu Hanxi'
EMAIL = 'fuhanxi@espressif.com'
NAME = 'pytest-embedded-idf'
SHORT_DESCRIPTION = 'pytest embedded plugin for esp-idf project'
LICENSE = 'MIT'
URL = 'https://espressif.com'
REQUIRES = []
EXTRAS_REQUIRE = {
    'serial': 'pytest-embedded-serial-esp',
}
ENTRY_POINTS = {
    'pytest11': [
        'pytest_embedded_idf = pytest_embedded_idf.plugin',
    ],
}

setup(
    name=NAME,
    version=__version__,
    author=AUTHOR,
    author_email=EMAIL,
    license=LICENSE,
    url=URL,
    description=SHORT_DESCRIPTION,
    long_description=read('README.md'),
    packages=setuptools.find_packages(exclude='tests'),
    python_requires='>=3.6',
    install_requires=REQUIRES,
    extras_require=EXTRAS_REQUIRE,
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
        'License :: OSI Approved :: MIT License',
    ],
    entry_points=ENTRY_POINTS,
)
