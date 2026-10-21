import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

xdist_only = pytest.mark.skipif(importlib.util.find_spec('xdist') is None, reason='pytest-xdist is not installed')
STRESS_WORKERS = 8
STRESS_TESTS = 64

MIXED_UNITY_OUTPUT = """\
TEST(group, unity_pass)foo.c:100::PASS
TEST(group, unity_fail)foo.c:101::FAIL:Expected 2 was 1
TEST(group, unity_ignore)foo.c:102::IGNORE:Not supported
-------------------
3 Tests 1 Failures 1 Ignored
FAIL
"""

PASSING_UNITY_OUTPUT = """\
TEST(group, unity_pass_a)foo.c:100::PASS
TEST(group, unity_pass_b)foo.c:101::PASS
-------------------
2 Tests 0 Failures 0 Ignored
OK
"""


def _run_args(use_xdist: bool) -> list[str]:
    return ['-n', '2', '--max-worker-restart=0'] if use_xdist else ['-p', 'no:xdist']


def _make_unity_module(testdir, module_name: str, test_name: str, output: str) -> None:
    testdir.makepyfile(
        **{
            module_name: f"""\
def {test_name}(dut):
    dut.write({output!r})
    dut.expect_unity_test_output()
"""
        }
    )


def _junit_cases(path='report.xml'):
    root = ET.parse(path).getroot()
    suite = root if root.tag == 'testsuite' else root.find('testsuite')
    assert suite is not None
    return suite, list(suite.findall('testcase'))


def test_xdist_is_not_a_runtime_dependency():
    pyproject = Path(__file__).parents[1] / 'pyproject.toml'
    project_config = pyproject.read_text().split('[project]', maxsplit=1)[1].split('\n[', maxsplit=1)[0]
    runtime_dependencies = project_config.split('dependencies = [', maxsplit=1)[1].split(']', maxsplit=1)[0]

    assert 'xdist' not in runtime_dependencies.lower()


@pytest.mark.parametrize(
    'use_xdist',
    [
        False,
        pytest.param(True, marks=xdist_only),
    ],
)
@pytest.mark.parametrize('mode', ['replace', 'merge'])
def test_unity_junit_pass_fail_ignore(testdir, use_xdist, mode):
    _make_unity_module(testdir, 'test_one', 'test_one', MIXED_UNITY_OUTPUT)
    _make_unity_module(testdir, 'test_two', 'test_two', MIXED_UNITY_OUTPUT)

    result = testdir.runpytest(
        *_run_args(use_xdist),
        '--junitxml',
        'report.xml',
        '--unity-test-report-mode',
        mode,
    )

    result.assert_outcomes(failed=2)
    if use_xdist:
        assert 'gw0' in result.stdout.str()
        assert 'gw1' in result.stdout.str()

    suite, cases = _junit_cases()
    unity_cases = [case for case in cases if case.get('is_unity_case') == '1']
    python_cases = [case for case in cases if case.get('is_unity_case') == '0']

    assert len(unity_cases) == 6
    assert len(python_cases) == (0 if mode == 'replace' else 2)
    assert suite.get('tests') == '6'
    assert suite.get('failures') == '2'
    assert suite.get('skipped') == '2'
    assert suite.get('errors') == '0'
    assert [case.get('name') for case in unity_cases].count('unity_pass') == 2
    assert [case.get('name') for case in unity_cases].count('unity_fail') == 2
    assert [case.get('name') for case in unity_cases].count('unity_ignore') == 2
    if use_xdist:
        assert {case.get('pytest_embedded_test_case') for case in unity_cases} == {'test_one', 'test_two'}
        assert all(case.get('classname') for case in unity_cases)
    else:
        assert all(case.get('pytest_embedded_test_case') is None for case in unity_cases)
        assert all(case.get('classname') is None for case in unity_cases)


@xdist_only
def test_xdist_custom_test_case_name_fixture(testdir):
    testdir.makeconftest(
        """\
import pytest

@pytest.fixture
def test_case_name(request):
    return f'custom.{request.node.callspec.params["case_index"]}'

@pytest.fixture(autouse=True)
def rename_junit_case(test_case_name, record_xml_attribute):
    record_xml_attribute('name', test_case_name)
"""
    )
    testdir.makepyfile(
        f"""\
import pytest

@pytest.mark.parametrize('case_index', range(4))
def test_custom_name(dut, case_index):
    dut.write({PASSING_UNITY_OUTPUT!r})
    dut.expect_unity_test_output()
"""
    )

    result = testdir.runpytest(
        '-n',
        '2',
        '--max-worker-restart=0',
        '--junitxml',
        'report.xml',
        '--unity-test-report-mode',
        'merge',
    )

    result.assert_outcomes(passed=4)
    _, cases = _junit_cases()
    unity_cases = [case for case in cases if case.get('is_unity_case') == '1']
    python_cases = [case for case in cases if case.get('is_unity_case') == '0']
    expected_names = {f'custom.{index}' for index in range(4)}
    assert {case.get('name') for case in python_cases} == expected_names
    assert {case.get('pytest_embedded_test_case') for case in unity_cases} == expected_names


