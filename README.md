# pytest-embedded

pytest embedded plugins

## Installation

TO BE PUBLISHED ON PYPI

## API Reference

TO BE PUBLISHED ON READTHEDOCS

## Functionalities Provided by Pytest

- Live Logging (https://docs.pytest.org/en/stable/logging.html#live-logs)

  ```shell
  # For example
  pytest --log-cli-level=INFO
  ```

- JUnit Report (https://docs.pytest.org/en/stable/usage.html#creating-junitxml-format-files)

  ```shell
  # For example
  pytest --junitxml=report.xml
  ```

- Test Case
  Filter (https://docs.pytest.org/en/latest/example/markers.html#using-k-expr-to-select-tests-based-on-their-name)

  ```shell
  # For example
  pytest -k esp  # all test functions names include esp would be run
  ```

These configs can also be set in the `pytest.ini` file in your repo's root dir. For details, please refer to
the [pytest documentation](https://docs.pytest.org/en/6.2.x/customize.html). For examples, you can refer to the
pytest.ini in this repo.

## Feature List

### Base Functionalities

- [ ] timeout context manager (for some third-party lib doesn't provide timeout feature)
- [x] expect multi/single str/regex from the file descriptor
  - [x] use `pexpect` expect str/regex from the file descriptor
- [x] send output to file descriptor
- [ ] junit support
  - [ ] parse serial stdout to junit

### Plugin Features

- [ ] detect chip and port
  - [ ] jtag
  - [x] serial
- [ ] get binary path (project specific)
- [x] get partition table / sdkconfig
- [ ] load binary to device
  - [ ] jtag
  - [x] serial
- [ ] redirect the output to custom file descriptor
  - [x] pre-process (decode/annotate/encode) and redefine the file descriptor (optional, provided by plugins,
    project-specific)
  - [x] serial
  - [ ] jtag
- [ ] QEMU fixture
  - specify command line arguments used to launch QEMU
  - optional: fixture prepares flash image before running QEMU
  - pytest-embedded-serial DUT connects to the TCP port created by QEMU (`socket://localhost:3333`)
  - the fixture has some methods to control QEMU by sending commands to its monitor port.
  - if debugging is implemented (see below), GDB fixture connects to the remote port opened by QEMU (localhost:1234)
- [ ] debugging
  - [ ] jtag
  - [ ] openocd related (`py_debug_backend`, `telnetlib`)
  - [ ] gdb related (`py_debug_backend`, `pygdbmi`)
  - [ ] custom process context manager (`pexpect`)
- [ ] CI related (project-specific)
  - [ ] setting up rules parsing `module_name` to get app_path, config, target for CI
  - [ ] rename test case name, (for example we're using `<target>.<config>.<test_function_name>` in idf)
  - [ ] CI Env File Parsing (project-specific)
- [ ] log metrics (idf specific)
  - [ ] performance
  - [ ] binary size/heap size

### Other Protocol Related Features

- [x] http/https server (https://pypi.org/project/pytest-httpserver/)
- [ ] UDP
- [ ] TCP
- [ ] TLS/SSL
- [ ] modbus
- [ ] mqtt

## Contributing

### How to run tests for this project?

By default, all tests under all plugins would be run.

```shell
>>> pip install -r requirements.txt
>>> bash foreach.sh install
>>> export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
>>> # export DONT_SKIP_SERIAL_TESTS=1 (when you connected to an espressif board)
>>> # export DONT_SKIP_SERIAL_TESTS=1 (when qemu-system-xtensa is ready)
>>> pytest
```

### How to write tests with these plugins?

Basically we're following
the [official documentation](https://docs.pytest.org/en/stable/writing_plugins.html#testing-plugins). You could also
refer to the tests under each plugin.

## Limitations

### Plugin Autoload

In case we use dynamic-linking-like plugin load method, you need to set `export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` to
disable the plugin autoload if you've installed multi plugins which provide the same functions/options. Otherwise, the
behavior could be unexpected or will raise some exceptions.

### Fixtures Scope

Due to the limitation of pytest fixture `request`'s scope is `function`, all the fixtures that would use cli
arguments/options should set their scope also to `function`.
