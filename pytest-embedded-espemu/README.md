### pytest-embedded-espemu

pytest-embedded service for running tests on [esp-emu](https://github.com/espressif/esp-emulator), Espressif's lightweight emulator for ESP RISC-V series SoCs, instead of real targets.

Supported targets: `esp32c3`, `esp32c6`, `esp32h2`, `esp32p4`, `esp32s31`.

#### Usage

```shell
pytest --embedded-services idf,espemu --target esp32c3
```

The service builds a merged flash binary from the app's build directory (via `esptool merge-bin`), launches `esp-emu` with UART0 on stdio, and drives it like any other DUT — including the Unity test menu machinery from `pytest-embedded-idf`.

Extra CLI options:

- `--espemu-image-path`: use an existing merged flash binary instead of generating one
- `--espemu-prog-path`: path to the `esp-emu` binary (default: `esp-emu` from `PATH`)
- `--espemu-cli-args` / `--espemu-extra-args`: forwarded to the `esp-emu` command line, e.g. `--espemu-extra-args "--net user,restrict=yes"`
