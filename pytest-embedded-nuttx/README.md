### pytest-embedded-nuttx

Pytest embedded service for the NuttX project, compatible with Espressif devices.

Using the 'nuttx' service alongside 'serial' enables reading from and writing to the serial port, taking NuttShell into account when running programs and retrieving return codes.

The `nuttx` service provides basic serial communication and testing. Adding the 'esp' service enables further capabilities for Espressif devices, including flashing and device rebooting. Alternatively, using the 'qemu' service is also supported with NuttX
binaries.

Additional Features:

- `app`: Scans the NuttX binary directory to locate firmware and bootloader files.
- `serial`: Parses binary information and flashes the board. Requires the 'esp' service.
- `dut`: Sends commands to the device through the serial port. Requires the 'serial' service, 'esp' service for Espressif devices or 'qemu' service for emulation.
