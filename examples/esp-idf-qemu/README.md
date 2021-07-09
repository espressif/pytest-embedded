# ESP-IDF QEMU Examples

The example shows how 

## Prerequisites

1. Prepare QEMU program which supports xtensa, name it `qemu-system-xtensa` and add its parent directory into `$PATH`
2. Install following packages
    - `pytest_embedded`
    - `pytest_embedded_idf`
    - `pytest_embedded_qemu`
    - `esptool` (for sending commands to QEMU via socket)
3. run `idf.py build` under the apps you want to test

## Test Steps

```shell
$ pytest  # to run all tests
$ pytest -k test_serial_tcp  # to run only the `test_serial_tcp` test case
```

QEMU flash image would be created automatically if not exists
