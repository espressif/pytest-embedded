# pytest-embedded [![Documentation Status](https://readthedocs.com/projects/espressif-pytest-embedded/badge/?version=latest)](https://docs.espressif.com/projects/pytest-embedded/en/latest/?badge=latest)

A pytest plugin that has multiple services available for various functionalities. Designed for the embedded testing.

## Installation

All packages are published to PyPI. Please install them with `pip`.

[![pytest-embedded](https://img.shields.io/pypi/v/pytest-embedded?color=green&label=pytest-embedded)](https://pypi.org/project/pytest-embedded/)
[![pytest-embedded-serial](https://img.shields.io/pypi/v/pytest-embedded-serial?color=green&label=pytest-embedded-serial)](https://pypi.org/project/pytest-embedded-serial/)
[![pytest-embedded-serial-esp](https://img.shields.io/pypi/v/pytest-embedded-serial-esp?color=green&label=pytest-embedded-serial-esp)](https://pypi.org/project/pytest-embedded-serial-esp/)
[![pytest-embedded-idf](https://img.shields.io/pypi/v/pytest-embedded-idf?color=green&label=pytest-embedded-idf)](https://pypi.org/project/pytest-embedded-idf/)
[![pytest-embedded-qemu](https://img.shields.io/pypi/v/pytest-embedded-qemu?color=green&label=pytest-embedded-qemu)](https://pypi.org/project/pytest-embedded-qemu/)

## Design Philosophy

### Fixtures

Each test case would initialize a few fixtures. The most important fixtures are:

- `pexpect_proc`, a pexpect process, that could run `pexpect.expect()` for testing purpose.
- `app`, the built binary
- `dut`, a "Device under test" (DUT) test unit.

    A DUT would contain several processes. The output of each process would be redirected to `pexpect_proc` and logged by `logging.info()`.

### Services

Activate a service would enable a set of fixtures or add some extra functionalities to a few fixtures. You can activate comma-separated services by `pytest --embedded-services`. For detailed information, please refer to the `embedded` group of the `pytest --help`.

Available services:

- `serial`: serial port utilities.
- `esp`: auto-detect target/port by esptool.
- `idf`: auto-detect more app info with idf specific rules, auto-flash the binary into the target.
- `jtag`: openocd/gdb utilities
- `qemu`: running test cases on QEMU instead of the real target.

### Multi DUTs

Sometimes we need multi DUTs while testing, e.g., master-slave or mesh testing.

Here are a few examples of how to enable this. For detailed information, please refer to the `embedded` group of the `pytest --help`.

1. We can enable multi DUTs by specifying `--count`. In this way, all the fixtures would be a tuple with instances. Each configuration will use `|` as a separator for each instance.

    !!! example

        ```shell
        pytest \
        --embedded-services serial|serial \
        --count 2 \
        --app-path <master_bin>|<slave_bin>
        ```
  
        In this example, `app` would be a tuple of 2 `App` instances, `dut` would be a tuple of 2 `Dut` Instances.
  
        You can test with:
  
        ```python
        def test(dut):
            master = dut[0]
            slave = dut[1]
  
            master.expect('sent')
            slave.expect('received')
        ```

3. The configuration could have only one value when this value is applying to all DUTs.

    !!! example
  
        ```shell
        pytest \
        --embedded-services serial \
        --count 2 \
        --app-path <master_bin>|<slave_bin> \
        ```
  
        `--embedded-services serial` would apply to all DUTs

4. The configuration could be vacant if this value is only useful for certain DUTs.

    !!! example
  
        ```shell
        pytest \
        --embedded-services qemu|serial \
        --count 2 \
        --app-path <master_bin>|<slave_bin> \
        --qemu-cli-args "<args>|" \
        --port "|<port>" \
        ```
  
        `--qemu-cli-args` would apply to the first DUT and `--port` would apply to the second DUT.

### Parametrizing

All the CLI options support parametrizing via `indirect=True`. Parametrizing is a feature provided by `pytest`, please refer to [Parametrizing tests](https://docs.pytest.org/en/latest/example/parametrize.html) for its documentation.

In order to support multi DUT and parametrizing, we use string to represent bool value. "y/yes/true" for `True` and "n/no/false" for `False`, case-insensitive.

!!! example

    ```python
    @pytest.mark.parametrize(
        'embedded_service,app_path',
        [
            ('idf', app_path_1),
            ('idf', app_path_2),
        ],
        indirect=True,
    )
    def test_serial_tcp(dut):
        assert dut.app.target == 'esp32'
        dut.expect('Restart now')
    ```

### Logging

Since all the output of each process would be duplicated with `logging.info()`, we recommend using pytest logging functionalities for the best user experience.

For the configuration of pytest logging, please refer to [pytest documentation: Live Logs](https://docs.pytest.org/en/stable/logging.html#live-logs)

Here's a simple example of a configuration file that logs to the console and the file simultaneously.

!!! example

    ```ini
    [pytest]
    log_auto_indent = True

    log_cli = True
    log_cli_level = INFO
    log_cli_format = %(asctime)s %(levelname)s %(message)s
    log_cli_date_format = %Y-%m-%d %H:%M:%S

    log_file = test.log
    log_file_level = INFO
    log_file_format = %(asctime)s %(levelname)s %(message)s
    log_file_date_format = %Y-%m-%d %H:%M:%S
    ```

### Expecting

We support `expect`, `expect_exact`, and `expect_list` to assert if one string or pattern exists.

These three functions are supported via `pexpect` same name function, but the return value is slightly different in `pytest-embedded`.

!!! example

    ```python
    def test_something(dut, redirect, pexpect_proc):
        with redirect():
            print('foo bar baz qux')  # write "foo bar baz qux" to the buffer
    
        res = dut.expect('foo')
        # res = dut.expect('f[o]{2}')  # could be a pattern
        # res = dut.expect(re.compile(b'foo'))  # could be a compiled regex for bytes
    
        # `expect` would return a `re.Match` object if matched successfully
        # don't forget to decode, sync they're actually bytes in the buffer
        logging.info(f'The first word is [{res.group().decode("utf8")}]')
        # >>> The first word is [foo]
    
        # `expect_exact` would do a string compare, and return the matched bytes if matched successfully
        res = dut.expect_exact(['nonsense1', 'bar', 'nonsense2'])
        logging.info(f'The second word is [{res.decode("utf8")}]')
        # >>> The second word is [bar]
    
        # `expect_list` would use compiled regex as argument
        # please note that we should use bytes pattern here, since they are actually bytes in the buffer
        res = dut.expect_list([re.compile(b'nonsense1'), re.compile(b'baz'), re.compile(b'nonsense2')])
        logging.info(f'The third word is [{res.group().decode("utf8")}]')
        # >>> The third word is [baz]
    
        # `expect` a `pexpect.EOF` would get all the remaining buffers
        pexpect_proc.terminate()  # to terminate the pexpect process and generate an EOF
        res = dut.expect(pexpect.EOF, timeout=None)
        logging.info(f'The forth word is [{res.decode("utf8")}], with an extra space')
        # >>> The forth word is [ qux], with an extra space
    ```
