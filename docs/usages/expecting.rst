#####################
 Expecting Functions
#####################

In testing, most of the work involves expecting a certain string or pattern and then making assertions. This is supported by the functions :func:`~pytest_embedded.dut.Dut.expect`, :func:`~pytest_embedded.dut.Dut.expect_exact`, :class:`~pytest_embedded.group.DutGroup` (multi-DUT synchronization), and :func:`~pytest_embedded.dut.Dut.expect_unity_test_output`.

All of these functions accept the following keyword arguments:

-  ``timeout``: Sets the timeout in seconds for this expect statement (default: 30s). Throws a :obj:`pexpect.TIMEOUT` exception if the specified value is exceeded.
-  ``expect_all``: Matches all specified patterns if set to ``True`` (default: ``False``).
-  ``not_matching``: Raises an exception if the specified pattern is found in the output (default: ``None``).
-  ``return_what_before_match``: Returns the bytes read before the match if specified (default: ``False``).

*****************************************
 :func:`~pytest_embedded.dut.Dut.expect`
*****************************************

The ``pattern`` can be a :obj:`str`, :obj:`bytes`, or a compiled regex with :obj:`bytes`.

If the pattern is a :obj:`str` or :obj:`bytes`, it will be converted to a compiled regex with :obj:`bytes` before the function is run.

.. code:: python

   import re

   def test_basic_expect(dut):
       dut.write('this would be redirected')

       dut.expect(b'this')
       dut.expect('would')
       dut.expect('[be]{2}')
       dut.expect(re.compile(b'redirected'))

If the expect call is successful, the return value will be a :obj:`re.Match` object.

.. code:: python

   def test_expect_return_value(redirect, dut):
       # Use the `redirect` fixture to write `sys.stdout` to the DUT
       with redirect():
           print('this would be redirected')

       res = dut.expect('this (would) be ([cdeirt]+)')
       assert res.group() == b'this would be redirected'
       assert res.group(1) == b'would'
       assert res.group(2).decode('utf-8') == 'redirected'

You can get the bytes read before a timeout by expecting a :obj:`pexpect.TIMEOUT` object.

.. code:: python

   import time
   import threading
   import pexpect

   def test_expect_from_eof(dut):
       def write_bytes():
           for _ in range(5):
               dut.write('1')
               time.sleep(2)

       write_thread = threading.Thread(target=write_bytes, daemon=True)
       write_thread.start()

       res = dut.expect(pexpect.TIMEOUT, timeout=3)
       assert res == b'11'

You can also get all bytes in the pexpect process buffer by expecting a :obj:`pexpect.EOF` object.

.. code:: python

   import pexpect

   def test_expect_from_eof_current_buffer(dut):
       dut.write('this would be redirected')
       dut.expect('this')

       # Close the pexpect process to generate an EOF
       dut.pexpect_proc.terminate()

       res = dut.expect(pexpect.EOF, timeout=None)
       assert res == b' would be redirected'

.. note::

   The pexpect process only reads from the process into its buffer when running expect functions. If you expect :obj:`pexpect.EOF` as the first statement, it will return an empty byte string.

   .. code:: python

      import pexpect


      def test_expect_from_eof_at_first(dut):
          dut.write("this would be redirected")

          # Close the pexpect process to generate an EOF
          dut.pexpect_proc.terminate()

          res = dut.expect(pexpect.EOF, timeout=None)
          assert res == b""

Additionally, the ``pattern`` argument can be a list of any of the supported types.

.. code:: python

   import re


   def test_expect_from_list(dut):
       dut.write("this would be redirected")

       pattern_list = [
           "this",
           b"would",
           "[be]+",
           re.compile(b"redirected"),
       ]

       for _ in range(4):
           dut.expect(pattern_list)

If you set ``expect_all`` to ``True``, the :func:`~pytest_embedded.dut.Dut.expect` function will return a list of the returned values for each item.

You can also set ``return_what_before_match`` to ``True`` to get the bytes read before the match, instead of the match object.

.. code:: python

   import pexpect

   def test_expect_before_match(dut):
       dut.write('this would be redirected')

       res = dut.expect('would', return_what_before_match=True)
       assert res == b'this '

       res = dut.expect_exact('be ', return_what_before_match=True)
       assert res == b' '

       res = dut.expect('ected', return_what_before_match=True)
       assert res == b'redir'

