import os
import shutil

import pytest

wokwi_cli_required = pytest.mark.skipif(
    shutil.which('wokwi-cli') is None,
    reason='Please make sure that `wokwi-cli` is in your PATH env var. '
    + 'To install: https://docs.wokwi.com/wokwi-ci/getting-started#cli-installation'
)

wokwi_token_required = pytest.mark.skipif(
    os.getenv('WOKWI_CLI_TOKEN') is None,
    reason='Please make sure that `WOKWI_CLI_TOKEN` env var is set. Get a token here: https://wokwi.com/dashboard/ci'
)


@wokwi_cli_required
@wokwi_token_required
def test_pexpect_by_wokwi_esp32(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest

        def test_pexpect_by_wokwi(dut):
            dut.expect('Hello world!')
            dut.expect('Restarting')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('foo bar not found', timeout=1)
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'idf,wokwi',
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_esp32'),
    )

    result.assert_outcomes(passed=1)


@wokwi_cli_required
@wokwi_token_required
def test_pexpect_by_wokwi_esp32_arduino(testdir):
    testdir.makepyfile("""
        import pexpect
        import pytest
        def test_pexpect_by_wokwi(dut):
            dut.expect('Hello Arduino!')
            with pytest.raises(pexpect.TIMEOUT):
                dut.expect('foo bar not found', timeout=1)
    """)

    result = testdir.runpytest(
        '-s',
        '--embedded-services', 'arduino,wokwi',
        '--app-path', os.path.join(testdir.tmpdir, 'hello_world_arduino'),
        '--wokwi-diagram', os.path.join(testdir.tmpdir, 'hello_world_arduino/esp32.diagram.json'),
    )

    result.assert_outcomes(passed=1)
