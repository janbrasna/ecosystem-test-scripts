# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Tests for the SuiteReporter module."""

import logging
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest import LogCaptureFixture
from pytest_mock import MockerFixture

from scripts.metric_reporter.config import MetricReporterArgs
from scripts.metric_reporter.suite_reporter import SuiteReporter, SuiteReporterResult

TEST_ARTIFACT_DIRECTORY_TEST_RESULTS = str(
    Path(__file__).parent / "test_data" / "test_artifact_directory_test_results"
)
TEST_METADATA_DIRECTORY_EMPTY_TEST_RESULTS = str(
    Path(__file__).parent / "test_data" / "test_metadata_directory_empty_test_results"
)
TEST_METADATA_DIRECTORY_TEST_RESULTS = str(
    Path(__file__).parent / "test_data" / "test_metadata_directory_test_results"
)

EXPECTED_ARTIFACT_RESULTS = [
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-01T00:00:00Z",
        date="2024-01-01",
        job=1,
        run_time=1.1,
        execution_time=1.1,
        failure=1,
        retry=1,
    ),
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-02T00:00:00Z",
        date="2024-01-02",
        job=2,
        run_time=1.2,
        execution_time=1.2,
        skipped=1,
        fixme=1,
    ),
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-03T00:00:00Z",
        date="2024-01-03",
        job=3,
        run_time=1.3,
        execution_time=1.3,
        success=1,
        retry=1,
    ),
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-04T00:00:00Z",
        date="2024-01-04",
        job=4,
        run_time=1.4,
        execution_time=1.4,
        skipped=1,
    ),
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-05T00:00:00Z",
        date="2024-01-05",
        job=5,
        run_time=1.5,
        execution_time=1.5,
        success=1,
    ),
]
EXPECTED_METADATA_RESULTS = [
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-01T00:00:00Z",
        date="2024-01-01",
        job=1,
        run_time=1.1,
        job_execution_time=3600.0,
        failure=1,
    ),
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-02T00:00:00Z",
        date="2024-01-02",
        job=2,
        run_time=1.2,
        job_execution_time=3600.0,
        skipped=1,
    ),
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-03T00:00:00Z",
        date="2024-01-03",
        job=3,
        run_time=1.3,
        job_execution_time=3600.0,
        success=1,
    ),
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-04T00:00:00Z",
        date="2024-01-04",
        job=4,
        run_time=1.4,
        job_execution_time=3600.0,
        skipped=1,
    ),
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-05T00:00:00Z",
        date="2024-01-05",
        job=5,
        run_time=1.5,
        job_execution_time=3600.0,
        success=1,
    ),
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-06T00:00:00Z",
        date="2024-01-06",
        job=6,
        run_time=1.6,
        job_execution_time=3600.0,
        unknown=1,
    ),
]
EXPECTED_ARTIFACT_AND_METADATA_RESULTS = [
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-01T00:00:00Z",
        date="2024-01-01",
        job=1,
        run_time=1.1,
        execution_time=1.1,
        job_execution_time=3600.0,
        failure=1,
        retry=1,
    ),
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-02T00:00:00Z",
        date="2024-01-02",
        job=2,
        run_time=1.2,
        execution_time=1.2,
        job_execution_time=3600.0,
        skipped=1,
        fixme=1,
    ),
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-03T00:00:00Z",
        date="2024-01-03",
        job=3,
        run_time=1.3,
        execution_time=1.3,
        job_execution_time=3600.0,
        success=1,
        retry=1,
    ),
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-04T00:00:00Z",
        date="2024-01-04",
        job=4,
        run_time=1.4,
        execution_time=1.4,
        job_execution_time=3600.0,
        skipped=1,
    ),
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-05T00:00:00Z",
        date="2024-01-05",
        job=5,
        run_time=1.5,
        execution_time=1.5,
        job_execution_time=3600.0,
        success=1,
    ),
    SuiteReporterResult(
        repository="repo",
        workflow="main",
        test_suite="suite",
        timestamp="2024-01-06T00:00:00Z",
        date="2024-01-06",
        job=6,
        run_time=1.6,
        job_execution_time=3600.0,
        unknown=1,
    ),
]

