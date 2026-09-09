######################
 Command-Line Options
######################

This page provides a complete reference for all command-line options supported by ``pytest-embedded`` and its service extensions.

You can also inspect these options from your terminal at any time by running:

.. code:: shell

   pytest --help

**************
 Core Options
**************

Options in the ``embedded`` group configure fundamental framework behaviors, multi-device topologies, and reporting.

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   -  -  Option
      -  Type
      -  Default
      -  Description

   -  -  ``--embedded-services``
      -  string
      -  ``""``
      -  Comma-separated list of services to activate (e.g. ``"serial"``, ``"esp,idf"``, ``"idf,qemu"``).

   -  -  ``--count``
      -  integer
      -  ``1``
      -  Number of DUTs required for multi-device test cases. When greater than 1, fixtures become tuples.

   -  -  ``--app-path``
      -  string
      -  ``None``
      -  Path to the application directory or binary file under test.

   -  -  ``--build-dir``
      -  string
      -  ``"build"``
      -  Name or relative path of the build directory inside ``--app-path``.

   -  -  ``--with-timestamp``
      -  bool (y/n)
      -  ``True``
      -  Enable or disable timestamp prefixes on live console log output.

   -  -  ``--logfile-extension``
      -  string
      -  ``".log"``
      -  File extension format for saved log files.

   -  -  ``--metric-path``
      -  string
      -  ``None``
      -  File path to save Prometheus/OpenMetrics text benchmarks recorded via ``log_metric``.

   -  -  ``--root-logdir``
      -  string
      -  temp dir
      -  Base directory where session log files are saved.

   -  -  ``--cache-dir``
      -  string
      -  temp dir
      -  Base directory for caching test metadata and binary hashes across tests.

   -  -  ``--parallel-count``
      -  integer
      -  ``1``
      -  Total number of parallel jobs when splitting the test suite in CI.

   -  -  ``--parallel-index``
      -  integer
      -  ``1``
      -  1-based index of the current parallel CI job.

   -  -  ``--check-duplicates``
      -  bool (y/n)
      -  ``False``
      -  Verify and reject duplicate test case or test script names.

   -  -  ``--prettify-junit-report``
      -  bool (y/n)
      -  ``False``
      -  Format and indent JUnit XML reports cleanly.

   -  -  ``--unity-test-report-mode``
      -  choice
      -  ``"replace"``
      -  Behavior for Unity test cases in the JUnit report: ``"replace"`` (default) or ``"merge"``.

****************
 Serial Options
****************

Options in the ``embedded-serial`` group configure physical UART serial connections.

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   -  -  Option
      -  Type
      -  Default
      -  Description

   -  -  ``--port``
      -  string
      -  ``None``
      -  Path to target serial port (e.g. ``/dev/ttyUSB0``, ``COM3``). Can be set via ``ESPPORT``.

   -  -  ``--port-location``
      -  string
      -  ``None``
      -  USB device location string (format: ``<bus>-<port>[-<port>]...``) to match dynamic ports.

   -  -  ``--baud``
      -  integer
      -  ``115200``
      -  Baud rate for serial communication with the target.

***********************
 Espressif SoC Options
***********************

Options in the ``embedded-esp`` group configure Espressif-specific target identification and flashing via ``esptool``.

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   -  -  Option
      -  Type
      -  Default
      -  Description

   -  -  ``--target``
      -  string
      -  ``"auto"``
      -  Target chip family (e.g. ``esp32``, ``esp32c3``, ``esp32s3``). Auto-detected if set to ``"auto"``.

   -  -  ``--beta-target``
      -  string
      -  same as target
      -  Chip type for beta target revisions.

   -  -  ``--flash-port``
      -  string
      -  ``None``
      -  Dedicated serial port for flashing if different from the monitoring port.

   -  -  ``--esptool-baud``
      -  integer
      -  ``921600``
      -  Baud rate used when flashing firmware via ``esptool``. Can be set via ``ESPBAUD``.

   -  -  ``--port-mac``
      -  string
      -  ``None``
      -  MAC address of the target board used to select the correct port among multiple boards.

   -  -  ``--port-serial-number``
      -  string
      -  ``None``
      -  Comma-separated list of USB serial numbers to filter available COM ports.

   -  -  ``--skip-autoflash``
      -  bool (y/n)
      -  ``False``
      -  Skip flashing the firmware binary onto the target chip before running the test.

   -  -  ``--erase-all``
      -  bool (y/n)
      -  ``False``
      -  Completely erase the target flash memory before flashing.

   -  -  ``--esp-flash-force``
      -  flag
      -  ``False``
      -  Pass force mode flag to ``esptool`` during flashing.

   -  -  ``--add-target-as-marker-with-amount``
      -  bool (y/n)
      -  ``False``
      -  Dynamically attach target chip name and device count as a test marker.

*****************
 ESP-IDF Options
*****************

