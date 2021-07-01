# pytest-embedded

pytest embedded plugins

## Installation

All packages are published to pypi. Please install them with `pip`.

[![pytest-embedded](https://img.shields.io/pypi/v/pytest-embedded?color=green&label=pytest-embedded)](https://pypi.org/project/pytest-embedded/)
[![pytest-embedded-serial](https://img.shields.io/pypi/v/pytest-embedded-serial?color=green&label=pytest-embedded-serial)](https://pypi.org/project/pytest-embedded-serial/)
[![pytest-embedded-serial-esp](https://img.shields.io/pypi/v/pytest-embedded-serial-esp?color=green&label=pytest-embedded-serial-esp)](https://pypi.org/project/pytest-embedded-serial-esp/)
[![pytest-embedded-idf](https://img.shields.io/pypi/v/pytest-embedded-idf?color=green&label=pytest-embedded-idf)](https://pypi.org/project/pytest-embedded-idf/)
[![pytest-embedded-qemu-idf](https://img.shields.io/pypi/v/pytest-embedded-qemu-idf?color=green&label=pytest-embedded-qemu-idf)](https://pypi.org/project/pytest-embedded-qemu-idf/)

## API Reference

[![Documentation Status](https://readthedocs.com/projects/espressif-pytest-embedded/badge/?version=latest)](https://docs.espressif.com/projects/pytest-embedded/en/latest/?badge=latest)

## Contributing

If you're interested in contributing to this project, please take a look at the [CONTRIBUTING.md](./CONTRIBUTING.md)

## Functionalities Provided by Pytest

- [Live Logging](https://docs.pytest.org/en/stable/logging.html#live-logs)

  ```shell
  # For example
  pytest --log-cli-level=INFO
  ```

- [JUnit Report](https://docs.pytest.org/en/stable/usage.html#creating-junitxml-format-files)

  ```shell
  # For example
  pytest --junitxml=report.xml
  ```

- [Test Case Filter](https://docs.pytest.org/en/latest/example/markers.html#using-k-expr-to-select-tests-based-on-their-name)

  ```shell
  # For example
  pytest -k esp  # all test functions names include esp would be run
  ```

These configs can also be set in the `pytest.ini` file in your repo's root dir. For details, please refer to
the [pytest documentation](https://docs.pytest.org/en/6.2.x/customize.html). For examples, you can refer to the
pytest.ini in this repo.

## Limitations

### Plugin Autoload

In case we use dynamic-linking-like plugin load method, you need to set `export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` to
disable the plugin autoload if you've installed multi plugins which provide the same functions/options. Otherwise, the
behavior could be unexpected or will raise some exceptions.

### Fixtures Scope

Due to the limitation of pytest fixture `request`'s scope is `function`, all the fixtures that would use cli
arguments/options should set their scope also to `function`.
