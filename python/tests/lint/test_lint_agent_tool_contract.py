from __future__ import annotations

from pathlib import Path
from typing import Protocol

from larch.lint import lint_agent_tool_contract as latc


class CaptureResult(Protocol):
    err: str
    out: str


class CaptureFixture(Protocol):
    def readouterr(self) -> CaptureResult: ...


def _write_agent(root: Path, relpath: str, *, frontmatter: str, body: str) -> None:
    path: Path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")


def _run_lint(root: Path, capsys: CaptureFixture) -> tuple[int, str, str]:
    code: int = latc.main(["--root", str(root)])
    captured: CaptureResult = capsys.readouterr()
    return code, captured.out, captured.err


def test_empty_tools_with_read_intent_is_detected(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_agent(
        tmp_path,
        "agents/needs-read.md",
        frontmatter="name: needs-read\ntools: []\n",
        body="Read the files before writing the verdict.\n",
    )

    code, stdout, stderr = _run_lint(tmp_path, capsys)

    assert code == 1
    assert stderr == ""
    assert "agents/needs-read.md:5: " + latc.FINDING_MESSAGE in stdout


def test_readless_inline_tool_list_with_read_intent_is_detected(
    tmp_path: Path, capsys: CaptureFixture
) -> None:
    _write_agent(
        tmp_path,
        ".claude/agents/grep-only.md",
        frontmatter="name: grep-only\ntools: [Grep]\n",
        body="Please open the file and summarize it.\n",
    )

    code, stdout, _stderr = _run_lint(tmp_path, capsys)

    assert code == 1
    assert ".claude/agents/grep-only.md:5: " + latc.FINDING_MESSAGE in stdout


def test_readless_inline_tool_list_with_use_read_intent_is_detected(
    tmp_path: Path, capsys: CaptureFixture
) -> None:
    _write_agent(
        tmp_path,
        "agents/use-read.md",
        frontmatter="name: use-read\ntools: [Grep]\n",
        body="Use Read for any referenced evidence.\n",
    )

    code, stdout, _stderr = _run_lint(tmp_path, capsys)

    assert code == 1
    assert "agents/use-read.md:5: " + latc.FINDING_MESSAGE in stdout


def test_inline_read_tool_with_read_intent_is_clean(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_agent(
        tmp_path,
        "agents/can-read.md",
        frontmatter="name: can-read\ntools: [Read]\n",
        body="Use Read for any referenced evidence.\n",
    )

    assert _run_lint(tmp_path, capsys) == (0, "", "")


def test_block_read_tool_with_read_intent_is_clean(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_agent(
        tmp_path,
        "agents/block-read.md",
        frontmatter="name: block-read\ntools:\n  - Grep\n  - Read\n",
        body="Read every bundle before voting.\n",
    )

    assert _run_lint(tmp_path, capsys) == (0, "", "")


def test_missing_tools_key_with_read_intent_is_clean(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_agent(
        tmp_path,
        "agents/unrestricted.md",
        frontmatter="name: unrestricted\n",
        body="Read all artifacts before responding.\n",
    )

    assert _run_lint(tmp_path, capsys) == (0, "", "")


def test_empty_tools_without_read_intent_is_clean(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_agent(
        tmp_path,
        "agents/reasoning.md",
        frontmatter="name: reasoning\ntools: []\n",
        body="Classify the supplied text and return one line.\n",
    )

    assert _run_lint(tmp_path, capsys) == (0, "", "")


def test_reason_bearing_suppression_is_clean(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_agent(
        tmp_path,
        "agents/suppressed.md",
        frontmatter="name: suppressed\ntools: []\n",
        body=(
            "Read the files named by the dispatcher.\n"
            "<!-- lint-agent-tool-contract: ok fixture intentionally covers suppression -->\n"
        ),
    )

    assert _run_lint(tmp_path, capsys) == (0, "", "")


def test_suppression_without_reason_does_not_suppress(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_agent(
        tmp_path,
        "agents/bad-suppression.md",
        frontmatter="name: bad-suppression\ntools: []\n",
        body="Read the files first.\n<!-- lint-agent-tool-contract: ok -->\n",
    )

    code, stdout, _stderr = _run_lint(tmp_path, capsys)

    assert code == 1
    assert "agents/bad-suppression.md:5: " + latc.FINDING_MESSAGE in stdout


def test_scalar_tools_value_is_unrestricted_and_clean(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_agent(
        tmp_path,
        "agents/scalar.md",
        frontmatter="name: scalar\ntools: *\n",
        body="Read the files before responding.\n",
    )

    assert _run_lint(tmp_path, capsys) == (0, "", "")


def test_malformed_inline_list_is_tool_failure(tmp_path: Path, capsys: CaptureFixture) -> None:
    _write_agent(
        tmp_path,
        "agents/malformed.md",
        frontmatter="name: malformed\ntools: [Read\n",
        body="Read the files before responding.\n",
    )

    code, _stdout, stderr = _run_lint(tmp_path, capsys)

    assert code == latc.TOOL_FAILURE_EXIT
    assert "lint-agent-tool-contract: agents/malformed.md: malformed inline tools list" in stderr


def test_live_tree_is_clean(capsys: CaptureFixture) -> None:
    repo_root: Path = Path(__file__).resolve().parents[3]

    assert _run_lint(repo_root, capsys) == (0, "", "")
