### pytest-embedded-wokwi

pytest-embedded service for running tests on [Wokwi](https://wokwi.com/ci) instead of the real target.

Wokwi supports most ESP32 targets, including: esp32, esp32s2, esp32s3, esp32c3, esp32c6, and esp32h2. In addition, it supports a [wide range of peripherals](https://docs.wokwi.com/getting-started/supported-hardware), including sensors, displays, motors, and debugging tools.

Running the tests with Wokwi requires an internet connection. Your firmware is uploaded to the Wokwi server for the duration of the simulation, but it is not saved on the server. On-premises Wokwi installations are available for enterprise customers.

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

#### Writing Tests

When writing tests for your firmware, you can use the same pytest fixtures and assertions as you would for local testing. The main difference is that your tests will be executed in the Wokwi simulation environment and you have access to the Wokwi API for controlling the simulation through the `wokwi` fixture.

All interactions with the Wokwi simulation is through the `wokwi.client` - [wokwi-python-client](https://github.com/wokwi/wokwi-python-client)

For example, you can use `wokwi.client.set_control()` to control virtual components in the simulation, such as buttons, LEDs, and other peripherals.
Whole documentations can be found at [Wokwi Documentation](https://wokwi.github.io/wokwi-python-client/)

Button test:
```py
import logging
from pytest_embedded_wokwi import Wokwi
from pytest_embedded import Dut


def test_gpio(dut: Dut, wokwi: Wokwi):
    LOGGER = logging.getLogger(__name__)

    LOGGER.info("Waiting for Button test begin...")
    dut.expect_exact("Butston test")

    for i in range(3):
        LOGGER.info(f"Setting button pressed for {i + 1} seconds")
        wokwi.client.set_control("btn1", "pressed", 1)

        dut.expect_exact(f"Button pressed {i + 1} times")
        wokwi.client.set_control("btn1", "pressed", 0)
```
