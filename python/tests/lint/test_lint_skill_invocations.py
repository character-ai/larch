from __future__ import annotations

from pathlib import Path

import pytest

from larch.lint.lint_skill_invocations import main


def write_skill(root: Path, rel: str, body: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(body, encoding="utf-8")


def run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    rc = main(["--root", str(root)])
    return rc, capsys.readouterr().err


def skill_doc(allowed_tools: str, body: str) -> str:
    return f"---\nname: fixture\ndescription: fixture\nallowed-tools: {allowed_tools}\n---\n\n{body}\n"


@pytest.mark.parametrize(
    ("label", "allowed", "body"),
    [
        ("pattern-a", "Bash, Skill", "Invoke the Skill tool:\n- skill: foo"),
        ("pattern-b", "Bash, Read, Skill", "Invoke `/foo` via the Skill tool."),
        ("no-skill", "Bash, Read", "No invocation phrase."),
        ("flow-list", "[Bash, Read, Skill]", "Invoke `/thing` via the Skill tool."),
        ("quoted-flow-list", '["Bash", "Skill"]', "Invoke `/thing` via the Skill tool."),
        ("single-quoted-flow-list", "['Bash', 'Skill']", "Invoke `/thing` via the Skill tool."),
        ("substring", "Bash, SkillCheck", "No invocation phrase."),
        ("quoted", '"Bash, Skill"', "Invoke the Skill tool:\n- skill: foo"),
    ],
)
def test_allowed_tools_shapes_pass(tmp_path: Path, capsys: pytest.CaptureFixture[str], label: str, allowed: str, body: str) -> None:
    write_skill(tmp_path, f"skills/{label}/SKILL.md", skill_doc(allowed, body))
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_block_sequence_allowed_tools(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(
        tmp_path,
        "skills/block/SKILL.md",
        "---\nname: block\ndescription: block\nallowed-tools:\n  - Bash\n  - Skill\n---\n\nInvoke `/x` via the Skill tool.\n",
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_malformed_allowed_tools_gate_false(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(
        tmp_path,
        "skills/malformed-bracket/SKILL.md",
        skill_doc("[Bash, Skill", "Missing phrase but malformed frontmatter."),
    )
    write_skill(
        tmp_path,
        "skills/malformed-quote/SKILL.md",
        skill_doc('"Bash, Skill', "Missing phrase but unclosed quote."),
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_file_level_violation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(tmp_path, "skills/missing/SKILL.md", skill_doc("Bash, Skill", "Missing phrase."))
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/missing/SKILL.md" in err
    assert "declares 'Skill' in allowed-tools" in err


def test_two_violations_and_claude_tree(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(tmp_path, "skills/one/SKILL.md", skill_doc("Skill", "Missing."))
    write_skill(tmp_path, ".claude/skills/two/SKILL.md", skill_doc("Skill", "Missing too."))
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/one/SKILL.md" in err
    assert ".claude/skills/two/SKILL.md" in err


def test_crlf_and_bom(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "skills/crlf/SKILL.md"
    path.parent.mkdir(parents=True)
    _ = path.write_bytes(
        b"\xef\xbb\xbf---\r\nname: crlf\r\ndescription: crlf\r\nallowed-tools: Bash, Skill\r\n---\r\n\r\nInvoke `/foo` via the Skill tool.\r\n"
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_non_utf8_exit_2_wins_over_violation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bad = tmp_path / "skills/bad/SKILL.md"
    bad.parent.mkdir(parents=True)
    _ = bad.write_bytes(b"\xff\xfe")
    write_skill(tmp_path, "skills/vio/SKILL.md", skill_doc("Skill", "Missing."))
    rc, err = run(tmp_path, capsys)
    assert rc == 2
    assert "bad/SKILL.md" in err
    assert "cannot read file" in err
    assert "vio/SKILL.md" in err


def test_per_invocation_line_violations(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(
        tmp_path,
        "skills/lines/SKILL.md",
        skill_doc(
            "Skill",
            "To pass total omission: Invoke `/setup` via the Skill tool.\n\nBut these are bare:\n- Invoke `/foo` first.\n- Then invoke `/bar` next.",
        ),
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/lines/SKILL.md:10:" in err
    assert "skills/lines/SKILL.md:11:" in err


def test_code_fence_and_citation_exemptions(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(
        tmp_path,
        "skills/exempt/SKILL.md",
        skill_doc(
            "Skill",
            "Invoke `/setup` via the Skill tool.\n\n```\nInvoke `/foo` bare.\n```\n\nAlways invoke the helper script before calling `/release`.\nInvoke the **Rebase + Re-bump Sub-procedure** which internally re-runs `/release`.",
        ),
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 0, err


def test_bare_reinvoke_is_violation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_skill(
        tmp_path,
        "skills/reinvoke/SKILL.md",
        skill_doc("Skill", "Invoke `/setup` via the Skill tool.\n\nThen re-invoke `/issue` if needed."),
    )
    rc, err = run(tmp_path, capsys)
    assert rc == 1
    assert "skills/reinvoke/SKILL.md" in err
    assert "via the Skill tool" in err
