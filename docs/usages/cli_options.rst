######################
 Command-Line Options
######################

This page is a reference for all command-line options and ``pytest.ini`` settings provided by ``pytest-embedded`` and its service extensions.

You can also view all available options from your terminal:

.. code:: shell

   pytest --help

*****************************
 Option Syntax & Conventions
*****************************

Boolean Options vs. Flags
=========================

-  **``bool (y/n)``**: Takes an explicit value — ``y`` / ``yes`` / ``true`` for ``True``, or ``n`` / ``no`` / ``false`` for ``False`` (case-insensitive). For example: ``--skip-autoflash y`` or ``--with-timestamp=false``. Accepting an explicit string allows per-DUT ``|`` splitting and indirect parametrization.
-  **``flag``**: A standard boolean switch that takes no argument and defaults to ``False`` (e.g. ``--esp-flash-force``).

Multi-DUT Values (``|``)
========================

When ``--count`` is greater than ``1``, per-DUT options can be split with ``|`` (for example, ``--port /dev/ttyUSB0|/dev/ttyUSB1``).

-  A single value without ``|`` is applied to every DUT.
-  Leave a slot empty when an option applies only to specific DUTs (for example, ``--part-tool path/to/gen_esp32part.py|``).
-  Providing a different number of ``|``-separated values than ``--count`` raises a ``ValueError``.

See :doc:`../concepts/key-concepts` for full multi-DUT examples.

Parametrization
===============

Most per-DUT CLI options can be overridden per test using ``@pytest.mark.parametrize(..., indirect=True)`` with the option's underscored name (for example, ``app_path`` for ``--app-path`` or ``target`` for ``--target``). Values resolve in the following order:

#. Parametrized value on the test function
#. CLI option value
#. Option default

Service Option Groups
=====================

Options under each ``embedded-<service>`` group take effect when the corresponding service is activated via ``--embedded-services``.

**************
 Core Options
**************

Options in the ``embedded`` group (plus ``--unity-test-report-mode``) configure framework behavior, multi-device setups, parallel CI execution, logging, and JUnit reporting.

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
      -  Comma-separated list of services to activate. Available services: ``serial``, ``esp``, ``idf``, ``jtag``, ``qemu``, ``espemu``, ``arduino``, ``wokwi``, ``nuttx``. Example: ``"esp,idf"``.

   -  -  ``--count``
      -  integer (≥ 1)
      -  ``1``
      -  Number of DUTs in a single test case. When greater than ``1``, DUT-related fixtures become tuples.

   -  -  ``--app-path``
      -  string
      -  test file dir
      -  Path to the application directory or binary under test. Defaults to the directory containing the test script.

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
      -  File extension for saved DUT log files.

   -  -  ``--metric-path``
      -  string
      -  ``None``
      -  Path to an OpenMetrics / Prometheus text file for metrics recorded via the ``log_metric`` fixture.

   -  -  ``--root-logdir``
      -  string
      -  system temp dir
      -  Session-based root directory where DUT log files are stored.

   -  -  ``--cache-dir``
      -  string
      -  system temp dir
      -  Root directory for storing cache files (such as port-to-target mappings) across runs.

   -  -  ``--parallel-count``
      -  integer (≥ 1)
      -  ``1``
      -  Total number of parallel jobs when splitting a test suite in CI.

   -  -  ``--parallel-index``
      -  integer (≥ 1)
      -  ``1``
      -  1-based index of the current job out of ``--parallel-count``.

   -  -  ``--check-duplicates``
      -  bool (y/n)
      -  ``False``
      -  Fail collection if duplicate test case or test script names are detected.

   -  -  ``--prettify-junit-report``
      -  bool (y/n)
      -  ``False``
      -  Format and indent the generated JUnit XML report.

   -  -  ``--unity-test-report-mode``
      -  choice
      -  ``"replace"``
      -  How Unity test cases are written into the main JUnit XML report: ``"replace"`` substitutes the parent Python test case with the Unity cases; ``"merge"`` keeps both.

