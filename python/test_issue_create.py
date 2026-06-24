# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Tests for /issue Python helper entrypoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import issue_create
import proc

SKILL_PATH = Path(__file__).resolve().parents[1] / "skills/issue/SKILL.md"


def _result(argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = "") -> proc.CommandResult:
    return proc.CommandResult(tuple(argv), returncode, stdout, stderr, 0.0)


def _parse_input_fixture(tmp_path: Path, capsys: Any, input_text: str) -> tuple[int, str, Path]:
    input_file = tmp_path / "input.md"
    input_file.write_text(input_text, encoding="utf-8")
    out_dir = tmp_path / "bodies"
    rc = issue_create.parse_input_main(["--input-file", str(input_file), "--output-dir", str(out_dir)])
    out = capsys.readouterr().out
    return rc, out, out_dir


def _kv_value(output: str, key: str) -> str:
    prefix = f"{key}="
    for line in output.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    return ""


def _body_file_contents(output: str, index: int) -> str:
    return Path(_kv_value(output, f"ITEM_{index}_BODY_FILE")).read_text(encoding="utf-8")


def test_parse_input_issue_129_oos_subheading_absorption(tmp_path: Path, capsys: Any) -> None:
    rc, out, _out_dir = _parse_input_fixture(
        tmp_path,
        capsys,
        "### OOS_1: Example bug\n"
        "- **Description**: First description paragraph.\n"
        "### Notes\n"
        "Second paragraph after the subheading.\n"
        "- **Reviewer**: Codex\n"
        "- **Vote tally**: YES=3, NO=0\n"
        "- **Phase**: review\n",
    )
    assert rc == 0
    assert _kv_value(out, "ITEMS_TOTAL") == "1"
    assert _kv_value(out, "ITEM_1_TITLE") == "Example bug"
    expected = "First description paragraph.\n### Notes\nSecond paragraph after the subheading."
    assert _body_file_contents(out, 1) == expected


def test_parse_input_issue_129_generic_body_preserves_oos_bullets(tmp_path: Path, capsys: Any) -> None:
    rc, out, _out_dir = _parse_input_fixture(
        tmp_path,
        capsys,
        "### Regular issue title\n"
        "This is preceding body text that must survive.\n"
        "- **Description**: stray description bullet that should stay in body\n"
        "- **Reviewer**: stray reviewer bullet\n"
        "- **Vote tally**: stray tally bullet\n"
        "- **Phase**: stray phase bullet\n"
        "Trailing body text after bullets.\n",
    )
    assert rc == 0
    assert _kv_value(out, "ITEMS_TOTAL") == "1"
    expected = (
        "This is preceding body text that must survive.\n"
        "- **Description**: stray description bullet that should stay in body\n"
        "- **Reviewer**: stray reviewer bullet\n"
        "- **Vote tally**: stray tally bullet\n"
        "- **Phase**: stray phase bullet\n"
        "Trailing body text after bullets."
    )
    assert _body_file_contents(out, 1) == expected
    assert "ITEM_1_REVIEWER=" not in out


def test_parse_input_issue_131_empty_inline_description(tmp_path: Path, capsys: Any) -> None:
    rc, out, _out_dir = _parse_input_fixture(
        tmp_path,
        capsys,
        "### OOS_1: Description body from continuations only\n"
        "- **Description**:\n"
        "  First continuation line.\n"
        "\n"
        "  Third line after blank.\n"
        "- **Reviewer**: Code\n"
        "- **Vote tally**: YES=3, NO=0\n"
        "- **Phase**: design\n",
    )
    assert rc == 0
    assert _kv_value(out, "ITEMS_TOTAL") == "1"
    expected = "  First continuation line.\n\n  Third line after blank."
    assert _body_file_contents(out, 1) == expected
    assert "ITEM_1_MALFORMED=" not in out


