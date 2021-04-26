# pytest-embedded

ESP pytest embedded plugin

## Fixtures

- app
- dut
- context managers
  - junit report writer
- module name
- test case name

All fixtures are with function scope by default, but we could provide different fixtures for different scope in order
to load binary to device only once for multiple test cases or other time-saving use cases.

For example:
- `dut` fixtures could be module scope if we put all the same test cases which need the same app into one test file
- `junit report writer` fixtures could be session scope to put all test cases into a single junit file

## Base Functionalities

- [ ] log utils
  - [ ] normal log utils to console/file
  - [ ] log performance
  - [ ] log binary size/heap size
- [ ] timeout context manager (for some third-party lib doesn't provide timeout feature)
- [ ] expect str/regex from stdout/stderr
- [ ] junit support
  - [ ] record test case into junit 
  - [ ] parse stdout to junit

## Plugin Features

- [ ] detect chip and port
  - [ ] jtag
  - [ ] serial
- [ ] get binary path (project specific)
- [ ] get partition table / sdkconfig
- [ ] load binary to device
  - [ ] jtag
  - [ ] serial
- [ ] run cmd on target
  - [ ] jtag
  - [ ] serial
- [ ] get stdout/stderr from target
  - [ ] jtag
  - [ ] serial
- [ ] send signal to port
- [ ] debugging
  - [ ] jtag
  - [ ] openocd related (`py_debug_backend`, `telnetlib`)
  - [ ] gdb related (`py_debug_backend`, `pygdbmi`)
  - [ ] custom process context manager (`pexpect`)

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
