# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Module for reporting test suite results from CircleCI metadata."""

import csv
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from scripts.common.error import BaseError
from scripts.metric_reporter.circleci_json_parser import CircleCIJsonParser
from scripts.metric_reporter.config import MetricReporterArgs
from scripts.metric_reporter.junit_xml_parser import JUnitXmlParser

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
SUCCESS_RESULTS = {"success", "system-out"}
FAILURE_RESULT = "failure"
SKIPPED_RESULT = "skipped"
CANCELED_JOB_STATUS = "canceled"


class Status(Enum):
    """Overall status of the test suite."""

    SUCCESS = "success"
    FAILED = "failed"
    UNKNOWN = "unknown"


class SuiteReporterResult(BaseModel):
    """Represents the results of a test suite run."""

    repository: str
    workflow: str
    test_suite: str

    # The timestamp between CI and JUnit XML is likely to be different since they represent job
    # start and test start respectively
    timestamp: str | None = None

    date: str | None = None
    job: int

    @property
    def status(self) -> Status:
        """Test Suite status"""
        # Note the CircleCI JSON has a status field, but it reflects the job status which may fail
        # for reasons other than test failure
        if self.failure > 0:
            return Status.FAILED
        if self.unknown > 0:
            return Status.UNKNOWN
        return Status.SUCCESS

    # The summation of all test run times in seconds. Parallelization is not taken into
    # consideration.
    run_time: float = 0

    # JUnit XML only. Equal to the longest run_time in seconds when tests are run in parallel.
    # We know tests are run in parallel if we have multiple reports for a
    # repository/workflow/test_suite
    execution_time: float | None = None

    # CI only. The amount of time for the test CI Job in seconds.
    job_execution_time: float | None = None

    success: int = 0
    failure: int = 0
    skipped: int = 0

    # JUnit XML only. An annotation available in Playwright only. Subset of 'skipped'.
    fixme: int = 0

    # CI only. When CircleCI fails to classify a test as 'success', 'failure' or 'skipped' it is set
    # to unknown.
    unknown: int = 0

    # JUnit XML only. The number of tests that were the result of a re-execution. It is possible
    # that the same test is re-executed more than once.
    retry: int = 0

    @property
    def total(self) -> int:
        """Calculate the total number of tests."""
        return self.success + self.failure + self.skipped + self.unknown

    @property
    def success_rate(self) -> float | None:
        """Calculate the success rate of the test suite."""
        return self._calculate_rate(self.success, self.total)

    @property
    def failure_rate(self) -> float | None:
        """Calculate the failure rate of the test suite."""
        return self._calculate_rate(self.failure, self.total)

    @property
    def skipped_rate(self) -> float | None:
        """Calculate the skipped rate of the test suite."""
        return self._calculate_rate(self.skipped, self.total)

    @property
    def fixme_rate(self) -> float | None:
        """Calculate the fixme rate of the test suite."""
        return self._calculate_rate(self.fixme, self.total)

    @property
    def unknown_rate(self) -> float | None:
        """Calculate the unknown rate of the test suite."""
        return self._calculate_rate(self.unknown, self.total)

    @staticmethod
    def _calculate_rate(value: int, total: int) -> float | None:
        """Calculate the percentage rate of a given value over the total.

        Args:
            value (int): The numerator for the rate calculation.
            total (int): The denominator for the rate calculation.

        Returns:
            float | None: The calculated rate as a percentage, or None if the total is 0.
        """
        return round((value / total) * 100, 2) if total > 0 else None

    def dict_with_fieldnames(self) -> dict[str, Any]:
        """Convert the test suite result to a dictionary with field names.

        Returns:
            dict[str, Any]: Dictionary representation of the test suite result.
        """
        return {
            "Repository": self.repository,
            "Workflow": self.workflow,
            "Test Suite": self.test_suite,
            "Date": self.date,
            "Timestamp": self.timestamp,
            "Job Number": self.job,
            "Status": self.status.value,
            "Execution Time": self.execution_time,
            "Job Execution Time": self.job_execution_time,
            "Run Time": self.run_time,
            "Success": self.success,
            "Failure": self.failure,
            "Skipped": self.skipped,
            "Fixme": self.fixme,
            "Unknown": self.unknown,
            "Retry Count": self.retry,
            "Total": self.total,
            "Success Rate (%)": self.success_rate,
            "Failure Rate (%)": self.failure_rate,
            "Skipped Rate (%)": self.skipped_rate,
            "Fixme Rate (%)": self.fixme_rate,
            "Unknown Rate (%)": self.unknown_rate,
        }


