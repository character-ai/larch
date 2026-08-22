"""Tests for issue_wire.py parity surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Callable, Mapping, Sequence

import pytest

from larch.git import gh
from larch.issue import issue_blocks, issue_wire
from larch.core import retry
from larch.errors import ShipError
from larch.core.proc import CommandResult


def test_owner_block_roundtrip_and_fenced_lookalike() -> None:
    block = issue_wire.OwnerBlock(
        domain="issue",
        verb="migration-audit",
        owners=(
            issue_wire.OwnerRow(
                "CREATE",
                "migration-owner",
                "python/larch/issue/issue_wire.py::OwnerBlock",
            ),
            issue_wire.OwnerRow(
                "REUSE", "typed-mutation", "python/larch/issue/issue_mutation.py", 7781
            ),
        ),
    )
    rendered = issue_wire.render_owner_block(block=block)
    body = f"```text\n{rendered}```\n{rendered}"
    parsed = issue_wire.parse_owner_block(body=body)
    assert parsed.block == block
    assert not parsed.defects
    assert parsed.block is not None
    assert issue_wire.render_owner_block(block=parsed.block) == rendered


@pytest.mark.parametrize(
    ("rows", "defect"),
    [
        (
            ("COMMAND\tissue\tmigration-audit", "CREATE\tbad_key\tx.py"),
            "invalid-owner-key",
        ),
        (
            ("COMMAND\tissue\tmigration-audit", "CREATE\tkey\t../x.py"),
            "unsafe-owner-target",
        ),
        (
            ("COMMAND\tissue\tmigration-audit", "CREATE\tkey\tx.py::bad symbol"),
            "unsafe-owner-target",
        ),
        (
            ("CREATE\tkey\tx.py", "COMMAND\tissue\tmigration-audit"),
            "unsorted-owner-rows",
        ),
        (
            (
                "COMMAND\tissue\tmigration-audit",
                "CREATE\tkey\tx.py",
                "CREATE\tkey\tx.py",
            ),
            "duplicate-owner-row",
        ),
        (
            (
                "COMMAND\tissue\tmigration-audit",
                "CREATE\tkey\tx.py",
                "REUSE\tkey\t#7\ty.py",
            ),
            "duplicate-owner-key",
        ),
    ],
)
def test_owner_block_rejects_adversarial_rows(
    rows: tuple[str, ...], defect: str
) -> None:
    body = "\n".join(
        ("<!-- larch:owners:start -->", *rows, "<!-- larch:owners:end -->")
    )
    assert defect in issue_wire.parse_owner_block(body=body).defects


def test_implementation_lease_roundtrip_and_malformed_refusal() -> None:
    lease = issue_wire.ImplementationLeaseMarker(
        run_id="0199f1e2-2238-403d-89f3-aaaaaaaaaaaa",
        branch="feature/owner-7783",
        base="a" * 40,
        plan="b" * 64,
        updated_at="2026-07-19T20:30:00Z",
    )
    rendered = issue_wire.render_implementation_lease(lease=lease)
    body = issue_wire.upsert_implementation_lease(body="body\n", lease=lease)
    assert body == f"body\n{rendered}\n"
    assert issue_wire.parse_implementation_lease(body=body) == lease
    assert issue_wire.strip_implementation_lease(body=body) == "body\n"
    with pytest.raises(ShipError, match="invalid-implementation-lease"):
        _ = issue_wire.render_implementation_lease(
            lease=issue_wire.ImplementationLeaseMarker(
                **{**lease.__dict__, "branch": "bad branch"}
            )
        )
    with pytest.raises(ShipError, match="malformed-implementation-lease"):
        _ = issue_wire.upsert_implementation_lease(
            body="<!-- larch:implementation-lease v1 broken -->\n", lease=lease
        )


def test_emit_untrusted_content_block_matches_file_block_redaction(
    tmp_path: Path,
) -> None:
    raw = "<tag> sk-" + "A" * 24 + " & text"
    file_path = tmp_path / "raw.txt"
    _ = file_path.write_text(raw, encoding="utf-8")
    assert issue_wire.emit_untrusted_content_block(
        tag="sample", text=raw
    ) == issue_wire.emit_untrusted_file_block(tag="sample", path=file_path)
    out = issue_wire.emit_untrusted_content_block(tag="sample", text=raw)
    assert "&lt;tag&gt;" in out
    assert "&lt;REDACTED-TOKEN&gt;" in out


def test_parse_named_block_marker_isolated_and_whitespace_tolerant() -> None:
    body = """before
  <!--   larch:design-pause:start   -->  
