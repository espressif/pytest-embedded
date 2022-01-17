# Key Concepts

## Fixtures

Each test case would initialize a few fixtures. The most important fixtures are:

- `pexpect_proc`, a pexpect process, that could run `pexpect.expect()` for testing purpose.
  
!!! note

    Each DUT would have a standalone pexpect process. in multi-DUT mode, they will not share their pexpect process.

- `app`, the built binary
- `dut`, a DUT test unit.

    A DUT would contain several daemon threads. The output of each thread would be redirected to `pexpect_proc` and 
    be printed with timestamp by default.

You can run `pytest --fixtures` to get all the fixtures defined with `pytest-embedded`.
They are under the section `fixtures defined from pytest_embedded.plugin`.

## Parametrizing

All the CLI options support parametrizing via `indirect=True`. Parametrizing is a feature provided by `pytest`,
please refer to [Parametrizing tests](https://docs.pytest.org/en/latest/example/parametrize.html) for its documentation.

To support multi DUT and parametrizing, we use string to represent bool value.
"y/yes/true" for `True` and "n/no/false" for `False`, case-insensitive.

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
## Services

You can activate more services with `pytest --embedded-services service[, service]` to enable extra fixtures and functionalities.
These services are provided by several optional dependencies. You can install them via `pip` as well.

Available services:

- `serial`: serial port utilities.
- `esp`: auto-detect target/port by [esptool](https://github.com/espressif/esptool).
- `idf`: auto-detect more app info with [ESP-IDF](https://github.com/espressif/esp-idf) specific rules, auto-flash the binary into the target.
- `jtag`: openocd/gdb utilities
- `qemu`: running test cases on QEMU instead of the real target.
- `arduino`: auto-detect more app info with [arduino](https://github.com/arduino/Arduino) specific rules, auto-flash the binary into the target.

## Multi DUTs

Sometimes we need multi DUTs while testing, e.g., master-slave or mesh testing.

Here are a few examples of how to enable this. For detailed information, please refer to the `embedded` group of the `pytest --help`.

### Enable multi DUTs by specifying `--count`

In this way, all the fixtures would be a tuple with instances. Each configuration will use `|` as a separator for each instance.

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

### Specify once when applying to all DUTs

If all DUTs share the same configuration value, you can specify only once.

!!! example
      
    ```shell
    pytest \
    --embedded-services serial \
    --count 2 \
    --app-path <master_bin>|<slave_bin> \
    ```

    `--embedded-services serial` would apply to all DUTs

### Vacant Value if it's Useless

Sometimes one option is only useful when enabling specific services. You can set a vacant value if this config is only useful for certain DUTs.

!!! example
      
    ```shell
    pytest \
    --embedded-services qemu|serial \
    --count 2 \
    --app-path <master_bin>|<slave_bin> \
    --qemu-cli-args "<args>|" \
    --port "|<port>" \
    ```
  
    `--qemu-cli-args` would apply to the first DUT with `qemu` service and `--port` would apply to the second DUT with `serial` service.

## Logging

`pytest-embedded` print all the DUT output with timestamp. If you want to remove the timestamp, please run pytest with
`pytest --with-timestamp n` to disable this feature.

By default, `pytest` would swallow the stdout. If you want to check the live output, please run pytest with `pytest -s`.

--8<-- "docs/abbr.md"
