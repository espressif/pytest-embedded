# pytest-embedded

Base plugin for all other plugins under this repo.

## Fixtures

- `test_file_path` (the test script file path)
- `test_case_name` (the test function name)
- `app` (instance of App class)
- `dut` (instance of Dut class)

## Functions

- `expect` (`pexpect.expect` wrapper)
