### pytest-embedded-qemu

pytest embedded service for running tests on QEMU instead of the real target.

Extra Functionalities:

=== "`pytest-embedded-idf` activated"

    - `app`: create the qemu bootable image automatically by the built binaries.
    - `qemu`: enable the fixture
    - `dut`: duplicate the `qemu` output to `pexpect_proc`.

=== "`pytest-embedded-idf` NOT activated"

    - `qemu`: enable the fixture
    - `dut`: duplicate the `qemu` output to `pexpect_proc`.

Used CLI Options:

- `qemu-image-path`
- `qemu-prog-path`
- `qemu-cli-args`
- `qemu-cli-extra-args`
- `qemu-log-path`
