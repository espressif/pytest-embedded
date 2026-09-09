### pytest-embedded-nuttx

A `pytest-embedded` service for testing Apache [NuttX](https://nuttx.apache.org/) RTOS firmware on physical targets or in QEMU.

#### Service Activation

Activate this service by passing `nuttx` to `--embedded-services`. Combine with `serial` (and optionally `esp` for Espressif chips):

```shell
pytest --embedded-services serial,esp,nuttx --app-path /path/to/nuttx/build
```

Or run NuttX tests inside QEMU:

```shell
pytest --embedded-services qemu,nuttx --app-path /path/to/nuttx/build
```

#### Extra Functionalities

- **NuttX App Detection**: Scans the NuttX build directory for bootloader, partition table, and firmware ELF/binary files.
- **NuttShell (NSH) Interaction**: Seamlessly runs commands in NuttShell via the serial port and verifies command exit codes.
- **Flashing & Reset Support**: Leverages the `esp` service to automatically flash Espressif chips and trigger hardware resets.
- **Emulation Support**: Supports running NuttX binaries inside the QEMU emulator.

#### Quick Example

```python
from pytest_embedded import Dut


def test_nuttx_shell(dut: Dut):
    # Wait for the NuttShell prompt
    dut.expect('nsh>')
    dut.write('help\n')
    dut.expect('Builtin Apps:')
```
