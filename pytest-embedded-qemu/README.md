### pytest-embedded-qemu

A `pytest-embedded` service for executing test cases in a [QEMU](https://www.qemu.org/) virtual machine without physical hardware.

#### Service Activation

Activate this service by passing `qemu` to `--embedded-services`. Typically paired with `idf`:

```shell
pytest --embedded-services idf,qemu --app-path /path/to/app
```

#### Extra Functionalities

- **Automatic Image Generation**: When used with `idf`, automatically merges binaries (bootloader, partition table, and app) into a single bootable QEMU flash image.
- **`qemu` Fixture**: Launches and supervises the QEMU process.
- **Flash Encryption Simulation**: Supports pre-encrypted flash images using a specified key file.
- **eFuse Support**: Allows specifying virtual eFuse states for chip feature simulation.

#### CLI Options

- `--qemu-image-path`: Path to the QEMU flash image binary. Default: `<app_path>/flash_image.bin`.
- `--qemu-prog-path`: Path to the QEMU executable. Default: `"qemu-system-xtensa"`.
- `--qemu-cli-args`: Base CLI options for QEMU. Default: `"-nographic -machine esp32"`.
- `--qemu-extra-args`: Extra arguments appended to the QEMU command line. Default: `None`.
- `--qemu-efuse-path`: Path to an eFuse file to simulate burn-in values. Default: `None`.
- `--skip-regenerate-image`: Skip recreating the flash image if one is already present. Default: `False`.
- `--encrypt`: Enable pre-encryption flash simulation workflow. Default: `False`.
- `--keyfile`: Path to the encryption key file for the pre-encrypted workflow. Default: `None`.

#### Quick Example

```python
from pytest_embedded import Dut


def test_qemu_execution(dut: Dut):
    # Runs entirely in QEMU software emulation
    dut.expect('Booting ESP-IDF app...')
    dut.expect('Hello world!')
```
