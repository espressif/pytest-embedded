##############
 Key Concepts
##############

**********
 Fixtures
**********

Each test case initializes a few fixtures. The most important fixtures are:

-  ``msg_queue``: A message queue. A background listener process reads all messages from this queue, logs them to the terminal with an optional timestamp, and records them to the pexpect process.
-  ``pexpect_proc``: A pexpect process that can run ``pexpect.expect()`` for testing purposes.
-  ``app``: The built binary.
-  ``dut``: Device Under Test (DUT). A DUT contains several daemon processes/threads, and the output of each is redirected to the ``msg_queue`` fixture.

.. note::

   You may redirect any output to the ``msg_queue`` fixture by ``contextlib.redirect_stdout``.

   .. code:: python

      import contextlib

      def test_redirect(dut, msg_queue):
          with contextlib.redirect_stdout(msg_queue):
              print("will be redirected")

          dut.expect_exact("redirected")

   Or you may redirect the output from a fixture ``redirect``

   .. code:: python

      def test_redirect(dut, msg_queue, redirect):
          with redirect():
              print("will also be redirected")

          dut.expect_exact("redirected")

You can run ``pytest --fixtures`` to see all fixtures defined by ``pytest-embedded``. They are listed under the ``fixtures defined from pytest_embedded.plugin`` section.

*****************
 Parametrization
*****************

All CLI options support parametrization via ``indirect=True``. Parametrization is a feature provided by ``pytest``. For more details, please refer to the `Parametrizing tests <https://docs.pytest.org/en/stable/example/parametrize.html>`_ documentation.

For example, running the ``pytest`` command with the following test script:

.. code:: python

   @pytest.mark.parametrize(
       "embedded_services, app_path",
       [
           ("idf", app_path_1),
           ("idf", app_path_2),
       ],
       indirect=True,
   )
   def test_serial_tcp(dut):
       assert dut.app.target == "esp32"
       dut.expect("Restart now")

is equivalent to running two separate commands, ``pytest --embedded-services idf --app-path <app_path_1>`` and ``pytest --embedded-services idf --app-path <app_path_2>``, with this test script:

.. code:: python

   def test_serial_tcp(dut):
       assert dut.app.target == "esp32"
       dut.expect("Restart now")

**********
 Services
**********

You can activate additional services with ``pytest --embedded-services service[,service]`` to enable extra fixtures and functionalities. These services are provided by optional dependencies, which can be installed with ``pip``.

Available services are described :doc:`here <services>`.

************
 Multi DUTs
************

Sometimes, you may need multiple DUTs for testing, for example, in master-slave or mesh network tests.

Here are a few examples of how to enable this feature. For detailed information, refer to the ``embedded`` group in the ``pytest --help`` output.

Enable multi DUTs by specifying ``--count``
===========================================

When multi-DUT mode is enabled, all fixtures become a tuple of instances. Each instance in the tuple is independent. For parametrization, each configuration uses ``|`` as a separator for each instance's values.

For example, running shell command:

.. code:: shell

   pytest \
   --embedded-services serial|serial \
   --count 2 \
   --app-path <master_bin>|<slave_bin>

enables two DUTs with the ``serial`` service. The ``app`` fixture becomes a tuple of two ``App`` instances, and ``dut`` becomes a tuple of two ``Dut`` instances.

You can test with:

.. code:: python

   def test(dut):
       master = dut[0]
       slave = dut[1]

       master.expect("sent")
       slave.expect("received")

Specify once when applying to all DUTs
======================================

If all DUTs share the same configuration value, you only need to specify it once.

.. code:: shell

   pytest \
   --embedded-services serial \
   --count 2 \
   --app-path <master_bin>|<slave_bin>

The ``--embedded-services serial`` option applies to all DUTs.

Vacant Value if it's Useless
============================

Sometimes, an option is only useful for a specific service. You can provide a vacant value if a configuration is not applicable to a particular DUT.

.. code:: shell

   pytest \
   --embedded-services qemu|serial \
   --count 2 \
   --app-path <master_bin>|<slave_bin> \
   --qemu-cli-args "<args>|" \
   --port "|<port>"

The ``--qemu-cli-args`` option applies to the first DUT (with the ``qemu`` service), while ``--port`` applies to the second DUT (with the ``serial`` service).

*********
 Logging
*********

``pytest-embedded`` prints all DUT output with a timestamp. To remove the timestamp, run pytest with the ``--with-timestamp n`` option.

By default, ``pytest`` swallows ``stdout``. To see the live output, run pytest with the ``-s`` option.
