# CHANGELOG

## v1.17.1 (2025-10-24)

### Fix

- mark the un-triggered test cases as "skipped"
- **qemu**: error when enable service `qemu` along without `idf`

## v1.17.0 (2025-09-08)

### Fix

- **qemu**: set `qemu_proj_path` for `QemuApp` correctly

### Feat

- add `--port-by-serial` option to filter ports by serial number

## v1.16.2 (2025-06-19)

### Fix

- synced cache file by adding support for filelock

## v1.16.1 (2025-04-22)

### Fix

- typing.Literal not working in python 3.7
- **nuttx**: use baudrate from EspSerial in EspNuttx
- **nuttx**:flash mode exception on Nuttx

## v1.16.0 (2025-03-13)

### Feat

- **idf**: Support selecting targets by soc caps in `idf_parametrize`

## v1.15.1 (2025-03-03)

### Fix

- **qemu**: limit RISCV flash image sizes to 2, 4, 8, 16MB

## v1.15.0 (2025-02-20)

### Feat

- **idf**: support pass `--supported_targets` and `preview_targets` as CLI args
- **idf**: support customisation for supported_targets and preview_targets by contextvar

## v1.14.0 (2025-02-11)

### Feat

- support marker helper function `idf_parametrize`

## v1.13.2 (2025-02-06)

### Fix

- app_path haven't recorded in python cases

## v1.13.1 (2025-01-29)

### Feat

- record `app_path` in junit reports
- support `return_what_before_match` in expect functions

### Fix

- improve listener performance, remove timeout in listener

## v1.13.0 (2025-01-21) (yanked)

### Feat

- support --add-target-as-marker-with-amount
- added skip_if_soc marker for idf target

### Fix

- **dut-factory**: Add a short delay in _listen() loop to prevent data missing

## v1.12.1 (2024-12-02)

### Feat

- **unity**: add flag to preserve Python test cases and "is_unity_case" attribute

### Fix

- **nuttx**: optional dependency for qemu
- **unity**: remove [dut-X] prefix from "line" and "file" attribute values in XML report

## v1.12.0 (2024-11-14)

### Feat

- **wokwi**: Use new boards for ESP32-P4
- **nuttx**: Support new service `nuttx`

## v1.11.8 (2024-10-29)

### Fix

- **wokwi**: Use merged bin to ensure partition and bootloader flashing

## v1.11.7 (2024-10-25)

### Fix

- **jtag**: bypass telnet sysaudit on python 3.7

## v1.11.6 (2024-10-18)

### Feat

- **arduino**: Support ESP32-P4

### Fix

- add more supported targets into App.RISCV32_TARGETS
- **qemu**: get default toolchain path correctly based on target
- **serial**: close serial port when exception happens

### Refactor

- **jtag**: remove deprecate warning from telnetlib.py by pulling telnetlib.py from python v3.12.6

## v1.11.5 (2024-08-19)

### Fix

- **wokwi**: pexpect.spawn not working on windows. use subprocess instead

## v1.11.4 (2024-08-16)

### Fix

- **jtag**: flush previous gdb responses before the first gdb command

## v1.11.3 (2024-08-09)

### Revert

- v1.11.2

## v1.11.2 (2024-08-09) (yanked)

### Fix

- **jtag**: gdb write "remotetimeout" stop waiting for response

## v1.11.1 (2024-08-07)

### Fix

- **jtag**: set gdb remote timeout to 10s by default

## v1.11.0 (2024-07-31)

### Feat

- **wokwi**: Add support for specifying diagram path
- **esp**: support flash with a different port

## v1.10.3 (2024-05-23)

### Feat

- dry run single board unity test
- flexible choices for run_all_single_board_cases

### Fix

- improve error message when CLI argument is wrong

## v1.10.2 (2024-04-30)

### Feat

- **esp**: support add target as marker ('|' will be escaped to '-')

### Fix

- **wokwi**: error when bin,elf file not under app_path

## v1.10.1 (2024-04-30)

### Fix

- **arduino**: stop require optional dependency 'esp'
- **qemu**: stop require optional dependency 'idf'

## v1.10.0 (2024-04-29)

### Feat

- **wokwi**: Add scenario path parameter

### Refactor

- **pytest8.2**: stash session_tempdir in a cleaner way
- **py3.12**: use datetime.now(timezone.utc) instead of utcnow()
- **py3.12**: use shutil.copytree instead of distutils

## v1.9.1 (2024-04-26)

### Fix

- remove required optional dependencies 'idf'

## v1.9.0 (2024-04-25) (yanked)

### Feat

- **wokwi**: Support Arduino
- Add `DutFactory` to create dut object inside the test functions

### Fix

- multiprocessing with context instead of set_start_method globally on macos

## v1.8.4 (2024-04-23)

### Fix

- non-standard default baud rate

## v1.8.3 (2024-04-09)

### Fix

- change baud when flash

## v1.8.2 (2024-04-02)

### Feat

- **idf**: support `flash` other IdfApp object

### Fix

- **unity**: change json files related log level from info to debug
- deprecate `use_esptool` args correctly
- wrong app.binary_path if app_path is different with cwd

## v1.8.1 (2024-03-01)

### Fix

- **idf**: check sdkconfig items while `erase_flash`

## v1.8.0 (2024-02-23)

### Feat

- support --esp-flash-force to run esptool.flash with the force flag

### Refactor

- call esptool.main() instead of implementing on our own

## v1.7.0 (2024-02-14)

### Feat

