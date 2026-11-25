<a href="https://www.espressif.com">
    <img src="https://www.espressif.com/sites/all/themes/espressif/logo-black.svg" align="right" height="20" />
</a>

# CHANGELOG

> All notable changes to this project are documented in this file.
> This list is not exhaustive - only important changes, fixes, and new features in the code are reflected here.

<div style="text-align: center;">
    <a href="https://keepachangelog.com/en/1.1.0/">
        <img alt="Static Badge" src="https://img.shields.io/badge/Keep%20a%20Changelog-v1.1.0-salmon?logo=keepachangelog&logoColor=black&labelColor=white&link=https%3A%2F%2Fkeepachangelog.com%2Fen%2F1.1.0%2F">
    </a>
    <a href="https://www.conventionalcommits.org/en/v1.0.0/">
        <img alt="Static Badge" src="https://img.shields.io/badge/Conventional%20Commits-v1.0.0-pink?logo=conventionalcommits&logoColor=black&labelColor=white&link=https%3A%2F%2Fwww.conventionalcommits.org%2Fen%2Fv1.0.0%2F">
    </a>
    <a href="https://semver.org/spec/v2.0.0.html">
        <img alt="Static Badge" src="https://img.shields.io/badge/Semantic%20Versioning-v2.0.0-grey?logo=semanticrelease&logoColor=black&labelColor=white&link=https%3A%2F%2Fsemver.org%2Fspec%2Fv2.0.0.html">
    </a>
</div>
<hr>

## v2.10.2 (2026-11-25)

### ✨ New Features

- **espemu**: support esp32s3 *(Harshal Patil - 6bb7140)*


## v2.10.1 (2026-11-23)

### ✨ New Features

- **junit**: optionally make app_path relative to pytest root *(Fu Hanxi - 427b866)*


## v2.10.0 (2026-11-23)

### ✨ New Features

- **espemu**: add dut.serial with hard reset and flash erase and write *(harshal.patil - cf330dd)*
- **espemu**: support esp32c5 *(harshal.patil - 35dd791)*
- **espemu**: support eFuse images and flash encryption *(harshal.patil - 85bfcfc)*

### 🐛 Bug Fixes

- **serial-esp**: Try USB serial ports before ttyS *(Peter Dragun - 658f189)*
- **qemu**: resolve Arduino image from app binary *(Lucas Saavedra Vaz - ef3cf22)*
- **wokwi**: isolate generated diagrams by target *(Lucas Saavedra Vaz - 33cabd3)*

### 📖 Documentation

- updated by llm *(Fu Hanxi - 0bc4de5)*


## v2.9.3 (2026-08-31)

### 🐛 Bug Fixes

- let the unity_tester fixture accept emulator duts *(harshal.patil - 9054331)*


## v2.9.2 (2026-08-27)

### 🐛 Bug Fixes

- expose target on the emulator duts *(harshal.patil - e50f74d)*


## v2.9.1 (2026-08-26)

### 🐛 Bug Fixes

- incompatible with pytest-ignore-test-results plugin when child cases failed *(Fu Hanxi - 70033b9)*


## v2.9.0 (2026-08-25)

### ✨ New Features

- add pytest-embedded-espemu service for esp-emu *(Shubham Patil - 0c1aa94)*

### 🐛 Bug Fixes

- read the redirect log as bytes, not text *(Pavel Sokolov - abb390d)*
- arduino app check both .ino.merged.bin and .ino.bin *(Fu Hanxi - 4f4d713)*

### 📖 Documentation

- add espemu service to services page and API reference *(Shubham Patil - c0ef895)*


## v2.8.1 (2026-06-16)

### ✨ New Features

- **arduino**: Add support for fast flashing with esptool *(Lucas Saavedra Vaz - 7ef3196)*
- **wokwi**: Add support for using the USB Serial JTAG *(Lucas Saavedra Vaz - 5280180)*


## v2.8.0 (2026-05-15)

### ✨ New Features

- **wokwi**: Add support for custom chips *(Lucas Saavedra Vaz - cdcaa9b)*

### 🐛 Bug Fixes

- Add lock for simultaneous printing *(Lucas Saavedra Vaz - 5d225e6)*
- support linux target not generating flasher_args.json *(Jan Beran - 7a81a5d)*


## v2.7.0 (2026-03-02)

### ✨ New Features

- proper exception on invalid soc statement *(horw - 5f0641a)*

### 🐛 Bug Fixes

- **wokwi**: pass flash size while simulating *(Fu Hanxi - 0a7651e)*
- **wokwi**: support wokwi-client 0.4.0 *(Fu Hanxi - 6dbc86c)*
- reset when first met pre-run-failure *(Fu Hanxi - b131a09)*
- prevent multi-stage tests from passing when earlier stages fail *(Fu Hanxi - 7457ba1)*
- linux elf not found explicit error msg *(horw - b23b2bd)*


