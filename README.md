# pytest-embedded

A collection of pytest plugins for the embedded world.

## Installation

All packages are published to PyPI. Please install them with `pip`.

[![pytest-embedded](https://img.shields.io/pypi/v/pytest-embedded?color=green&label=pytest-embedded)](https://pypi.org/project/pytest-embedded/)
[![pytest-embedded-serial](https://img.shields.io/pypi/v/pytest-embedded-serial?color=green&label=pytest-embedded-serial)](https://pypi.org/project/pytest-embedded-serial/)
[![pytest-embedded-serial-esp](https://img.shields.io/pypi/v/pytest-embedded-serial-esp?color=green&label=pytest-embedded-serial-esp)](https://pypi.org/project/pytest-embedded-serial-esp/)
[![pytest-embedded-idf](https://img.shields.io/pypi/v/pytest-embedded-idf?color=green&label=pytest-embedded-idf)](https://pypi.org/project/pytest-embedded-idf/)
[![pytest-embedded-qemu](https://img.shields.io/pypi/v/pytest-embedded-qemu?color=green&label=pytest-embedded-qemu)](https://pypi.org/project/pytest-embedded-qemu/)

## Design Philosophy

### Fixtures

Each test case would initialize a few fixtures. The most important fixtures are:

- `pexpect_proc`, a pexpect process, which could run `pexpect.expect()` for testing purpose.
- `app`, the built binary
- `dut`, a "Device under test" (DUT) test unit.

  A DUT would contain several processes. The output of each process would be redirected to `pexpect_proc` and logged by `logging.info()`.

The fixtures of different plugins could have the same names. By this method, the fixtures of the latter activated plugin will override the fixtures with the same names which are already activated.

!!! warning

    **Limitations of the overriding technique**

    Since the fixtures with the same names could be overridden, you need to run `export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` and activate the plugin manually with `-p [PLUGIN_NAME]` when running `pytest`. We recommend using [configuration files](https://docs.pytest.org/en/stable/customize.html#configuration) to declare the plugin activate sequence.

    !!! example

    ```ini
    [pytest]
    addopts = -p pytest_embedded -p pytest_embedded_serial_esp -p pytest_embedded_idf
    ```

### Logging

Since all the output of each process would be duplicated with `logging.info()`, we recommend using pytest logging functionalities for the best user experience.

For the configuration of pytest logging, please refer to [pytest documentation: Live Logs](https://docs.pytest.org/en/stable/logging.html#live-logs)

Here's a simple example of a configuration file that logs to the console and the file simultaneously.

!!! example

    ```ini
    [pytest]
    log_cli = True
    log_cli_level = INFO
    log_cli_format = %(asctime)s %(levelname)s %(message)s
    log_cli_date_format = %Y-%m-%d %H:%M:%S

    log_file = test.log
    log_file_level = INFO
    log_file_format = %(asctime)s %(levelname)s %(message)s
    log_file_date_format = %Y-%m-%d %H:%M:%S
    ```

## API Reference

[![Documentation Status](https://readthedocs.com/projects/espressif-pytest-embedded/badge/?version=latest)](https://docs.espressif.com/projects/pytest-embedded/en/latest/?badge=latest)
