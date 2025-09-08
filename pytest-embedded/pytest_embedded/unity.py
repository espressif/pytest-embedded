import enum
import logging
import os
import re
import xml.etree.ElementTree as ET
from copy import deepcopy
from functools import reduce
from typing import Any, AnyStr
from xml.sax.saxutils import escape

from .utils import to_str

UNITY_BASIC_REGEX = re.compile(
    #        foo.c:          100:        test_case:                FAIL           :Expected 2 was 1
    r'(?P<file>.+):(?P<line>\d+):(?P<name>[^\r\n]+):(?P<result>PASS|FAIL|IGNORE)(?::(?P<message>.+))?'
)

UNITY_FIXTURE_REGEX = re.compile(
    # TEST (        group_name,         case_name )             stdout
    r'TEST\((?P<group>[^\s,]+), (?P<name>[^\r\n)]+)\)(?P<stdout>[\S\s]*?)'
    #           foo.c:          100::                  FAIL           : Expected 2 was 1
    r'(?:(?P<file>.+):(?P<line>\d+)::)?(?P<result>PASS|FAIL|IGNORE)(?::(?P<message>.+))?'
)

UNITY_SUMMARY_LINE_REGEX = re.compile(
    rb'^[-]+\s*(\d+) Tests (\d+) Failures (\d+) Ignored\s*(?P<result>OK|FAIL)',
    re.MULTILINE,
)

# https://www.w3.org/TR/xml11/#NT-Char
# https://www.w3.org/TR/xml11/#NT-RestrictedChar
_avoid_compatibility_chars = [
    (0x00, 0x08),
    (0x0B, 0x0C),
    (0x0E, 0x1F),
    (0x7F, 0x84),
    (0x86, 0x9F),
    (0xFDD0, 0xFDDF),
    (0xFFFE, 0xFFFF),
    (0x1FFFE, 0x1FFFF),
    (0x2FFFE, 0x2FFFF),
    (0x3FFFE, 0x3FFFF),
    (0x4FFFE, 0x4FFFF),
    (0x5FFFE, 0x5FFFF),
    (0x6FFFE, 0x6FFFF),
    (0x7FFFE, 0x7FFFF),
    (0x8FFFE, 0x8FFFF),
    (0x9FFFE, 0x9FFFF),
    (0xAFFFE, 0xAFFFF),
    (0xBFFFE, 0xBFFFF),
    (0xCFFFE, 0xCFFFF),
    (0xDFFFE, 0xDFFFF),
    (0xEFFFE, 0xEFFFF),
    (0xFFFFE, 0xFFFFF),
    (0x10FFFE, 0x10FFFF),
]
ILLEGAL_XML_CHAR_REGEX = re.compile(
    f'[{"".join([f"{chr(lower)}-{chr(upper)}" for lower, upper in _avoid_compatibility_chars])}]'
)


def escape_illegal_xml_chars(s: str) -> str:
    return ILLEGAL_XML_CHAR_REGEX.sub('', s)


def escape_dict_value(d: dict[str, Any]) -> dict[str, str]:
    escaped_dict = {}
    for k, v in d.items():
        escaped_dict[k] = escape(str(v))

    return escaped_dict


class TestFormat(enum.Enum):
    BASIC = 0
    FIXTURE = 1


class UnityTestReportMode(str, enum.Enum):
    REPLACE = 'replace'
    MERGE = 'merge'


