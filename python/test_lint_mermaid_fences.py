from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

from larch.lint import lint_mermaid_fences
from larch.lint.lint_mermaid_fences import extract_fences, main


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def run_in(root: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], args: list[str]) -> tuple[int, str, str]:
    monkeypatch.chdir(root)
    rc = main(args)
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def test_usage_errors(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--unknown"]) == 1
    assert "unknown flag" in capsys.readouterr().err
    assert main(["--changed-only", "x.md"]) == 1
    assert "does not accept" in capsys.readouterr().err


def test_no_files_and_larch_logs_skip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    rc, out, err = run_in(tmp_path, monkeypatch, capsys, ["larch-logs/run/doc.md"])
    assert rc == 0
    assert "INFO: no Markdown files to lint" in out
    assert err == ""


def test_extract_gfm_indented_fences(tmp_path: Path) -> None:
    src = tmp_path / "doc.md"
    outdir = tmp_path / "out"
    outdir.mkdir()
    write(src, "  ```mermaid\ngraph TD\nA-->B\n  ```\n    ```mermaid\nnot a fence\n    ```\n")
    assert extract_fences(src=src, outdir=outdir) == 1
    assert (outdir / "fence-1.mmd").read_text(encoding="utf-8") == "graph TD\nA-->B\n"


def test_nested_markdown_fence_does_not_extract_inner_mermaid(tmp_path: Path) -> None:
    src = tmp_path / "nested.md"
    outdir = tmp_path / "out-nested"
    outdir.mkdir()
    write(src, "````markdown\n```mermaid\nflowchart TD\n  A[bad|example]\n```\n````\n")
    assert extract_fences(src=src, outdir=outdir) == 0

def test_zero_fence_does_not_resolve_mmdc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "doc.md", "# no diagrams\n")
    def fail_resolve(_self: object) -> None:
        pytest.fail("mmdc should not resolve")

    monkeypatch.setattr(lint_mermaid_fences.MermaidRunner, "ensure", fail_resolve)
    rc, _out, err = run_in(tmp_path, monkeypatch, capsys, ["doc.md"])
    assert rc == 0, err


def _fake_mmdc(path: Path, help_text: str, fail: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exit_line = "exit 1" if fail else 'touch "$4" 2>/dev/null || true; exit 0'
    _ = path.write_text(f"#!/usr/bin/env bash\nif [ \"${{1:-}}\" = --help ]; then printf '%s\\n' '{help_text}'; exit 0; fi\n{exit_line}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_parse_only_and_render_modes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "doc.md", "```mermaid\ngraph TD\nA-->B\n```\n")
    mmdc = tmp_path / "mermaid-lint/node_modules/.bin/mmdc"
    _fake_mmdc(mmdc, "usage --parseOnly")
    monkeypatch.setattr(lint_mermaid_fences, "_repo_root", lambda: tmp_path)
    rc, _out, err = run_in(tmp_path, monkeypatch, capsys, ["doc.md"])
    assert rc == 0, err
    _fake_mmdc(mmdc, "usage without parse")
    rc, _out, err = run_in(tmp_path, monkeypatch, capsys, ["doc.md"])
    assert rc == 0, err


def test_non_ci_browser_launch_failure_skips_render(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "doc.md", "```mermaid\ngraph TD\nA-->B\n```\n")
    mmdc = tmp_path / "mermaid-lint/node_modules/.bin/mmdc"
    _fake_mmdc(mmdc, "usage without parse", fail=True)
    _ = mmdc.write_text(
        """#!/usr/bin/env bash
if [ "${1:-}" = --help ]; then printf '%s\n' 'usage without parse'; exit 0; fi
printf '%s\n' 'Error: Failed to launch the browser process!' >&2
exit 1
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(lint_mermaid_fences, "_repo_root", lambda: tmp_path)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    rc, _out, err = run_in(tmp_path, monkeypatch, capsys, ["doc.md"])
    assert rc == 0
    assert "browser" in err


def test_ci_browser_launch_failure_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "doc.md", "```mermaid\ngraph TD\nA-->B\n```\n")
    mmdc = tmp_path / "mermaid-lint/node_modules/.bin/mmdc"
    _fake_mmdc(mmdc, "usage without parse", fail=True)
    _ = mmdc.write_text(
        """#!/usr/bin/env bash
if [ "${1:-}" = --help ]; then printf '%s\n' 'usage without parse'; exit 0; fi
printf '%s\n' 'Error: Failed to launch the browser process!' >&2
exit 1
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(lint_mermaid_fences, "_repo_root", lambda: tmp_path)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    rc, _out, err = run_in(tmp_path, monkeypatch, capsys, ["doc.md"])
    assert rc == 1
    assert "Failed to launch" in err


def test_missing_local_mmdc_runs_npm_ci(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "doc.md", "```mermaid\ngraph TD\nA-->B\n```\n")
    write(tmp_path / "mermaid-lint/package-lock.json", "{}\n")
    npm = tmp_path / "bin/npm"
    write(
        npm,
        """#!/bin/sh
mkdir -p node_modules/.bin
cat > node_modules/.bin/mmdc <<'EOF'
#!/bin/sh
if [ "${1:-}" = --help ]; then printf '%s\n' 'usage --parseOnly'; exit 0; fi
exit 0
EOF
chmod +x node_modules/.bin/mmdc
""",
    )
    npm.chmod(npm.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(lint_mermaid_fences, "_repo_root", lambda: tmp_path)
    monkeypatch.setenv("PATH", f"{npm.parent}{os.pathsep}{os.defpath}")
    rc, _out, err = run_in(tmp_path, monkeypatch, capsys, ["doc.md"])
    assert rc == 0, err
    assert (tmp_path / "mermaid-lint/node_modules/.bin/mmdc").is_file()


def test_missing_mmdc_with_fence_exit_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "doc.md", "```mermaid\ngraph TD\n```\n")
    monkeypatch.setattr(lint_mermaid_fences, "_repo_root", lambda: tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path / "empty-bin"))
    rc, _out, err = run_in(tmp_path, monkeypatch, capsys, ["doc.md"])
    assert rc == 2
    assert "missing Mermaid CLI" in err


def test_changed_files_non_ci_origin_missing_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _ = subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    rc, _out, err = run_in(tmp_path, monkeypatch, capsys, ["--changed-only"])
    assert rc == 0
    assert "origin/main unavailable" in err


def test_changed_files_ci_origin_missing_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _ = subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.delenv("GITHUB_EVENT_NAME", raising=False)
    rc, _out, err = run_in(tmp_path, monkeypatch, capsys, ["--changed-only"])
    assert rc == 2
    assert "origin/main unavailable in CI" in err


def test_push_fallback_range(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.append(cmd)
        if len(cmd) > 1 and cmd[1] == "diff":
            return subprocess.CompletedProcess(cmd, 0, stdout="doc.md\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(lint_mermaid_fences.subprocess, "run", fake_run)
    rc, files = lint_mermaid_fences._changed_files(root=tmp_path, env={"GITHUB_EVENT_NAME": "push"})  # pyright: ignore[reportPrivateUsage]
    assert rc == 0
    assert files == ["doc.md"]
    assert any("HEAD~1..HEAD" in cmd for cmd in seen)