EXPECTED_ARTIFACT_CSV = (
    "Repository,Workflow,Test Suite,Date,Timestamp,Job Number,Status,Execution Time,Job Execution Time,Run Time,Success,Failure,Skipped,Fixme,Unknown,Retry Count,Total,Success Rate (%),Failure Rate (%),Skipped Rate (%),Fixme Rate (%),Unknown Rate (%)\r\n"
    "repo,main,suite,2024-01-01,2024-01-01T00:00:00Z,1,failed,1.1,,1.1,0,1,0,0,0,1,1,0.0,100.0,0.0,0.0,0.0\r\n"
    "repo,main,suite,2024-01-02,2024-01-02T00:00:00Z,2,success,1.2,,1.2,0,0,1,1,0,0,1,0.0,0.0,100.0,100.0,0.0\r\n"
    "repo,main,suite,2024-01-03,2024-01-03T00:00:00Z,3,success,1.3,,1.3,1,0,0,0,0,1,1,100.0,0.0,0.0,0.0,0.0\r\n"
    "repo,main,suite,2024-01-04,2024-01-04T00:00:00Z,4,success,1.4,,1.4,0,0,1,0,0,0,1,0.0,0.0,100.0,0.0,0.0\r\n"
    "repo,main,suite,2024-01-05,2024-01-05T00:00:00Z,5,success,1.5,,1.5,1,0,0,0,0,0,1,100.0,0.0,0.0,0.0,0.0\r\n"
)
EXPECTED_METADATA_CSV = (
    "Repository,Workflow,Test Suite,Date,Timestamp,Job Number,Status,Execution Time,Job Execution Time,Run Time,Success,Failure,Skipped,Fixme,Unknown,Retry Count,Total,Success Rate (%),Failure Rate (%),Skipped Rate (%),Fixme Rate (%),Unknown Rate (%)\r\n"
    "repo,main,suite,2024-01-01,2024-01-01T00:00:00Z,1,failed,,3600.0,1.1,0,1,0,0,0,0,1,0.0,100.0,0.0,0.0,0.0\r\n"
    "repo,main,suite,2024-01-02,2024-01-02T00:00:00Z,2,success,,3600.0,1.2,0,0,1,0,0,0,1,0.0,0.0,100.0,0.0,0.0\r\n"
    "repo,main,suite,2024-01-03,2024-01-03T00:00:00Z,3,success,,3600.0,1.3,1,0,0,0,0,0,1,100.0,0.0,0.0,0.0,0.0\r\n"
    "repo,main,suite,2024-01-04,2024-01-04T00:00:00Z,4,success,,3600.0,1.4,0,0,1,0,0,0,1,0.0,0.0,100.0,0.0,0.0\r\n"
    "repo,main,suite,2024-01-05,2024-01-05T00:00:00Z,5,success,,3600.0,1.5,1,0,0,0,0,0,1,100.0,0.0,0.0,0.0,0.0\r\n"
    "repo,main,suite,2024-01-06,2024-01-06T00:00:00Z,6,unknown,,3600.0,1.6,0,0,0,0,1,0,1,0.0,0.0,0.0,0.0,100.0\r\n"
)
EXPECTED_ARTIFACT_AND_METADATA_CSV = (
    "Repository,Workflow,Test Suite,Date,Timestamp,Job Number,Status,Execution Time,Job Execution Time,Run Time,Success,Failure,Skipped,Fixme,Unknown,Retry Count,Total,Success Rate (%),Failure Rate (%),Skipped Rate (%),Fixme Rate (%),Unknown Rate (%)\r\n"
    "repo,main,suite,2024-01-01,2024-01-01T00:00:00Z,1,failed,1.1,3600.0,1.1,0,1,0,0,0,1,1,0.0,100.0,0.0,0.0,0.0\r\n"
    "repo,main,suite,2024-01-02,2024-01-02T00:00:00Z,2,success,1.2,3600.0,1.2,0,0,1,1,0,0,1,0.0,0.0,100.0,100.0,0.0\r\n"
    "repo,main,suite,2024-01-03,2024-01-03T00:00:00Z,3,success,1.3,3600.0,1.3,1,0,0,0,0,1,1,100.0,0.0,0.0,0.0,0.0\r\n"
    "repo,main,suite,2024-01-04,2024-01-04T00:00:00Z,4,success,1.4,3600.0,1.4,0,0,1,0,0,0,1,0.0,0.0,100.0,0.0,0.0\r\n"
    "repo,main,suite,2024-01-05,2024-01-05T00:00:00Z,5,success,1.5,3600.0,1.5,1,0,0,0,0,0,1,100.0,0.0,0.0,0.0,0.0\r\n"
    "repo,main,suite,2024-01-06,2024-01-06T00:00:00Z,6,unknown,,3600.0,1.6,0,0,0,0,1,0,1,0.0,0.0,0.0,0.0,100.0\r\n"
)