## v2.6.0 (2026-01-16)

### ✨ New Features

- support 'skip_decode_panic', split panic decode output and coredump output *(Fu Hanxi - db11168)*

### 🐛 Bug Fixes

- **idf**: panic decoding. Remove '--panic-output-decode-script' cli option *(Ivan Grokhotkov - 57e7954)*


## v2.5.0 (2025-12-19)

### ✨ New Features

- **wokwi**: C5 support + add wokwi to local packages *(Lucas Saavedra Vaz - bb0152a)*

### 🐛 Bug Fixes

- **readme**: Fix Arduino readme *(Lucas Saavedra Vaz - 70b3581)*

### 🏗️ Changes

- **arduino**: Rework arduino app *(Lucas Saavedra Vaz - dff48ba)*

---

## v2.4.0 (2025-11-12)

### ✨ New Features

- **arduino**: Add support for C2, C61 and fix deprecated commands *(Lucas Saavedra Vaz - c09d745)*

---

## v2.3.0 (2025-11-06)

### ✨ New Features

- support log_metric *(Fu Hanxi - fb9dbfa)*

### 📖 Documentation

- remove the 1.x changelog *(Fu Hanxi - 0c6edaf)*
- small fixes *(Fu Hanxi - e5d06e0)*

---

## v2.2.1 (2025-10-27)

### 🐛 Bug Fixes

- Raise exceptions for Dut created by DutFactory *(Evgeny Torbin - c73f684)*

---

## v2.2.0 (2025-10-24)

### ✨ New Features

- reconnect after serial lost connection *(horw - 019e38a)*

---

## v2.1.2 (2025-10-16)

### 🐛 Bug Fixes

- Fix ESP32-C5 bootloader offset *(Lucas Saavedra Vaz - b77e2f7)*

---

## v2.1.1 (2025-10-13)

### 🐛 Bug Fixes

- **qemu**: error when enable service `qemu` along without `idf` *(Fu Hanxi - 01efc71)*
- mark the un-triggered test cases as "skipped" *(Fu Hanxi - 1b0aa5c)*
- Add missing offsets for ESP32-C5 *(Lucas Saavedra Vaz - 54bc3d1)*

---

## v2.1.0 (2025-09-25)

### ✨ New Features

- add support for efuse in qemu *(horw - e682c45)*
- add support for virtual efuse on NuttX *(Filipe Cavalcanti - 5e946a0)*

---

## v2.0.0 (2025-09-23)

### 🔧 Code Refactoring

- always use multiprocess spawn *(Fu Hanxi - 387b877)*

### 🏗️ Changes

- rename esptool underscore arguments and subcommands to dash *(Fu Hanxi - b2b88d0)*

### Breaking Changes

- **Python Support**: Drop support for Python 3.7, 3.8, 3.9. Now requires Python 3.10+
- **esptool**: Update esptool requirement to >=5.1.dev1,<6 (from ~=4.9)
- **wokwi**: Remove support for `WokwiCLI` class, which is a wrapper of `wokwi-cli` executable. Use `Wokwi` class instead, which depends on `wokwi-python-client`, supporting a wide range of peripherals.
- **Deprecated Code Removal**:
  - Remove `EsptoolArgs` class from `pytest-embedded-serial-esp`
  - Remove deprecated parameters `hard_reset_after` and `no_stub` from `use_esptool()` decorator
  - Remove deprecated `stub` property from `EspSerial` class (use `esp` instead)
  - Remove deprecated `parse_test_menu()` and `parse_unity_menu_from_str()` methods from `IdfUnityDutMixin` (use `test_menu` property instead)
  - Remove deprecated CLI option `--add-target-as-marker` (use `--add-target-as-marker-with-amount` instead)

### Migration Guide

1. **Python Version**: Upgrade to Python 3.10 or higher
2. **esptool**: Update esptool to version 5.1.dev1 or higher (but less than 6.0)
3. **Code Changes**:
   - Replace `dut.stub` with `dut.esp`
   - Replace `dut.parse_test_menu()` calls with `dut.test_menu` property access
   - Replace `parse_unity_menu_from_str()` with `_parse_unity_menu_from_str()` if needed. `dut.test_menu` is preferred.
   - Update CLI usage from `--add-target-as-marker` to `--add-target-as-marker-with-amount`
   - Remove any usage of `EsptoolArgs` class
   - Remove `hard_reset_after` and `no_stub` parameters from `use_esptool()` calls

For the changelog of 1.x versions, please refer to the [1.x changelog](https://github.com/espressif/pytest-embedded/blob/release/v1.x/CHANGELOG.md).
