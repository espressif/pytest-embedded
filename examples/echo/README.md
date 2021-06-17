# Basic DUT echo example

This example shows the basics of working with a DUT.

`dut` fixture in this example is provided by `pytest-embedded-serial` plugin. This fixture wraps a port implemented by `pyserial`. This is normally a serial port, however `pyserial` also supports TCP, RFC2217, loopback ports via [URL handlers](https://pyserial.readthedocs.io/en/latest/url_handlers.html).

In this example, `loopback://` port is used, which means that any data sent to teh DUT will be received back. The port is specified in [pytest.ini](pytest.ini).

You could also try this example with a real serial port (`--port /dev/ttyUSB0`), connecting RX and TX lines. The `--port` argument specified on the command line overrides the same argument from pytest.ini.

## Prerequisites

### Plugins need to be installed

- pytest_embedded
- pytest_embedded_serial

## Steps

Run `pytest` to execute the test defined in [test_echo.py](test_echo.py).

