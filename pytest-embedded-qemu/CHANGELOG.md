## v1.3.0 (2023-05-31)

### Feat

- **idf**: `IdfApp` add new property `is_xtensa`, `is_riscv32`
- **idf**: add `confirm_write` method to make sure the write happens
- **idf**: add `run_single_board_case` function
- **idf**: expose pytest_embedded_idf.UnittestMenuCase
- **qemu**: support flash encryption workflow
- **qemu**: support riscv32 targets, remove target restriction

### Fix

- **qemu**: Add more idf non-target related functions when enabling service `idf`

## v1.2.5 (2023-04-11)

### Feat

- add log in system-out

### Fix

- **idf**: lazy import optional dependencies
- **idf**: skip decode panic output when no elf file

## v1.2.4 (2023-03-10)

### Feat

- **idf**: support loadable app with bin file

### Fix

- illegal xml chars for all types of test cases
- remove 1.1 added unused argument `start_time`

### Refactor

- improve logging and use "shell=False" in `DuplicateStdoutPopen`
- refine errors and warnings

## v1.2.3 (2023-02-06)

### Fix

- illegal xml chars
- support rfc2217 connections

## v1.2.2 (2023-01-29)

### Fix

- teardown skipped when setting up period failed for multi-dut
- leaking file descriptors

## v1.2.1 (2023-01-05)

### Fix

- **idf**: `LinuxDut.write` failed since `serial` is `None`

## v1.2.0 (2022-12-29)

### Feat

- support running tests on linux targets

### Fix

- ImportError when install `pytest_embedded` only

## v1.1.1 (2022-12-08)

### Fix

- **idf**: load_ram could use `flash_project_args` file as well

## v1.1.0 (2022-12-05)

### Feat

- **idf**: add fixture `unity_tester` to test multi device unity test cases (beta)
- add "--check-duplicates" cli option
- **idf**: add `run_all_single_board_cases()` to `IdfDut`
- Added tests for testcase runner. Added unity test execution time into JUnit report
- add a script for supporting multi-dev and multi-stage case from idf to pytest embedded
- **jtag**: add cli option `--no-gdb` to stop create gdb instance automatically

### Fix

- **idf**: erase_all when hit the port-app cache cause no binary got flashed
- **idf**: set correct toolchain prefix for RISC-V targets
- Added test case name uniqueness validation
- create openocd/gdb processes earlier than app/serial

## v1.0.2 (2022-11-07)

### Fix

- **jtag**: stop redirecting openocd output to pexpect process
- **esp**: drop port-app cache when `erase_flash`
- **esp**: erase flash before `flash` when set `--erase-all`

### Refactor

- rewrite set/drop/hit cache code

## v1.0.1 (2022-10-28)

### Feat

- support set file extension of the log file

### Fix

- `_meta.logdir` should be the `test_case_tempdir`, change to function-scope
- remove unused cli option "--reorder-by-app-path"

## v1.0.0 (2022-10-20)

### Fix

- **idf**: use empty list or dict for default values
- **serial**: improve logging when _event_loop run into unknown error

## v1.0.0b3 (2022-10-20)

### Fix

- **serial**: use thread for serial

## v1.0.0b2 (2022-10-18)

### Fix

- multi-dut \r\n messed-up the log
- **serial**: event loop with interval seconds
- **esp**: add missing redirect lines
- **esp**: `hard_reset` not working

## v1.0.0b1 (2022-10-14)

### Feat

- make DuplicateStdoutPopen logs under `session_tmpdir`

### Fix

- improve teardown logic
- **jtag**: `openocd` instance redirect stdout to pexpect proc

## v1.0.0b0 (2022-10-13)

### Feat

- add fixture `port_target_cache`, `port_app_cache`

### Fix

- add micro second digits to `session_tempdir`
- revert the breaking change to rename `dut.pexpect_proc` to `dut._p`

## v1.0.0a2 (2022-10-12)

### Feat

- **esp**: support bind ports by esptool read_mac
- Added support for binding ports based on the USB device location
- **esp**: support loadable elf
- **esp**: add `EsptoolArgs` to `EspSerial`
- **esp**: `use_esptool` new argument `hard_reset_after` and `no_stub`
- `live_print_call` could accept kwargs `msg_queue` and `expect_returncode`
- **jtag**: support loadable elf
- blocking io gdb write
- **jtag**: flash via JTAG accept port-app-cache
- improve logging in popen objects
- **jtag**: flash via JTAG
- add fixture dut_index and dut_total

