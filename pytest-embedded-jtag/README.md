### pytest-embedded-jtag

pytest embedded service for openocd/gdb utilities

Extra Functionalities:

- `openocd`: enable the fixture
- `gdb`: enable the fixture
- `dut`: duplicate the `openocd` output and the `gdb` output to `dut.pexpect_proc`.

Used CLI Options:

- `gdb-prog-path`
- `gdb-cli-args`
- `openocd-prog-path`
- `openocd-cli-args`
