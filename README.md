# pytest-embedded

[![Documentation Status](https://readthedocs.com/projects/espressif-pytest-embedded/badge/?version=latest)](https://docs.espressif.com/projects/pytest-embedded/en/latest/?badge=latest) ![Python 3.7+](https://img.shields.io/pypi/pyversions/pytest-embedded)

A pytest plugin that has multiple services available for various functionalities. Designed for embedded testing.

## Installation

[![pytest-embedded](https://img.shields.io/pypi/v/pytest-embedded?color=green&label=pytest-embedded)](https://pypi.org/project/pytest-embedded/)
[![pytest-embedded-serial](https://img.shields.io/pypi/v/pytest-embedded-serial?color=green&label=pytest-embedded-serial)](https://pypi.org/project/pytest-embedded-serial/)
[![pytest-embedded-serial-esp](https://img.shields.io/pypi/v/pytest-embedded-serial-esp?color=green&label=pytest-embedded-serial-esp)](https://pypi.org/project/pytest-embedded-serial-esp/)
[![pytest-embedded-idf](https://img.shields.io/pypi/v/pytest-embedded-idf?color=green&label=pytest-embedded-idf)](https://pypi.org/project/pytest-embedded-idf/)
[![pytest-embedded-qemu](https://img.shields.io/pypi/v/pytest-embedded-qemu?color=green&label=pytest-embedded-qemu)](https://pypi.org/project/pytest-embedded-qemu/)
[![pytest-embedded-arduino](https://img.shields.io/pypi/v/pytest-embedded-arduino?color=green&label=pytest-embedded-arduino)](https://pypi.org/project/pytest-embedded-arduino/)
[![pytest-embedded-wokwi](https://img.shields.io/pypi/v/pytest-embedded-wokwi?color=green&label=pytest-embedded-wokwi)](https://pypi.org/project/pytest-embedded-wokwi/)
[![pytest-embedded-nuttx](https://img.shields.io/pypi/v/pytest-embedded-nuttx?color=green&label=pytest-embedded-nuttx)](https://pypi.org/project/pytest-embedded-nuttx/)

Packages under this repo mainly use semantic versioning. Sometimes a bug fix version may contain some non-breaking new features as well.

It is recommended to use `~=1.0` to get rid of breaking changes, and use the latest new features. For example,

```shell
pip install -U pytest-embedded~=1.0
```

## Quickstart

- `pip install -U pytest-embedded~=1.0`
- Create a file `test_basic.py`

```python
from pytest_embedded import Dut


def test_basic_expect(redirect, dut: Dut):
    with redirect():
        print('this would be redirected')

    dut.expect('this')
    dut.expect_exact('would')
    dut.expect('[be]{2}')
    dut.expect_exact('redirected')
```

- Run the test with `pytest`, the result would be like:

```shell
collected 1 item

test_basic.py .                                                        [100%]

============================= 1 passed in 0.01s =============================
```

- if run with `pytest -s`, the output would be as follows:

```shell
collected 1 item

test_basic.py 2022-01-01 12:34:56 this would be redirected
.

============================= 1 passed in 0.01s =============================
```

The `print` line is also duplicated to console output.

## Extra Services

You can activate more services with `pytest --embedded-services service[,service]` to enable extra fixtures and functionalities. These services are provided by several optional dependencies. You can install them via `pip` as well.

Available services:

- `serial`: serial port utilities.
- `esp`: auto-detect target/port by [esptool](https://github.com/espressif/esptool).
- `idf`: auto-detect more app info with [ESP-IDF](https://github.com/espressif/esp-idf) specific rules, auto-flash the binary into the target.
- `jtag`: openocd/gdb utilities
- `qemu`: running test cases on QEMU instead of the real target.
- `arduino`: auto-detect more app info with [arduino](https://github.com/arduino/Arduino) specific rules, auto-flash the binary into the target.
- `wokwi`: running test cases with [Wokwi](https://wokwi.com/) instead of the real target.
- `nuttx`: service for [nuttx](https://nuttx.apache.org/) project, optionally with espressif devices.

## Resources

- Documentation is hosted at [https://docs.espressif.com/projects/pytest-embedded/en/latest/](https://docs.espressif.com/projects/pytest-embedded/en/latest/)
- More examples under [examples](https://github.com/espressif/pytest-embedded/tree/main/examples)
