## v0.7.6 (2022-07-25)

### Fix

- raise exception only if dut `isinstance` `Dut` with failure cases
- record session_tempdir into `config.stash`

### Feat

- **esp**: add fixture `esptool_baud`
- **serial**: move fixture `baud` to service `serial`

## v0.7.5 (2022-07-11)

### Fix

- cli option "--erase-flash" conflict with function `erase_flash()`

## v0.7.4 (2022-07-11)

### Fix

- **idf**: use fixed major version instead of major.minor for esp-coredump
- **serial**: port occupied before init finished

### Feat

- **esp**: Add `--erase-flash` option to erase the flash before programming

## v0.7.3 (2022-06-06)

### Fix

- **esp**: fix esptool import

## v0.7.2 (2022-06-01)

### Fix

- **esp**: loose esptool version dependency. remove the upper limit

## v0.7.1 (2022-05-25)

### Feat

- **idf**: add cli option "--skip-check-coredump"

### Fix

- **idf**: make elf file detection optional

## v0.7.0 (2022-05-09)

### Feat

- **idf**: added erase_flash and erase_partition functionality

### Fix

- **idf**: KeyError when not enabled coredump related configs

## v0.7.0rc3 (2022-05-07)

### Fix

- **esp**: remove cryptography version limit
- **esp**: remove cryptography version limit

## v0.7.0rc2 (2022-05-07)

### Fix

- improve debug string
- **idf**: non-iterable error when flash with encrypted mode

## v0.7.0rc1 (2022-04-25)

### Feat

- add method `parse_multi_dut_args`

### Breaking Changes

- rename `apply_count_generator` to `multi_dut_generator_fixture`
- rename `apply_count` to `multi_dut_fixture`
- rename `parse_configuration` to `multi_dut_argument`

## v0.7.0rc0 (2022-04-15)

### Feat

- support 3.7+ python
- **idf**: add cli option "--erase-nvs"
- **idf**: parse coredump when teardown dut
- **idf**: use flasher_args.json to flash files. Require less files
- **serial**: add stop_redirect_thread method and disable_redirect_thread context manager

### Fix

- **esp**: fix requirements for rpi
- **serial**: use other serial type as well

## v0.6.2 (2022-03-18)

### Fix

- **esp**: stubbed loader can never read serial because of redirect_io_thread

### Feat

- add `expect_all` keyword for `expect` and `expect_exact` functions

## v0.6.1 (2022-03-18)

### Fix

- **esp**: esptool wrong boot mode issue
- **esp**: sort ports before auto detect port target

## v0.6.0 (2022-03-08)

## v0.6.0rc1 (2022-03-04)

### Fix

- `apply_count` for non-iterable items

### Feat

- **esp**: add `hard_reset` method

## v0.6.0rc0 (2022-02-22)

### Fix

- **jtag**: -gdb-set could pass multiple args
- **log**: flush to sys.stdout instantly
- **log**: multi-dut now would print source prefix
- unity case name now could include spaces
- would raise correctly when `expect` a list pattern failed

### Feat

- **esp**: add use_esptool decorator to auto connect before and hard reset after
- **esp**: cache port and target
- **idf**: add --confirm-target-elf-sha256 cli option
- **idf**: add `dump_flash` method in `IdfSerial`
- **idf**: add attr `bin_file` in IdfApp
- **idf**: add flashed elf related methods in `IdfSerial`
- **idf**: add IdfDut class
- **idf**: cache port and app
- cache port/target, port/app_path_build_dir if possible. use pytest 7.0 feature stash
- extract the binary_path to the `App` class
- log the log folders while setup for test case
- the logging.error would turn to be derived error
- use pytest>=7.0

## v0.5.1 (2022-01-21)

### Fix

- **serial**: write to pexpect process until '\n'

## v0.5.0 (2022-01-21)

### Feat

- **unity**: fail at the end if unity test case failed, try run more tests
- **unity**: set expect_unity_test_output timeout to 60s

## v0.5.0rc1 (2022-01-18)

### Feat

- **qemu**: default image path move to `APP_PATH/BUILD_DIR/IMAGE_NAME`
- add `Dut.expect_unity_test_output` method
- add fixture `test_case_tempdir`
- make import pytest-embedded easier
- show log file location when expect functions failed
- show pexpect process full log file location when expect function failed

### Fix

- **jtag**: use real file logging instead of pipe
- **qemu**: `dut.write` to qemu process correctly
- **qemu**: re-generate qemu image. add cli option "--skip-regenerate_image"
- **serial**: `dut.write()` could accept `str` data, auto add `\n` ending
- ensure use default value set in class if not specified in cli or param
- raise idf app not parsable error if binary path not parsable

### Breaking Changes

- **log**: thread-safe print instead of logging.info
- remove `expect_list`

## v0.5.0rc0 (2022-01-06)

### Feat

- **arduino**: Add Arduino service
- **esp**: simplify esptool call process
- **esp**: use env var `ESPPORT` for "--port" and `ESPBAUD` for "--baud"
- **esp**: use suggest flash baudrate if lower
- **log**: log buffer as error when no matched pattern while expecting
- **windows**: Add Windows support

### Fix

- **esp**: different dut will not use the same ports anymore
- **macos**: multiprocessing pickle error
- **windows**: make setup.py installable
- make the hook function to apply parallel count as the last step

### Breaking Changes

- **log**: remove `source` argument in all `DuplicatedStdout` related functions
- **qemu**: remove cli option `qemu-log-path`

## v0.4.5 (2021-11-29)

### Feat

- real-time logging
- add `expect_list` and `expect_exact` method to `DUT` class
- add parallel run cli options

### Fix

- **idf**: Run hard reset when skipping auto flash

## v0.4.4 (2021-11-18)

### Fix

- **qemu**: add the missing `build_dir` to the parent `IdfApp`
- use realpath instead

### Feat

- **base**: use the folder where `test_file_path` locates as the default `app_path`
- **idf**: replace parse binary config from sdkconfig to sdkconfig.json
- **idf**: add cli option "build_dir"

## v0.4.3 (2021-11-16)

### Feat

- return `re.Match` if `dut.expect()` succeeded
- **idf**: add option `--skip-autoflash`

## v0.4.2 (2021-10-25)

### Fix

- add version limit or armv71(rpi)

### Feat

- add dut count at the start of each line

## v0.4.1 (2021-08-26)

### Fix

- run close method only when initialized correctly
- correct the error message when service required package not installed
- pexpect process would echo the input, set echo to off

## v0.4.0 (2021-08-25)

### Fix

- create folder failed when specifying a file under current folder

### Feat

- add multi DUT support, use "count" option to duplicate fixtures
- use "embedded-services" option to extend functionalities instead of activating plugins.

## v0.3.2 (2021-08-12)

### Fix

- **jtag**: do not import idf package

## v0.3.1 (2021-07-09)

### Fix

- **idf**: optional dependency with `pytest-embedded-serial-esp` while import

## v0.3.0 (2021-07-06)

### Feat

- **qemu**: rename package to `pytest-embedded-qemu`, with optional dependency `pytest-embedded-idf`
- **jtag**: add dependency `pytest-embedded-serial`, remove optional requirements `pytest-embedded-serial-esp`
- **idf**: rename module `dut` to `serial`, override `serial` if satisfy the optional dependency
- **esp**: rename module `dut` to `serial`, override `serial` fixture
- **serial**: extract serial into a standalone fixture
- **base**: Add fixture `pexpect_proc`

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
