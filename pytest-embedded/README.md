## pytest-embedded

Base plugin for all other plugins under this repo.

### Fixtures

- `test_file_path`: current test script file path
- `test_case_name`: current test case function name
- `pexpect_proc`: `PexpectProcess` instance
- `redirect`: `DuplicateStdout` instance
- `app`: `App` instance
- `dut`: `Dut` instance

### CLI Options
- `app_path`: App path
