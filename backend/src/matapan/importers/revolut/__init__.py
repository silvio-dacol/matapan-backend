"""The verified English Revolut bank-statement CSV variant."""

from matapan.importers.revolut.revolut import (
    HEADERS,
    MAX_FILE_BYTES,
    PARSER_ID,
    PARSER_VERSION,
    Statement,
    StatementError,
    parse_statement,
)

__all__ = [
    "HEADERS",
    "MAX_FILE_BYTES",
    "PARSER_ID",
    "PARSER_VERSION",
    "Statement",
    "StatementError",
    "parse_statement",
]
