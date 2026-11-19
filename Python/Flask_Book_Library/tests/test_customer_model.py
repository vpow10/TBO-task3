"""Unit tests for the ``Customer`` model (project/customers/models.py).

The tests describe the *expected* contract of the model, in the spirit of
"Security by Design": a ``Customer`` object must never exist in an invalid
state, so the constructor has to reject bad input by raising an exception.

Specification encoded by these tests:

* ``name``   - str, 2-64 chars, letters (incl. Polish), spaces and hyphens only
* ``city``   - str, 2-64 chars, letters (incl. Polish), spaces and hyphens only
* ``age``    - int (not bool, not str), 1-120
* ``pesel``  - str, exactly 11 digits, a real birth date and a valid checksum
* ``street`` - str, 2-128 chars, letters, digits, spaces and ``. - /``
* ``appNo``  - str, 1-9 digits optionally followed by one letter (max 10 chars)

The current model performs no validation at all, so every test expecting an
exception is supposed to FAIL - that is the point of the exercise.

Every "negative" test starts from a fully valid customer and breaks exactly
ONE field. Otherwise a test could pass because some *other* field was wrong.
"""

import pytest

from project.customers.models import Customer

# Exceptions an invalid input may legitimately raise (wrong value / wrong type).
INVALID = (ValueError, TypeError)

VALID_DATA = {
    "name": "Jan Kowalski",
    "city": "Warszawa",
    "age": 30,
    "pesel": "44051401359",
    "street": "ul. Marszałkowska 10",
    "appNo": "12",
}

TEXT_FIELDS = ["name", "city", "pesel", "street", "appNo"]


def make_customer(**overrides):
    """Build a customer from valid data, replacing only the given fields."""
    return Customer(**{**VALID_DATA, **overrides})


# ---------------------------------------------------------------------------
# 1. Valid data - the object is created and keeps the given values
# ---------------------------------------------------------------------------

def test_valid_customer_is_created_with_given_values():
    customer = make_customer()

    for field, value in VALID_DATA.items():
        assert getattr(customer, field) == value


@pytest.mark.parametrize(
    "field, value",
    [
        ("name", "Anna Nowak-Kowalska"),
        ("name", "Zażółć Gęślą"),
        ("city", "Bielsko-Biała"),
        ("city", "Łódź"),
        ("age", 18),
        ("age", 99),
        ("pesel", "90010112349"),
        ("pesel", "05211509876"),  # born in 2005 -> month encoded as 21
        ("pesel", "02322900112"),  # born 2002-12-29
        ("street", "Aleje Jerozolimskie 123/4"),
        ("street", "ul. 3-go Maja"),
        ("appNo", "1"),
        ("appNo", "12A"),
    ],
)
def test_valid_field_values_are_accepted(field, value):
    customer = make_customer(**{field: value})

    assert getattr(customer, field) == value


# ---------------------------------------------------------------------------
# 2. Invalid data - missing values, wrong types, wrong formats
# ---------------------------------------------------------------------------

# Values that are never a meaningful text input.
EMPTY_LIKE = [None, "", " ", "\t", "\n", "null", "None", "nil", "0", "--"]


@pytest.mark.parametrize("field", TEXT_FIELDS)
@pytest.mark.parametrize("value", EMPTY_LIKE)
def test_empty_like_text_values_are_rejected(field, value):
    with pytest.raises(INVALID):
        make_customer(**{field: value})


@pytest.mark.parametrize("field", TEXT_FIELDS)
@pytest.mark.parametrize("value", [123, 4.5, True, ["Jan"], {"a": 1}, b"bytes"])
def test_non_string_text_values_are_rejected(field, value):
    with pytest.raises(INVALID):
        make_customer(**{field: value})


@pytest.mark.parametrize(
    "field, value",
    [
        ("name", "Jan Kowalski 3"),
        ("name", "Jan_Kowalski"),
        ("name", "jan@example.com"),
        ("name", "€$%^&*"),
        ("city", "Warszawa1"),
        ("city", "Kraków!"),
        ("street", "ul. Długa #5"),
        ("street", "ul. Długa; 5"),
        ("appNo", "A12"),
        ("appNo", "12AB"),
        ("appNo", "-1"),
        ("appNo", "1 2"),
    ],
)
def test_text_values_with_forbidden_characters_are_rejected(field, value):
    with pytest.raises(INVALID):
        make_customer(**{field: value})


@pytest.mark.parametrize(
    "value",
    [None, "30", "abc", "", 30.5, True, False, [30], -5],
)
def test_invalid_age_is_rejected(value):
    with pytest.raises(INVALID):
        make_customer(age=value)


@pytest.mark.parametrize(
    "value",
    [
        "4405140135",      # 10 digits
        "440514013590",    # 12 digits
        "4405140135X",     # letter instead of digit
        "4405 140135",     # whitespace inside
        " 44051401359",    # leading whitespace
        "44051401350",     # wrong checksum
        "90010112340",     # wrong checksum
        "00000000000",     # all zeros (checksum OK, but not a real date)
        "４４０５１４０１３５９",  # full-width Unicode digits
    ],
)
def test_invalid_pesel_is_rejected(value):
    with pytest.raises(INVALID):
        make_customer(pesel=value)


