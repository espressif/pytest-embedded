### pytest-embedded

The core plugin for the `pytest-embedded` framework. Designed for embedded testing across multiple targets and environments.

#### Key Features

- **Core Fixtures**: Provides essential fixtures including `dut`, `app`, `msg_queue`, `pexpect_proc`, and `redirect`.
- **String & Regex Matching**: Integrates `pexpect` for powerful output parsing with `dut.expect()` and `dut.expect_exact()`.
- **Multi-DUT Orchestration**: Test multi-device topologies (such as master-slave or mesh networks) using `--count`.
- **Flexible Parametrization**: Easily parametrize apps, targets, and services using `pytest` markers.
- **Unified Test Reports**: Parse and merge embedded Unity test results into JUnit XML reports.

#### Quickstart

```python
from pytest_embedded import Dut


def test_basic_expect(redirect, dut: Dut):
    with redirect():
        print('Ready to test!')

    dut.expect('Ready to test!')
```

Run the test:

```shell
pytest test_basic.py -s
```
