# Services

## Fixtures

Please refer to instructions under the "fixtures defined from pytest_embedded.plugin" chapter of the output of `pytest --fixtures`.

## CLI Options

Please refer to the instructions under the "embedded" or "embedded-[SERVICE]" groups of the output of `pytest --help`.

## Services

Activate a service would enable a set of fixtures or add some extra functionalities to a few fixtures.

```{include} ../pytest-embedded-serial/README.md
```

```{include} ../pytest-embedded-serial-esp/README.md
```

```{include} ../pytest-embedded-idf/README.md
```

```{include} ../pytest-embedded-jtag/README.md
```

```{include} ../pytest-embedded-qemu/README.md
```

```{include} ../pytest-embedded-arduino/README.md
```

## Dependency Graph

```{mermaid}
graph LR
    pytest_embedded --> pytest_embedded_serial
    pytest_embedded -->|pytest_embedded_serial_esp is an optional dependency| pytest_embedded_idf
    pytest_embedded -->|pytest_embedded_idf is an optional dependency| pytest_embedded_qemu
    pytest_embedded -->|pytest_embedded_serial is an optional dependency| pytest_embedded_arduino

    pytest_embedded_serial --> pytest_embedded_serial_esp
    pytest_embedded_serial --> pytest_embedded_jtag
```
