"""Static contract pins for the shipped public debate surface."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKILL = ROOT / "skills" / "debate" / "SKILL.md"
AGENT = ROOT / "agents" / "debater.md"


def _skill() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_public_surface_and_lifecycle_are_declared() -> None:
    text = _skill()
    assert "# larch-run-lifecycle: shared-v1 skill=debate" in text
    assert "name: debate" in text
    assert 'argument-hint: "[-s|--vote-stalemates] <issue-number | free-form description>"' in text
    assert "run-log lifecycle-start" in text
    for terminal in ("lifecycle-finalize", "lifecycle-failure", "lifecycle-cancel", "lifecycle-early-return"):
        assert f"run-log {terminal}" in text
    assert "skills/debate/scripts/step-name-registry.tsv" in text


def test_pre_title_dependency_gates_are_ordered() -> None:
    text = _skill()
    title_start = text.index("--mode start")
    assert text.index("confirm `SendMessage` is present") < title_start
    assert text.index("both `CODEX_PRESENT` and `CURSOR_PRESENT`") < title_start
    assert text.index("debate init") < title_start
    assert "unavailable vendor: <cursor|codex>" in text
    assert "proceeding with two live slots" in text


def test_noninteractive_and_one_shot_contract() -> None:
    text = _skill()
    assert '{"error_class":"prompt_required","ok":false,"operation":"debate","prompt_required":true}' in text
    assert "has no resumable or scheduled route" in text
    assert "ScheduleWakeup" not in text
    assert "/pause" not in text
    assert "never invokes `/design`" in text
    assert "Skill(design)" not in text
    for forbidden in ("### NEW:", "### UPDATED:", "### REWRITTEN:", "### MAY_UPDATE:", "diff_lines:"):
        assert forbidden not in text


def test_persistent_panel_and_claude_ingestion_are_explicit() -> None:
    text = _skill()
    assert "spawn exactly one `larch:debater`" in text
    assert "continue that same agent with `SendMessage`" in text
    assert "Do not fresh-spawn the Claude leg" in text
    assert "debate round-external" in text
    assert "debate round-ingest" in text
    assert "--claude-input-file" in text
    assert "Never use an ambient last-session selector" in text
    assert "<slot>-round-<ROUND>-prompt.md" in text
    assert "DEBATE_DENY_ACTIVE_SENTINEL=%s" in text
    assert "retained `DEBATE_DENY_ACTIVE_SENTINEL` path" in text


def test_generated_handoffs_are_validated_before_use() -> None:
    text = _skill()
    preview = text.index("debate adjudication-preview")
    preview_path = text.index("$DEBATE_TMPDIR/adjudication-preview.json", preview)
    preview_wrap = text.index("untrusted file-block", preview)
    assert preview < preview_path < preview_wrap
    assert "$PREVIEW_FILE" not in text
    # The publish-run composite envelope replaces the publish-prepare.env parse
    # and the separate untrusted title-wrapping turn.
    publish = text.index("debate publish-run")
    issue_child = text.index('--title-prefix "[PROPOSAL]"', publish)
    finish = text.index("debate publish-finish", issue_child)
    assert publish < issue_child < finish
    for key in (
        "source_issue_number",
        "cross_link_issue_number",
        "source_fingerprint",
        "proposal_title_block",
    ):
        assert key in text[publish:issue_child]
    assert "publish-prepare.env" not in text
    assert "$TITLE_FILE" not in text
    assert "$BODY_FILE" not in text


def test_issue_pattern_b_and_cross_links_are_verified() -> None:
    text = _skill()
    assert text.count("--sentinel-file") >= 3
    assert text.count("verify skill-called") >= 2
    assert "ISSUES_CREATED=1" in text
    assert "ISSUES_FAILED=0" in text
    assert '--title-prefix "[PROPOSAL]"' in text
    assert "`/issue` owns case-insensitive prefix deduplication" in text
    assert "proposal-linked-body.md" in text
    assert "The proposal body now links to the source and the source comment links to the proposal" in text
    assert "<!-- larch:debate-proposal runid=$RUN_ID -->" in text
    # publish-finish rebuilds the URL from the verified number in Rust.
    assert "--proposal-number" in text
    assert "--proposal-url" in text


def test_abort_is_owned_idempotent_and_sanitized() -> None:
    text = _skill()
    assert "debate abort-run" in text
    assert "--title-adopted" in text
    assert "live title still equals this run's exact `[DEBATING]` title" in text
    assert "A foreign title returns `owned=false` and is never overwritten" in text
    assert "<!-- larch:debate-aborted runid=$RUN_ID -->" in text
    assert "The debate ended before proposal publication. No outcome was adopted." in text
    assert "Upsert identity makes retries update the same comment" in text
    # Comment verification now lives inside the composite verbs (`round-ingest`,
    # `publish-finish`, and `abort-run`); no separate verify turn remains.
    assert text.count("debate comment-verify") == 0


def test_debater_agent_is_read_only_and_fails_closed() -> None:
    text = AGENT.read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]
    assert "name: debater" in frontmatter
    assert "  - Read" in frontmatter
    assert "  - Grep" in frontmatter
    assert "  - Glob" in frontmatter
    for forbidden_tool in ("Bash", "Edit", "Write"):
        assert f"  - {forbidden_tool}" not in frontmatter
    assert "missing or unreadable, return no ledger" in text
    assert "final message is only the ledger" in text


def test_permissions_docs_and_topology_publish_the_surface() -> None:
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    allow = settings["permissions"]["allow"]
    assert "Skill(debate)" in allow
    assert "Skill(larch:debate)" in allow
    assert allow == sorted(allow)
    for path in (
        ROOT / "README.md",
        ROOT / "docs" / "skills.md",
        ROOT / "docs" / "configuration-and-permissions.md",
        ROOT / "docs" / "security" / "workflow-trust-and-mutations.md",
        ROOT / "docs" / "security" / "artifacts-redaction-and-publication.md",
        ROOT / "skills" / "shared" / "external-reviewers.md",
        ROOT / "skills" / "shared" / "progress-reporting.md",
    ):
        assert "/debate" in path.read_text(encoding="utf-8")
    topology = (ROOT / "skills" / "shared" / "topology.tsv").read_text(encoding="utf-8")
    assert "debate.panel\t" in topology
    assert "debate.rounds\t" in topology
    assert "debate.publication\t" in topology
    projected = (ROOT / "docs" / "topology.md").read_text(encoding="utf-8")
    assert 'id="debate.panel"' in projected
    assert 'id="debate.publication"' in projected