.. hint::

   For better performance when retrieving text before a pattern, use:

   .. code:: python

      before_str = dut.expect('pattern', return_what_before_match=True).decode('utf-8')

   Instead of:

   .. code:: python

      before_str = dut.expect('(.+)pattern').group(1).decode('utf-8')

   The latter performs unnecessary recursive matching of preceding bytes.

***********************************************
 :func:`~pytest_embedded.dut.Dut.expect_exact`
***********************************************

The ``pattern`` can be a :obj:`str` or :obj:`bytes`.

If the pattern is a :obj:`str`, it will be converted to :obj:`bytes` before the function is run.

.. code:: python

   def test_expect_exact(dut):
       dut.write('this would be redirected')

       dut.expect_exact('this would')
       dut.expect_exact(b'be redirected')

As with the :func:`~pytest_embedded.dut.Dut.expect` function, the ``pattern`` argument can be a list of any of the supported types.

.. code:: python

   def test_expect_exact_from_list(dut):
       dut.write('this would be redirected')

       pattern_list = [
           'this would',
           b'be redirected',
       ]

       for _ in range(2):
           dut.expect_exact(pattern_list)

***************************
 Multi-DUT Synchronization
***************************

When you use ``--count N`` (or equivalent), each board has its own serial stream and its own :class:`~pytest_embedded.dut.Dut` instance. Waiting for readiness on each device with separate ``expect`` calls works, but:

-  Sequential calls use **per-call** timeouts, so two ``expect_exact(..., timeout=120)`` lines can behave like a much larger wall-clock budget than a single 120s deadline.
-  The **slowest** device should not delay matching on others more than your chosen global timeout.

:class:`~pytest_embedded.group.DutGroup`
========================================

``DutGroup`` is a transparent proxy: **every method** available on a single :class:`~pytest_embedded.dut.Dut` can be called on the group. The call runs on all members **in parallel** and returns a list of per-DUT results.

.. code:: python

   from pytest_embedded import DutGroup

   def test_two_boards(dut):
       group = DutGroup(dut[0], dut[1])
       # or from a list:
       group = DutGroup(*dut)

It is also available as ``Dut.DutGroup`` for discoverability.

expect / expect_exact
---------------------

``expect`` and ``expect_exact`` support both **broadcast** (one pattern for all DUTs) and **per-DUT** patterns (N patterns for N DUTs), all running in parallel:

.. code:: python

   # Broadcast -- same pattern to every DUT
   group.expect_exact("[READY]", timeout=120)

   # Per-DUT patterns -- one per DUT, in constructor order
   group.expect_exact("[AP] ready", "[CLIENT] ready", timeout=120)

   # Regex -- also supports broadcast and per-DUT forms
   results = group.expect(r"IP=(\S+)", timeout=10)
   ip0 = results[0].group(1).decode()
   ip1 = results[1].group(1).decode()

   # Same as :class:`~pytest_embedded.dut.Dut`: a single pattern may use the keyword form
   group.expect_exact(pattern="[READY]", timeout=120)

Other methods
-------------

Any other :class:`~pytest_embedded.dut.Dut` method called on the group is forwarded with the **same arguments** to every DUT in parallel:

.. code:: python

   group.write(ssid)

For per-DUT arguments on non-expect methods, index into the group:

.. code:: python

   group[0].write(ap_config)
   group[1].write(client_config)

Container protocol
------------------

``DutGroup`` supports indexing, iteration, and length:

.. code:: python

   group[0]        # first DUT
   group[-1]       # last DUT
   len(group)      # number of DUTs
   list(group)     # iterate over DUTs
   group.duts      # underlying tuple (read-only)

Non-callable attributes are returned as a list:

.. code:: python

   procs = group.pexpect_proc  # [proc_0, proc_1, ...]

Names and clearer errors
------------------------

Pass optional **member** labels and an optional **group** label so logs and failures are easy to read:

.. code:: python

   group = DutGroup(*dut, names=("ap", "client"), group_name="wifi_ap")
   # group.names -> ("ap", "client"); group.group_name -> "wifi_ap"

