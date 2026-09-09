#############################
 Helper Functions & Fixtures
#############################

This guide covers built-in helper functions and auxiliary fixtures provided by ``pytest-embedded``.

**********************
 ``redirect`` Fixture
**********************

The ``redirect`` fixture allows you to redirect Python console output (``sys.stdout``) into the internal DUT message queue. This is useful for writing simulated inputs, logging test steps, or verifying output redirection.

.. code:: python

   def test_redirect_example(dut, redirect):
       with redirect():
           print("Simulated device response")

       dut.expect("Simulated device response")

************************
 ``log_metric`` Fixture
************************

The ``log_metric`` fixture records numeric benchmarks (such as boot duration, heap memory usage, or transfer speeds) during test runs. It writes data following the Prometheus / OpenMetrics text format.

Use Case
========

Use ``log_metric`` to track performance over time across firmware revisions and detect regressions in CI.

Enabling Metric Logging
=======================

Provide the ``--metric-path`` CLI option to specify where metrics are saved:

.. code:: shell

   pytest --metric-path output/metrics.txt

Usage Example
=============

Include ``log_metric`` as an argument in your test function:

.. code:: python

   def test_performance(log_metric):
       boot_time_ms = 142.5
       free_heap_kb = 230

       # Record metric with key, numeric value, and optional labels
       log_metric("boot_duration_ms", boot_time_ms, target="esp32s3", config="release")
       log_metric("free_heap_kb", free_heap_kb, target="esp32s3")

Output Format
=============

The recorded file follows the Prometheus text format:

.. code:: text

   boot_duration_ms{target="esp32s3",config="release"} 142.5
   free_heap_kb{target="esp32s3"} 230

.. note::

   If ``--metric-path`` is not specified, ``log_metric`` issues a ``UserWarning`` and performs no file writing.

**********************************
 Test Context & Metadata Fixtures
**********************************

``pytest-embedded`` provides several fixtures to query test session metadata:

-  ``test_case_name``: Returns the name of the current test function as a string (e.g. ``"test_performance"``).
-  ``test_file_path``: Returns the absolute path to the currently executing test Python script.
-  ``session_root_logdir``: Returns the root directory path where log files for the current pytest session are stored. Configured via ``--root-logdir``.
-  ``session_temp_dir``: Returns the temporary directory created for the active test session.

Example:

.. code:: python

   def test_metadata(test_case_name, test_file_path, session_root_logdir):
       print(f"Executing: {test_case_name}")
       print(f"File: {test_file_path}")
       print(f"Logs stored in: {session_root_logdir}")
