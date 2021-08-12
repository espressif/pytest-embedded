## pytest-embedded-idf

pytest embedded plugin for esp-idf project

### Fixtures With More Functionalities

=== "`pytest-embedded-serial-esp` activated"

    - `app`: `IdfApp` instance, would parse the built binary by idf rules and gather more information.
    - `serial`: `IdfSerial` instance, would flash the built binary into the target board at first.

=== "`pytest-embedded-serial-esp` NOT activated"

    - `app`: `IdfApp` instance, would parse the built binary by idf rules and gather more information.

### CLI Options

- `part-tool`: Partition tool path, used for parsing partition table