### Fix

- **serial**: remove occupied ports from the list of available ports
- **qemu**: wrong init args
- kill processes generated inside popen afterwards

### Refactor

- **jtag**: remove `JtagDut`. use `SerialDut` or its subclasses instead
- **serial**: rename `start_redirect_serial_process` to `start_redirect_process`

## v1.0.0a1 (2022-09-22)

### Fix

- **serial**: event loop for interacting with `serial.proc`

## v1.0.0a0 (2022-09-20)

### Feat

- **esp**: Support esptool>4.0 only
- add fixture `session_root_logdir` and cli option `--root-logdir`
- added panic handler support

### Fix

- **serial**: skip creating a new one if exists when `start_redirect_serial_process`
- **esp**: file stream keep open when exception is raised
- remove `autouse` for fixture `session_tempdir`

### Refactor

- use multiprocessing.Process with Queue

## v0.8.2 (2022-08-23)

### Fix

- **esp**: UnboundLocalError when specify beta_target and port together

## v0.8.1 (2022-08-22)

### Fix

- parse error when unity test case name with colon

## v0.8.0 (2022-08-22)

### Feat

- **esp**: support `beta_target`

### Fix

- **idf**: parse_unity_menu subcases index to int

## v0.7.10 (2022-08-04)

### Fix

- multi dut with single junit report

## v0.7.9 (2022-08-02)

### Fix

- merge junit report error when multi-dut

## v0.7.8 (2022-07-28)

### Feat

- **idf**: add function to parse case list from unit test menu

### Fix

- remove asci color code in logging

## v0.7.7 (2022-07-26)

### Fix

- wrong xml detected when `_session_tempdir` stash is not initialized
- issue when fixture value is not str

## v0.7.6 (2022-07-25)

### Feat

- **esp**: add fixture `esptool_baud`
- **serial**: move fixture `baud` to service `serial`

### Fix

- record session_tempdir into config.stash

## v0.7.5 (2022-07-11)

### Fix

- cli option "--erase-flash" conflict with function `erase_flash()`

## v0.7.4 (2022-07-11)

### Fix

- use fixed major version instead of major.minor
- port occupied before init finished

## v0.7.3 (2022-06-06)

## v0.7.2 (2022-06-01)

### Fix

- loose esptool version dependency. remove the upper limit

## v0.7.1 (2022-05-25)

### Feat

- **idf**: add cli option "--skip-check-coredump"

### Fix

- **idf**: make elf file detection optional

## v0.7.0 (2022-05-09)

### Fix

- **idf**: KeyError when not enabled coredump related configs

## v0.7.0rc3 (2022-05-07)

### Fix

- **esp**: remove cryptography version limit

## v0.7.0rc2 (2022-05-07)

### Fix

- improve debug string
- **idf**: flash with non-iterable empty files

## v0.7.0rc1 (2022-04-25)

### Feat

- extract method `parse_multi_dut_args`

## v0.7.0rc0 (2022-04-15)

### Feat

- support 3.7+ python
- **idf**: parse coredump when teardown dut
- **serial**: add stop_redirect_thread method and disable_redirect_thread context manager
- **idf**: add cli option "--erase-nvs"
- **idf**: use flasher_args.json to flash files. Require less files

### Fix

- **esp**: fix requirements for rpi
- **serial**: use other serial type as well

## v0.6.2 (2022-03-18)

### Feat

- add `expect_all` keyword for `expect` and `expect_exact` functions

### Fix

- **esp**: stubbed loader can never read serial because of redirect_io_thread

## v0.6.1 (2022-03-18)

### Fix

- **esp**: esptool wrong boot mode issue
- use typing.Pattern instead of re.Pattern
- **esp**: sort ports before auto detect port target

## v0.6.0 (2022-03-08)

## v0.6.0rc1 (2022-03-04)

### Feat

- **esp**: add `hard_reset` method

### Fix

- `apply_count` for non-iterable items

## v0.6.0rc0 (2022-02-22)

### Feat

