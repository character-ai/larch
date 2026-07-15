"""Coverage for the Tier-1 doc-pointer-paths lint."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

from larch import cli as larch_cli
from larch.lint import lint_doc_pointer_paths as lint


def _write_tier1(root: Path, *, agents: str, security: str) -> None:
    _ = (root / "AGENTS.md").write_text(agents, encoding="utf-8")
    _ = (root / "SECURITY.md").write_text(security, encoding="utf-8")


def test_dead_pointer_fails_with_file_line_and_token(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_tier1(
        tmp_path,
        agents="# ok\n",
        security="See `python/missing_module.py` for details.\n",
    )

    assert lint.main(["--root", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "SECURITY.md:1: dead doc pointer `python/missing_module.py`" in err


def test_live_pointer_passes(tmp_path: Path) -> None:
    live = tmp_path / "python" / "larch" / "core" / "redact.py"
    live.parent.mkdir(parents=True)
    _ = live.write_text("# stub\n", encoding="utf-8")
    _write_tier1(
        tmp_path,
        agents=f"Uses `{live.relative_to(tmp_path).as_posix()}`.\n",
        security="# ok\n",
    )

    assert lint.main(["--root", str(tmp_path)]) == 0


def test_multiple_tokens_produce_separate_findings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_tier1(
        tmp_path,
        agents="# ok\n",
        security="Bad `python/a.py` and `python/b.py`.\n",
    )

    assert lint.main(["--root", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "python/a.py" in err
    assert "python/b.py" in err
    assert err.count("dead doc pointer") == 2


def test_fenced_examples_are_skipped(tmp_path: Path) -> None:
    _write_tier1(
        tmp_path,
        agents="# ok\n",
        security="```\n`python/missing_in_fence.py`\n```\nLive prose.\n",
    )

    assert lint.main(["--root", str(tmp_path)]) == 0


def test_placeholder_and_whitespace_tokens_are_skipped(tmp_path: Path) -> None:
    _write_tier1(
        tmp_path,
        agents="# ok\n",
        security=(
            "Skip `python/<placeholder>.py` and `python/cli.py ship pr` "
            "and `python/foo*.py`.\n"
        ),
    )

    assert lint.main(["--root", str(tmp_path)]) == 0


def test_larch_logs_paths_are_skipped(tmp_path: Path) -> None:
    _write_tier1(
        tmp_path,
        agents="# ok\n",
        security="See `larch-logs/implement/run-1/summary.md`.\n",
    )

    assert lint.main(["--root", str(tmp_path)]) == 0


def test_symbol_and_fragment_suffixes_check_file_portion(tmp_path: Path) -> None:
    live = tmp_path / "python" / "larch" / "design" / "clarify.py"
    live.parent.mkdir(parents=True)
    _ = live.write_text("# stub\n", encoding="utf-8")
    rel = live.relative_to(tmp_path).as_posix()
    _write_tier1(
        tmp_path,
        agents=f"See `{rel}::sweep_main` and `{rel}#section`.\n",
        security="# ok\n",
    )

    assert lint.main(["--root", str(tmp_path)]) == 0


def test_reason_bearing_suppression_passes(tmp_path: Path) -> None:
    _write_tier1(
        tmp_path,
        agents="# ok\n",
        security=(
            "Historical `python/missing.py` "
            "<!-- lint-doc-pointer-paths: ok temporary example -->\n"
        ),
    )

    assert lint.main(["--root", str(tmp_path)]) == 0


def test_missing_reason_suppression_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_tier1(
        tmp_path,
        agents="# ok\n",
        security="No pointer <!-- lint-doc-pointer-paths: ok -->\n",
    )

    assert lint.main(["--root", str(tmp_path)]) == 1
    assert "empty lint-doc-pointer-paths suppression reason" in capsys.readouterr().err


def test_root_escaping_candidate_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    outside = tmp_path.parent / f"outside-{tmp_path.name}.txt"
    _ = outside.write_text("secret\n", encoding="utf-8")
    try:
        _write_tier1(
            tmp_path,
            agents="# ok\n",
            security="Escape `python/../outside-should-not-resolve.txt`.\n",
        )
        # Craft a probe that escapes via .. even if the outside file exists.
        security = tmp_path / "SECURITY.md"
        escape_name = outside.name
        _ = security.write_text(
            f"Escape `python/../{escape_name}`.\n",
            encoding="utf-8",
        )
        _ = (tmp_path / "AGENTS.md").write_text("# ok\n", encoding="utf-8")

        assert lint.main(["--root", str(tmp_path)]) == 1
        err = capsys.readouterr().err
        assert "dead or escaping doc pointer" in err
    finally:
        outside.unlink(missing_ok=True)


def test_missing_document_returns_tool_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _ = (tmp_path / "AGENTS.md").write_text("# ok\n", encoding="utf-8")

    assert lint.main(["--root", str(tmp_path)]) == 2
    assert "missing required Tier-1 document" in capsys.readouterr().err


def test_symlink_document_returns_tool_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    real = tmp_path / "real-security.md"
    _ = real.write_text("# ok\n", encoding="utf-8")
    _ = (tmp_path / "AGENTS.md").write_text("# ok\n", encoding="utf-8")
    _ = (tmp_path / "SECURITY.md").symlink_to(real)

    assert lint.main(["--root", str(tmp_path)]) == 2
    assert "refusing symlink input" in capsys.readouterr().err


def test_unreadable_document_returns_tool_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_tier1(tmp_path, agents="# ok\n", security="# ok\n")
    security = tmp_path / "SECURITY.md"
    security.chmod(0)

    try:
        assert lint.main(["--root", str(tmp_path)]) == 2
        assert "unreadable" in capsys.readouterr().err
    finally:
        security.chmod(0o644)


def test_cli_registration_points_at_module() -> None:
    assert larch_cli._REGISTRY[("lint", "doc-pointer-paths")] == (  # pyright: ignore[reportPrivateUsage]  # accessing _REGISTRY to verify cli dispatch registration
        "larch.lint.lint_doc_pointer_paths",
        "main",
    )


def test_repo_root_scan_is_clean() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    assert lint.main(["--root", str(repo_root)]) == 0
