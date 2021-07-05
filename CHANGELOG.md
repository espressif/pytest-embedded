## v0.2.0 (2021-06-29)

### Feat

- **jtag**: add jtag support
- **log**: add LivePrintPopen custom Popen class
- **qemu**: `qemu_cli_args` and `qemu_extra_args` now can be set via cli and override via parameterization
- **serial**: make serial port could be overridden by parameterization

### Fix

- **log**: use rstrip instead of strip to keep the logs' indentation

## v0.1.1 (2021-06-16)

### Feat

- **qemu**: check image_path exist or not and target chip type while running
- **qemu**: move `qemu_cli_args` and `qemu_extra_args` from cli args to parametrize option

### Fix

- **idf**: add base dependency

## v0.1.0 (2021-06-11)

### Feat

- **base**: add App class
- **base**: add plugin `redirect` to duplicate and redirect `sys.stdout`
- **base**: App support encrypt files
- **base**: class App read target from sdkconfig file
- **base**: fixture `redirect` could have argument `source`
- **idf**: make serial/esp dependencies optional
- **idf**: move idf related app into IDFApp
- **idf**: move the flash specific code into idf plugin
- **idf**: simplify flash files, encrypt files parsing
- **print**: redirect esptool print to pexpect
- **qemu**: Move qemu to single fixture
- **qemu-idf**: add qemu-idf
- **serial**: move serial related into serial plugin
- **serial**: support flash by serial
- **serial**: support pexpect from serial
- **serial_esp**: move esp related serial into a standalone plugin
- duplicate stdout to file descriptor
- move redirect stdout to pexpect process into a reusable decorator
- re-organize code. move esp related serial into embedded-serial-esp
- rename serial_dut/serial_esp to dut to keep consistency
- rename to pytest-embedded
- update feature list after review
- use dynamic import, but not nested plugins
- use multi plugins to attach the method to the DUT class
- writing feature list and some initial design

### Fix

- **base**: remove redundant double quote in sdkconfig
- **log**: fix the subprocess.popen issue while redirecting sys.stdout
- app_path would use test script path if not set
- small fixes about examples and type hint
- typing "list" not available before python 3.9
