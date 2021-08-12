## pytest-embedded-serial

pytest embedded plugin for testing serial ports

### New Fixtures and Fixtures With More Functionalities

- `serial`: `Serial` instance
- `dut`: `SerialDut` instance, would redirect the `serial` output to `pexpect_proc` and duplicate it with `logging.info()`.

### CLI Options

- `port`: port (support parametrizing)
