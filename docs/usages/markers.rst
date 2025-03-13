##################
 Addition Markers
##################

``pytest-embedded`` provides additional markers to enhance testing functionality.

*****************
 ``skip_if_soc``
*****************

The ``skip_if_soc`` marker allows you to skip tests based on the ``soc_caps`` (system-on-chip capabilities) of a target device. These capabilities are defined in the ``esp-idf``. For example, for the ESP32, you can reference them in the ``soc_caps.h`` file: `soc_caps.h <https://github.com/espressif/esp-idf/blob/master/components/soc/esp32/include/soc/soc_caps.h>`_.

Use Case
========

Imagine you have multiple targets, such as ``[esp32, esp32c3, ..., esp32s4]``. However, you may want to skip tests for chips that do not support specific features.

The ``skip_if_soc`` marker simplifies this by allowing you to define conditions based on the ``soc_caps`` property of your chip. This enables dynamic filtering of targets without the need for manual target-specific logic.

Examples
========

Here are examples of how to use ``skip_if_soc`` with different conditions:

**Condition 1**: A boolean expression such as ``SOC_ULP_SUPPORTED != 1 and SOC_UART_NUM != 3``. This skips tests for chips that:

   -  Do not support the ``low power mode`` feature (``SOC_ULP_SUPPORTED != 1``).
   -  **And** have a UART number other than 3 (``SOC_UART_NUM != 3``).

.. code:: python

   @pytest.mark.skip_if_soc("SOC_ULP_SUPPORTED != 1 and SOC_UART_NUM != 3")
   @pytest.mark.parametrize("target", ["esp32", "esp32s2", "esp32c3"], indirect=True)
   def test_template_first_condition():
       pass

----

**Condition 2**: A boolean expression such as ``SOC_ULP_SUPPORTED != 1 or SOC_UART_NUM != 3``. This skips tests for chips that:

   -  Either do not support the ``low power mode`` feature (``SOC_ULP_SUPPORTED != 1``).
   -  **Or** have a UART number other than 3 (``SOC_UART_NUM != 3``).

.. code:: python

   @pytest.mark.skip_if_soc("SOC_ULP_SUPPORTED != 1 or SOC_UART_NUM != 3")
   @pytest.mark.parametrize("target", ["esp32", "esp32s2", "esp32c3"], indirect=True)
   def test_template_second_condition():
       pass

----

**Condition 3**: You can use a shortcut to apply this condition to all ESP-IDF supported targets (assuming ``IDF_PATH`` is set).

.. code:: python

   import pytest
   from esp_bool_parser.constants import SUPPORTED_TARGETS

   @pytest.mark.skip_if_soc("SOC_ULP_SUPPORTED != 1")
   @pytest.mark.parametrize("target", SUPPORTED_TARGETS, indirect=True)
   def test_template():
       pass

*********************
 ``idf_parametrize``
*********************

``idf_parametrize`` is a wrapper around ``pytest.mark.parametrize`` that simplifies and extends string-based parameterization for tests. By using ``idf_parametrize``, testing parameters becomes more flexible and easier to maintain.

**Key Features:**

-  **Target Expansion**: Automatically expands lists of supported targets, reducing redundancy in test definitions.
-  **Markers**: use a marker as one of the parameters. If a marker is used, put it as the last parameter.

Use Cases
=========

Target Extension
----------------

In scenarios where the supported targets are [esp32, esp32c3, esp32s3], ``idf_parametrize`` simplifies the process of creating parameterized tests by automatically expanding the target list.

By default, the values for ``SUPPORTED_TARGETS`` and ``PREVIEW_TARGETS`` are imported from:

.. code:: python

   from esp_bool_parser import PREVIEW_TARGETS, SUPPORTED_TARGETS

However, you can propagate custom values by using the following:

.. code:: python

   from pytest_embedded_idf.utils import supported_targets, preview_targets

   supported_targets.set(CUSTOM_SUPPORT_TARGETS)
   preview_targets.set(CUSTOM_SUPPORT_TARGETS)

Another way to override ``supported_targets`` and ``preview_targets`` is by using command-line arguments:

.. code:: sh

   pytest --supported-targets esp32,esp32c3 --preview-targets esp32p4 ...

**Example:**

.. code:: python

   @idf_parametrize('target', [
       ('supported_targets'),
   ], indirect=True)
   @idf_parametrize('config', [
       'default',
       'psram'
   ])
   def test_st(dut: Dut) -> None:
       ...

**Equivalent to:**

.. code:: python

   @pytest.mark.parametrize('target', [
       'esp32',
       'esp32c3',
       'esp32s3'
   ], indirect=True)
   @pytest.mark.parametrize('config', [
       'default',
       'psram'
   ])
   def test_st(dut: Dut) -> None:
       ...

**Resulting Parameters Matrix:**

