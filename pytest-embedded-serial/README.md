### pytest-embedded-serial

pytest embedded service for testing via serial ports

Extra Functionalities:

- `serial`: enable the fixture
- `dut`: redirect the `serial` output to `pexpect_proc` and duplicate it with `logging.info()`.

Used CLI Options:

- `port`
