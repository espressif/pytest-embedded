#####################
 Expecting Functions
#####################

In embedded testing, most test steps involve sending input to a device and verifying the output received on the serial port or console. ``pytest-embedded`` provides three core expectation methods on the ``dut`` fixture:

-  :func:`~pytest_embedded.dut.Dut.expect`
-  :func:`~pytest_embedded.dut.Dut.expect_exact`
-  :func:`~pytest_embedded.dut.Dut.expect_unity_test_output`

All expectation functions accept the following common keyword arguments:

-  ``timeout``: Maximum waiting time in seconds (default: 30 seconds). Raises :obj:`pexpect.TIMEOUT` if the pattern is not matched before timeout expires.
-  ``expect_all``: When matching a list of patterns, requires all patterns to match if set to ``True`` (default: ``False``).
-  ``not_matching``: A pattern that must **not** appear in the output. If this pattern appears while waiting for the expected pattern, a :obj:`ValueError` is raised immediately (default: ``None``).
-  ``return_what_before_match``: Returns the raw bytes received before the matched pattern instead of a match object (default: ``False``). Cannot be used together with ``expect_all``.

*****************************************
 :func:`~pytest_embedded.dut.Dut.expect`
*****************************************

Matches a regular expression or string against the incoming buffer.

The ``pattern`` argument can be:

-  A :obj:`str` or :obj:`bytes` (automatically compiled into a regex)
-  A compiled regular expression object (:obj:`re.compile`)
-  A list of any of the above types

Basic Usage
===========

.. code:: python

   import re


   def test_basic_expect(dut):
       dut.write(b"reboot\r\n")

       # Match plain string, bytes, regex, or compiled pattern
       dut.expect("Restarting")
       dut.expect(b"Booting")
       dut.expect(r"Chip revision: v\d+\.\d+")
       dut.expect(re.compile(b"App version: [0-9.]+"))

Capturing Groups
================

When a pattern matches successfully, :func:`~pytest_embedded.dut.Dut.expect` returns a :obj:`re.Match` object:

.. code:: python

   def test_capture_groups(redirect, dut):
       with redirect():
           print("IP address: 192.168.1.100")

       match = dut.expect(r"IP address: (\d+\.\d+\.\d+\.\d+)")
       ip_addr = match.group(1).decode("utf-8")
       assert ip_addr == "192.168.1.100"

Matching a List of Patterns
===========================

You can pass a list of patterns. By default, the function succeeds when **any** pattern in the list matches:

.. code:: python

   def test_match_any(dut):
       # Succeeds as soon as either "SUCCESS" or "OK" is received
       dut.expect(["SUCCESS", "OK"])

If you set ``expect_all=True``, the function waits until **all** patterns in the list have been matched:

.. code:: python

   def test_match_all(dut):
       dut.expect(["Connected to Wi-Fi", "Obtained IP", "Starting server"], expect_all=True)

Reading Text Before Match
=========================

Use ``return_what_before_match=True`` to retrieve the bytes received before the matched pattern:

.. code:: python

   def test_read_before(redirect, dut):
       with redirect():
           print("device_id=ESP32_A1B2C3 ready")

       # Returns b"device_id=ESP32_A1B2C3 "
       raw_bytes = dut.expect("ready", return_what_before_match=True)
       assert b"device_id=ESP32_A1B2C3" in raw_bytes

.. tip::

   Using ``return_what_before_match=True`` is significantly faster than using regex greedy capture groups like ``(.*)pattern``, because it avoids expensive backtracking.

Handling Timeouts and EOF
=========================

You can expect :obj:`pexpect.TIMEOUT` or :obj:`pexpect.EOF` to inspect the buffered output:

.. code:: python

   import pexpect


   def test_timeout_buffer(dut):
       dut.write(b"slow_task\n")

       # Returns all bytes accumulated before timeout occurred
       buffer_content = dut.expect(pexpect.TIMEOUT, timeout=5)
       assert b"Still processing" in buffer_content

***********************************************
 :func:`~pytest_embedded.dut.Dut.expect_exact`
***********************************************

Matches exact string or byte sequences without regex compilation.

Use :func:`~pytest_embedded.dut.Dut.expect_exact` whenever you are looking for a fixed literal string. It is faster than regex matching and does not require escaping special characters (such as ``[``, ``]``, ``(``, ``)``, or ``.``).

.. code:: python

   def test_expect_exact(dut):
       # No regex escaping needed for parentheses or dots
       dut.expect_exact("Version (v1.2.3)")
       dut.expect_exact(b"[WiFi] Connected successfully.")

Like :func:`~pytest_embedded.dut.Dut.expect`, it also accepts a list of patterns:

.. code:: python

   def test_expect_exact_list(dut):
       dut.expect_exact(["Ready.", "System idle."])

***********************************************************
 :func:`~pytest_embedded.dut.Dut.expect_unity_test_output`
***********************************************************

Parses `Unity test framework <https://github.com/ThrowTheSwitch/Unity>`_ results printed by C firmware running on the target.

Features:

-  Parses individual Unity test cases, assertions, and summaries.
-  Automatically raises an :obj:`AssertionError` if any Unity test case fails.
-  Generates a JUnit XML test report and merges it into the pytest report when ``--junitxml`` is used.

.. code:: python

   def test_firmware_unit_tests(dut):
       # Instruct firmware to execute unit tests
       dut.write(b"run_all_tests\r\n")

       # Wait for and validate Unity test suite completion
       dut.expect_unity_test_output(timeout=120)

Additional arguments for :func:`~pytest_embedded.dut.Dut.expect_unity_test_output`:

-  ``timeout``: Test suite timeout in seconds (default: 60 seconds).
-  ``remove_asci_escape_code``: Strips ANSI color escape sequences from the console before parsing (default: ``True``).
-  ``extra_before``: Prepends additional log text read previously to the buffer.
