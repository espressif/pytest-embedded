### pytest-embedded-jtag

pytest embedded service for openocd/gdb utilities

Extra Functionalities:

- `openocd`: enable the fixture
- `gdb`: enable the fixture
- `dut`: redirect the `openocd` output and the `gdb` output to `pexpect_proc` and duplicate them with `logging.info()`.

Used CLI Options:

- `gdb-prog-path`
- `gdb-cli-args`
- `openocd-prog-path`
- `openocd-cli-args`
