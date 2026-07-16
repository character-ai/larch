# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportUnusedCallResult=false
"""Tests for the shared open-issue row owner and JSON CLI helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.core.proc import CommandResult
from larch.errors import ShipError
from larch.issue import open_rows


class _ListRunner:
    def __init__(self, *, stdout: str = "", returncode: int = 0, stderr: str = ""):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr
        self.calls: list[list[str]] = []

    def run(self, argv, **_kwargs):
        self.calls.append(list(argv))
        return CommandResult(tuple(argv), self.returncode, self.stdout, self.stderr, 0.01)


def test_open_issue_rows_read_filters_closed_sorts_and_normalizes_labels():
    payload = json.dumps([
        {"number": 4, "title": "closed", "state": "CLOSED", "labels": [], "body": ""},
        {"number": 3, "title": "b", "state": "OPEN", "labels": [{"name": "bug"}, {"name": "p1"}], "body": "bb"},
        {"number": 1, "title": "a", "state": "open", "labels": ["plain"], "body": "aa"},
    ])
    runner = _ListRunner(stdout=payload)
    rows = open_rows.open_issue_rows_read(runner, repo="o/r")
    assert [row.number for row in rows] == [1, 3]
    assert rows[0] == open_rows.OpenIssueRow(number=1, title="a", state="open", labels=("plain",), body="aa")
    assert rows[1].labels == ("bug", "p1")
    call = runner.calls[0]
    assert call[:3] == ["gh", "issue", "list"]  # lint-gh-argv-literal: ok fixture assertion
    assert call[call.index("--json") + 1] == "number,title,state,labels,body"
    assert call[call.index("--limit") + 1] == "100000"
    assert call[call.index("--state") + 1] == "open"


def test_open_issue_rows_read_skips_malformed_rows_without_failing():
    payload = json.dumps([
        "not-a-dict",
        {"title": "no number", "state": "open"},
        {"number": 0, "state": "open"},
        {"number": -2, "state": "open"},
        {"number": True, "state": "open"},
        {"number": 7, "state": "open"},
    ])
    rows = open_rows.open_issue_rows_read(_ListRunner(stdout=payload), repo="o/r")
    assert [row.number for row in rows] == [7]


def test_open_issue_rows_read_preserves_duplicate_numbers():
    payload = json.dumps([
        {"number": 5, "title": "first", "state": "open"},
        {"number": 5, "title": "second", "state": "open"},
    ])
    rows = open_rows.open_issue_rows_read(_ListRunner(stdout=payload), repo="o/r")
    assert [row.number for row in rows] == [5, 5]


def test_open_issue_rows_read_raises_shiperror_on_gh_failure():
    runner = _ListRunner(returncode=1, stderr="auth denied")
    with pytest.raises(ShipError) as excinfo:
        open_rows.open_issue_rows_read(runner, repo="o/r")
    assert "JSON parse failed" not in str(excinfo.value)


def test_open_issue_rows_read_raises_shiperror_on_invalid_json():
    runner = _ListRunner(stdout="not json")
    with pytest.raises(ShipError) as excinfo:
        open_rows.open_issue_rows_read(runner, repo="o/r")
    assert "JSON parse failed" in str(excinfo.value)


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        ("scalar", None),
        (123, None),
        ({"state": "open"}, None),
        ({"number": 0, "state": "open"}, None),
        ({"number": -1, "state": "open"}, None),
        ({"number": True, "state": "open"}, None),
        ({"number": False, "state": "open"}, None),
        ({"number": "9", "state": "open"}, 9),
        ({"number": "0", "state": "open"}, None),
        ({"number": "x", "state": "open"}, None),
        ({"number": 3, "state": "closed"}, None),
        ({"number": 3}, None),
        ({"number": 3, "state": "Open"}, 3),
    ],
)
def test_parse_open_issue_row_number_and_state_policy(row, expected):
    parsed = open_rows.parse_open_issue_row(row)
    if expected is None:
        assert parsed is None
    else:
        assert parsed is not None
        assert parsed.number == expected
        assert parsed.state == "open"


def test_parse_open_issue_row_defaults_missing_optional_fields():
    parsed = open_rows.parse_open_issue_row({"number": 8, "state": "open"})
    assert parsed == open_rows.OpenIssueRow(number=8, title="", state="open", labels=(), body="")


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        ("not-a-list", ()),
        (None, ()),
        ([], ()),
        (["bug", "p1"], ("bug", "p1")),
        ([{"name": "bug"}, {"name": "p1"}], ("bug", "p1")),
        ([{"name": "bug"}, {"color": "red"}, {"name": ""}, "", 0, "p1"], ("bug", "p1")),
    ],
)
def test_parse_open_issue_row_normalizes_labels_to_names(labels, expected):
    parsed = open_rows.parse_open_issue_row({"number": 1, "state": "open", "labels": labels})
    assert parsed is not None
    assert parsed.labels == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, None),
        (False, None),
        (5, 5),
        (0, None),
        (-3, None),
        ("7", 7),
        ("0", None),
        ("-7", None),
        ("abc", None),
        (None, None),
        (2.5, None),
    ],
)
def test_positive_int_value(value, expected):
    assert open_rows.positive_int_value(value) == expected


def test_load_json_file_reads_valid_json(tmp_path: Path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({"a": 1}), encoding="utf-8")
    assert open_rows.load_json_file(str(path), desc="data-file") == {"a": 1}


def test_load_json_file_missing_file_raises_value_error(tmp_path: Path):
    with pytest.raises(ValueError, match="data-file: file not found"):
        open_rows.load_json_file(str(tmp_path / "absent.json"), desc="data-file")


def test_load_json_file_invalid_json_raises_value_error(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="data-file: invalid JSON"):
        open_rows.load_json_file(str(path), desc="data-file")


def test_emit_json_sorts_keys_and_appends_newline(capsys):
    rc = open_rows.emit_json({"b": 2, "a": 1})
    assert rc == 0
    out = capsys.readouterr().out
    assert out == '{"a": 1, "b": 2}\n'


def test_open_issue_row_as_dict_shape():
    row = open_rows.OpenIssueRow(number=2, title="t", state="open", labels=("x", "y"), body="b")
    assert row.as_dict() == {"number": 2, "title": "t", "state": "open", "labels": ["x", "y"], "body": "b"}
