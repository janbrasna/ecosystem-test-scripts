# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Custom error handling for the ecosystem test scripts."""


class BaseError(Exception):
    """Base class for custom exceptions in the ecosystem test scripts."""

    def __init__(self, message: str, inner_exception: Exception | None = None) -> None:
        """Initialize the BaseError.

        Args:
            message (str): The error message.
            inner_exception (Exception | None): The inner exception that caused this error, if any.
        """
        super().__init__(message)
        self.inner_exception = inner_exception

    def __str__(self) -> str:
        """Return the string representation of the error.

        Returns:
            str: The error message, including the inner exception if present.
        """
        if self.inner_exception:
            return f"{super().__str__()} (caused by {self.inner_exception})"
        return super().__str__()