class TestCase:
    def __init__(self, name: str, result: str, **kwargs):
        self.name = name
        self.result = result
        if self.result not in ['PASS', 'FAIL', 'IGNORE']:
            raise ValueError('Unity test case result should be one of "PASS", "FAIL", "IGNORE"')

        self.attrs = kwargs

        self._xml = None

    def to_xml(self) -> ET.Element:
        if self._xml:
            return self._xml

        message = self.attrs.pop('message', '').strip()
        stdout = self.attrs.pop('stdout', '').strip()

        sub_attrs = {}
        text = None
        if message and stdout:
            sub_attrs = {'message': message}
            text = stdout
        elif message:
            sub_attrs = {'message': message}
        elif stdout:
            if self.result == 'FAIL':
                sub_attrs = {'message': stdout}
            else:
                text = stdout

        child = None
        if self.result == 'FAIL':
            child = ET.Element('failure', attrib=escape_dict_value(sub_attrs))
            if text:
                child.text = escape(text)
        else:
            if sub_attrs or text:
                child = ET.Element('system-out', attrib=escape_dict_value(sub_attrs))
                if text:
                    child.text = escape(text)

        attrs = deepcopy(self.attrs)
        attrs['name'] = self.name
        testcase = ET.Element('testcase', attrib=escape_dict_value(attrs))
        if child is not None:
            testcase.append(child)

        self._xml = testcase
        return self._xml


class TestSuite:
    def __init__(self, name: str | None = None, **kwargs):
        # required
        self.name = name or kwargs.pop('name')  # may overwrite later

        # default stats
        self.attrs: dict[str, Any] = {
            'errors': 0,
            'failures': 0,
            'skipped': 0,
            'tests': 0,
        }
        self.attrs.update(kwargs)

        self.testcases: list[TestCase] = []

        self._xml = None

    @property
    def failed_cases(self) -> list[TestCase]:
        return [case for case in self.testcases if case.result == 'FAIL']

    def add_unity_test_cases(self, s: AnyStr, additional_attrs: dict[str, Any] | None = None) -> None:
        s = to_str(s)

        # check format
        check = UNITY_FIXTURE_REGEX.search(s)
        if check:
            regex = UNITY_FIXTURE_REGEX
        else:
            regex = UNITY_BASIC_REGEX

        # real parsing
        res = regex.finditer(s)
        for item in res:
            attrs = {k: v for k, v in item.groupdict().items() if v is not None}

            if additional_attrs:
                attrs.update(additional_attrs)

            testcase = TestCase(**attrs)
            self.testcases.append(testcase)
            if testcase.result == 'FAIL':
                self.attrs['failures'] += 1
            elif testcase.result == 'IGNORE':
                self.attrs['skipped'] += 1

            self.attrs['tests'] += 1

        if not self.testcases:
            raise ValueError(f'unity test case not found, buffer:\n{s}')

    def to_xml(self) -> ET.Element:
        if self._xml:
            return self._xml

        attrs = deepcopy(self.attrs)
        attrs['name'] = self.name

        testsuite = ET.Element('testsuite', attrib=escape_dict_value(self.attrs))
        if not self.testcases:
            raise ValueError('No test cases found!')

        for case in self.testcases:
            testsuite.append(case.to_xml())

        self._xml = testsuite
        return self._xml

    def dump(self, path: str) -> None:
        with open(path, 'w') as fw:
            fw.write(escape_illegal_xml_chars(ET.tostring(self.to_xml(), encoding='unicode')))


