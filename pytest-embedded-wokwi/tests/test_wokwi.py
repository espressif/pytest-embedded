import json
import os

import pytest

from pytest_embedded_wokwi.wokwi import Wokwi

wokwi_token_required = pytest.mark.skipif(
    not os.getenv('WOKWI_CLI_TOKEN', None),
    reason='Please make sure that `WOKWI_CLI_TOKEN` env var is set. Get a token here: https://wokwi.com/dashboard/ci',
)


@wokwi_token_required
def test_pexpect_by_wokwi_esp32(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest

        def test_pexpect_by_wokwi(dut):
            dut.expect('Hello world!')
            dut.expect('Restarting')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('Hello world! or Restarting not found', timeout=1)
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'idf,wokwi',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_esp32'),
    )

    result.assert_outcomes(passed=1)


@wokwi_token_required
def test_pexpect_by_wokwi_esp32_arduino(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest
        def test_pexpect_by_wokwi(dut):
            dut.expect('Hello Arduino!')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('Hello Arduino! not found', timeout=1)
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services',
        'arduino,wokwi',
        '--app-path',
        os.path.join(testdir.tmpdir, 'hello_world_arduino'),
        '--wokwi-diagram',
        os.path.join(testdir.tmpdir, 'hello_world_arduino/esp32.diagram.json'),
    )

    result.assert_outcomes(passed=1)


class TestApplySerialInterfaceOverride:
    """Unit tests for Wokwi._apply_serial_interface_override (no token needed)."""

    def _write_diagram(self, tmp_path, diagram: dict) -> str:
        path = os.path.join(str(tmp_path), 'diagram.json')
        with open(path, 'w') as f:
            json.dump(diagram, f)
        return path

    def test_adds_serial_interface_and_removes_serial_monitor(self, tmp_path):
        diagram = {
            'version': 1,
            'parts': [{'type': 'board-esp32-devkit-c-v4', 'id': 'esp'}],
            'connections': [
                ['esp:TX', '$serialMonitor:RX', ''],
                ['esp:RX', '$serialMonitor:TX', ''],
            ],
        }
        src = self._write_diagram(tmp_path, diagram)
        result_path = Wokwi._apply_serial_interface_override(src)

        try:
            with open(result_path) as f:
                result = json.load(f)

            assert result['parts'][0]['attrs']['serialInterface'] == 'USB_SERIAL_JTAG'
            assert result['connections'] == []
        finally:
            os.unlink(result_path)

    def test_preserves_non_serial_monitor_connections(self, tmp_path):
        diagram = {
            'version': 1,
            'parts': [{'type': 'board-esp32-s3-devkitc-1', 'id': 'esp32', 'attrs': {}}],
            'connections': [
                ['esp32:RX', '$serialMonitor:TX', '', []],
                ['esp32:TX', '$serialMonitor:RX', '', []],
                ['btn1:1.l', 'esp32:14', 'blue', ['h-38.4', 'v105.78']],
                ['esp32:4', 'led1:A', 'green', ['h0']],
            ],
        }
        src = self._write_diagram(tmp_path, diagram)
        result_path = Wokwi._apply_serial_interface_override(src)

        try:
            with open(result_path) as f:
                result = json.load(f)

            assert len(result['connections']) == 2
            assert result['connections'][0] == ['btn1:1.l', 'esp32:14', 'blue', ['h-38.4', 'v105.78']]
            assert result['connections'][1] == ['esp32:4', 'led1:A', 'green', ['h0']]
        finally:
            os.unlink(result_path)

    def test_does_not_mutate_original_file(self, tmp_path):
        diagram = {
            'version': 1,
            'parts': [{'type': 'board-esp32-devkit-c-v4', 'id': 'esp'}],
            'connections': [
                ['esp:TX', '$serialMonitor:RX', ''],
                ['esp:RX', '$serialMonitor:TX', ''],
            ],
        }
        src = self._write_diagram(tmp_path, diagram)
        result_path = Wokwi._apply_serial_interface_override(src)

        try:
            with open(src) as f:
                original = json.load(f)

            assert 'serialInterface' not in original['parts'][0].get('attrs', {})
            assert len(original['connections']) == 2
            assert result_path != src
        finally:
            os.unlink(result_path)

    def test_adds_attrs_when_missing(self, tmp_path):
        diagram = {
            'version': 1,
            'parts': [{'type': 'board-esp32-p4-function-ev', 'id': 'esp'}],
            'connections': [],
        }
        src = self._write_diagram(tmp_path, diagram)
        result_path = Wokwi._apply_serial_interface_override(src)

        try:
            with open(result_path) as f:
                result = json.load(f)

            assert result['parts'][0]['attrs'] == {'serialInterface': 'USB_SERIAL_JTAG'}
            assert result['connections'] == []
        finally:
            os.unlink(result_path)

    def test_overrides_existing_serial_interface(self, tmp_path):
        diagram = {
            'version': 1,
            'parts': [{'type': 'board-esp32-devkit-c-v4', 'id': 'esp', 'attrs': {'serialInterface': 'UART'}}],
            'connections': [],
        }
        src = self._write_diagram(tmp_path, diagram)
        result_path = Wokwi._apply_serial_interface_override(src)

        try:
            with open(result_path) as f:
                result = json.load(f)

            assert result['parts'][0]['attrs']['serialInterface'] == 'USB_SERIAL_JTAG'
        finally:
            os.unlink(result_path)