.. list-table::
   :header-rows: 1

   -  -  Target
      -  Config
   -  -  esp32
      -  default
   -  -  esp32c3
      -  default
   -  -  esp32s3
      -  default
   -  -  esp32
      -  psram
   -  -  esp32c3
      -  psram
   -  -  esp32s3
      -  psram

SOC Related Targets
-------------------

If you need to retrieve targets filtered by a specific SOC attribute, you can use the ``soc_filtered_targets`` function.

This function processes both ``supported_targets`` and ``preview_targets``, applies the specified filter, and returns a list of targets that match the given SOC statement.

**Function Signature**

.. code:: python

   def soc_filtered_targets(soc_statement: str, targets: ValidTargets = 'all') -> list[str]:
       """Filters targets based on a given SOC (System on Chip) statement."""

**Valid Target Categories**

The ``targets`` parameter determines which target sets should be considered:

-  ``"supported_targets"``: Includes only officially supported targets.
-  ``"preview_targets"``: Includes only preview (experimental) targets.
-  ``"all"`` (default): Includes both supported and preview targets.

**Example:**

Filter all targets that support ULP:

.. code:: python

   from pytest_embedded_idf.utils import soc_filtered_targets

   @idf_parametrize('target', soc_filtered_targets('SOC_ULP_SUPPORTED != 1'), indirect=['target'])
   def test_all_targets_which_support_ulp(case_tester) -> None:
       pass

Filter only **supported** targets that support ULP:

.. code:: python

   from pytest_embedded_idf.utils import soc_filtered_targets

   @idf_parametrize('target', soc_filtered_targets('SOC_ULP_SUPPORTED != 1', targets="supported_targets"), indirect=['target'])
   def test_only_supported_targets_which_support_ulp(case_tester) -> None:
       pass

Markers
-------

Markers can also be combined for added flexibility. It must be placed in the last position. In this case, if some test cases do not have markers, you can skip their definition. Look at the example.

**Example:**

In IDF testing, an environment marker (``marker``) determines which test runner will execute a test. This enables tests to run on various runners, such as:

-  **generic**: Tests run on generic runners.
-  **sdcard**: Tests require an SD card runner.
-  **usb_device**: Tests require a USB device runner.

.. code:: python

   @pytest.mark.generic
   @idf_parametrize('config', [
       'defaults'
   ], indirect=['config'])
   @idf_parametrize('target, markers', [
       ('esp32', (pytest.mark.usb_device,)),
       ('esp32c3')
       ('esp32', (pytest.mark.sdcard,))
   ], indirect=['target'])
   def test_console(dut: Dut, test_on: str) -> None:
     ...

**Resulting Parameters Matrix:**

.. list-table::
   :header-rows: 1

   -  -  Target
      -  Markers
   -  -  esp32
      -  generic, usb_device
   -  -  esp32c3
      -  generic, sdcard
   -  -  esp32
      -  generic, sdcard

Examples
========

Target with Config
------------------

**Example:**

.. code:: python

   @idf_parametrize('target, config', [
       ('esp32', 'release'),
       ('esp32c3', 'default'),
       ('supported_target', 'psram')
   ], indirect=True)
   def test_st(dut: Dut) -> None:
       ...

**Resulting Parameters Matrix:**

.. list-table::
   :header-rows: 1

   -  -  Target
      -  Config
   -  -  esp32
      -  release
   -  -  esp32c3
      -  default
   -  -  esp32
      -  psram
   -  -  esp32c3
      -  psram
   -  -  esp32s3
      -  psram

Supported Target on Runners
---------------------------

**Example:**

.. code:: python

   @idf_parametrize('target, markers', [
       ('esp32', (pytest.mark.generic, )),
       ('esp32c3', (pytest.mark.sdcard, )),
       ('supported_target', (pytest.mark.usb_device, ))
   ], indirect=True)
   def test_st(dut: Dut) -> None:
       ...

**Resulting Parameters Matrix:**

.. list-table::
   :header-rows: 1

   -  -  Target
      -  Markers
   -  -  esp32
      -  generic
   -  -  esp32c3
      -  sdcard
   -  -  esp32
      -  usb_device
   -  -  esp32c3
      -  usb_device
   -  -  esp32s3
      -  usb_device

Runner for All Tests
--------------------

**Example:**

.. code:: python

   @pytest.mark.generic
   @idf_parametrize('target, config', [
       ('esp32', 'release'),
       ('esp32c3', 'default'),
       ('supported_target', 'psram')
   ], indirect=True)
   def test_st(dut: Dut) -> None:
       ...

**Resulting Parameters Matrix:**

.. list-table::
   :header-rows: 1

   -  -  Target
      -  Config
      -  Markers

   -  -  esp32
      -  release
      -  generic

   -  -  esp32c3
      -  default
      -  generic

   -  -  esp32
      -  psram
      -  generic

   -  -  esp32c3
      -  psram
      -  generic

   -  -  esp32s3
      -  psram
      -  generic