pause
  <!--   larch:design-pause:end   -->
<!-- larch:plan:start -->
plan
<!-- larch:plan:end -->
after
"""
    assert issue_wire.parse_named_block(body=body, marker="plan") == ("plan\n", "")
    assert issue_wire.parse_named_block(body=body, marker="design-pause") == (
        "pause\n",
        "",
    )
    assert issue_wire.parse_named_block(body=body, marker="other") == (None, "")


def test_parse_named_block_ignores_marker_examples_inside_fences() -> None:
    body = (
        "```\n"
        "<!-- larch:plan:start -->\n"
        "example\n"
        "<!-- larch:plan:end -->\n"
        "```\n\n"
        "<!-- larch:plan:start -->\n"
        "live plan\n"
        "<!-- larch:plan:end -->\n"
    )
    assert issue_wire.parse_named_block(body=body, marker="plan") == ("live plan\n", "")


def test_neutralize_named_block_markers_keeps_examples_out_of_wire_parser() -> None:
    example = issue_wire.compose_named_block(marker="plan", inner="example")
    neutralized = issue_wire.neutralize_named_block_markers(text=example, marker="plan")
    assert "<!--\u200b larch:plan:start -->" in neutralized
    assert issue_wire.parse_named_block(body=neutralized, marker="plan") == (None, "")


@pytest.mark.parametrize(
    ("body", "token"),
    [
        (
            "<!-- larch:plan:start -->\na\n<!-- larch:plan:end -->\n<!-- larch:plan:start -->\nb\n<!-- larch:plan:end -->\n",
            "multiple-start",
        ),
        (
            "<!-- larch:plan:start -->\na\n<!-- larch:plan:end -->\n<!-- larch:plan:end -->\n",
            "multiple-end",
        ),
        ("<!-- larch:plan:start -->\na\n", "start-without-end"),
        ("<!-- larch:plan:end -->\n", "end-without-start"),
        ("<!-- larch:plan:end -->\na\n<!-- larch:plan:start -->\n", "end-before-start"),
    ],
)
def test_parse_named_block_malformed_tokens(body: str, token: str) -> None:
    assert issue_wire.parse_named_block(body=body, marker="plan") == (None, token)
    assert issue_blocks.strip_named_block(body=body, marker="plan") == ("", token)


def test_strip_named_block_preserves_unrelated_blocks() -> None:
    body = """intro
<!-- larch:design-pause:start -->
pause
<!-- larch:design-pause:end -->
<!-- larch:plan:start -->
plan
<!-- larch:plan:end -->
tail
"""
    stripped, malformed = issue_blocks.strip_named_block(body=body, marker="plan")
    assert malformed == ""
    assert "larch:design-pause:start" in stripped
    assert "plan\n" not in stripped
    assert stripped.endswith("tail\n")


def test_strip_plan_receipt_lines_preserves_fenced_examples() -> None:
    receipt = (
        "<!-- larch:plan-receipt v1 "
        f"plan_sha256={'a' * 64} base_sha={'b' * 40} "
        f"blockers_sha256={'c' * 64} owners_sha256={'d' * 64} -->"
    )
    body = f"```text\n{receipt}\n```\n{receipt}\ntail\n"

    assert issue_blocks.strip_plan_receipt_lines(body=body) == (
        f"```text\n{receipt}\n```\ntail\n"
    )


def test_replace_named_block_preserves_markers_and_unrelated_body() -> None:
    body = """intro
<!-- larch:design-pause:start -->
pause
<!-- larch:design-pause:end -->
<!-- larch:plan:start -->
old plan
<!-- larch:plan:end -->
tail
"""
    replaced, malformed = issue_blocks.replace_named_block(
        body=body,
        marker="plan",
        inner="new plan",
    )

    assert malformed == ""
    assert (
        replaced
        == """intro
