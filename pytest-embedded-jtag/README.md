## pytest-embedded-jtag

pytest embedded plugin for openocd/gdb utilities

### New Fixtures and Fixtures With More Functionalities

- `openocd`: `OpenOcd` instance
- `gdb`: `Gdb` instance
- `dut`: `JtagDut` instance, would redirect the `openocd` output and the `gdb` output to `pexpect_proc` and duplicate them with `logging.info()`.

### CLI Options

- `gdb-prog-path`: GDB program path.
- `gdb-cli-args`: GDB cli arguments. (support parametrizing)
- `openocd-prog-path`: OpenOCD program path.
- `openocd-cli-args`: OpenOCD cli arguments. (support parametrizing)
