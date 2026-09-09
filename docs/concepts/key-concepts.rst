##############
 Key Concepts
##############

This document explains the core architecture and fundamental concepts of ``pytest-embedded``.

**********
 Fixtures
**********

Each test case initializes several fixtures provided by ``pytest-embedded``:

-  ``dut``: Device Under Test. The central object representing your target device or emulator. It provides methods like ``dut.expect()``, ``dut.expect_exact()``, and ``dut.write()``, and attaches service objects (such as ``dut.serial`` or ``dut.openocd``).
-  ``app``: The built application. Contains parsed application metadata such as ``target``, ``app_path``, ``build_dir``, binary paths, and partition tables.
-  ``pexpect_proc``: The underlying ``PexpectProcess`` instance that performs pattern matching on logs read from the DUT.
-  ``msg_queue``: A multiprocessing message queue. A background thread reads all messages from this queue, prints them to the terminal with timestamps, and feeds them to ``pexpect_proc``.
-  ``redirect``: A context manager fixture to capture standard console output and send it into the DUT message queue.

.. note::

   You can redirect any Python stdout output to the DUT stream using the ``redirect`` fixture:

   .. code:: python

      def test_redirect(dut, redirect):
          with redirect():
              print("Sending simulated output")

          dut.expect_exact("Sending simulated output")

Run ``pytest --fixtures`` to see all fixtures available in your current environment.

***************
 DUT Lifecycle
***************

Every test case follows a predictable lifecycle:

#. **Service Assembly**: Resolves active services (from ``--embedded-services`` or fixture markers) and instantiates the proper ``App``, ``Serial``, and ``Dut`` classes.
#. **Flash & Cache**: Reads binary metadata. If hardware flashing is enabled, it flashes the target. A session cache remembers flashed binary hashes to avoid reflashing identical binaries in subsequent tests.
#. **Log Streaming**: Starts a background reader process to capture device UART output or emulator logs into ``msg_queue``.
#. **Test Execution**: The test runs assertions, sends inputs via ``dut.write()``, and verifies outputs via ``dut.expect()``.
#. **Teardown & Diagnostics**: On test completion or failure, ``pytest-embedded`` checks for panic messages or core dumps in target memory, decodes backtraces, terminates background processes, and releases serial ports.

*********************************
 Dynamic DUTs via ``DutFactory``
*********************************

In addition to test-scoped fixtures, you can dynamically create custom DUT instances inside a test using ``DutFactory``:

.. code:: python

   from pytest_embedded.dut_factory import DutFactory


   def test_dynamic_duts(dut):
       # dut is created automatically from pytest CLI arguments
       # Create an additional auxiliary DUT dynamically:
       aux_dut = DutFactory.create(embedded_services="serial", port="/dev/ttyUSB1")

       aux_dut.write(b"status\n")
       aux_dut.expect("OK")

*****************
 Parametrization
*****************

All CLI options support parametrization via ``indirect=True``. This lets you test multiple configurations, chips, or binaries in a single test run without multiple command executions.

For example:

.. code:: python

   import pytest


   @pytest.mark.parametrize(
       "embedded_services, app_path",
       [
           ("idf", "examples/app_v1"),
           ("idf", "examples/app_v2"),
       ],
       indirect=True,
   )
   def test_firmware_versions(dut):
       dut.expect("System initialized")

This is equivalent to running ``pytest`` twice with different ``--app-path`` values.

************
 Multi DUTs
************

Some test scenarios require multiple physical devices or emulators, such as master-slave communication, mesh networks, or gateway testing.

Enable Multi-DUT mode with ``--count <N>``
==========================================

When ``--count`` is greater than 1, fixtures such as ``dut`` and ``app`` become tuples of instances.

Use the pipe character (``|``) to provide distinct options for each DUT.

.. code:: shell

   pytest \
     --embedded-services serial|serial \
     --count 2 \
     --app-path path/to/master|path/to/slave \
     --port /dev/ttyUSB0|/dev/ttyUSB1

In your test function:

.. code:: python

   def test_master_slave(dut):
       master = dut[0]
       slave = dut[1]

       master.write(b"ping\n")
       slave.expect("received ping")

Single values apply to all DUTs
===============================

If an option is shared across all devices, specify it once without the ``|`` delimiter:

.. code:: shell

   pytest --embedded-services serial --count 2 --port /dev/ttyUSB0|/dev/ttyUSB1

Vacant values for specific DUTs
===============================

If an option applies only to one device in the setup, leave the other position empty:

.. code:: shell

   pytest \
     --embedded-services qemu|serial \
     --count 2 \
     --qemu-cli-args "<args>|" \
     --port "|/dev/ttyUSB0"

*******************************
 Parallel Test Execution in CI
*******************************

To speed up test runs across multiple CI workers, ``pytest-embedded`` provides built-in test suite splitting:

-  ``--parallel-count <N>``: Total number of parallel jobs.
-  ``--parallel-index <I>``: 1-based index of the current job.

For example, to split a test suite into 3 parallel jobs:

.. code:: shell

   # Worker 1
   pytest --parallel-count 3 --parallel-index 1

   # Worker 2
   pytest --parallel-count 3 --parallel-index 2

   # Worker 3
   pytest --parallel-count 3 --parallel-index 3

*********
 Logging
*********

-  **Live Output**: By default, pytest suppresses output from passing tests. Use the ``-s`` flag to see real-time DUT logs in your terminal.
-  **Timestamps**: Logs include timestamps by default. Use ``--with-timestamp n`` to disable timestamps.
-  **Custom Log Folder**: Set ``--root-logdir /path/to/logs`` to store full test logs in a specific folder.
-  **OpenMetrics**: Use ``--metric-path metrics.txt`` together with the ``log_metric`` fixture to export performance benchmarks in Prometheus format.
