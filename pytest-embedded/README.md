### pytest-embedded

The core plugin for the `pytest-embedded` framework. Designed for embedded testing across multiple targets and environments.

#### Key Features

- **Core Fixtures**: Provides essential fixtures including `dut`, `app`, `msg_queue`, `pexpect_proc`, and `redirect`.
- **String & Regex Matching**: Integrates `pexpect` for powerful output parsing with `dut.expect()` and `dut.expect_exact()`.
- **Multi-DUT Orchestration**: Test multi-device topologies (such as master-slave or mesh networks) using `--count`.
- **Flexible Parametrization**: Easily parametrize apps, targets, and services using `pytest` markers.
- **Unified Test Reports**: Parse and merge embedded Unity test results into JUnit XML reports.

#### Unity case names and item results

Implement `pytest_custom_unity_case_name(item, case_name)` in a plugin or `conftest.py` to customize
Unity child-case names. Return a string for the final name, or `None` to retain the original name:

```python
def pytest_custom_unity_case_name(item, case_name):
    return f'{item.name}::{case_name}'
```

At call report time, `pytest-embedded` stores the same final names in
`item.stash[pytest_embedded.unity.UnityCasesStashKey]` as a list of `UnityCase(name, result)`.
Results are `passed`, `failed`, or `skipped`. The merged JUnit XML uses these names too.
For multi-DUT tests the list includes each DUT's cases; without a naming hook, names are unchanged.

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
