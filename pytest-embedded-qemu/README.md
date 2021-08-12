## pytest-embedded-qemu

pytest embedded plugin for qemu, not target chip

### New Fixtures and Fixtures With More Functionalities

=== "`pytest-embedded-idf` activated"

    - `app`: `QemuApp` instance, would create the qemu bootable image automatically by the built binaries.
    - `qemu`: `Qemu` instance
    - `dut`: `QemuDut` instance, would redirect the `qemu` output to `pexpect_proc` and duplicate it with `logging.info()`.

=== "`pytest-embedded-idf` NOT activated"

    - `qemu`: `Qemu` instance
    - `dut`: `QemuDut` instance, would redirect the `qemu` output to `pexpect_proc` and duplicate it with `logging.info()`.

### CLI Options

- `qemu-image-path`: QEMU image path. (support parametrizing)
- `qemu-prog-path`: QEMU program path.
- `qemu-cli-args`: QEMU CLI arguments. (support parametrizing)
- `qemu-cli-extra-args`: QEMU CLI extra agruments, will append to the argument list. (support parametrizing)
- `qemu-log-path`: QEMU log file path.