<!-- larch:design-pause:start -->
pause
<!-- larch:design-pause:end -->
<!-- larch:plan:start -->
new plan
<!-- larch:plan:end -->
tail
"""
    )
    assert issue_blocks.replace_named_block(
        body="no plan", marker="plan", inner="new plan"
    ) == ("", "missing-block")


def test_compose_named_block_strips_trailing_lf() -> None:
    assert issue_wire.compose_named_block(marker="plan", inner="inner\n\n") == (
        "<!-- larch:plan:start -->\ninner\n<!-- larch:plan:end -->\n"
    )
    assert issue_wire.compose_named_block(marker="plan", inner="") == (
        "<!-- larch:plan:start -->\n<!-- larch:plan:end -->\n"
    )


def _empty_str_list() -> list[str]:
    return []


def _empty_call_list() -> list[list[str]]:
    return []


@dataclass
class IssueRunner:
    body: str
    title: str = "Regular issue"
    edit_bodies: list[str] = field(default_factory=_empty_str_list)
    calls: list[list[str]] = field(default_factory=_empty_call_list)
    edit_failures: int = 0
    persist_edits: bool = True
    updated_at: str = "2026-07-19T00:00:00Z"

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,  # pylint: disable=unused-argument
        cwd: str | None = None,  # pylint: disable=unused-argument
        env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
        check: bool = False,  # pylint: disable=unused-argument
        stdout: int | None = None,  # pylint: disable=unused-argument
        stderr: int | None = None,  # pylint: disable=unused-argument
    ) -> CommandResult:
        args = list(argv)
        self.calls.append(args)
        if args[:4] == [
            "gh",
            "issue",
            "view",
            "9",
        ]:  # lint-gh-argv-literal: ok fixture assertion
            labels: list[object] = []
            payload: dict[str, object] = {
                "title": self.title,
                "body": self.body,
                "labels": labels,
                "state": "OPEN",
                "updatedAt": self.updated_at,
            }
            return CommandResult(
                tuple(args), 0, __import__("json").dumps(payload), "", 0.01
            )
        if args[:4] == [
            "gh",
            "issue",
            "edit",
            "9",
        ]:  # lint-gh-argv-literal: ok fixture assertion
            body_file = args[args.index("--body-file") + 1]
            edited = Path(body_file).read_text(encoding="utf-8")
            self.edit_bodies.append(edited)
            if self.edit_failures:
                self.edit_failures -= 1
                return CommandResult(tuple(args), 1, "", "Could not resolve host", 0.01)
            if self.persist_edits:
                self.body = edited
                self.updated_at = "2026-07-19T00:00:01Z"
            return CommandResult(tuple(args), 0, "", "", 0.01)
        if args[:3] == [
            "gh",
            "repo",
            "view",
        ]:  # lint-gh-argv-literal: ok fixture assertion
            return CommandResult(tuple(args), 0, "owner/repo\n", "", 0.01)
        raise AssertionError(f"unexpected call: {args}")


def test_extract_scope_paths_honors_section_bounds_and_optional_filter(
    tmp_path: Path,
) -> None:
    plan = """## Plan
