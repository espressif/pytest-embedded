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
3. cd into the app folder
4. run `idf.py build` under the apps you want to test

## Test Steps

```shell
$ pytest
```
