### pytest-embedded-espemu

A `pytest-embedded` service for running tests on [esp-emu](https://github.com/espressif/esp-emulator), Espressif's lightweight emulator for ESP RISC-V series SoCs, without real hardware.

Supported targets: `esp32c3`, `esp32c6`, `esp32h2`, `esp32p4`, `esp32s31`.

#### Service Activation

Activate this service by passing `espemu` to `--embedded-services`. Typically combined with `idf`:

```shell
pytest --embedded-services idf,espemu --target esp32c3 --app-path /path/to/app
```

#### Extra Functionalities

- **Automatic Merged Binary**: Automatically generates a merged flash binary from the build artifacts using `esptool merge-bin`.
- **Unity Test Support**: Fully supports Unity test menus and automated test cases from `pytest-embedded-idf`.
- **Fast Execution**: Lightweight software emulation running UART0 directly on standard I/O.

#### CLI Options

- `--espemu-image-path`: Path to an existing merged flash binary instead of generating one. Default: `<app_path>/<build_dir>/espemu_image.bin`.
- `--espemu-prog-path`: Path to the `esp-emu` executable. Default: `"esp-emu"`.
- `--espemu-cli-args`: Base arguments passed to `esp-emu`. Default: `None`.
- `--espemu-extra-args`: Extra arguments appended to the `esp-emu` command line (e.g. `--espemu-extra-args "--net user,restrict=yes"`). Default: `None`.

#### Quick Example

```python
from pytest_embedded import Dut


def test_espemu(dut: Dut):
    dut.expect('Hello from esp-emu!')
```
