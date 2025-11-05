#############
 Log Metrics
#############

The ``log_metric`` fixture is a powerful tool for recording performance metrics or other numerical data during your tests. It generates a file that follows the Prometheus text-based format, which is highly compatible with modern monitoring systems and the OpenMetrics standard.

**********
 Use Case
**********

You can use this fixture to track key metrics from your embedded device, such as boot time, memory usage, or network throughput. By logging these values, you can monitor performance trends over time and catch regressions automatically.

**************
 CLI Argument
**************

To enable metric logging, you need to provide the ``--metric-path`` command-line argument. This specifies the file where the metrics will be saved.

.. code:: bash

   pytest --metric-path=output/metrics.txt

***************
 Fixture Usage
***************

To use the fixture, simply include ``log_metric`` as an argument in your test function. It provides a callable that you can use to log your metrics.

.. code:: python

   def test_my_app(log_metric):
       # ... test code ...
       boot_time = 123.45  # measured boot time
       log_metric("boot_time", boot_time, target="esp32", sdk="v5.1")

***************
 Output Format
***************

The metrics are written to the file specified by ``--metric-path`` in the Prometheus text-based format. Each line represents a single metric.

Example output in ``output/metrics.txt``:

.. code:: text

   boot_time{target="esp32",sdk="v5.1"} 123.45

If ``--metric-path`` is not provided, the ``log_metric`` function will do nothing and issue a ``UserWarning``.
