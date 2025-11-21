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

The Arduino service requires only the build directory to work properly.
The app path is not required but can be used to derive the build directory. If not specified, it will be set to the current working directory.

The build directory is the directory that contains the binary and configuration files.
It can be specified as an absolute path or a relative path to the app path.
If nothing is specified, it will look for the `build` directory in the app path. If it still doesn't find it, it will assume the build directory is the app path.

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

You can run the tests specifiying the build directory used to build the example:

```shell
$ pytest --build-dir build examples/arduino -k test_hello_arduino
```
