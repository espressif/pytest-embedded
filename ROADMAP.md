# Roadmap

## Base Functionalities

- [ ] timeout context manager (for some third-party lib doesn't provide timeout feature)
- [x] expect multi/single str/regex from the file descriptor
  - [x] use `pexpect` expect str/regex from the file descriptor
- [x] send output to file descriptor
- [x] junit support
  - [x] parse serial stdout to junit

## Plugin Features

- [ ] detect chip and port
  - [ ] jtag
  - [x] serial
- [ ] get binary path (project specific)
- [x] get partition table / sdkconfig
- [x] load binary to device
  - [x] jtag
  - [x] serial
- [x] redirect the output to custom file descriptor
  - [x] pre-process (decode/annotate/encode) and redefine the file descriptor (optional, provided by plugins,
    project-specific)
  - [x] serial
  - [x] jtag
- [ ] QEMU fixture
  - [x] specify command line arguments used to launch QEMU
  - [x] optional: fixture prepares flash image before running QEMU (only for esp-idf project)
  - [x] pytest-embedded-serial DUT connects to the TCP port created by QEMU (`socket://localhost:3333`)
  - [ ] the fixture has some methods to control QEMU by sending commands to its monitor port.
  - [ ] if debugging is implemented (see below), GDB fixture connects to the remote port opened by QEMU (localhost:1234)
- [x] debugging
  - [x] jtag
  - [x] openocd related (`py_debug_backend`, `telnetlib`)
  - [x] gdb related (`py_debug_backend`, `pygdbmi`)
- [ ] CI related (project-specific)
  - [ ] setting up rules parsing `module_name` to get app_path, config, target for CI
  - [ ] rename test case name, (for example we're using `<target>.<config>.<test_function_name>` in idf)
  - [ ] CI Env File Parsing (project-specific)
- [ ] log metrics (idf specific) (structurized log?)
  - [ ] performance
  - [ ] binary size/heap size

## Other Protocol Related Features

- [x] http/https server (https://pypi.org/project/pytest-httpserver/)
- [ ] UDP
- [ ] TCP
- [ ] TLS/SSL
- [ ] modbus
- [ ] mqtt
