### pytest-embedded-jtag

A `pytest-embedded` service for hardware debugging via OpenOCD and GDB.

#### Service Activation

Activate this service by passing `jtag` to `--embedded-services`:

```shell
pytest --embedded-services serial,jtag --app-path /path/to/app
```

#### Extra Functionalities

- **`openocd` Fixture**: Launches and manages an OpenOCD background process. Supports sending commands over the OpenOCD Telnet port.
- **`gdb` Fixture**: Launches and manages a GDB process connected to the target debugger.
- **Output Duplication**: Duplicates both OpenOCD and GDB output streams into `dut.pexpect_proc` for unified log matching.

#### CLI Options

- `--openocd-prog-path`: Path to the OpenOCD executable. Default: `"openocd"`.
- `--openocd-cli-args`: Arguments passed to OpenOCD. Default: `"-f board/esp32-wrover-kit-3.3v.cfg"`.
- `--gdb-prog-path`: Path to the architecture-specific GDB executable. Default: `"xtensa-esp32-elf-gdb"`.
- `--gdb-cli-args`: Arguments passed to GDB. Default: `"--quiet"`.
- `--no-gdb`: Set to `True` to skip creating the GDB instance when only OpenOCD is needed. Default: `False`.

#### Quick Example

```python
from pytest_embedded import Dut
from pytest_embedded_jtag import Gdb, OpenOcd


def test_jtag_debugging(dut: Dut, openocd: OpenOcd, gdb: Gdb):
    gdb.write('target remote :3333')
    gdb.expect('Remote debugging using :3333')
    gdb.write('monitor reset halt')
    dut.expect('Target halted')
```
