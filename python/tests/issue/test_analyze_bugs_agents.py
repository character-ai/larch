# pyright: reportUnusedCallResult=false
"""Pinned agent-contract checks that do not import retired analyze_bugs."""

from __future__ import annotations

from pathlib import Path


def test_bug_fix_triage_agent_grants_read_tool() -> None:
    agent = (Path(__file__).resolve().parents[3] / ".claude/agents/bug-fix-triage.md").read_text(encoding="utf-8")

    assert "tools: [Read]" in agent
    assert "tools: []" not in agent
    assert '"introduced_risk"' in agent
    assert "failed scan-status stanza" in agent


def test_bug_fix_verifier_contract_requires_targeted_greps_and_class_fields() -> None:
    agent = (Path(__file__).resolve().parents[3] / ".claude/agents/bug-fix-verifier.md").read_text(encoding="utf-8")

    assert "Grep against the current checkout for every `introduced_risk` verdict" in agent
    assert "targeted Grep outside the fixed site" in agent
    assert '"class_complete"' in agent
    assert '"sibling_sites"' in agent
    assert "class_complete=false" in agent


def test_sweep_bug_finder_agent_contract_pinned() -> None:
    root = Path(__file__).resolve().parents[3]
    agent_path = root / ".claude" / "agents" / "sweep-bug-finder.md"
    text = agent_path.read_text(encoding="utf-8")

    lines = text.split("\n")
    assert lines[0] == "---"
    frontmatter_end = lines.index("---", 1)
    frontmatter_text = "\n".join(lines[1:frontmatter_end])
    body = "\n".join(lines[frontmatter_end + 1 :])

    assert "tools:" in frontmatter_text
    assert "- Read" in frontmatter_text
    assert "- Grep" in frontmatter_text
    assert "- Glob" in frontmatter_text
    assert "model: sonnet" in frontmatter_text

    # Strict finder and refuter JSONL schemas are pinned verbatim.
    assert '"merge_sha"' in body
    assert '"findings"' in body
    assert '"finding_index"' in body
    assert '"verdict"' in body
    assert '"survives|refuted"' in body
    assert '"high|medium|low"' in body

    # Read requirement, adversarial finder language, queue-row-only refuter handoff.
    assert "read the bundle" in body.lower()
    assert "Read, Grep, and Glob" in body
    assert "planted" in body.lower()
    assert "disprove" in body.lower()
    assert "REFUTER_QUEUE_PATH" in body
    assert "exactly one" in body

    # Unreadable-evidence fail-closed fallback and the live lint stays clean.
    assert "never invent" in body.lower()
