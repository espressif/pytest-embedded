# ESP-IDF QEMU Examples

The example shows how to create idf app qemu flash image automatically and run this with qemu.

## Prerequisites

1. Prepare QEMU program which supports xtensa, name it `qemu-system-xtensa` and add its parent directory into `$PATH`
2. Install following packages
   - `pytest_embedded`
   - `pytest_embedded_idf`
   - `pytest_embedded_qemu`
   - `esptool` (for sending commands to QEMU via socket)
3. cd into the app folder
4. run `idf.py build` under the apps you want to test

## Test Steps

```shell
$ pytest
```

QEMU flash image would be created automatically if not exists
