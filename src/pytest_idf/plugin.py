# -*- coding: utf-8 -*-
import importlib

import pytest


def pytest_addoption(parser):
    group = parser.getgroup('idf')
    group.addoption('--printf',
                    default='a')


KNOWN_KEYWORDS = ['printf']


@pytest.fixture
def import_dict(request):
    res = {}
    for keyword in KNOWN_KEYWORDS:
        res[keyword] = request.config.getoption(keyword)
    return res


@pytest.fixture
def dut(import_dict):
    for subpackage, module in import_dict.items():
        globals()[subpackage] = getattr(importlib.import_module(f'pytest_idf.{subpackage}.{module}'),
                                        subpackage)  # noqa

    class DUT:
        def printf(self, *args, **kwargs):
            return globals()['printf'](*args, **kwargs)  # noqa

    return DUT()
