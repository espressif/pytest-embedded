# ESP-IDF Examples

## Prerequisites

### QEMU program which supports xtensa

### Plugins need to be installed

- pytest_embedded
- pytest_embedded_idf
- pytest_embedded_qemu_idf

### build all the binaries you want to test

## Steps

To run all the tests: `pytest`

To run only tcp server test: `pytest -k tcp`

QEMU image would be created automatically if not exists

`qemu_cli_args` and `qemu_extra_args` could be passed through `pytest.mark.parameterize`
