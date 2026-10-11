"""Parse the supplied UTF-8 English statement format, without persistence."""

import csv
import hashlib
import io
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext

PARSER_ID = "revolut_bank_csv_en"
PARSER_VERSION = "1"
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_ROWS = 10_000
HEADERS = (
    "Type",
    "Product",
    "Started Date",
    "Completed Date",
    "Description",
    "Amount",
    "Fee",
    "Currency",
    "State",
    "Balance",
)
PRODUCTS = {"Current", "Savings"}


class StatementError(ValueError):
    """An unsupported file; messages never contain private source values."""


def decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if value == 0 else text


def money(value: str) -> Decimal:
    if not re.fullmatch(r"-?(0|[1-9][0-9]{0,19})(\.[0-9]{1,8})?", value):
        raise ValueError("Expected a decimal with at most 20 integer and 8 fractional digits")
    return Decimal(value)


def timestamp(value: str) -> datetime:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", value):
        raise ValueError("Expected YYYY-MM-DD HH:MM:SS")
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


@dataclass(frozen=True)
class Row:
    row_number: int
    product: str
    currency_code: str
    transaction_type: str
    source_state: str
    source_description: str
    started_at: datetime | None
    posted_at: datetime | None
    source_amount: Decimal | None
    fee: Decimal | None
    amount: Decimal | None
    balance: Decimal | None
    fingerprint: str | None
    errors: tuple[str, ...]


@dataclass(frozen=True)
class Statement:
    file_hash: str
    rows: tuple[Row, ...]


def parse_row(number: int, values: list[str]) -> Row:
    if len(values) != len(HEADERS):
        return Row(
            number,
            "",
            "",
            "",
            "",
            "",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            ("Row has a different number of fields from the header.",),
        )
    source = dict(zip(HEADERS, values, strict=True))
    errors = []
    product = source["Product"].strip()
    currency = source["Currency"].strip()
    state = source["State"].strip()
    kind = source["Type"].strip()
    description = source["Description"].strip()
    if product not in PRODUCTS:
        errors.append("Unsupported Product; only Current and Savings are supported.")
    if not re.fullmatch(r"[A-Z]{3}", currency):
        errors.append("Currency must contain three uppercase letters.")
    if not kind or len(kind) > 64:
        errors.append("Type is missing or too long.")
    if len(description) > 500:
        errors.append("Description exceeds the supported 500 characters.")
    dates = {}
    for column in ("Started Date", "Completed Date"):
        try:
            dates[column] = timestamp(source[column].strip())
        except ValueError:
            dates[column] = None
            if column == "Started Date" or state == "COMPLETED":
                errors.append(f"{column} must use YYYY-MM-DD HH:MM:SS.")
    amounts = {}
    for column in ("Amount", "Fee", "Balance"):
        value = source[column].strip()
        if column == "Balance" and not value:
            amounts[column] = None
            continue
        try:
            amounts[column] = money(value)
        except ValueError:
            amounts[column] = None
            errors.append(f"{column} must be a supported exact decimal.")
    if amounts["Fee"] is not None and amounts["Fee"] < 0:
        errors.append("Negative fees are not supported by this verified variant.")
    net = None
    if amounts["Amount"] is not None and amounts["Fee"] is not None:
        with localcontext() as context:
            context.prec = 64
            net = amounts["Amount"] - amounts["Fee"]
    fingerprint = None
    if not errors and state == "COMPLETED":
        normalized_description = " ".join(
            unicodedata.normalize("NFKC", description).casefold().split()
        )
        identity = [
            product,
            currency,
            kind,
            dates["Completed Date"].date().isoformat(),
            decimal_text(net),
            decimal_text(amounts["Fee"]),
            normalized_description,
        ]
        fingerprint = hashlib.sha256(
            json.dumps(identity, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
    return Row(
        number,
        product,
        currency,
        kind,
        state,
        description,
        dates["Started Date"],
        dates["Completed Date"],
        amounts["Amount"],
        amounts["Fee"],
        net,
        amounts["Balance"],
        fingerprint,
        tuple(errors),
    )


def parse_statement(content: bytes) -> Statement:
    if len(content) > MAX_FILE_BYTES:
        raise StatementError("Statement exceeds the 10 MiB file limit.")
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise StatementError("Expected a UTF-8 English Revolut CSV statement.") from error
    reader = csv.reader(io.StringIO(decoded, newline=""), strict=True)
    try:
        if tuple(next(reader, [])) != HEADERS:
            raise StatementError("Unsupported CSV header; upload the documented Revolut variant.")
        rows = []
        for number, values in enumerate(reader, start=2):
            if not values:
                continue
            if len(rows) >= MAX_ROWS:
                raise StatementError("Statement exceeds the 10,000 row limit.")
            rows.append(parse_row(number, values))
    except csv.Error as error:
        raise StatementError("Malformed CSV; the statement could not be read safely.") from error
    if not rows:
        raise StatementError("Statement has no transaction rows.")
    return Statement(hashlib.sha256(content).hexdigest(), tuple(rows))
