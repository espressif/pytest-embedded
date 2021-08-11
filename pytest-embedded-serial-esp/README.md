## pytest-embedded-serial-esp

pytest embedded plugin for testing espressif boards via serial ports

### Fixtures With More Functionalities

- `serial`: `EspSerial` instance, would detect and confirm target and port by `esptool` automatically.

### CLI Options

- `target`: target chip type (support parametrizing)
