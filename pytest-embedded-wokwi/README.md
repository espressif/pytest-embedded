### pytest-embedded-wokwi

pytest-embedded service for running tests on [Wokwi](https://wokwi.com/ci) instead of the real target.

Wokwi supports most ESP32 targets, including: esp32, esp32s2, esp32s3, esp32c3, esp32c6, and esp32h2. In addition, it supports a [wide range of peripherals](https://docs.wokwi.com/getting-started/supported-hardware), including sensors, displays, motors, and debugging tools.

Running the tests with Wokwi requires an internet connection. Your firmware is uploaded to the Wokwi server for the duration of the simulation, but it is not saved on the server. On-premises Wokwi installations are available for enterprise customers.

#### Wokwi CLI installation

The Wokwi plugin uses the [Wokwi CLI](https://github.com/wokwi/wokwi-cli) to interact with the wokwi simulation server. You can download the precompiled CLI binaries from the [releases page](https://github.com/wokwi/wokwi-cli/releases). Alternatively, on Linux or Mac OS, you can install the CLI using the following command:

```bash
curl -L https://wokwi.com/ci/install.sh | sh
```

And on Windows:

```powershell
iwr https://wokwi.com/ci/install.ps1 -useb | iex
```

#### Wokwi API Tokens

Before using this plugin, you need to create a free Wokwi account and [generate an API key](https://wokwi.com/dashboard/ci). You can then set the `WOKWI_CLI_TOKEN` environment variable to the API key.

Linux / Mac OS / WSL:

```bash
export WOKWI_CLI_TOKEN="your-api-key"
```

Windows PowerShell:

```powershell
$env:WOKWI_CLI_TOKEN="your-api-key"
```

#### Usage

To run your tests with Wokwi, make sure to specify the `wokwi` service when running pytest, e.g.:

```
pytest --embedded-services idf,wokwi
```

To limit the amount of simulation time, use the `--wokwi-timeout` flag. For example, to set the simulation time limit to 60 seconds (60000 milliseconds):

```
pytest --embedded-services idf,wokwi --wokwi-timeout=60000
```
