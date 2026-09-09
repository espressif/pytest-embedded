### pytest-embedded-idf

A `pytest-embedded` service tailored for [ESP-IDF](https://github.com/espressif/esp-idf) applications and test workflows.

#### Service Activation

Activate this service by passing `idf` to `--embedded-services`. Typically used together with `esp` for physical hardware testing:

```shell
pytest --embedded-services esp,idf --app-path /path/to/esp-idf-app
```

#### Extra Functionalities

- **App Metadata Parsing**: Reads `project_description.json` and build artifacts to identify the target chip, flash settings, partition tables, and binary paths.
- **Smart Flashing & Caching**: Automatically flashes the bootloader, partition table, and application. Caches binary hashes across the session to skip redundant flashing.
- **Panic & Core Dump Decoding**: Automatically parses and decodes panic stack traces and core dumps from target flash/UART when a test fails.
- **Partition Table & NVS Controls**: Erase NVS blocks or customize the partition tool script.
- **Unity Test Runner**: Integrated support for Unity C test suites via `dut.expect_unity_test_output()` and the `case_tester` fixture for test menu navigation.
- **Linux Target Support**: Includes `LinuxDut` and `LinuxSerial` to test ESP-IDF POSIX/Linux applications directly on the host machine.
- **Dynamic Parametrization**: Provides `idf_parametrize` to expand `supported_targets` and filter chips by SoC capability strings.

#### CLI Options

- `--supported-targets`: Comma-separated list of officially supported targets for the test. Default: `None`.
- `--preview-targets`: Comma-separated list of preview/experimental targets for the test. Default: `None`.
- `--part-tool`: Path to the partition table generator script. Default: `$IDF_PATH/components/partition_table/gen_esp32part.py`.
- `--confirm-target-elf-sha256`: Verify ELF SHA256 against target flash before skipping re-flashing. Default: `False`.
- `--erase-nvs`: Erase NVS partition blocks when flashing binaries. Default: `False`.
- `--skip-check-coredump`: Skip auto-checking for core dumps and panic traces on test failure. Default: `False`.

#### Quick Example

```python
from pytest_embedded import Dut


def test_idf_app(dut: Dut):
    # App information is parsed automatically from the ESP-IDF build directory
    print(f'Running target: {dut.app.target}')
    dut.expect('Booting ESP-IDF app...')
    dut.expect('Hello world!')
```
