### pytest-embedded-serial-esp

A `pytest-embedded` service that extends `pytest-embedded-serial` with [esptool](https://github.com/espressif/esptool) integration for Espressif SoCs (ESP32 series).

#### Service Activation

Activate this service by passing `esp` to `--embedded-services`:

```shell
pytest --embedded-services esp --app-path /path/to/app
```

#### Extra Functionalities

- **Automatic Chip & Port Detection**: Uses `esptool` to query the connected chip and automatically detect the chip model (e.g. `esp32`, `esp32c3`, `esp32s3`) and available serial ports.
- **Device Filtering**: Disambiguate multiple connected development boards by MAC address or USB serial number.
- **Flashing Controls**: Configure flashing baud rate, force mode, full flash erasure, or separate flash and monitor ports.

#### CLI Options

- `--target`: Expected target chip type. Default: `"auto"`.
- `--beta-target`: Beta version target chip type. Default: same as `--target`.
- `--flash-port`: Dedicated serial port for flashing when separate from the monitoring port. Default: `None`.
- `--port-mac`: Expected MAC address of the target board. Default: `None`.
- `--port-serial-number`: Comma-separated list of USB serial numbers to filter available ports. Default: `None`.
- `--esptool-baud`: Baud rate used during flashing. Default: `921600` (or `ESPBAUD` environment variable).
- `--skip-autoflash`: Skip automatically flashing the binary to target flash. Default: `False`.
- `--erase-all`: Erase the entire flash chip before writing binaries. Default: `False`.
- `--esp-flash-force`: Force flashing mode in `esptool`. Default: `False`.
- `--add-target-as-marker-with-amount`: Attach target chip as a test marker. Default: `False`.

#### Quick Example

```python
from pytest_embedded import Dut


def test_chip_info(dut: Dut):
    print(f'Connected to target chip: {dut.app.target}')
    dut.expect('Hello world!')
```