Options in the ``embedded-idf`` group configure ESP-IDF build parsing, partition tables, and panic decoding.

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   -  -  Option
      -  Type
      -  Default
      -  Description

   -  -  ``--supported-targets``
      -  string
      -  ``None``
      -  Comma-separated list of officially supported target chips for the test suite.

   -  -  ``--preview-targets``
      -  string
      -  ``None``
      -  Comma-separated list of preview/experimental target chips for the test suite.

   -  -  ``--part-tool``
      -  string
      -  IDF default
      -  Path to the partition table generator script (``gen_esp32part.py``).

   -  -  ``--confirm-target-elf-sha256``
      -  bool (y/n)
      -  ``False``
      -  Verify the SHA256 of the flashed binary against the local ELF before skipping flashing.

   -  -  ``--erase-nvs``
      -  bool (y/n)
      -  ``False``
      -  Erase NVS partition blocks when flashing the target board.

   -  -  ``--skip-check-coredump``
      -  bool (y/n)
      -  ``False``
      -  Disable automatic panic trace decoding and flash/UART core dump checking on test failure.

************************
 JTAG & OpenOCD Options
************************

Options in the ``embedded-jtag`` group configure on-chip debugging with OpenOCD and GDB.

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   -  -  Option
      -  Type
      -  Default
      -  Description

   -  -  ``--openocd-prog-path``
      -  string
      -  ``"openocd"``
      -  Path to the OpenOCD executable.

   -  -  ``--openocd-cli-args``
      -  string
      -  ``"-f board/esp32-wrover-kit-3.3v.cfg"``
      -  Command-line arguments passed to OpenOCD.

   -  -  ``--gdb-prog-path``
      -  string
      -  ``"xtensa-esp32-elf-gdb"``
      -  Path to architecture-specific GDB executable.

   -  -  ``--gdb-cli-args``
      -  string
      -  ``"--quiet"``
      -  Command-line arguments passed to GDB.

   -  -  ``--no-gdb``
      -  bool (y/n)
      -  ``False``
      -  Skip creating a GDB instance when only OpenOCD is required.

**************
 QEMU Options
**************

Options in the ``embedded-qemu`` group configure virtual machine execution under QEMU.

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   -  -  Option
      -  Type
      -  Default
      -  Description

   -  -  ``--qemu-image-path``
      -  string
      -  ``"<app_path>/flash_image.bin"``
      -  Path to the bootable QEMU flash image.

   -  -  ``--qemu-prog-path``
      -  string
      -  ``"qemu-system-xtensa"``
      -  Path to the QEMU binary executable.

   -  -  ``--qemu-cli-args``
      -  string
      -  ``"-nographic -machine esp32"``
      -  Default base arguments for QEMU.

   -  -  ``--qemu-extra-args``
      -  string
      -  ``None``
      -  Additional CLI arguments appended to the QEMU invocation command.

   -  -  ``--qemu-efuse-path``
      -  string
      -  ``None``
      -  Path to a virtual eFuse data file.

   -  -  ``--skip-regenerate-image``
      -  bool (y/n)
      -  ``False``
      -  Skip rebuilding the QEMU flash image if one is already present.

   -  -  ``--encrypt``
      -  bool (y/n)
      -  ``False``
      -  Enable flash pre-encryption simulation workflow.

   -  -  ``--keyfile``
      -  string
      -  ``None``
      -  Key file used for the pre-encrypted flash workflow.

*****************
 esp-emu Options
*****************

Options in the ``embedded-espemu`` group configure lightweight ESP RISC-V SoC emulation.

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   -  -  Option
      -  Type
      -  Default
      -  Description

   -  -  ``--espemu-image-path``
      -  string
      -  merged bin path
      -  Path to an existing merged flash binary for ``esp-emu``.

   -  -  ``--espemu-prog-path``
      -  string
      -  ``"esp-emu"``
      -  Path to the ``esp-emu`` executable binary.

   -  -  ``--espemu-cli-args``
      -  string
      -  ``None``
      -  Base arguments passed to ``esp-emu``.

   -  -  ``--espemu-extra-args``
      -  string
      -  ``None``
      -  Extra arguments appended to the ``esp-emu`` command line.

*****************
 Arduino Options
*****************

Options in the ``embedded-arduino`` group configure Arduino sketch testing.

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   -  -  Option
      -  Type
      -  Default
      -  Description

   -  -  ``--no-fast-flash``
      -  bool (y/n)
      -  ``False``
      -  Disable fast differential flashing (``--diff-with``) and write the entire flash.

***************
 Wokwi Options
***************

Options in the ``embedded-wokwi`` group configure Wokwi web/API simulation.

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   -  -  Option
      -  Type
      -  Default
      -  Description

   -  -  ``--wokwi-diagram``
      -  string
      -  ``None``
      -  Path to a custom Wokwi diagram JSON file.

   -  -  ``--wokwi-usb-serial-jtag``
      -  bool (y/n)
      -  ``False``
      -  Use USB Serial JTAG interface instead of standard UART in the Wokwi diagram.
