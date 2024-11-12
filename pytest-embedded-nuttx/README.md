### pytest-embedded-nuttx

Pytest embedded service for NuttX project. alongside Espressif devices.

Using the 'nuttx' service alongside 'serial' allows writing and reading from
the serial port, taking the NuttShell into consideration when running programs
and even getting return codes.

While using pytest-embedded-nuttx allows you to communicate with serial
devices and run simple tests, enabling the 'esp' service  adds extra capabilities for
Espressif devices, such as flashing and device rebooting.

Extra Functionalities:

- `app`: Explore the NuttX binary directory and identify firmware and bootloader files.
- `serial`: Parse the binary information and flash the board. Requires 'esp' service.
- `dut`:  Send commands to device through serial port. Requires 'serial' service or 'esp' for Espressif devices.