class JunitMerger:
    SUB_JUNIT_FILENAME = 'dut.xml'
    # multi-dut junit reports should be dut-[INDEX].xml

    def __init__(self, main_junit: str | None, unity_test_report_mode: str | None = None) -> None:
        self.junit_path = main_junit
        self.unity_test_report_mode = unity_test_report_mode or UnityTestReportMode.REPLACE.value

        self._junit = None

        self.failed = False

    @property
    def junit(self) -> ET.ElementTree:
        if self._junit:
            return self._junit

        self._junit = ET.parse(self.junit_path)
        return self._junit

    @staticmethod
    def _int_add(*args) -> str:
        return reduce(lambda a, b: str(int(a) + int(b)), args)

    def merge(self, junit_files: list[str]):
        if not self.junit_path:
            return

        # first round, merge the multi dut ones
        test_case_dir_sub_junit_files = {}
        for file in junit_files:
            if os.path.dirname(file) not in test_case_dir_sub_junit_files:
                test_case_dir_sub_junit_files[os.path.dirname(file)] = [file]
            else:
                test_case_dir_sub_junit_files[os.path.dirname(file)].append(file)

        _merged_multi_dut_junit_files = []
        for _dir, _junit_files in test_case_dir_sub_junit_files.items():
            merged_dut_junit_filepath = os.path.join(_dir, self.SUB_JUNIT_FILENAME)

            # multi-dut, multi junit files
            if len(_junit_files) > 1:
                _data = None
                for _junit_file in _junit_files:
                    logging.debug(f'Merging {_junit_file} to {merged_dut_junit_filepath}')
                    _junit = ET.parse(_junit_file)
                    _root = _junit.getroot()

                    if _data is None:
                        _data = _junit
                    else:
                        _data.getroot().extend(_root)
                        _data.getroot().attrib['errors'] = self._int_add(
                            _data.getroot().attrib['errors'], _root.attrib['errors']
                        )
                        _data.getroot().attrib['failures'] = self._int_add(
                            _data.getroot().attrib['failures'], _root.attrib['failures']
                        )
                        _data.getroot().attrib['skipped'] = self._int_add(
                            _data.getroot().attrib['skipped'], _root.attrib['skipped']
                        )
                        _data.getroot().attrib['tests'] = self._int_add(
                            _data.getroot().attrib['tests'],
                            _root.attrib['tests'],
                        )
                _data.write(merged_dut_junit_filepath)
            # multi-dut, single junit file
            elif _junit_files[0] != merged_dut_junit_filepath:
                _junit_file = _junit_files[0]
                logging.debug(f'Rename {_junit_file} to {merged_dut_junit_filepath}')
                os.rename(_junit_file, merged_dut_junit_filepath)

            _merged_multi_dut_junit_files.append(merged_dut_junit_filepath)

        # second round, merge the test case junit report back to the main junit report
        for file in _merged_multi_dut_junit_files:
            logging.debug(f'Merging {file} to {self.junit_path}')
            merging_xml = ET.parse(file)
            merging_cases = merging_xml.findall('testcase')
            merging_parent = merging_xml.getroot()

            # a normal file path should be /tmp/pytest-embedded/<test_case_name>/dut.xml
            test_case_name = os.path.basename(os.path.dirname(file))
            junit_parent = self.junit.find(f'.//testcase[@name="{test_case_name}"]...')
            junit_case = self.junit.find(f'.//testcase[@name="{test_case_name}"]')
            if junit_case is None:
                self.junit.write('debug.xml')
                raise ValueError(f'Could\'t find test case {test_case_name}, dumped into "debug.xml" for debugging')

            junit_case_is_fail = junit_case.find('failure') is not None

            junit_case.attrib['is_unity_case'] = '0'
            if self.unity_test_report_mode == UnityTestReportMode.REPLACE.value:
                junit_parent.remove(junit_case)

            for case in merging_cases:
                case.attrib['is_unity_case'] = '1'
                junit_parent.append(case)

            junit_parent.attrib['errors'] = self._int_add(
                junit_parent.attrib['errors'], merging_parent.attrib['errors']
            )
            junit_parent.attrib['failures'] = self._int_add(
                junit_parent.attrib['failures'],
                merging_parent.attrib['failures'],
                -int(junit_case_is_fail),
            )
            junit_parent.attrib['skipped'] = self._int_add(
                junit_parent.attrib['skipped'], merging_parent.attrib['skipped']
            )
            junit_parent.attrib['tests'] = self._int_add(
                junit_parent.attrib['tests'], merging_parent.attrib['tests'], -1
            )

            if int(junit_parent.attrib['failures']) > 0:
                self.failed = True

        self.junit.write(self.junit_path)
        logging.debug(f'Merged junit report dumped to {os.path.realpath(self.junit_path)}')
