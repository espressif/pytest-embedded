### pytest-embedded-arduino

A `pytest-embedded` service for testing [Arduino](https://www.arduino.cc/) sketch builds on embedded targets.

#### Service Activation

Activate this service by passing `arduino` to `--embedded-services`. Typically combined with `esp` to enable flashing and serial monitoring:

```shell
pytest --embedded-services esp,arduino --app-path /path/to/arduino-build
```

#### Extra Functionalities

- **Sketch Metadata Parsing**: Automatically locates the compiled sketch binary, bootloader, and partition table from the Arduino build folder.
- **Fast Flashing**: Uses differential flashing (`--diff-with`) to only write updated flash sectors, significantly speeding up consecutive test runs.
- **Full Reflash Option**: Easily disable fast flashing with `--no-fast-flash` when the flash state is unknown (such as after OTA tests).

#### CLI Options

- `--no-fast-flash`: Disable fast differential flashing and write the complete flash image. Default: `False`.

#### Quick Example

```python
from pytest_embedded import Dut


def test_arduino_sketch(dut: Dut):
    dut.expect('Setup complete')
    dut.expect('Sensor read: ')
```
