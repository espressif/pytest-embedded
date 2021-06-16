## v0.1.1 (2021-06-16)

### Feat

- **qemu**: move `qemu_cli_args` and `qemu_extra_args` from cli args to parametrize option
- **qemu**: check image_path exist or not and target chip type while running

### Fix

- **test**: remove local dir
- **idf**: add base dependency

## v0.1.0 (2021-06-11)

### Feat

- **qemu**: Move qemu to single fixture
- **base**: fixture `redirect` could have argument `source`
- **base**: add plugin `redirect` to duplicate and redirect `sys.stdout`
- duplicate stdout to file descriptor
- rename serial_dut/serial_esp to dut to keep consistency
- **qemu-idf**: add qemu-idf
- **idf**: make serial/esp dependencies optional
- move redirect stdout to pexpect process into a reusable decorator
- **idf**: simplify flash files, encrypt files parsing
- **serial_esp**: move esp related serial into a standalone plugin
- re-organize code. move esp related serial into embedded-serial-esp
- **print**: redirect esptool print to pexpect
- **idf**: move the flash specific code into idf plugin
- **serial**: move serial related into serial plugin
- **idf**: move idf related app into IDFApp
- **serial**: support flash by serial
- **base**: App support encrypt files
- **serial**: support pexpect from serial
- **base**: class App read target from sdkconfig file
- **base**: add App class
- update feature list after review
- writing feature list and some initial design
- rename to pytest-embedded
- re-organize the file structure
- use multi plugins to attach the method to the DUT class
- use dynamic import, but not nested plugins

### Fix

- **log**: fix the subprocess.popen issue while redirecting sys.stdout
- **ci**: fix pip install issue
- **ci**: run publish pypi on main branch
- small fixes about examples and type hint
- app_path would use test script path if not set
- **ci**: publish packages
- typing "list" not available before python 3.9
- **docs**: missing requirements
- **ci**: use pip install . to include less files
- **base**: remove redundant double quote in sdkconfig
