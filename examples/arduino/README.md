# Arduino Examples

This folder contains basic examples that show how to use the Arduino service.

## Prerequisites

1. Connect to the board
2. Make sure the necessary packages are installed, at least:
  - `pytest_embedded`
  - `pytest_embedded_serial_esp`
  - `pytest_embedded_arduino`
3. Build an example.  For this you can use `arduino-cli`.
```shell
  $ arduino-cli compile --build-path hello_world/build --fqbn espressif:esp32:esp32:PartitionScheme=huge_app hello_world`
```
The above command is supposed to be run from the directory `examples/arduino`,
adapt the build folder appropriately when run from a different location.
On success, this will create a `build` directory under the `hello_world`
example.

### Run the tests

```shell
$ pytest
```

This command can be run from the same location as earlier, i.e.
`examples/arduino`.  It can also be run from the top level directory, with:

```shell
$ pytest examples/arduino -k test_hello_arduino
```

This will parse the `build` directory created earlier, flash the chip and
expect the `Hello Arduino!` text to be printed.