****************
 Serial Options
****************

Options in the ``embedded-serial`` group configure UART serial connections.

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
      -  Serial port path (for example, ``/dev/ttyUSB0`` or ``COM3``). Falls back to the ``ESPPORT`` environment variable when the ``esp`` service is enabled.

   -  -  ``--port-location``
      -  string
      -  ``None``
      -  USB device location string (``<bus>-<port>[-<port>]...``) used to match dynamic serial ports.

   -  -  ``--baud``
      -  integer
      -  ``115200``
      -  Baud rate for serial communication with the target.

***********************
 Espressif SoC Options
***********************

Options in the ``embedded-esp`` group configure Espressif target detection, port filtering, and flashing via ``esptool``.

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
      -  Target chip family (for example, ``esp32``, ``esp32c3``, ``esp32s3``). Auto-detected when set to ``"auto"``.

   -  -  ``--beta-target``
      -  string
      -  same as ``--target``
      -  Beta revision chip type for the serial target.

   -  -  ``--flash-port``
      -  string
      -  ``None``
      -  Dedicated serial port for flashing. Set only when the flashing port differs from ``--port``.

   -  -  ``--esptool-baud``
      -  integer
      -  ``921600``
      -  Flashing baud rate passed to ``esptool``. Falls back to the ``ESPBAUD`` environment variable when the ``esp`` service is enabled.

   -  -  ``--port-mac``
      -  string
      -  ``None``
      -  MAC address of the target board, used to select a specific board among multiple connected devices.

   -  -  ``--port-serial-number``
      -  string
      -  ``None``
      -  Comma-separated list of USB serial numbers to filter candidate serial ports.

   -  -  ``--skip-autoflash``
      -  bool (y/n)
      -  ``False``
      -  Disable automatic firmware flashing before running the test.

   -  -  ``--erase-all``
      -  bool (y/n)
      -  ``False``
      -  Erase the entire target flash before programming.

   -  -  ``--esp-flash-force``
      -  flag
      -  ``False``
      -  Pass force mode to ``esptool`` during flashing.

   -  -  ``--add-target-as-marker-with-amount``
      -  bool (y/n)
      -  ``False``
      -  Attach the ``target`` parameter and device count as a pytest marker (useful for CI runner tag matching). Parametrization is not supported; ``|`` is escaped as ``+``.

*****************
 ESP-IDF Options
*****************

Options in the ``embedded-idf`` group configure ESP-IDF target lists, partition table parsing, flash verification, and crash diagnostics.

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
      -  Comma-separated list of officially supported targets used by ``idf_parametrize``.

   -  -  ``--preview-targets``
      -  string
      -  ``None``
      -  Comma-separated list of preview/experimental targets used by ``idf_parametrize``.

   -  -  ``--part-tool``
      -  string
      -  ``"$IDF_PATH/components/partition_table/gen_esp32part.py"``
      -  Path to the ESP-IDF partition table tool used to parse partition tables.

   -  -  ``--confirm-target-elf-sha256``
      -  bool (y/n)
      -  ``False``
      -  Read the ELF SHA-256 from target flash and compare it against the local ELF in ``app.binary_path`` before allowing the session cache to skip auto-flashing.

   -  -  ``--erase-nvs``
      -  bool (y/n)
      -  ``False``
      -  Erase NVS partition blocks when flashing the target. Requires a valid ``--part-tool``.

   -  -  ``--skip-check-coredump``
      -  bool (y/n)
      -  ``False``
      -  Skip automatic UART/flash core dump checking and panic handler decoding during teardown of a failing test. Requires a valid ``--part-tool`` and ``project_description.json`` in the build directory.

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
      -  Path to the target-architecture GDB executable.

   -  -  ``--gdb-cli-args``
      -  string
      -  ``"--quiet"``
      -  Command-line arguments passed to GDB.

   -  -  ``--no-gdb``
      -  bool (y/n)
      -  ``False``
      -  Skip launching a GDB instance automatically when only OpenOCD is needed.