### UPDATED: `outside.txt`
## Files to modify/create
### MAY_UPDATE: `docs/optional.md`
### MAY_UPDATE: `a/b.py`
### UPDATED: `a/b.py`, `c/d.md`
### REWRITTEN: skills/design/scripts/x.sh (legacy)
## Acceptance
"""
    assert issue_wire.extract_scope_paths(plan_text=plan) == [
        "docs/optional.md",
        "a/b.py",
        "c/d.md",
        "skills/design/scripts/x.sh",
    ]
    assert issue_wire.extract_scope_paths(plan_text=plan, include_optional=False) == [
        "a/b.py",
        "c/d.md",
        "skills/design/scripts/x.sh",
    ]
    empty = tmp_path / "empty.md"
    _ = empty.write_text(
        "## Files to modify/create\n\n## Acceptance\n", encoding="utf-8"
    )
    assert issue_wire.extract_scope_paths(
        plan_text=empty.read_text(encoding="utf-8")
    ) == ["skills/design/SKILL.md"]
    assert (
        issue_wire.extract_scope_paths(
            plan_text=empty.read_text(encoding="utf-8"), use_fallback=False
        )
        == []
    )
    scopeless = "## Plan\n### UPDATED: `docs/expected.md`\n## Acceptance\n"
    assert issue_wire.extract_scope_paths(plan_text=scopeless, use_fallback=False) == [
        "docs/expected.md"
    ]
    multi_scopeless = (
        "## Plan\n"
        "### UPDATED: `a/one.py`\n"
        "### NEW: `b/two.md`\n"
        "### REWRITTEN: c/three.sh (legacy)\n"
        "### MAY_UPDATE: `d/opt.py`\n"
        "## Acceptance\n"
    )
    assert issue_wire.extract_scope_paths(
        plan_text=multi_scopeless, use_fallback=False, include_optional=False
    ) == ["a/one.py", "b/two.md", "c/three.sh"]


def test_extract_scope_paths_ignores_fenced_sections_and_keeps_root_paths() -> None:
    plan = """```md
## Files to modify/create
### UPDATED: hidden.py
```
## Files to modify/create
## UPDATED [README.md]
### NEW: Makefile
## Acceptance
"""
    assert issue_wire.extract_scope_paths(plan_text=plan) == ["README.md", "Makefile"]


def test_title_eligibility_and_insert_signal_marker() -> None:
    assert (
        issue_wire.title_lifecycle_reject_marker("  [implementing] x")
        == "[IMPLEMENTING]"
    )
    assert issue_wire.title_lifecycle_reject_marker("[STALLED] x") is None
    assert issue_wire.title_lifecycle_reject_marker("[Debating] x") == "[DEBATING]"
    assert issue_wire.title_lifecycle_reject_marker("  [dEbAtEd] x") == "[DEBATED]"
    assert (
        issue_wire.insert_signal_marker(
            title="[DESIGNED] My feature", marker="FALSE-POSITIVE"
        )
        == "[DESIGNED] [FALSE-POSITIVE] My feature"
    )
    assert (
        issue_wire.insert_signal_marker(
            title="[DESIGNED] [FALSE-POSITIVE] My feature", marker="FALSE-POSITIVE"
        )
        == "[DESIGNED] [FALSE-POSITIVE] My feature"
    )
    assert (
        issue_wire.insert_signal_marker(
            title="[DEBATING] Open question", marker="NEEDS-INPUT"
        )
        == "[DEBATING] [NEEDS-INPUT] Open question"
    )
    assert (
        issue_wire.insert_signal_marker(
            title="[Debated] Mixed case", marker="FALSE-POSITIVE"
        )
        == "[Debated] [FALSE-POSITIVE] Mixed case"
    )
    assert (
        issue_wire.insert_signal_marker(
            title="[Debated] [FALSE-POSITIVE] Mixed case",
            marker="FALSE-POSITIVE",
        )
        == "[Debated] [FALSE-POSITIVE] Mixed case"
    )
    assert (
        issue_wire.insert_signal_marker(
            title="[DEBATED] [NEEDS-INPUT] Ordered",
            marker="FALSE-POSITIVE",
        )
        == "[DEBATED] [FALSE-POSITIVE] [NEEDS-INPUT] Ordered"
    )


def test_untrusted_helpers(tmp_path: Path) -> None:
    token = "sk-" + "B" * 24
    redacted = issue_wire.redact_untrusted_stream(f"<{token}&>")
    assert "&lt;" in redacted
    assert "&amp;" in redacted
    assert token not in redacted
    file = tmp_path / "payload.txt"
    _ = file.write_text("<x>", encoding="utf-8")
    assert (
        issue_wire.emit_untrusted_file_block(tag="tag", path=file)
        == '<tag encoding="literal-redacted">\n&lt;x&gt;\n\n</tag>\n\n'
    )


def test_gh_issue_view_body_and_edit_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = IssueRunner("body", edit_failures=2)

    def retry_no_sleep(
        fn: Callable[[], tuple[CommandResult, int, str]],
    ) -> retry.RetryResult[CommandResult]:
        return retry.with_transient_retry(fn, sleeper=lambda _seconds: None)

    _ = monkeypatch.setattr(gh, "with_transient_retry", retry_no_sleep)
    body = gh.issue_view_body(runner, "9", repo="owner/repo")
    assert body == "body"
    result = gh.issue_edit_body_with_retry(runner, "9", "redacted", repo="owner/repo")
    assert result.returncode == 0
    edit_calls = [
        call for call in runner.calls if call[:3] == ["gh", "issue", "edit"]
    ]  # lint-gh-argv-literal: ok fixture assertion
    assert len(edit_calls) == 3
    assert runner.edit_bodies[-1] == "redacted"
