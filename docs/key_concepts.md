# Key Concepts

## Fixtures

Each test case would initialize a few fixtures. The most important fixtures are:

- `msg_queue`, a message queue. There's a background listener process to read all the messages from this queue, log them to the terminal with an optional timestamp, and record them to the pexpect process.
- `pexpect_proc`, a pexpect process, that could run `pexpect.expect()` for testing purposes.
- `app`, the built binary
- `dut`, Device Under Test (DUT)

    A DUT would contain several daemon processes/threads. The output of each of them would be redirected to the `msg_queue` fixture.

```{eval-rst}
.. note::

    You may redirect any output to the ``msg_queue`` fixture by ``contextlib.redirect_stdout``.

    .. code-block:: python

        import contextlib

        def test_redirect(dut, msg_queue):
            with contextlib.redirect_stdout(msg_queue):
                print('will be redirected')

            dut.expect_exact('redirected')

    Or you may redirect the output from a fixture `redirect`

    .. code-block:: python

        def test_redirect(dut, msg_queue, redirect):
            with redirect():
                print('will also be redirected')

            dut.expect_exact('redirected')

```

You can run `pytest --fixtures` to get all the fixtures defined with `pytest-embedded`. They are under the section `fixtures defined from pytest_embedded.plugin`.

## Parametrization

All the CLI options support parametrization via `indirect=True`. Parametrization is a feature provided by `pytest`, please refer to [Parametrizing tests](https://docs.pytest.org/en/latest/example/parametrize.html) for its documentation.

For example, running shell command `pytest` with the test script:

```python
@pytest.mark.parametrize(
    'embedded_services, app_path',
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

is equivalent to running two shell commands `pytest --embedded-services idf --app-path <app_path_1>` and `pytest --embedded-services idf --app-path <app_path_2>` with the test script:

```python
def test_serial_tcp(dut):
    assert dut.app.target == 'esp32'
    dut.expect('Restart now')
```

## Services

You can activate more services with `pytest --embedded-services service[,service]` to enable extra fixtures and functionalities. These services are provided by several optional dependencies. You can install them via `pip` as well.

Available services:

- `serial`: serial port utilities.
- `esp`: auto-detect target/port by [esptool](https://github.com/espressif/esptool).
- `idf`: auto-detect more app info with [ESP-IDF](https://github.com/espressif/esp-idf) specific rules, auto-flash the binary into the target.
- `jtag`: openocd/gdb utilities.
- `qemu`: running test cases on QEMU instead of the real target.
- `arduino`: auto-detect more app info with [arduino](https://github.com/arduino/Arduino) specific rules, auto-flash the binary into the target.
- `wokwi`: running test cases with [Wokwi](https://wokwi.com/) instead of the real target.

## Multi DUTs

Sometimes we need multi DUTs while testing, e.g., master-slave or mesh testing.

Here are a few examples of how to enable this. For detailed information, please refer to the `embedded` group of the `pytest --help`.

### Enable multi DUTs by specifying `--count`

After you enabled the multi-dut mode, all the fixtures would be a tuple with instances. Each instance inside the tuple would be independent. For parametrization, each configuration will use `|` as a separator for each instance.

For example, running shell command:

```shell
pytest \
--embedded-services serial|serial \
--count 2 \
--app-path <master_bin>|<slave_bin>
```

would enable 2 DUTs with `serial` service. `app` would be a tuple of 2 `App` instances, and `dut` would be a tuple of 2 `Dut` Instances.

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

```shell
pytest \
--embedded-services serial \
--count 2 \
--app-path <master_bin>|<slave_bin>
```

`--embedded-services serial` would apply to all DUTs

### Vacant Value if it's Useless

Sometimes one option is only useful when enabling specific services. You can set a vacant value if this config is only useful for certain DUTs.

```shell
pytest \
--embedded-services qemu|serial \
--count 2 \
--app-path <master_bin>|<slave_bin> \
--qemu-cli-args "<args>|" \
--port "|<port>"
```

`--qemu-cli-args` would apply to the first DUT with `qemu` service and `--port` would apply to the second DUT with `serial` service.

## Logging

`pytest-embedded` print all the DUT output with the timestamp. If you want to remove the timestamp, please run pytest with `pytest --with-timestamp n` to disable this feature.

By default, `pytest` would swallow the stdout. If you want to check the live output, please run pytest with `pytest -s`.