**************
 QEMU Options
**************

Options in the ``embedded-qemu`` group configure virtual target execution under QEMU.

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
      -  Path to the QEMU flash image.

   -  -  ``--qemu-prog-path``
      -  string
      -  ``"qemu-system-xtensa"``
      -  Path to the QEMU executable.

   -  -  ``--qemu-cli-args``
      -  string
      -  ``"-nographic -machine esp32"``
      -  Default base arguments passed to QEMU.

   -  -  ``--qemu-extra-args``
      -  string
      -  ``None``
      -  Additional arguments appended to the QEMU command line.

   -  -  ``--qemu-efuse-path``
      -  string
      -  ``None``
      -  Path to a virtual eFuse image file for QEMU simulation.

   -  -  ``--skip-regenerate-image``
      -  bool (y/n)
      -  ``False``
      -  Disable automatic regeneration of the QEMU flash image.

   -  -  ``--encrypt``
      -  bool (y/n)
      -  ``False``
      -  Enable the flash pre-encryption workflow.

   -  -  ``--keyfile``
      -  string
      -  ``None``
      -  Path to the flash encryption key file used with ``--encrypt``.

*****************
 esp-emu Options
*****************

Options in the ``embedded-espemu`` group configure lightweight Espressif SoC emulation with ``esp-emu``.

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   -  -  Option
      -  Type
      -  Default
      -  Description

   -  -  ``--espemu-image-path``
      -  string
      -  ``"<app_path>/<build_dir>/espemu_image.bin"``
      -  Path to the merged flash image for ``esp-emu``.

   -  -  ``--espemu-prog-path``
      -  string
      -  ``"esp-emu"``
      -  Path to the ``esp-emu`` executable.

   -  -  ``--espemu-cli-args``
      -  string
      -  ``None``
      -  Base arguments passed to ``esp-emu``.

   -  -  ``--espemu-efuse-path``
      -  string
      -  ``None``
      -  Path to an ``esp-emu`` eFuse image. Read on startup and written back on exit; a blank image is created if the file does not exist.

   -  -  ``--espemu-extra-args``
      -  string
      -  ``None``
      -  Additional arguments appended to the ``esp-emu`` command line.

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
      -  Disable fast differential reflashing (``--diff-with``) for Arduino targets. Useful when flash state is unknown, such as after OTA updates.

***************
 Wokwi Options
***************

Options in the ``embedded-wokwi`` group configure Wokwi simulation.

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
      -  Use the ``USB_SERIAL_JTAG`` interface instead of UART in the Wokwi diagram and remove ``$serialMonitor`` connections.

************************
 ``pytest.ini`` Options
************************

``pytest-embedded`` also registers configuration keys in ``pytest.ini`` (or ``pyproject.toml`` under ``[tool.pytest.ini_options]``).

.. list-table::
   :header-rows: 1
   :widths: 30 15 15 40

   -  -  Option
      -  Type
      -  Default
      -  Description

   -  -  ``junit_path_relative_to_root``
      -  bool
      -  ``false``
      -  Record JUnit ``app_path`` and Unity ``testcase`` source-file paths relative to pytest's ``rootdir`` when they point inside it.

   -  -  ``junit_app_path_relative_to_root``
      -  bool
      -  ``false``
      -  *Deprecated.* Alias for ``junit_path_relative_to_root``; will be removed in the 3.x release. Emits a ``PytestConfigWarning`` when set, and is ignored if ``junit_path_relative_to_root`` is also configured.

Example:

.. code:: ini

   [pytest]
   junit_path_relative_to_root = true

Behavior details:

-  Only absolute paths inside pytest's ``rootdir`` are converted to relative paths; paths outside ``rootdir`` and already-relative paths remain unchanged.
-  The ``app_path`` fixture itself still returns the original path.
-  For ESP-IDF compiler-generated paths starting with ``/IDF/``, set the ``IDF_PATH`` environment variable so they can be resolved against ``rootdir``.
