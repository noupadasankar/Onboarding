"""Loader-specific exceptions.

All exceptions inherit from LoaderError so callers can catch the whole
hierarchy with a single except clause, or handle specific cases individually.
"""


class LoaderError(Exception):
    """Base class for all document loading failures."""


class UnsupportedFileTypeError(LoaderError):
    """Raised when no loader exists for the given file extension."""


class CorruptedFileError(LoaderError):
    """Raised when the file cannot be parsed (malformed bytes, truncated, etc.)."""


class PasswordProtectedFileError(LoaderError):
    """Raised when a file is encrypted and the password is not provided."""


class EmptyFileError(LoaderError):
    """Raised when the file contains no bytes or no extractable content."""


class InvalidEncodingError(LoaderError):
    """Raised when a text file cannot be decoded with any detectable encoding."""