# ---------------------------------------------------------------------------
# 3. Boundary conditions - just inside vs. just outside the allowed range
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "field, value",
    [
        ("name", "Al"),          # min length 2
        ("name", "A" * 64),      # max length 64
        ("city", "Ul"),
        ("city", "A" * 64),
        ("street", "Al"),
        ("street", "A" * 128),   # max length 128
        ("appNo", "1" * 9 + "A"),  # max length 10
        ("age", 1),
        ("age", 120),
    ],
    ids=lambda v: v if isinstance(v, str) and len(v) < 20 else None,
)
def test_values_on_the_boundary_are_accepted(field, value):
    customer = make_customer(**{field: value})

    assert getattr(customer, field) == value


@pytest.mark.parametrize(
    "field, value",
    [
        ("name", "A"),           # 1 char below min
        ("name", "A" * 65),      # 1 char above max
        ("city", "A"),
        ("city", "A" * 65),
        ("street", "A"),
        ("street", "A" * 129),
        ("appNo", "1" * 10 + "A"),  # 11 chars
        ("appNo", "1" * 10),
        ("age", 0),
        ("age", 121),
    ],
    ids=lambda v: v if isinstance(v, str) and len(v) < 20 else None,
)
def test_values_just_outside_the_boundary_are_rejected(field, value):
    with pytest.raises(INVALID):
        make_customer(**{field: value})


# ---------------------------------------------------------------------------
# 4. Injection attempts - SQL, JavaScript (XSS) and log injection
# ---------------------------------------------------------------------------

SQL_INJECTION_PAYLOADS = [
    "' OR 1=1 --",
    "\" OR 1 = 1 -- -",
    "'''''''''''''UNION SELECT '2'",
    "1' ORDER BY 1--+",
    "' UNION SELECT sum(columnname) from tablename --",
    ",(select * from (select(sleep(10)))a)",
    "Robert'); DROP TABLE customers;--",
    "admin'--",
    "1; DELETE FROM customers",
]

XSS_PAYLOADS = [
    "\"-prompt(8)-\"",
    "'-prompt(8)-'",
    "<img/src/onerror=prompt(8)>",
    "<script\\x20type=\"text/javascript\">javascript:alert(1);</script>",
    "<script>alert(document.cookie)</script>",
    "<svg onload=alert(1)>",
    "<a href=\"javascript:alert(1)\">x</a>",
    "javascript:alert(1)",
    "<iframe src=//evil.example></iframe>",
]

# The constructor prints the object, so CR/LF in a value lets an attacker
# forge extra lines in the application log.
LOG_INJECTION_PAYLOADS = [
    "Jan\nINFO: admin logged in successfully",
    "Jan\r\nERROR: database dropped",
    "Jan\x1b[2J",  # ANSI escape - clears the terminal of whoever reads the log
]


@pytest.mark.parametrize("field", TEXT_FIELDS)
@pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
def test_sql_injection_is_rejected(field, payload):
    with pytest.raises(INVALID):
        make_customer(**{field: payload})


@pytest.mark.parametrize("field", TEXT_FIELDS)
@pytest.mark.parametrize("payload", XSS_PAYLOADS)
def test_javascript_injection_is_rejected(field, payload):
    with pytest.raises(INVALID):
        make_customer(**{field: payload})


@pytest.mark.parametrize("field", TEXT_FIELDS)
@pytest.mark.parametrize("payload", LOG_INJECTION_PAYLOADS)
def test_log_injection_is_rejected(field, payload):
    with pytest.raises(INVALID):
        make_customer(**{field: payload})


# ---------------------------------------------------------------------------
# 5. Extreme data - very large inputs must be rejected, not processed
# ---------------------------------------------------------------------------

# Only the length is passed as a parameter (and used as the test id), so huge
# strings are neither kept in memory at collection time nor printed as ids.
EXTREME_LENGTHS = [10_000, 100_000, 1_000_000, 4_000_000, 10_000_000]


@pytest.mark.parametrize("field", TEXT_FIELDS)
@pytest.mark.parametrize("length", EXTREME_LENGTHS)
def test_extremely_long_text_is_rejected(field, length):
    with pytest.raises(INVALID):
        make_customer(**{field: "X" * length})


@pytest.mark.parametrize(
    "value",
    [10**100, -(10**100), 2**63, float("inf"), float("-inf"), float("nan")],
    ids=["googol", "minus-googol", "int64-overflow", "inf", "minus-inf", "nan"],
)
def test_extreme_age_is_rejected(value):
    with pytest.raises(INVALID):
        make_customer(age=value)


# ---------------------------------------------------------------------------
# 6. Sensitive data - PESEL must not leak through repr() or logs
# ---------------------------------------------------------------------------

def test_pesel_is_not_exposed_in_repr():
    customer = make_customer()

    assert VALID_DATA["pesel"] not in repr(customer)


def test_pesel_is_not_written_to_logs_on_creation(capsys):
    make_customer()

    captured = capsys.readouterr()
    assert VALID_DATA["pesel"] not in captured.out + captured.err
