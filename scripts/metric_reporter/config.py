# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Configuration handling for the MetricReporter."""

import logging
import re
from configparser import NoSectionError, NoOptionError
from pathlib import Path

from pydantic import BaseModel, ValidationError, Field

from scripts.common.config import BaseConfig, InvalidConfigError, DIRECTORY_PATTERN


class MetricReporterArgs(BaseModel):
    """Model for MetricReporter arguments."""

    repository: str
    workflow: str
    test_suite: str
    test_artifact_directory_path: str
    test_metadata_directory_path: str
    csv_report_file_path: str


class MetricReporterConfig(BaseModel):
    """Model for MetricReporter configuration."""

    reports_dir: str = Field(..., pattern=DIRECTORY_PATTERN)


class Config(BaseConfig):
    """Configuration handler for the MetricReporter."""

    logger = logging.getLogger(__name__)

    def __init__(self, config_file: str = "config.ini") -> None:
        """Initialize the Config.

        Args:
            config_file (str): Path to the configuration file.

        Raises:
            InvalidConfigError: If the configuration file contains missing or invalid values,
                                or if an error occurs while building metric reporter arguments.
        """
        super().__init__(config_file)
        self.metric_reporter_config: MetricReporterConfig = self._parse_metric_reporter_config()
        self.metric_reporter_args: list[MetricReporterArgs] = self._build_metric_reporter_args()
        self.logger.info("Successfully loaded configuration")

    def _parse_metric_reporter_config(self) -> MetricReporterConfig:
        try:
            reports_dir: str = self.config_parser.get("metric_reporter", "reports_dir")
            return MetricReporterConfig(reports_dir=reports_dir)
        except (NoSectionError, NoOptionError, ValidationError) as error:
            error_mapping: dict[type, str] = {
                NoSectionError: "The 'metric_reporter' section is missing",
                NoOptionError: "Missing config option in 'metric_reporter' section",
                ValidationError: "Unexpected value or schema in 'metric_reporter' section",
            }
            error_msg: str = error_mapping[type(error)]
            self.logger.error(error_msg, exc_info=error)
            raise InvalidConfigError(error_msg, error)

    @staticmethod
    def _normalize_name(name: str, delimiter: str = "") -> str:
        normalized = re.sub(r"[^a-zA-Z0-9_]+", delimiter, name).lower()
        return normalized.strip("_")

    def _build_metric_reporter_args(self) -> list[MetricReporterArgs]:
        # Here we assume that the structure of the test_result_dir directory is as follows:
        # test_result_dir/
        #     ├── repository/
        #         ├── workflow/
        #             ├── test_suite/
        #                 ├── test_artifact_dir/
        #                 ├── test_metadata_dir/
        try:
            test_metric_args_list: list[MetricReporterArgs] = []
            test_result_dir_path = Path(self.common_config.test_result_dir)
            for directory_path, directory_names, files in test_result_dir_path.walk():
                for directory_name in directory_names:
                    current_path = Path(directory_path) / directory_name
                    artifact_path = current_path / self.common_config.test_artifact_dir
                    metadata_path = current_path / self.common_config.test_metadata_dir
                    if artifact_path.exists() or metadata_path.exists():
                        repository_name = self._normalize_name(
                            Path(directory_path).parents[0].name
                        )
                        test_suite_name = self._normalize_name(directory_name, "_")
                        csv_report_file_name = f"{repository_name}_{test_suite_name}_results.csv"
                        test_metric_args = MetricReporterArgs(
                            repository=repository_name,
                            workflow=directory_path.name,
                            test_suite=directory_name,
                            test_artifact_directory_path=str(artifact_path),
                            test_metadata_directory_path=str(metadata_path),
                            csv_report_file_path=str(
                                Path(self.metric_reporter_config.reports_dir)
                                / csv_report_file_name
                            ),
                        )
                        test_metric_args_list.append(test_metric_args)

            return test_metric_args_list
        except (OSError, ValidationError) as error:
            error_mapping: dict[type, str] = {
                OSError: "Filesystem error while building MetricReporter arguments",
                ValidationError: (
                    "Unexpected value or schema while building MetricReporter arguments"
                ),
            }
            error_msg: str = error_mapping[type(error)]
            self.logger.error(error_msg, exc_info=error)
            raise InvalidConfigError(error_msg, error)
