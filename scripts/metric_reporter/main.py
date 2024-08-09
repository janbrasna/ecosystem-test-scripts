# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Main module for running the Metric Reporter."""

import argparse
import logging

from scripts.metric_reporter.circleci_json_parser import (
    CircleCIJsonParserError,
    CircleCIJsonParser,
    CircleCIJobTestMetadata,
)
from scripts.metric_reporter.config import Config, InvalidConfigError
from scripts.metric_reporter.junit_xml_parser import JUnitXmlParser, JUnitXMLJobTestSuites
from scripts.metric_reporter.suite_reporter import SuiteReporter, SuiteReporterError

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main(config_file: str = "config.ini") -> None:
    """Run the Metric Reporter.

    Args:
        config_file (str): Path to the configuration file. Defaults to 'ecosystem-test-scripts/config.ini'.
    """
    try:
        logger.info(f"Starting Metric Reporter with configuration file: {config_file}")
        config = Config(config_file)
        for metric_reporter_args in config.metric_reporter_args:
            circleci_job_test_metadata_list: list[CircleCIJobTestMetadata] | None = None
            if metric_reporter_args.test_metadata_directory:
                circleci_parser = CircleCIJsonParser()
                circleci_job_test_metadata_list = circleci_parser.parse(
                    metric_reporter_args.test_metadata_directory
                )

            junit_xml_job_test_suites_list: list[JUnitXMLJobTestSuites] | None = None
            if metric_reporter_args.test_artifact_directory:
                junit_xml_parser = JUnitXmlParser()
                junit_xml_job_test_suites_list = junit_xml_parser.parse(
                    metric_reporter_args.test_artifact_directory
                )

            reporter = SuiteReporter(
                metric_reporter_args.repository,
                metric_reporter_args.workflow,
                metric_reporter_args.test_suite,
                circleci_job_test_metadata_list,
                junit_xml_job_test_suites_list,
            )
            reporter.output_results_csv(metric_reporter_args.csv_report_file_path)

        logger.info("Reporting complete")
    except InvalidConfigError as error:
        logger.error(f"Configuration error: {error}")
    except CircleCIJsonParserError as error:
        logger.error(f"CircleCI JSON Parsing error: {error}")
    except SuiteReporterError as error:
        logger.error(f"Test Suite Reporter error: {error}")
    except Exception as error:
        logger.error(f"Unexpected error: {error}", exc_info=error)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Metric Reporter")
    parser.add_argument("--config", help="Path to the config.ini file", default="config.ini")
    args = parser.parse_args()
    main(args.config)
