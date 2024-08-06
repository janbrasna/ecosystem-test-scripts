# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Main module for running the MetricReporter."""

import argparse
import logging

from scripts.metric_reporter.circleci_json_parser import CircleCIJsonParserError
from scripts.metric_reporter.config import Config, InvalidConfigError
from scripts.metric_reporter.suite_reporter import SuiteReporter, SuiteReporterError

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main(config_file: str = "config.ini") -> None:
    """Run the MetricReporter.

    Args:
        config_file (str): Path to the configuration file. Defaults to 'ecosystem-test-scripts/config.ini'.
    """
    try:
        logger.info(f"Starting MetricReporter with configuration file: {config_file}")
        config = Config(config_file)
        for metric_reporter_args in config.metric_reporter_args:
            reporter = SuiteReporter(metric_reporter_args)
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
    parser = argparse.ArgumentParser(description="Run the MetricReporter")
    parser.add_argument("--config", help="Path to the config.ini file", default="config.ini")
    args = parser.parse_args()
    main(args.config)