- **wokwi**: support for specifying simulation timeout
- support expect with `not_matching` keyword

## v1.6.4 (2024-01-22)

### Fix

- **unity**: avoid missing attr `message` in `failure` nodes

## v1.6.3 (2024-01-18)

### Fix

- **wokwi**: run in interactive mode

## v1.6.2 (2024-01-15)

### Feat

- **wokwi**: preliminary esp32p4 support

### Fix

- use socket bind to get allowed port

## v1.6.1 (2024-01-04)

### Fix

- **qemu**: fix qmp client missing event loop in main thread

## v1.6.0 (2024-01-02)

### Feat

- Support qemu qmp

### Fix

- **idf**: make LinuxDut inherit from IdfUnityDutMixin
- **unity**: remove extra time sleep inside multi-stage tests

## v1.5.0 (2023-12-29)

### Feat

- use gdb_panic_server from esp_idf_panic_decoder instead static $IDF_PATH/tools/gdb_panic_server.py

### Fix

- **unity**: make single board test procedure more robust

## v1.4.2 (2023-12-04)

### Feat

- **unity**: Support data transfer with signal in multi-dut unity test cases

### Fix

- added interrupt if one of the test was failed
- remove testcase name postfix

## v1.4.1 (2023-11-27)

### Refactor

- change threads to generator functions
- change logic of threading control in CaseTester for MultiDev

## v1.4.0 (2023-11-07)

### Feat

- **wokwi**: Support wokwi

### Fix

- clear all references for the message queue

## v1.3.5 (2023-09-13)

### Feat

- Support hard_reset without stub
- add local cache for port-target-cache between session

## v1.3.4 (2023-07-10)

### Fix

- **arduino**: separated flash settings for each target

## v1.3.3 (2023-07-05)

- **arduino**: Support target esp32h2 and esp32c6

## v1.3.2 (2023-06-14)

### Fix

- **qemu**: qemu-system-xtensa < 8.0.0 only support 4MB flash size
- **qemu**: calculate flash image size when "flash_size" not available
- **qemu**: qemu flash image generated by esptool, support windows as well

## v1.3.1 (2023-06-06)

### Fix

- **unity**: stop sleep 1 second in subcases
- confirm_write with pattern or string

## v1.3.0 (2023-05-31) (yanked)

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

- add log in system-out of the junit report

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
- **serial**: support rfc2217 connections

## v1.2.2 (2023-01-29)

### Fix

- teardown skipped when setting up period failed for multi-dut
- leaking file descriptors

## v1.2.1 (2023-01-05)

### Fix

- **idf**: `LinuxDut.write` failed since `serial` is `None`

## v1.2.0 (2022-12-29)

### Feat

- **idf**: support running tests on linux targets

### Fix

- ImportError when install `pytest_embedded` only

## v1.1.1 (2022-12-08)

### Fix

- **idf**: load_ram could use `flash_project_args` file as well

## v1.1.0 (2022-12-05)

### Feat

- add "--check-duplicates" cli option to check if there were duplicated test case names or test script names.
- **idf**: add `run_all_single_board_cases()` to `IdfDut`. This function would record duration time for each unity test case even it's unfinished.
- **idf**: add fixture `unity_tester` to test multi device unity test cases (beta)
- **jtag**: add cli option `--no-gdb` to stop create gdb instance automatically

### Fix

- **idf**: erase_all when hit the port-app cache cause no binary got flashed
- **idf**: set correct toolchain prefix for RISC-V targets
- **jtag**: initialize openocd/gdb processes earlier than app/serial

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

### Feat

- add fixture `msg_queue`
- add fixture `session_root_logdir` and cli option `--root-logdir`
- add fixture `dut_index` and `dut_total`
- add fixture `port_target_cache`, `port_app_cache`
- simplify import path by adding more object to `__all__`
- improve logging in `DuplicateStdoutPopen` instances
- `live_print_call` could accept kwargs `msg_queue` and `expect_returncode`
- **idf**: Support panic handler output for RISC-V targets
- **serial**: support bind ports by USB device location
- **esp**: `EspSerial.use_esptool` could accept kwargs `hard_reset_after` and `no_stub`
- **esp**: add `EsptoolArgs`
- **esp**: support bind ports by `esptool` `read_mac`
- **esp**: support loadable elf
- **jtag**: support flash via JTAG
- **jtag**: support loadable elf

### Fix

- remove `autouse=True` for fixture `session_tempdir`
- add micro second digits to `session_tempdir`
- make DuplicateStdoutPopen logs under `session_tmpdir`
- multi-dut \r\n messed-up the log
- **idf**: use empty list or dict for default values

### Refactor

- use multiprocessing.Process with Queue. Only `serial` instance redirect with `threading.Thread` instance.

### Breaking Changes

- `DuplicateStdoutPopen` and all subclasses
    - remove `create_forward_io_thread()`, the redirect process would be auto-created
    - rename `send()` to `write()` in order to keep the consistency with other classes
- remove `DuplicateStdout`. Now you may use `contextlib.redirect_stdout(msg_queue)` instead
- remove `DuplicateStdoutMixin`
- **esp**: Support `esptool>4.0` only
- **jtag**: remove `JtagDut`. use `SerialDut` or its subclasses instead

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

### Fix

- remove asci color code in expect failed exception

### Feat

- **idf**: add function to parse the case lists from unit test menu

## v0.7.7 (2022-07-26)

### Fix

- wrong xml detected when `_session_tempdir` stash is not initialized
- issue when fixture value is not str

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