@xdist_only
def test_unity_junit_multi_dut_xdist(testdir):
    body = f"""\
import pytest

@pytest.mark.parametrize('count', [2], indirect=True)
def TEST_NAME(dut):
    for device in dut:
        device.write({PASSING_UNITY_OUTPUT!r})
        device.expect_unity_test_output()
"""
    testdir.makepyfile(test_one=body.replace('TEST_NAME', 'test_one'))
    testdir.makepyfile(test_two=body.replace('TEST_NAME', 'test_two'))

    result = testdir.runpytest(
        '-n',
        '2',
        '--max-worker-restart=0',
        '--junitxml',
        'report.xml',
    )

    result.assert_outcomes(passed=2)
    suite, cases = _junit_cases()
    unity_cases = [case for case in cases if case.get('is_unity_case') == '1']
    assert len(unity_cases) == 8
    assert suite.get('tests') == '8'
    assert suite.get('failures') == '0'


@pytest.mark.parametrize(
    'use_xdist',
    [
        False,
        pytest.param(True, marks=xdist_only),
    ],
)
def test_unity_junit_rerun_does_not_duplicate_report(testdir, use_xdist):
    testdir.makepyfile(
        f"""\
from pathlib import Path

def test_flaky(dut):
    marker = Path('attempted')
    output = {PASSING_UNITY_OUTPUT!r} if marker.exists() else {MIXED_UNITY_OUTPUT!r}
    marker.touch()
    dut.write(output)
    dut.expect_unity_test_output()
"""
    )

    result = testdir.runpytest(
        *_run_args(use_xdist),
        '--reruns',
        '1',
        '--junitxml',
        'report.xml',
    )

    outcomes = result.parseoutcomes()
    assert outcomes['failed'] == 1
    assert outcomes['rerun'] == 1
    suite, cases = _junit_cases()
    assert [case.get('name') for case in cases] == ['unity_pass', 'unity_fail', 'unity_ignore']
    assert suite.get('tests') == '3'
    assert suite.get('failures') == '1'


@xdist_only
def test_xdist_rerun_recovers_from_fixture_setup_failure(testdir):
    testdir.makeconftest(
        """\
from pathlib import Path

import pytest

@pytest.fixture
def transient_fixture():
    marker = Path('setup-attempted')
    if not marker.exists():
        marker.touch()
        pytest.fail('simulated transient setup failure')
    yield object()
"""
    )
    testdir.makepyfile(
        """\
def test_after_setup_rerun(transient_fixture):
    assert transient_fixture is not None
"""
    )

    result = testdir.runpytest('-n', '1', '--max-worker-restart=0', '--reruns', '1')

    outcomes = result.parseoutcomes()
    assert outcomes['passed'] == 1
    assert outcomes['rerun'] == 1


@xdist_only
def test_xdist_without_junitxml(testdir):
    _make_unity_module(testdir, 'test_one', 'test_one', PASSING_UNITY_OUTPUT)
    _make_unity_module(testdir, 'test_two', 'test_two', PASSING_UNITY_OUTPUT)

    result = testdir.runpytest('-n', '2', '--max-worker-restart=0')

    result.assert_outcomes(passed=2)


@xdist_only
def test_xdist_stress_many_workers_produces_complete_junit(testdir):
    expected_output = {}
    for index in range(STRESS_TESTS):
        case_name = f'stress_{index:03d}'
        case_output = f'worker-output-{index:03d}'
        expected_output[case_name] = case_output
        _make_unity_module(
            testdir,
            f'test_{case_name}',
            f'test_{case_name}',
            f"""\
TEST(group, {case_name}){case_output}
foo.c:100::PASS
-------------------
1 Tests 0 Failures 0 Ignored
OK
""",
        )

    result = testdir.runpytest(
        '-n',
        str(STRESS_WORKERS),
        '--max-worker-restart=0',
        '--junitxml',
        'report.xml',
    )

    result.assert_outcomes(passed=STRESS_TESTS)
    output = result.stdout.str()
    assert f'created: {STRESS_WORKERS}/{STRESS_WORKERS} workers' in output
    assert f'{STRESS_WORKERS} workers [{STRESS_TESTS} items]' in output

    suite, cases = _junit_cases()
    assert suite.get('tests') == str(STRESS_TESTS)
    assert suite.get('failures') == '0'
    assert suite.get('skipped') == '0'
    assert suite.get('errors') == '0'
    assert [case.get('name') for case in cases] == sorted(expected_output)

    for case in cases:
        assert case.get('is_unity_case') == '1'
        assert case.get('pytest_embedded_test_case') == f'test_{case.get("name")}'
        system_out = case.find('system-out')
        assert system_out is not None
        assert system_out.text == expected_output[case.get('name')]
