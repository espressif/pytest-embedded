### pytest-embedded-serial

A `pytest-embedded` service for interacting with target hardware over serial (UART) ports.

#### Service Activation

Activate this service by passing `serial` to `--embedded-services`:

```shell
pytest --embedded-services serial --port /dev/ttyUSB0
```

#### Extra Functionalities

- **`serial` Fixture**: Provides a `Serial` object that manages port connection, reading, and writing.
- **`dut` Integration**: Automatically streams all incoming serial output to the `dut` and `pexpect_proc` fixtures for pattern matching.
- **Port Matching**: Select serial ports by device path or USB bus location.

#### CLI Options

- `--port`: Path to the serial port (e.g. `/dev/ttyUSB0`, `COM3`). Default: `None`.
- `--port-location`: USB device location string (format: `<bus>-<port>[-<port>]...`) to match dynamic port paths.
- `--baud`: Serial communication baud rate. Default: `115200`.

#### Quick Example

```python
from pytest_embedded import Dut


def test_serial_echo(dut: Dut):
    dut.write(b'ping\r\n')
    dut.expect('pong')
```