- **idf**: add --confirm-target-elf-sha256 cli option
- **idf**: cache port and app
- **esp**: cache port and target
- use pytest>=7.0
- extract the binary_path to the `App` class
- cache port/target, port/app_path_build_dir if possible. use pytest 7.0 feature stash
- **idf**: add flashed elf related methods in `IdfSerial`
- **idf**: add attr `bin_file` in IdfApp
- log the log folders while setup for test case
- **idf**: add `dump_flash` method in `IdfSerial`
- **idf**: add IdfDut class
- **esp**: add use_esptool decorator to auto connect before and hard reset after
- the logging.error would turn to be derived error

### Fix

- unity case name now could include spaces
- would raise correctly when `expect` a list pattern failed
- **jtag**: -gdb-set could pass multiple args
- **log**: multi-dut now would print source prefix
- **log**: flush to sys.stdout instantly

### Refactor

- add function _request_param_or_config_option_or_default for fixtures

## v0.5.1 (2022-01-21)

### Fix

- **serial**: write to pexpect process until '\n'

## v0.5.0 (2022-01-21)

### Feat

- fail at the end if unity test case failed, try run more tests
- set expect_unity_test_output timeout to 60s

## v0.5.0rc1 (2022-01-18)

### Feat

- **unity**: add argument `extra_before` to `expect_unity_test_output`
- **qemu**: default image path move to `APP_PATH/BUILD_DIR/IMAGE_NAME`
- **log**: thread-safe print instead of logging.info
- remove `expect_list`
- add `Dut.expect_unity_test_output` method
- make import pytest-embedded easier
- show log file location when expect functions failed
- add fixture `test_case_tempdir`

### Fix

- raise idf app not parsable error if binary path not parsable
- **qemu**: re-generate qemu image. add cli option "--skip-regenerate_image"
- **jtag**: use real file logging instead of pipe
- ensure use default value set in class if not specified in cli or param
- **qemu**: `dut.write` to qemu process correctly
- **serial**: `dut.write()` could accept `str` data, auto add `\n` ending

## v0.5.0rc0 (2022-01-06)

### Feat

- **qemu**: remove cli option `qemu-log-path`
- **log**: log buffer as error when no matched pattern while expecting
- **log**: remove `source` argument in all `DuplicatedStdout` related functions
- Add Arduino service.
- **esp**: use suggest flash baudrate if lower
- support windows by using real file and fdspawn
- **esp**: use env var `ESPPORT` for "--port" and `ESPBAUD` for "--baud"
- **esp**: simplify esptool call process

### Fix

- setup.py regex issue with prerelease version
- **esp**: different dut will not use the same ports anymore
- make setup.py installable on windows
- multiprocessing pickle error on macos
- make the hook function to apply parallel count as the last step

### Refactor

- Move skip_autoflash to EspSerial.
- Move "build_dir" option to the base group since it's also used by other apps.
- replace multiprocessing with thread
- make `pexpect_proc` as required for most of the classes

## v0.4.5 (2021-11-29)

### Feat

- real-time logging
- add `expect_list` and `expect_exact`
- add parallel run cli options

### Fix

- hard reset when skipping auto flash

## v0.4.4 (2021-11-18)

### Feat

- **base**: use the folder where `test_file_path` locates as the default `app_path`
- **idf**: replace parse binary config from sdkconfig to sdkconfig.json
- **idf**: add cli option "build_dir"

### Fix

- **qemu**: add the missing `build_dir` to the parent `IdfApp`
- use realpath instead

## v0.4.3 (2021-11-16)

### Feat

- return `re.Match` if `dut.expect()` succeeded
- **idf**: add option `--skip-autoflash`

## v0.4.2 (2021-10-25)

### Feat

- add dut count at the start of each line

### Fix

- add version limit or armv71(rpi)

## v0.4.1 (2021-08-26)

### Fix

- run close method only when initialized correctly
- correct the error message when service required package not installed
- pexpect process would echo the input, set echo to off

## v0.4.0 (2021-08-25)

### Feat

- add multi DUT support, use "count" option to duplicate fixtures
- use "embedded-services" option to extend functionalities instead of activating plugins.

### Fix

- create folder failed when specifying a file under current folder

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
- **serial**: make serial port could be overridden by parameterization
- **qemu**: `qemu_cli_args` and `qemu_extra_args` now can be set via cli and override via parameterization

### Fix

- **log**: use rstrip instead of strip to keep the logs' indentation

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
