###############################
 Payload Capture & Echo Muting
###############################

Embedded devices sometimes emit large blocks of data over the serial port — Base64-encoded binary blobs, coverage dumps, diagnostic payloads, etc. ``pytest-embedded`` provides tools to **capture** these blocks programmatically and **mute** the terminal echo so the console stays readable.

***********************
 Automatic Echo Muting
***********************

The listener process that echoes serial output to ``stdout`` supports pattern-based muting. Override the ``mute_patterns`` fixture in your project's ``conftest.py``:

.. code:: python

   # conftest.py
   import pytest

   @pytest.fixture
   def mute_patterns():
       return [
           ("<<<PAYLOAD_START>>>", "<<<PAYLOAD_END>>>"),
       ]

Each ``(start, end)`` pair defines a muting region. When the listener detects *start* in the serial stream, it suppresses ``stdout`` echo until *end* is seen. Log-file writing is **never** affected — all data is always recorded to the pexpect log file.

Multiple patterns can be registered simultaneously:

.. code:: python

   @pytest.fixture
   def mute_patterns():
       return [
           ("<<<GCOV_DUMP_START>>>", "<<<GCOV_DUMP_END>>>"),
           ("<<<DIAG_START>>>", "<<<DIAG_END>>>"),
       ]

.. note::

   ``mute_patterns`` operates inside the listener process itself, so there is no race condition between the device producing output and the test code reacting to it.

********************
 Manual Echo Muting
********************

For sections that are not delimited by fixed markers, use the :func:`~pytest_embedded.dut.Dut.muted_echo` context manager:

.. code:: python

   def test_noisy_section(dut):
       with dut.muted_echo():
           dut.expect("some verbose output")
           # stdout is silent, but the log file still records everything

You can also call :func:`~pytest_embedded.dut.Dut.mute_echo` and :func:`~pytest_embedded.dut.Dut.unmute_echo` directly for fine-grained control.

********************
 Capturing Payloads
********************

:func:`~pytest_embedded.dut.Dut.capture_payload` waits for a *start* marker, collects all bytes until the *end* marker, and returns them as raw ``bytes``:

.. code:: python

   def test_extract_data(dut):
       data = dut.capture_payload(
           start="<<<DATA_START>>>",
           end="<<<DATA_END>>>",
           start_timeout=10,
           timeout=60,
       )
       assert data is not None
       # process `data` ...

If you prefer to persist the captured data to a file (for example, to accumulate data from multiple reboots), use :func:`~pytest_embedded.dut.Dut.capture_payload_to_file`:

.. code:: python

   def test_multi_boot_capture(dut):
       for boot in range(3):
           dut.write("reboot\n")
           ok = dut.capture_payload_to_file(
               start="<<<DUMP_START>>>",
               end="<<<DUMP_END>>>",
               filepath="/tmp/dump.txt",
               append=True,          # accumulate across boots
               include_markers=True,  # wrap each block with markers
           )
           assert ok

*************************
 Combining Both Features
*************************

Registering start/end markers in ``mute_patterns`` **and** using them in ``capture_payload`` is the recommended pattern — the listener mutes the echo automatically while the test code captures the data:

.. code:: python

   # conftest.py
   import pytest

   DUMP_START = "<<<GCOV_DUMP_START>>>"
   DUMP_END   = "<<<GCOV_DUMP_END>>>"

   @pytest.fixture
   def mute_patterns():
       return [(DUMP_START, DUMP_END)]

.. code:: python

   # test_coverage.py
   from conftest import DUMP_START, DUMP_END

   def test_gcov(dut):
       ok = dut.capture_payload_to_file(
           start=DUMP_START,
           end=DUMP_END,
           filepath="gcov_raw.txt",
       )
       assert ok

The console stays clean, the log file has everything, and ``gcov_raw.txt`` contains just the payload.