def test_parse_input_issue_132_generic_body_absorbs_nested_oos_heading(tmp_path: Path, capsys: Any) -> None:
    rc, out, _out_dir = _parse_input_fixture(
        tmp_path,
        capsys,
        "### Regular issue with nested OOS-shaped heading\n"
        "Preceding body text.\n"
        "### OOS_42: nested example\n"
        "Trailing body text after the nested heading.\n",
    )
    assert rc == 0
    assert _kv_value(out, "ITEMS_TOTAL") == "1"
    expected = "Preceding body text.\n### OOS_42: nested example\nTrailing body text after the nested heading."
    assert _body_file_contents(out, 1) == expected
    assert "ITEM_2_TITLE=" not in out


def test_parse_input_oos_and_malformed_body_file(tmp_path: Path, capsys: Any) -> None:
    input_file = tmp_path / "items.md"
    input_file.write_text(
        "### OOS_1: first\n"
        "- **Description**: body\n"
        "### Ambiguous\n"
        "pending body\n"
        "### OOS_2: second\n"
        "- **Description**: ok\n"
        "- **Reviewer**: R\n"
        "- **Vote tally**: YES=1\n"
        "- **Phase**: review\n"
        "### title only\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    assert issue_create.parse_input_main(["--input-file", str(input_file), "--output-dir", str(out_dir)]) == 0
    out = capsys.readouterr().out
    assert "ITEMS_TOTAL=4" in out
    assert "ITEM_1_BODY_FILE=" in out
    assert "ITEM_1_MALFORMED=true" in out
    assert "ITEM_3_REVIEWER=R" in out
    assert "ITEM_4_TITLE=title only" in out
    assert "ITEM_4_BODY_FILE=" not in out
    assert (out_dir / "item-1-body.txt").read_text(encoding="utf-8") == "body"


def test_parse_input_finding_format_oos_captures_body(tmp_path: Path, capsys: Any) -> None:
    """#5260: a FINDING-block OOS (Concern/Reviewer(s)) must round-trip to a non-empty body."""
    rc, out, _out_dir = _parse_input_fixture(
        tmp_path,
        capsys,
        "### OOS_1: [OUT_OF_SCOPE] Stale rubric cross-reference\n"
        "- **Reviewer(s)**: cursor-edge-cases, cursor-testing\n"
        "- **Severity**: latent\n"
        "- **Concern**: `plan-review.md` points to a renamed section; stale cross-doc guidance only.\n"
        "- **Suggested revisions (informational for voters; coder decides)**:\n"
        "  - From cursor-edge-cases: Update the bullet to the new contract.\n",
    )
    assert rc == 0
    assert _kv_value(out, "ITEMS_TOTAL") == "1"
    assert _kv_value(out, "ITEM_1_TITLE") == "[OUT_OF_SCOPE] Stale rubric cross-reference"
    assert "ITEM_1_MALFORMED=" not in out
    assert _kv_value(out, "ITEM_1_REVIEWER") == "cursor-edge-cases, cursor-testing"
    body = _body_file_contents(out, 1)
    assert "stale cross-doc guidance only." in body
    assert "Suggested revisions" in body
    assert "Update the bullet to the new contract." in body


def test_parse_input_oos_body_without_field_labels_is_captured(tmp_path: Path, capsys: Any) -> None:
    """#5260: prose directly under an OOS heading (no Description/Concern line) is captured, not dropped."""
    rc, out, _out_dir = _parse_input_fixture(
        tmp_path,
        capsys,
        "### OOS_1: Body prose with no field labels\nFirst body line under the heading.\nSecond body line.\n",
    )
    assert rc == 0
    assert _kv_value(out, "ITEMS_TOTAL") == "1"
    assert "ITEM_1_MALFORMED=" not in out
    assert _body_file_contents(out, 1) == "First body line under the heading.\nSecond body line."


def test_allocate_candidates_union_credit() -> None:
    rows = (
        "CAND 1 10 dup high\n"
        "CAND 1 11 dup medium\n"
        "CAND 2 10 dup low\n"
        "CAND 2 12 dep high"
    )
    assert issue_create.allocate_candidates(2, rows) == [10, 11, 12]


def test_allocate_candidates_n11_floor_two_spillover() -> None:
    rows = ""
    for i in range(1, 12):
        base = i * 100
        rows += f"CAND {i} {base} dup high\nCAND {i} {base + 1} dup high\nCAND {i} {base + 2} dup medium\n"
    expected = (
        "100,101,102,200,201,202,300,301,302,400,401,402,500,501,502,"
        "600,601,602,700,701,702,800,801,802,900,901,1000,1001,1100,1101"
    )
    assert issue_create.allocate_candidates(11, rows) == [int(value) for value in expected.split(",")]


def test_allocate_candidates_n16_floor_one_spillover() -> None:
    rows = ""
    for i in range(1, 17):
        base = i * 100
        rows += f"CAND {i} {base} dup high\nCAND {i} {base + 1} dup high\n"
    expected = (
        "100,101,200,201,300,301,400,401,500,501,600,601,700,701,800,801,"
        "900,901,1000,1001,1100,1101,1200,1201,1300,1301,1400,1401,1500,1600"
    )
    assert issue_create.allocate_candidates(16, rows) == [int(value) for value in expected.split(",")]


def test_allocate_candidates_n30_floor_one() -> None:
    rows = "".join(f"CAND {i} {i * 100} dup high\n" for i in range(1, 31))
    assert issue_create.allocate_candidates(30, rows) == [i * 100 for i in range(1, 31)]


def test_allocate_candidates_over_cap_confidence_only() -> None:
    rows = ""
    for i in range(1, 16):
        base = i * 100
        rows += f"CAND {i} {base} dup high\nCAND {i} {base + 50} dup medium\nCAND {i} {base + 75} dup low\n"
    expected = [
        100,
        150,
        200,
        250,
        300,
        350,
        400,
        450,
        500,
        550,
        600,
        650,
        700,
        750,
        800,
        850,
        900,
        950,
        1000,
        1050,
        1100,
        1150,
        1200,
        1250,
        1300,
        1350,
        1400,
        1450,
        1500,
        1550,
    ]
    assert issue_create.allocate_candidates(31, rows) == expected


def test_allocate_candidates_tie_break_issue_asc() -> None:
    rows = (
        "CAND 1 105 dup medium\n"
        "CAND 1 102 dup medium\n"
        "CAND 1 101 dup medium\n"
        "CAND 1 104 dup medium\n"
        "CAND 1 103 dup medium\n"
    )
    assert issue_create.allocate_candidates(10, rows) == [101, 102, 103, 104, 105]


def test_allocate_candidates_kind_both_first_class() -> None:
    rows = "CAND 1 100 both high\nCAND 2 100 both medium\n"
    assert issue_create.allocate_candidates(2, rows) == [100]


def test_allocate_candidates_missing_confidence_defaults_low() -> None:
    rows = "CAND 1 100 dup\nCAND 1 101 dup high\n"
    assert issue_create.allocate_candidates(1, rows) == [100, 101]


def test_allocate_candidates_unknown_kind_defaults_dup() -> None:
    rows = "CAND 1 100 unknown high\nCAND 1 101 weird medium\n"
    assert issue_create.allocate_candidates(1, rows) == [100, 101]


def test_allocate_candidates_n_zero_ignores_stdin() -> None:
    assert issue_create.allocate_candidates(0, "CAND 1 100 dup high\n") == []


def test_allocate_candidates_empty_stdin() -> None:
    assert issue_create.allocate_candidates(5, "") == []


def test_allocate_candidates_hard_cap_thirty() -> None:
    rows = ""
    for i in range(1, 6):
        for offset in range(10):
            rows += f"CAND {i} {i * 1000 + offset} dup high\n"
    assert len(issue_create.allocate_candidates(5, rows)) == 30


def test_create_one_dry_run_redacts(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    body = tmp_path / "body.md"
    body.write_text("body crsr_0123456789abcdefghijklmnopqrstuvwxyzABCDEF", encoding="utf-8")

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "label", "list"]:
            return _result(argv, stdout="bug\n")
        return _result(argv, stdout="owner/repo\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    rc = issue_create.create_one_main(
        [
            "--title",
            "[OOS] leaking crsr_0123456789abcdefghijklmnopqrstuvwxyzABCDEF",
            "--title-prefix",
            "[OOS]",
            "--label",
            "bug",
            "--body-file",
            str(body),
            "--repo",
            "owner/repo",
            "--dry-run",
        ],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "DRY_RUN=true" in out
    assert "DRY_RUN_LABELS=bug" in out
    assert "[OOS] leaking <REDACTED-TOKEN>" in out
    assert "crsr_0123456789" not in out


def test_create_one_success_json(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    body = tmp_path / "body.md"
    body.write_text("body", encoding="utf-8")

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "issue", "create"]:
            return _result(argv, stdout=json.dumps({"id": 99, "number": 5, "url": "https://x/issues/5"}))
        return _result(argv, stdout="owner/repo\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    assert issue_create.create_one_main(["--title", "T", "--body-file", str(body), "--repo", "owner/repo"]) == 0
    out = capsys.readouterr().out
    assert "ISSUE_NUMBER=5" in out
    assert "ISSUE_ID=99" in out
    assert "ISSUE_TITLE=T" in out


def test_create_one_success_plain_url_fallback(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    body = tmp_path / "body.md"
    body.write_text("body", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["gh", "issue", "create"]:
            return _result(argv, stdout="https://github.com/owner/repo/issues/42\n")
        if argv[:3] == ["gh", "api", "/repos/owner/repo/issues/42"]:
            return _result(argv, stdout="4242\n")
        return _result(argv, stdout="owner/repo\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    assert issue_create.create_one_main(["--title", "T", "--body-file", str(body), "--repo", "owner/repo"]) == 0
    out = capsys.readouterr().out
    assert "ISSUE_NUMBER=42" in out
    assert "ISSUE_ID=4242" in out
    create_calls = [argv for argv in calls if argv[:3] == ["gh", "issue", "create"]]
    assert len(create_calls) == 1
    assert "--json" in create_calls[0]


def test_create_one_resolves_rest_id_for_graphql_node_id(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    body = tmp_path / "body.md"
    body.write_text("body", encoding="utf-8")

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "issue", "create"]:
            return _result(
                argv,
                stdout=json.dumps({"id": "MDU6SXNzdWUx", "number": 5, "url": "https://x/issues/5"}),
            )
        if argv[:3] == ["gh", "api", "/repos/owner/repo/issues/5"]:
            return _result(argv, stdout="12345\n")
        return _result(argv, stdout="owner/repo\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    rc = issue_create.create_one_main(["--title", "T", "--body-file", str(body), "--repo", "owner/repo"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ISSUE_ID=12345" in out
    assert "ISSUE_NUMBER=5" in out


def test_create_one_graphql_node_id_lookup_failure_rolls_back(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    body = tmp_path / "body.md"
    body.write_text("body", encoding="utf-8")

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "issue", "create"]:
            return _result(
                argv,
                stdout=json.dumps({"id": "MDU6SXNzdWUx", "number": 5, "url": "https://x/issues/5"}),
            )
        if argv[:3] == ["gh", "api", "/repos/owner/repo/issues/5"]:
            return _result(argv, returncode=1, stderr="lookup failed")
        if argv[:3] == ["gh", "issue", "close"]:
            return _result(argv)
        return _result(argv, stdout="owner/repo\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    rc = issue_create.create_one_main(["--title", "T", "--body-file", str(body), "--repo", "owner/repo"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "ISSUE_FAILED=true" in captured.out
    assert "ROLLBACK: closed orphan issue #5" in captured.err


def test_create_one_id_lookup_failure_emits_rollback_failed(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    body = tmp_path / "body.md"
    body.write_text("body", encoding="utf-8")

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "issue", "create"]:
            return _result(argv, stdout="https://github.com/owner/repo/issues/42\n")
        if argv[:3] == ["gh", "api", "/repos/owner/repo/issues/42"]:
            return _result(argv, returncode=1, stderr="lookup failed")
        if argv[:3] == ["gh", "issue", "close"]:
            return _result(argv, returncode=1, stderr="close failed")
        return _result(argv, stdout="owner/repo\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    rc = issue_create.create_one_main(["--title", "T", "--body-file", str(body), "--repo", "owner/repo"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "ISSUE_FAILED=true" in captured.out
    assert "ROLLBACK_FAILED" in captured.err


def test_skill_pins_body_file_title_semantics() -> None:
    text = SKILL_PATH.read_text(encoding="utf-8")
    needles = (
        "trailing arg is the explicit title",
        "EXPLICIT_TITLE",
        "if `EXPLICIT_TITLE` is set",
        "derived from `DESCRIPTION`",
        "body-file content is empty",
    )
    for needle in needles:
        assert needle in text, needle


def test_write_sentinel_dry_run_and_failures(tmp_path: Path, capsys: Any) -> None:
    target = tmp_path / "sentinel.env"
    args = ["--path", str(target), "--issues-created", "1", "--issues-deduplicated", "0", "--issues-failed", "0"]
    assert issue_create.write_sentinel_main([*args, "--dry-run"]) == 0
    assert capsys.readouterr().err == "WROTE=false REASON=dry_run\n"
    assert not target.exists()
    failure_args = [
        "--path",
        str(target),
        "--issues-created",
        "1",
        "--issues-deduplicated",
        "0",
        "--issues-failed",
        "1",
    ]
    assert issue_create.write_sentinel_main(failure_args) == 0
    assert capsys.readouterr().err == "WROTE=false REASON=failures\n"


def test_fetch_issue_details_partial_failure(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    payload = {
        "number": 9,
        "title": "T",
        "body": "body",
        "state": "open",
        "url": "https://x/issues/9",
        "comments": [],
    }

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "issue", "view"] and argv[3] == "9":
            return _result(argv, stdout=json.dumps(payload))
        if argv[:3] == ["gh", "issue", "view"] and argv[3] == "10":
            return _result(argv, returncode=1, stderr="not found")
        return _result(argv, stdout="o/r\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    out_path = tmp_path / "corpus.md"
    assert issue_create.fetch_issue_details_main(["--numbers", "9,10", "--output", str(out_path), "--repo", "o/r"]) == 0
    out = capsys.readouterr().out
    assert "FETCH_STATUS_9=ok" in out
    assert "FETCH_STATUS_10=failed" in out
    text = out_path.read_text(encoding="utf-8")
    assert "<external_issue_9>" in text
    assert "<external_issue_10>" not in text


def test_add_blocked_by_transient_retry(monkeypatch: Any, capsys: Any) -> None:
    calls: list[list[str]] = []
    api_calls = 0

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["gh", "api", "/repos/o/r/issues/2"]:
            return _result(argv, stdout="200\n")
        if argv[:3] == ["gh", "api", "/repos/o/r/issues/1/dependencies/blocked_by"]:
            nonlocal api_calls
            api_calls += 1
            if api_calls < 3:
                return _result(argv, returncode=1, stderr="HTTP 503")
            return _result(argv)
        return _result(argv)

    sleeps: list[float] = []

    def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    rc = issue_create.add_blocked_by_main(
        ["--client-issue", "1", "--blocker-issue", "2", "--repo", "o/r"],
        sleep_fn=record_sleep,
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "BLOCKED_BY_ADDED=true" in out
    assert sleeps == [10.0, 30.0]
    assert api_calls == 3


def test_add_blocked_by_retry_idempotent(monkeypatch: Any, capsys: Any) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["gh", "api", "/repos/o/r/issues/2"]:
            return _result(argv, stdout="200\n")
        return _result(argv, returncode=1, stderr="HTTP 422 duplicate dependency")

    sleeps: list[float] = []
    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    def record_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    rc = issue_create.add_blocked_by_main(
        ["--client-issue", "1", "--blocker-issue", "2", "--repo", "o/r"],
        sleep_fn=record_sleep,
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "BLOCKED_BY_ADDED=true" in out
    assert not sleeps
    assert len(calls) == 2


def test_list_issues_filters_archival(monkeypatch: Any, capsys: Any) -> None:
    payload = [
        {"number": 1, "title": "Keep\tTitle", "state": "open", "html_url": "u1"},
        {"number": 2, "title": "Research spike", "state": "open", "html_url": "u2"},
        {"number": 3, "title": "Closed", "state": "closed", "closed_at": "2099-01-01T00:00:00Z", "html_url": "u3"},
        {"number": 4, "title": "PR", "state": "open", "pull_request": {}, "html_url": "u4"},
    ]

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "api", "--paginate"]:
            return _result(argv, stdout=json.dumps(payload))
        return _result(argv, stdout="o/r\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    assert issue_create.list_issues_main(["--repo", "o/r", "--closed-window-days", "90"]) == 0
    out = capsys.readouterr().out
    assert "LIST_STATUS=ok" in out
    assert "1\tKeep Title\topen\tu1" in out
    assert "2\t" not in out
    assert "3\tClosed\tclosed\tu3" in out
    assert "4\t" not in out


def test_parse_input_write_failure_returns_one(tmp_path: Path, monkeypatch: Any, capsys: Any) -> None:
    input_file = tmp_path / "items.md"
    input_file.write_text("### OOS_1: first\n- **Description**: body\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    def fail_write(*_: object, **__: object) -> None:
        raise OSError(13, "permission denied")

    monkeypatch.setattr(Path, "write_text", fail_write)
    assert issue_create.parse_input_main(["--input-file", str(input_file), "--output-dir", str(out_dir)]) == 1
    assert "failed to write body file" in capsys.readouterr().err


def test_fetch_issue_details_success_and_validation(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    payload = {
        "number": 9,
        "title": "T",
        "body": "body",
        "state": "open",
        "url": "https://x/issues/9",
        "comments": [],
    }

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "issue", "view"]:
            return _result(argv, stdout=json.dumps(payload))
        return _result(argv, stdout="o/r\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    out_path = tmp_path / "corpus.md"
    assert issue_create.fetch_issue_details_main(["--numbers", "9", "--output", str(out_path), "--repo", "o/r"]) == 0
    out = capsys.readouterr().out
    assert "FETCH_STATUS_9=ok" in out
    assert "<external_issue_9>" in out_path.read_text(encoding="utf-8")
    assert issue_create.fetch_issue_details_main(["--numbers", "9", "--output", str(out_path), "--max-comments", "x"]) == 1


def test_cleanup_failed_closes_orphan(monkeypatch: Any, capsys: Any) -> None:
    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "issue", "close"]:
            return _result(argv)
        return _result(argv, stdout="o/r\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    assert issue_create.cleanup_failed_main(["--issue-number", "7", "--repo", "o/r"]) == 0
    out = capsys.readouterr().out
    assert "CLOSED=true" in out
    assert "ISSUE=7" in out


def test_allocate_candidates_rejects_over_cap(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setattr("issue_create.sys.stdin", type("S", (), {"read": lambda _self: ""})())
    assert issue_create.allocate_candidates_main(["--total-items", "31"]) == 0
    assert "exceeds 30" in capsys.readouterr().err


def test_add_blocked_by_404_no_retry(monkeypatch: Any, capsys: Any) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["gh", "api", "/repos/o/r/issues/2"]:
            return _result(argv, stdout="200\n")
        return _result(argv, returncode=1, stderr="HTTP 404: Not Found")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    rc = issue_create.add_blocked_by_main(["--client-issue", "1", "--blocker-issue", "2", "--repo", "o/r"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "BLOCKED_BY_FAILED=true" in out
    assert len(calls) == 2


def test_add_blocked_by_redaction_failure_exits_three(monkeypatch: Any, capsys: Any) -> None:
    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "api", "/repos/o/r/issues/2"]:
            return _result(argv, stdout="200\n")
        return _result(argv, returncode=1, stderr="HTTP 404: Not Found")

    def boom(_text: str) -> str:
        raise RuntimeError("redact failed")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    monkeypatch.setattr(issue_create, "redact_secrets_outbound", boom)
    rc = issue_create.add_blocked_by_main(["--client-issue", "1", "--blocker-issue", "2", "--repo", "o/r"])
    out = capsys.readouterr().out
    assert rc == 3
    assert "BLOCKED_BY_FAILED=true" in out
    assert "ERROR=redaction:" in out


def test_create_one_dry_run_preserves_operator_paths(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    body = tmp_path / "body.md"
    operator_path = "/Users/alice/myproject/docs/guide.md"
    body.write_text(f"see {operator_path}", encoding="utf-8")

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "label", "list"]:
            return _result(argv, stdout="bug\n")
        return _result(argv, stdout="owner/repo\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    rc = issue_create.create_one_main(
        [
            "--title",
            f"Path in {operator_path}",
            "--body-file",
            str(body),
            "--repo",
            "owner/repo",
            "--dry-run",
        ],
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert operator_path in out
    assert "<OPERATOR_REPO_PATH>" not in out


def test_create_one_empty_json_fields_do_not_fallback(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    body = tmp_path / "body.md"
    body.write_text("body", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["gh", "issue", "create"]:
            return _result(argv, stdout=json.dumps({"id": "", "number": "", "url": ""}))
        return _result(argv, stdout="owner/repo\n")

    monkeypatch.setattr(issue_create.proc, "run", fake_run)
    rc = issue_create.create_one_main(["--title", "T", "--body-file", str(body), "--repo", "owner/repo"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "ISSUE_FAILED=true" in out
    assert "empty field" in out
    create_calls = [argv for argv in calls if argv[:3] == ["gh", "issue", "create"]]
    assert len(create_calls) == 1
    assert "--json" in create_calls[0]


def test_list_issues_missing_gh_emits_failed(monkeypatch: Any, capsys: Any) -> None:
    def missing_gh(argv: list[str], **_: object) -> proc.CommandResult:
        if argv and argv[0] == "gh":
            return proc.CommandResult(tuple(argv), 127, "", "gh: command not found\n", 0.0)
        return _result(argv)

    monkeypatch.setattr(issue_create.proc, "run", missing_gh)
    assert issue_create.list_issues_main(["--repo", "o/r"]) == 0
    out = capsys.readouterr().out
    assert "LIST_STATUS=failed" in out


def test_create_one_redaction_failure_exits_three(monkeypatch: Any, tmp_path: Path, capsys: Any) -> None:
    body = tmp_path / "body.md"
    body.write_text("body", encoding="utf-8")

    def boom(_text: str) -> str:
        raise RuntimeError("redact failed")

    monkeypatch.setattr(issue_create, "redact_secrets_outbound", boom)
    rc = issue_create.create_one_main(["--title", "T", "--body-file", str(body), "--repo", "o/r"])
    out = capsys.readouterr().out
    assert rc == 3
    assert "ISSUE_FAILED=true" in out
    assert "ISSUE_ERROR=redaction:" in out


def test_skill_pins_intra_batch_dependency_contract() -> None:
    text = SKILL_PATH.read_text(encoding="utf-8")
    needles = (
        "N_NON_MALFORMED >= 2",
        "skip `issue fetch-issue-details` entirely",
        "Empty-CANDIDATES + multi-item path",
        "no-external-refs",
        "FETCH_STATUS_",
        "intra-batch-deps-file FILE",
        "Caller-supplied intra-batch deps merge",
        "no-dep-llm",
    )
    for needle in needles:
        assert needle in text, needle


def test_skill_pins_blocked_by_issue_contract() -> None:
    text = SKILL_PATH.read_text(encoding="utf-8")
    needles = (
        "--blocked-by-issue N",
        "--no-dedup and --blocked-by-issue are mutually exclusive",
        "--blocked-by-issue requires --input-file (batch mode)",
        "--blocked-by-issue must be a positive integer",
        'gh api "/repos/$REPO/issues/$BLOCKED_BY_ISSUE"',
        "pull_request != null",
        "Caller-supplied --blocked-by-issue merge",
        "Carve-out for --blocked-by-issue",
        "--blocker-id $BLOCKED_BY_ISSUE_ID",
    )
    for needle in needles:
        assert needle in text, needle


def test_write_sentinel_stderr_only(tmp_path: Path, capsys: Any) -> None:
    target = tmp_path / "sentinel.env"
    rc = issue_create.write_sentinel_main(
        ["--path", str(target), "--issues-created", "1", "--issues-deduplicated", "2", "--issues-failed", "0"],
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == ""
    assert captured.err == "WROTE=true\n"
    assert "ISSUES_CREATED=1" in target.read_text(encoding="utf-8")
