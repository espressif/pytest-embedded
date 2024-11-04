# Services

## Fixtures

Please refer to instructions under the "fixtures defined from pytest_embedded.plugin" chapter of the output of `pytest --fixtures`.

## CLI Options

Please refer to the instructions under the "embedded" or "embedded-[SERVICE]" groups of the output of `pytest --help`.

## Dependency Graph for Services

The arrow points from the dependent service to the service it depends on. For example, `pytest-embedded-serial-esp` depends on `pytest-embedded-serial`.

```{mermaid}
graph LR
    pytest-embedded-serial

    pytest-embedded-nuttx --> pytest-embedded-serial
    pytest-embedded-nuttx -->|optional, support test on espressif chips| pytest-embedded-serial-esp

    pytest-embedded-serial-esp --> pytest-embedded-serial

    pytest-embedded-jtag --> pytest-embedded-serial

    pytest-embedded-idf -->|optional, support test on espressif chips| pytest-embedded-serial-esp
    pytest-embedded-idf -->|optional, support test on qemu| pytest-embedded-qemu
    pytest-embedded-idf -->|optional, support test on wokwi| pytest-embedded-wokwi

    pytest-embedded-arduino -->|optional, support test on espressif chips| pytest-embedded-serial-esp
    pytest-embedded-arduino -->|optional, support test on qemu| pytest-embedded-qemu
    pytest-embedded-arduino -->|optional, support test on wokwi| pytest-embedded-wokwi
```

## Supported Services

Activate a service would enable a set of fixtures or add some extra functionalities to a few fixtures.

```{include} ../../pytest-embedded-serial/README.md
```

```{include} ../../pytest-embedded-serial-esp/README.md
```

```{include} ../../pytest-embedded-idf/README.md
```

```{include} ../../pytest-embedded-jtag/README.md
```

```{include} ../../pytest-embedded-qemu/README.md
```

```{include} ../../pytest-embedded-arduino/README.md
```

```{include} ../../pytest-embedded-wokwi/README.md
```

```{include} ../../pytest-embedded-nuttx/README.md
```