@pytest.mark.parametrize(
    "test_artifact_directory, test_metadata_directory, expected_results",
    [
        (TEST_ARTIFACT_DIRECTORY_TEST_RESULTS, "", EXPECTED_ARTIFACT_RESULTS),
        ("", TEST_METADATA_DIRECTORY_TEST_RESULTS, EXPECTED_METADATA_RESULTS),
        (
            TEST_ARTIFACT_DIRECTORY_TEST_RESULTS,
            TEST_METADATA_DIRECTORY_TEST_RESULTS,
            EXPECTED_ARTIFACT_AND_METADATA_RESULTS,
        ),
        ("", TEST_METADATA_DIRECTORY_EMPTY_TEST_RESULTS, []),
    ],
    ids=[
        "with_artifact_test_results",
        "with_metadata_test_results",
        "with_artifact_metadata_test_results",
        "with_empty_test_results",
    ],
)
def test_suite_reporter_init(
    test_artifact_directory: str,
    test_metadata_directory: str,
    expected_results: list[SuiteReporterResult],
) -> None:
    """Test SuiteReporter initialization.

    Args:
        test_artifact_directory (str): Directory for artifacts.
        test_metadata_directory (str): Directory for metadata.
        expected_results (list[SuiteReporterResult]): Expected results from the SuiteReporter.
    """
    args = MetricReporterArgs(
        repository="repo",
        workflow="main",
        test_suite="suite",
        test_artifact_directory_path=test_artifact_directory,
        test_metadata_directory_path=test_metadata_directory,
        csv_report_file_path="",
    )

    reporter = SuiteReporter(args)

    assert reporter.results == expected_results


@pytest.mark.parametrize(
    "test_artifact_directory, test_metadata_directory, expected_csv",
    [
        (TEST_ARTIFACT_DIRECTORY_TEST_RESULTS, "", EXPECTED_ARTIFACT_CSV),
        ("", TEST_METADATA_DIRECTORY_TEST_RESULTS, EXPECTED_METADATA_CSV),
        (
            TEST_ARTIFACT_DIRECTORY_TEST_RESULTS,
            TEST_METADATA_DIRECTORY_TEST_RESULTS,
            EXPECTED_ARTIFACT_AND_METADATA_CSV,
        ),
    ],
    ids=[
        "with_artifact_test_results",
        "with_metadata_test_results",
        "with_artifact_metadata_test_results",
    ],
)
def test_suite_reporter_output_csv(
    mocker: MockerFixture,
    test_artifact_directory: str,
    test_metadata_directory: str,
    expected_csv: str,
) -> None:
    """Test SuiteReporter output_results_csv method with test results.

    Args:
        mocker (MockerFixture): pytest_mock fixture for mocking.
        test_artifact_directory (str): Directory for artifacts.
        test_metadata_directory (str): Directory for metadata.
        expected_csv (dtr): Expected csv output from the SuiteReporter.
    """
    args = MetricReporterArgs(
        repository="repo",
        workflow="main",
        test_suite="suite",
        test_artifact_directory_path=test_artifact_directory,
        test_metadata_directory_path=test_metadata_directory,
        csv_report_file_path="",
    )
    reporter = SuiteReporter(args)
    report_path = "fake_path.csv"

    mock_open: MagicMock = mocker.mock_open()
    mocker.patch("builtins.open", mock_open)
    mocker.patch("os.makedirs")

    reporter.output_results_csv(report_path)

    mock_open.assert_called_once_with(report_path, "w", newline="")
    handle = mock_open()
    actual_csv = "".join(call[0][0] for call in handle.write.call_args_list)
    assert actual_csv == expected_csv


def test_suite_reporter_output_csv_with_empty_test_results(
    caplog: LogCaptureFixture, mocker: MockerFixture
) -> None:
    """Test SuiteReporter output_results_csv method with no test results.

    Args:
        caplog (LogCaptureFixture): pytest fixture for capturing log output.
        mocker (MockerFixture): pytest_mock fixture for mocking.
    """
    args = MetricReporterArgs(
        repository="repo",
        workflow="main",
        test_suite="suite",
        test_artifact_directory_path="",
        test_metadata_directory_path=TEST_METADATA_DIRECTORY_EMPTY_TEST_RESULTS,
        csv_report_file_path="",
    )
    reporter = SuiteReporter(args)
    report_path = "fake_path.csv"
    expected_log = "No data to write to the CSV file."

    with caplog.at_level(logging.INFO):
        mock_open: MagicMock = mocker.mock_open()
        mocker.patch("builtins.open", mock_open)
        mocker.patch("os.makedirs")

        reporter.output_results_csv(report_path)

        mock_open.assert_not_called()
        assert expected_log in caplog.text