If you omit ``names``, members default to ``dut-0``, ``dut-1``, … (aligned with per-DUT log file names when using ``--count``).

When any parallel call fails on one DUT, pytest-embedded raises :exc:`pytest_embedded.group.DutGroupMemberError`. Its message and attributes identify the member (``member_name``, ``member_index``) and group (``group_name``), and the original error (for example :exc:`pexpect.TIMEOUT`) is chained as :attr:`__cause__`. A structured line is also written to the Python logger at ERROR (including the underlying exception context).

Full example
------------

.. code:: python

   from pytest_embedded import DutGroup

   def test_wifi_ap(dut):
       group = DutGroup(*dut)

       # Phase 1: wait for both devices to be ready
       group.expect_exact("[READY]", timeout=120)

       # Phase 2: exchange SSID
       group.expect_exact("Send SSID:", timeout=10)
       group.write(ap_ssid)

       # Phase 3: exchange password
       group.expect_exact("Send Password:", timeout=10)
       group.write(ap_password)

       # Phase 4: verify connection
       results = group.expect(r"IP=(\S+)", timeout=30)
       for r in results:
           assert r.group(1) != b""

Phase synchronization
=====================

``DutGroup`` methods can be called **multiple times** in one test to synchronize phases. Each call blocks until every DUT has matched before continuing. After a successful match, those substrings are consumed from each DUT's buffer; emit new output for the next phase.

.. code:: python

   group = DutGroup(*dut)
   group.expect_exact("Init OK", timeout=30)
   group.expect_exact("Server started", timeout=10)
   group.expect_exact("Connected", timeout=60)

.. note::

   If one DUT fails, pending work is cancelled where possible; expects that have already started may still run until they match or time out, because pexpect cannot always be interrupted from another thread. The failure is reported as :exc:`~pytest_embedded.group.DutGroupMemberError` with the underlying error as :attr:`~BaseException.__cause__`.

***********************************************************
 :func:`~pytest_embedded.dut.Dut.expect_unity_test_output`
***********************************************************

`Unity Test <https://github.com/ThrowTheSwitch/Unity>`__ is a C test framework.

This function parses the output as Unity test output. The default ``timeout`` is 60 seconds.

When the test script finishes, the DUT object will raise an :obj:`AssertionError` if any Unity test case has a "FAIL" result.

Additionally, it will dump a JUnit report to a temporary folder and merge it with the main report if you use the ``pytest --junitxml`` feature.

.. code:: python

   import inspect
   import pytest

   def test_expect_unity_test_output_basic(dut):
       dut.write(inspect.cleandoc('''
           foo.c:100:test_case:FAIL:Expected 2 was 1
           foo.c:101:test_case_2:FAIL:Expected 1 was 2
           -------------------
           2 Tests 2 Failures 0 Ignored
           FAIL
       '''))
       with pytest.raises(AssertionError):
           dut.expect_unity_test_output()

       assert len(dut.testsuite.testcases) == 2
       assert dut.testsuite.attrs['failures'] == 2
       assert dut.testsuite.testcases[0].attrs['message'] == 'Expected 2 was 1'
       assert dut.testsuite.testcases[1].attrs['message'] == 'Expected 1 was 2'

It also supports `Unity fixtures <https://github.com/ThrowTheSwitch/Unity/tree/master/extras/fixture>`__.

.. code:: python

   import inspect
   import pytest

   def test_expect_unity_test_output_fixture(dut):
       dut.write(inspect.cleandoc('''
           TEST(group, test_case)foo.c:100::FAIL:Expected 2 was 1
           TEST(group, test_case_2)foo.c:101::FAIL:Expected 1 was 2
           -------------------
           2 Tests 2 Failures 0 Ignored
           FAIL
       '''))
       with pytest.raises(AssertionError):
           dut.expect_unity_test_output()

       assert len(dut.testsuite.testcases) == 2
       assert dut.testsuite.attrs['failures'] == 2
       assert dut.testsuite.testcases[0].attrs['message'] == 'Expected 2 was 1'
       assert dut.testsuite.testcases[1].attrs['message'] == 'Expected 1 was 2'
