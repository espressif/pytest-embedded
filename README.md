# pytest-embedded

ESP pytest embedded plugin

## Fixtures

- test_file_name (the test script file name)
- test_case_name (the test function name)
- app
- dut

All fixtures are with function scope by default, but we could provide different fixtures for different scope in order to
load binary to device only once for multiple test cases or other time-saving use cases.

For example:

- `dut` fixtures could be module scope if we put all the same test cases which need the same app into one test file

## Functionalities Provided by Pytest

- Live Logging (https://docs.pytest.org/en/stable/logging.html#live-logs)
- JUnit Report (https://docs.pytest.org/en/stable/usage.html#creating-junitxml-format-files)
- Test Case
  Filter (https://docs.pytest.org/en/latest/example/markers.html#using-k-expr-to-select-tests-based-on-their-name)

## Base Functionalities

- [ ] log metrics
  - [ ] performance
  - [ ] binary size/heap size
- [ ] timeout context manager (for some third-party lib doesn't provide timeout feature)
- [ ] expect multi/single str/regex from the file descriptor
  - [ ] use `pexpect` expect str/regex from the file descriptor
- [ ] junit support
  - [ ] parse serial stdout to junit

## Plugin Features

- [ ] detect chip and port
  - [ ] jtag
  - [ ] serial
- [ ] get binary path (project specific)
- [ ] get partition table / sdkconfig
- [ ] load binary to device
  - [ ] jtag
  - [ ] serial
- [ ] redirect the output to custom file descriptor
  - [ ] pre-process (decode/annotate/encode) and redefine the file descriptor (optional, provided by plugins,
    project-specific)
  - [ ] serial
  - [ ] jtag
- [ ] debugging
  - [ ] jtag
  - [ ] openocd related (`py_debug_backend`, `telnetlib`)
  - [ ] gdb related (`py_debug_backend`, `pygdbmi`)
  - [ ] custom process context manager (`pexpect`)
- [ ] CI related (project-specific)
  - [ ] setting up rules parsing `module_name` to get app_path, config, target for CI
  - [ ] rename test case name, (for example we're using `<target>.<config>.<test_function_name>` in idf)
  - [ ] CI Env File Parsing (yaml file example: https://gitlab.espressif.cn:6688/qa/ci-test-runner-configs/-/blob/master
    , project-specific)

## Other Protocal Related Features

- [ ] http/https
  - [ ] UDP
  - [ ] TCP
  - [ ] TLS/SSL
- [ ] modbus
- [ ] mqtt

## Limitation

In case we use dynamic-linking-like plugin load method, you need to set `export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` to
disable the plugin autoload. If not set, the behavior could be unexpected.
