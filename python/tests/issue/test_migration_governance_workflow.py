"""Static contract tests for the scheduled migration governance workflow."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "migration-governance.yaml"
MARKER = "<!-- larch:migration-governance v1 chief=7687 -->"


def _workflow() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _step_body(workflow: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^      - name: {re.escape(name)}\n(?P<body>.*?)(?=^      - name: |\Z)",
        workflow,
    )
    assert match is not None, f"missing workflow step: {name}"
    return match.group("body")


def test_triggers_permissions_and_concurrency_are_narrow() -> None:
    """The workflow has only its two triggers and required token scopes."""
    workflow = _workflow()

    assert '    - cron: "17 7 * * *"' in workflow
    assert "  workflow_dispatch:\n" in workflow
    assert "permissions:\n  contents: read\n  issues: write\n" in workflow
    assert "pull-requests:" not in workflow
    assert "actions: write" not in workflow
    assert "contents: write" not in workflow
    assert "group: migration-governance-chief-7687" in workflow
    assert "cancel-in-progress: true" in workflow


def test_builds_verified_repository_binary_and_runs_exact_audit() -> None:
    """The audit uses the lockfile-built lint binary through PATH."""
    workflow = _workflow()
    build = _step_body(workflow, "Build and verify larch")
    audit = _step_body(workflow, "Run the aggregate migration audit")

    assert "cargo build --locked --release --package larch-cli" in build
    assert "./target/release/larch --version" in build
    assert '"$GITHUB_WORKSPACE/target/release" >> "$GITHUB_PATH"' in build
    assert "cargo run" not in audit
    assert "target/release/larch" not in audit
    assert "GH_TOKEN: ${{ github.token }}" in audit
    assert (
        "python3 python/cli.py issue migration-audit \\\n"
        "            --repo character-ai/larch \\\n"
        "            --chief 7687"
    ) in audit
    assert '--output "$report_path"' in audit
    assert '--table-output stderr 2> "$summary_path"' in audit
    assert 'if [ -s "$report_path" ] && [ -s "$summary_path" ]; then' in audit
    assert "audit_rc=2" in audit
    assert "report_ready=true" in audit
    assert "2) report_ready=false ;;" in audit


def test_artifact_precedes_comment_and_terminal_outcome() -> None:
    """Report publication happens before either comment or status handling."""
    workflow = _workflow()
    audit_at = workflow.index("- name: Run the aggregate migration audit")
    upload_at = workflow.index("- name: Upload the JSON report when present")
    comment_at = workflow.index("- name: Refresh the Chief report comment")
    outcome_at = workflow.index("- name: Apply the audit outcome")
    upload = _step_body(workflow, "Upload the JSON report when present")
    outcome = _step_body(workflow, "Apply the audit outcome")

    assert audit_at < upload_at < comment_at < outcome_at
    assert "if: ${{ always() }}" in upload
    assert "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in upload
    assert "path: ${{ runner.temp }}/migration-governance.json" in upload
    assert "if-no-files-found: ignore" in upload
    assert "0) exit 0 ;;" in outcome
    assert "1)" in outcome
    assert "exit 1" in outcome
    assert "2)" in outcome
    assert "exit 2" in outcome


def test_chief_comment_uses_the_stable_renderer_and_exact_marker() -> None:
    """The sole comment command consumes the aggregate's rendered table."""
    workflow = _workflow()
    comment = _step_body(workflow, "Refresh the Chief report comment")

    assert "if: ${{ steps.audit.outputs.report_ready == 'true' }}" in comment
    assert "scripts/larch.sh tracking-issue upsert-summary" in comment
    assert "--issue 7687" in comment
    assert f"--marker '{MARKER}'" in comment
    assert '--content-file "$RUNNER_TEMP/migration-governance-comment.md"' in comment
    assert "--repo character-ai/larch" in comment
    assert _workflow().count("tracking-issue upsert-summary") == 1


def test_no_other_repository_or_issue_mutation_is_reachable() -> None:
    """No repository or issue mutation outside the comment upsert is present."""
    workflow = _workflow()
    cli_calls = set(
        re.findall(r"python3 python/cli\.py ([a-z0-9-]+) ([a-z0-9-]+)", workflow)
    ) | set(re.findall(r"scripts/larch\.sh ([a-z0-9-]+) ([a-z0-9-]+)", workflow))
    actions = set(re.findall(r"(?m)^        uses: (\S+)", workflow))
    forbidden = (
        "--title",
        "--body",
        "--label",
        "--blocker",
        "--owner",
        "--lease",
        "gh ",
        "git commit",
        "git push",
        "git tag",
        "curl ",
        "wget ",
    )

    assert cli_calls == {
        ("issue", "migration-audit"),
        ("tracking-issue", "upsert-summary"),
    }
    assert actions == {
        "actions/checkout@8e8c483db84b4bee98b60c0593521ed34d9990e8",
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
    }
    for command in forbidden:
        assert command not in workflow
