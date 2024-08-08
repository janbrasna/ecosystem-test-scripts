# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Module for parsing test suite results from JUnit XML content."""

import logging
import re
from pathlib import Path
from typing import Any

import defusedxml.ElementTree as ElementTree
from pydantic import BaseModel, ValidationError

from scripts.common.error import BaseError


class Property(BaseModel):
    """Represents a property of a test case."""

    name: str
    value: str


class Skipped(BaseModel):
    """Represents a skipped test case."""

    reason: str | None = None


class Failure(BaseModel):
    """Represents a failure of a test case."""

    message: str
    type: str | None = None
    text: str | None = None


class JUnitXMLSystemOut(BaseModel):
    """Represents system out information."""

    text: str | None = None


class JUnitXMLTestCase(BaseModel):
    """Represents a test case in a test suite."""

    name: str
    classname: str | None = None
    time: float | None = None
    properties: list[Property] | None = None
    skipped: Skipped | None = None
    failure: Failure | None = None
    system_out: JUnitXMLSystemOut | None = None


class JUnitXMLTestSuite(BaseModel):
    """Represents a test suite containing multiple test cases."""

    name: str
    timestamp: str | None = None
    hostname: str | None = None
    tests: int
    failures: int
    skipped: int | None = None
    time: float | None = None
    errors: int | None = None
    test_cases: list[JUnitXMLTestCase]


class JUnitXMLTestSuites(BaseModel):
    """Represents a collection of test suites."""

    id: str | None = None
    name: str | None = None
    tests: int | None = None
    failures: int | None = None
    skipped: int | None = None
    errors: int | None = None
    time: float | None = None
    timestamp: str | None = None
    test_suites: list[JUnitXMLTestSuite] = []


class JUnitXMLJobTestSuites(BaseModel):
    """Represents the test suite results for a CircleCI job."""

    job: int
    test_suites: list[JUnitXMLTestSuites]


class JUnitXmlParserError(BaseError):
    """Custom exception for errors raised by the JUnit XML parser."""

    pass


class JUnitXmlParser:
    """Parses JUnit XML files."""

    logger = logging.getLogger(__name__)

    @staticmethod
    def _normalize_xml_content(content: str) -> str:
        return re.sub(r"\x00", "", content)

    def _parse_test_case(self, test_case, xml_file_path: Path) -> dict[str, Any]:
        test_case_dict: dict[str, Any] = test_case.attrib
        for child in test_case:
            tag: str = child.tag
            if tag == "properties":
                test_case_dict["properties"] = [prop.attrib for prop in child]
            elif tag == "skipped":
                test_case_dict["skipped"] = child.attrib
            elif tag == "system-out":
                test_case_dict["system_out"] = {"text": child.text}
            elif tag == "failure":
                test_case_dict["failure"] = child.attrib
                test_case_dict["failure"]["text"] = child.text
            else:
                error_msg = f"Could not parse XML file, {xml_file_path}, unexpected tag: {tag}"
                self.logger.error(error_msg)
                raise JUnitXmlParserError(error_msg)
        return test_case_dict

    def _parse_test_suite(self, test_suite, xml_file_path: Path) -> dict[str, Any]:
        test_suite_dict: dict[str, Any] = test_suite.attrib
        test_suite_dict["test_cases"] = [
            self._parse_test_case(test_case, xml_file_path) for test_case in test_suite
        ]
        return test_suite_dict

    def parse(self, test_artifact_directory: str) -> list[JUnitXMLJobTestSuites]:
        """Parse JUnit XML content from the specified directory.

        Args:
            test_artifact_directory (str): The path to the directory containing the JUnit XML test
            files.

        Returns:
            list[JUnitXMLJobTestSuites]: A list of parsed `JUnitXMLJobTestSuites` objects.

        Raises:
            JUnitXmlParserError: If the directory does not exist, or if there is an error reading or
                                 parsing the XML files.
        """
        result: list[JUnitXMLJobTestSuites] = []

        test_artifact_path = Path(test_artifact_directory)
        if not test_artifact_directory or not test_artifact_path.is_dir():
            self.logger.warning(f"There are no test artifacts to parse in {test_artifact_path}")
            return []

        test_result_directories = sorted(test_artifact_path.iterdir())
        for directory in test_result_directories:
            job_number = int(directory.name)
            test_suites_list = []
            xml_files = sorted(directory.glob("*.xml"))
            for xml_file_path in xml_files:
                self.logger.info(f"Parsing {xml_file_path}")
                try:
                    with xml_file_path.open() as xml_file:
                        content: str = xml_file.read()
                        normalized_content: str = self._normalize_xml_content(content)

                        root = ElementTree.fromstring(normalized_content)
                        test_suites_dict: dict[str, Any] = root.attrib
                        test_suites_dict["test_suites"] = [
                            self._parse_test_suite(test_suite, xml_file_path)
                            for test_suite in root
                        ]
                        test_suites = JUnitXMLTestSuites(**test_suites_dict)

                        test_suites_list.append(test_suites)
                except (OSError, ElementTree.ParseError, ValidationError) as error:
                    error_mapping: dict[type, str] = {
                        OSError: f"Error reading the file {xml_file_path}",
                        ElementTree.ParseError: f"Error parsing the XML in file {xml_file_path}",
                        ValidationError: f"Unexpected value or schema in the file {xml_file_path}",
                    }
                    error_msg = error_mapping[type(error)]
                    self.logger.error(error_msg, exc_info=error)
                    raise JUnitXmlParserError(error_msg, error)

            result.append(JUnitXMLJobTestSuites(job=job_number, test_suites=test_suites_list))
        return result
