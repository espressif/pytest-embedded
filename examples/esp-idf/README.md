# ESP-IDF Examples

This example shows:
1. how `pytest_embedded_serial_esp` auto-detect chip target and port
2. how `pytest_embedded_idf` auto flash the app into the target chip

## Prerequisites

1. Connect to the target chips
2. Install following packages
     - `pytest_embedded`
     - `pytest_embedded_serial_esp`
     - `pytest_embedded_idf`
3. run `idf.py build` under the apps you want to test

## Test Steps

```shell
$ export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1  # `pytest-embedded-serial-esp` is overriding `pytest-embedded-serial`
$ pytest --part-tool ./gen_esp32part.py  # to run all tests
$ pytest -k test_blink.py --part-tool ./gen_esp32part.py  # to run only blink tests
```
