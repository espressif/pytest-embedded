# ESP-IDF Examples

## Prerequisites

### Connect to the target chips

### Plugins need to be installed

- pytest_embedded
- pytest_embedded_serial_esp
- pytest_embedded_idf

### build all the binaries you want to test

## Steps

To run all the tests: `pytest`

To run only hello world: `pytest -k hello_world`

target and port will be auto-detected, binary would be auto flashed in.
