# -*- coding: utf-8 -*-
import os

import pytest


def pytest_addoption(parser):
    group = parser.getgroup('idf')
    group.addoption('--target',
                    nargs='+',
                    default=['esp32'],
                    help='Run all tests with different targets')
    group.addoption(
        '--port',
        default=os.environ.get('ESPPORT', None),
        help='Serial port',
    )
    group.addoption(
        '--baud',
        default=os.environ.get('ESPBAUD', 460800),
        help='Baud rate',
    )


@pytest.fixture
def target(request):
    return request.config.option.target


@pytest.fixture
def port(request):
    return request.config.option.port