class SuiteReporterError(BaseError):
    """Exception raised for errors in the SuiteReporter."""

    pass


class SuiteReporter:
    """Handles the reporting of test suite results from CircleCI metadata and JUnit XML Reports."""

    logger = logging.getLogger(__name__)

    def __init__(self, args: MetricReporterArgs) -> None:
        """Initialize the reporter with the directory containing test result data.

        Args:
            args (MetricReporterArgs): MetricReporter script arguments.

        Raises:
            CircleCIJsonParserError: If there is an error parsing the test metadata.
            JUnitXmlParserError: If there is an error parsing JUnit XML test results.
        """
        self._repository = args.repository
        self._workflow = args.workflow
        self._test_suite = args.test_suite
        # Path to the directory with JUnit XML test results
        self._test_artifact_directory: str = args.test_artifact_directory_path
        # Path to the directory with CircleCI test metadata.
        self._test_metadata_directory: str = args.test_metadata_directory_path

        self.results: list[SuiteReporterResult] = self._parse_results()

    def _parse_results(self) -> list[SuiteReporterResult]:
        metadata_results_dict: dict[int, SuiteReporterResult] = self._parse_circleci_metadata()
        artifact_results_dict: dict[int, SuiteReporterResult] = self._parse_junit_xmls()

        # Reconcile data preferring artifact results, but use 'job_execution_time' from metadata
        # results if available
        results: list[SuiteReporterResult] = []
        for job_number, artifact_result in artifact_results_dict.items():
            metadata_result = metadata_results_dict.pop(job_number, None)
            if metadata_result:
                self._check_for_mismatch(artifact_result, metadata_result)
                artifact_result.job_execution_time = metadata_result.job_execution_time
            results.append(artifact_result)
        # Add remaining metadata results that were not matched
        results.extend(metadata_results_dict.values())

        # Sort by timestamp and then by job
        sorted_results = sorted(results, key=lambda result: (result.timestamp, result.job))
        return sorted_results

    def _parse_circleci_metadata(self) -> dict[int, SuiteReporterResult]:
        results: dict[int, SuiteReporterResult] = {}
        circleci_parser = CircleCIJsonParser()
        for job_test_metadata in circleci_parser.parse(self._test_metadata_directory):
            if (
                not job_test_metadata.test_metadata
                or job_test_metadata.job.status == CANCELED_JOB_STATUS
            ):
                continue

            started_at = datetime.strptime(job_test_metadata.job.started_at, DATETIME_FORMAT)
            stopped_at = datetime.strptime(job_test_metadata.job.stopped_at, DATETIME_FORMAT)
            job_execution_time = (stopped_at - started_at).total_seconds()
            test_suite_result = SuiteReporterResult(
                repository=self._repository,
                workflow=self._workflow,
                test_suite=self._test_suite,
                job=job_test_metadata.job.job_number,
                date=started_at.strftime(DATE_FORMAT),
                timestamp=job_test_metadata.job.started_at,
                job_execution_time=job_execution_time,
            )

            run_time: float = 0
            for test in job_test_metadata.test_metadata:
                run_time += test.run_time
                if test.result in SUCCESS_RESULTS:
                    test_suite_result.success += 1
                elif test.result == FAILURE_RESULT:
                    test_suite_result.failure += 1
                elif test.result == SKIPPED_RESULT:
                    test_suite_result.skipped += 1
                else:
                    test_suite_result.unknown += 1
            test_suite_result.run_time = round(run_time, 3)

            results[job_test_metadata.job.job_number] = test_suite_result
        return results

    def _parse_junit_xmls(self) -> dict[int, SuiteReporterResult]:
        results: dict[int, SuiteReporterResult] = {}
        junit_xml_parser = JUnitXmlParser()
        for job_test_suites in junit_xml_parser.parse(self._test_artifact_directory):
            test_suite_result = SuiteReporterResult(
                repository=self._repository,
                workflow=self._workflow,
                test_suite=self._test_suite,
                job=job_test_suites.job,
            )

            run_times: list[float] = []
            execution_times: list[float] = []
            for test_suites in job_test_suites.test_suites:
                run_time: float = 0
                # Jest and Playwright JUnit XMLs only have a top level time. The top level time may
                # not be equal to the sum of the test case times due to the use of threads/workers.
                execution_time: float | None = (
                    test_suites.time if test_suites.time and test_suites.time > 0 else None
                )
                for test_suite in test_suites.test_suites:
                    if not test_suite_result.date and test_suite.timestamp:
                        test_suite_result.timestamp = test_suite.timestamp
                        test_suite_result.date = test_suite.timestamp.split("T")[0]

                    # Mocha test reporting has been known to inaccurately total the number of tests
                    # in the 'tests' attribute, so we count the number of test cases
                    tests = len(test_suite.test_cases)
                    skipped = test_suite.skipped if test_suite.skipped else 0
                    test_suite_result.failure += test_suite.failures
                    test_suite_result.skipped += skipped
                    test_suite_result.success += tests - test_suite.failures - skipped

                    for test_case in test_suite.test_cases:
                        # Summing the time for each test case if test_suite.time is not available
                        if test_case.time:
                            run_time += test_case.time

                        # Increment "fixme" count , Playwright only
                        if test_case.properties and any(
                            prop.name == "fixme" for prop in test_case.properties
                        ):
                            test_suite_result.fixme += 1

                        # Check for retry condition
                        # An assumption is made that the presence of a nested system-out tag in a
                        # test case that contains a link to a trace.zip attachment file as content
                        # is the result of a retry in Playwright.
                        if (
                            test_case.system_out
                            and test_case.system_out.text
                            and "trace.zip" in test_case.system_out.text
                        ):
                            test_suite_result.retry += 1
                run_times.append(run_time)
                # If a time at the test suites level is not provided, then use the summation of
                # times at the test case level, or run_time.
                execution_times.append(execution_time if execution_time is not None else run_time)
            test_suite_result.run_time = round(sum(run_times), 3)
            test_suite_result.execution_time = round(max(execution_times), 3)
            results[job_test_suites.job] = test_suite_result
        return results

    def _check_for_mismatch(
        self, artifact_result: SuiteReporterResult, metadata_result: SuiteReporterResult
    ) -> None:
        excluded_field_set = {
            "job",
            "repository",
            "workflow",
            "test_suite",
            "timestamp",
            "execution_time",
            "job_execution_time",
            "fixme",
            "retry",
        }
        artifact_data: dict[str, Any] = {
            f: v for f, v in artifact_result.model_dump().items() if f not in excluded_field_set
        }
        metadata_data: dict[str, Any] = {
            f: v for f, v in metadata_result.model_dump().items() if f not in excluded_field_set
        }
        mismatches: dict[str, Any] = {
            f: (artifact_data[f], metadata_data.get(f))
            for f in artifact_data
            if artifact_data[f] != metadata_data.get(f)
        }
        if mismatches:
            self.logger.warning(
                f"Mismatches detected for {artifact_result.repository}/{artifact_result.workflow}/"
                f"{artifact_result.test_suite}/{artifact_result.job}, executed on "
                f"{artifact_result.timestamp}:\n"
                f"Mismatched Fields: {mismatches}"
            )

    def output_results_csv(self, report_path: str) -> None:
        """Output the test suite results to a CSV file.

        Args:
            report_path (str): Path to the file where the CSV report will be saved.

        Raises:
            SuiteReporterError: If the report file cannot be created or written to, or if
                                          there is an issue with the test data.
        """
        try:
            Path(report_path).parent.mkdir(parents=True, exist_ok=True)
            if not self.results:
                self.logger.info("No data to write to the CSV file.")
                return

            fieldnames: list[str] = list(self.results[0].dict_with_fieldnames().keys())
            with open(report_path, "w", newline="") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                for result in self.results:
                    writer.writerow(result.dict_with_fieldnames())
        except (OSError, IOError) as error:
            error_mapping: dict[type, str] = {
                OSError: "Error creating directories for the report file",
                IOError: "The report file cannot be created or written to",
            }
            error_msg: str = error_mapping[type(error)]
            self.logger.error(error_msg, exc_info=error)
            raise SuiteReporterError(error_msg, error)
