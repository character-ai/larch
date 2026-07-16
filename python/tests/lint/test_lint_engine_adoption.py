"""Coverage for the shared lint-engine adoption ratchet."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from typing import cast

from larch.lint import lint_engine_adoption as lint
from larch.lint.engine import (
    EXIT_CLEAN,
    EXIT_ERROR,
    EXIT_FINDINGS,
    Finding,
    SourceFile,
    run_rule,
)
from tests.lint.test_lint_engine import (
    RecordingRunner,
    _git_ok_runner,  # type: ignore[reportPrivateUsage]  # shared helper from sibling lint test module
    _write_files,  # type: ignore[reportPrivateUsage]  # shared helper from sibling lint test module
)

SCOPE = "python/larch/lint"


def _source(name: str, text: str) -> SourceFile:
    path = f"{SCOPE}/{name}"
    return SourceFile(path=path, text=text, lines=tuple(text.splitlines()))


def _baseline_row(
    path: str,
    *,
    line: int = 1,
    message: str = lint.MSG_ARGPARSE,
    anchor: str = lint.ANCHOR_ARGPARSE,
    reason: str = "deferred legacy debt",
) -> dict[str, object]:
    return {
        "path": path,
        "line": line,
        "rule_id": lint.RULE_ID,
        "message": message,
        "anchor": anchor,
        "reason": reason,
    }


def _invoke(
    root: Path,
    runner: RecordingRunner,
    *,
    paths: list[str] | None = None,
    baseline_path: str | Path | None = None,
    write_baseline: bool = False,
    initial_reason: str | None = None,
    strict_stale: bool = False,
) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = run_rule(
            lint.RULE,
            root,
            runner,
            paths=paths,
            baseline_path=baseline_path,
            write_baseline=write_baseline,
            initial_reason=initial_reason,
            strict_stale=strict_stale,
        )
    return code, stdout.getvalue(), stderr.getvalue()


def test_allow_inline_suppression_is_false() -> None:
    assert lint.RULE.allow_inline_suppression is False


def test_detect_direct_argparse_construction() -> None:
    text = (
        "import argparse\n"
        "\n"
        "def main(argv: list[str] | None = None) -> int:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    return 0\n"
    )
    findings = lint.detect(_source("lint_demo.py", text))
    assert len(findings) == 1
    assert findings[0].message == lint.MSG_ARGPARSE
    assert findings[0].anchor == lint.ANCHOR_ARGPARSE


def test_detect_module_alias_and_symbol_alias_argparse() -> None:
    module_alias = (
        "import argparse as argparse_module\n"
        "\n"
        "def main() -> int:\n"
        "    parser = argparse_module.ArgumentParser()\n"
        "    return 0\n"
    )
    symbol_alias = (
        "from argparse import ArgumentParser as Parser\n"
        "\n"
        "def main() -> int:\n"
        "    parser = Parser()\n"
        "    return 0\n"
    )
    for text in (module_alias, symbol_alias):
        findings = lint.detect(_source("lint_keyword_only_like.py", text))
        assert len(findings) == 1
        assert findings[0].anchor == lint.ANCHOR_ARGPARSE


def test_detect_ignores_comments_docstrings_strings_refs_and_subclasses() -> None:
    text = (
        '"""Use argparse.ArgumentParser in docs only."""\n'
        "# argparse.ArgumentParser()\n"
        'MSG = "argparse.ArgumentParser()"\n'
        "import argparse\n"
        "\n"
        "class Custom(argparse.ArgumentParser):\n"
        "    pass\n"
        "\n"
        "def helper() -> type:\n"
        "    return argparse.ArgumentParser\n"
        "\n"
        "def main() -> int:\n"
        "    return 0\n"
    )
    assert not lint.detect(_source("lint_clean_refs.py", text))


def test_engine_adoption_via_main_run_rule_exempts_parser_only() -> None:
    text = (
        "import argparse\n"
        "from pathlib import Path\n"
        "from larch.lint.engine import run_rule\n"
        "\n"
        'BASELINE_FILENAME = "demo-baseline.json"\n'
        "\n"
        "def main(argv: list[str] | None = None) -> int:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    root = Path('.')\n"
        "    return run_rule(RULE, root, runner)\n"
    )
    findings = lint.detect(_source("lint_adopted.py", text))
    assert not findings


def test_engine_import_without_main_call_does_not_exempt() -> None:
    text = (
        "import argparse\n"
        "from larch.lint.engine import run_rule\n"
        "\n"
        "def helper() -> int:\n"
        "    return run_rule(RULE, root, runner)\n"
        "\n"
        "def main() -> int:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    return 0\n"
    )
    findings = lint.detect(_source("lint_import_only.py", text))
    assert len(findings) == 1
    assert findings[0].anchor == lint.ANCHOR_ARGPARSE


def test_aliased_run_rule_import_with_main_delegation_exempts() -> None:
    text = (
        "import argparse\n"
        "from larch.lint.engine import run_rule as engine_run\n"
        "\n"
        "def main() -> int:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    return engine_run(RULE, root, runner)\n"
    )
    assert not lint.detect(_source("lint_aliased_engine.py", text))


def test_unrelated_run_rule_name_does_not_exempt() -> None:
    text = (
        "import argparse\n"
        "\n"
        "def run_rule(rule: object, root: object, runner: object) -> int:\n"
        "    return 0\n"
        "\n"
        "def main() -> int:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    return run_rule(None, None, None)\n"
    )
    findings = lint.detect(_source("lint_fake_run_rule.py", text))
    assert len(findings) == 1
    assert findings[0].anchor == lint.ANCHOR_ARGPARSE


def test_pragma_does_not_clear_finding() -> None:
    text = (
        "import argparse\n"
        "\n"
        "def main() -> int:\n"
        "    parser = argparse.ArgumentParser()  "
        f"# {lint.SUPPRESSION_TOKEN}: ok deliberate\n"
        "    return 0\n"
    )
    findings = lint.detect(_source("lint_pragma.py", text))
    assert len(findings) == 1
    assert findings[0].anchor == lint.ANCHOR_ARGPARSE


def test_one_finding_per_class_across_multiple_sites() -> None:
    text = (
        "import argparse\n"
        "from pathlib import Path\n"
        "\n"
        'BASELINE_FILENAME = "demo-baseline.json"\n'
        "\n"
        "def load_baseline(path: Path) -> object:\n"
        "    return path.read_text(encoding='utf-8')\n"
        "\n"
        "def main() -> int:\n"
        "    a = argparse.ArgumentParser()\n"
        "    b = argparse.ArgumentParser()\n"
        "    root = Path('.')\n"
        "    first = root / 'python' / BASELINE_FILENAME\n"
        "    second = root / 'python' / BASELINE_FILENAME\n"
        "    _ = load_baseline(first)\n"
        "    _ = load_baseline(second)\n"
        "    return 0\n"
    )
    findings = lint.detect(_source("lint_multi.py", text))
    anchors = sorted(f.anchor for f in findings if f.anchor is not None)
    assert anchors == [lint.ANCHOR_ARGPARSE, lint.ANCHOR_BASELINE]
    assert all(f.message in {lint.MSG_ARGPARSE, lint.MSG_BASELINE} for f in findings)


def test_baseline_direct_write_and_helper_indirection() -> None:
    direct = (
        "from pathlib import Path\n"
        "\n"
        'BASELINE_FILENAME = "demo-baseline.json"\n'
        "\n"
        "def main() -> int:\n"
        "    path = Path('python') / BASELINE_FILENAME\n"
        "    _ = path.write_text('[]\\n', encoding='utf-8')\n"
        "    return 0\n"
    )
    helper = (
        "import json\n"
        "from pathlib import Path\n"
        "\n"
        'BASELINE_FILENAME = "demo-baseline.json"\n'
        "\n"
        "def load_baseline(path: Path) -> object:\n"
        "    return json.loads(path.read_text(encoding='utf-8'))\n"
        "\n"
        "def main() -> int:\n"
        "    root = Path('.')\n"
        "    baseline_path = root / 'python' / BASELINE_FILENAME\n"
        "    _ = load_baseline(baseline_path)\n"
        "    return 0\n"
    )
    for text in (direct, helper):
        findings = lint.detect(_source("lint_baseline_io.py", text))
        assert len(findings) == 1
        assert findings[0].anchor == lint.ANCHOR_BASELINE
        assert findings[0].message == lint.MSG_BASELINE


def test_unrelated_json_and_non_baseline_files_are_clean() -> None:
    text = (
        "import json\n"
        "from pathlib import Path\n"
        "\n"
        "def main() -> int:\n"
        "    payload = json.loads('[]')\n"
        "    path = Path('python') / 'manifest.json'\n"
        "    _ = path.read_text(encoding='utf-8')\n"
        "    return len(payload)\n"
    )
    assert not lint.detect(_source("lint_json_clean.py", text))


def test_adopted_module_still_reports_baseline_io() -> None:
    text = (
        "import argparse\n"
        "from pathlib import Path\n"
        "from larch.lint.engine import run_rule\n"
        "\n"
        'BASELINE_FILENAME = "demo-baseline.json"\n'
        "\n"
        "def main() -> int:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    path = Path('python') / BASELINE_FILENAME\n"
        "    _ = path.write_text('[]\\n', encoding='utf-8')\n"
        "    return run_rule(RULE, Path('.'), runner)\n"
    )
    findings = lint.detect(_source("lint_adopted_baseline.py", text))
    assert len(findings) == 1
    assert findings[0].anchor == lint.ANCHOR_BASELINE


def test_stable_identity_after_line_movement() -> None:
    early = (
        "import argparse\n"
        "\n"
        "def main() -> int:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    return 0\n"
    )
    late = (
        "import argparse\n"
        "\n"
        "CONST = 1\n"
        "OTHER = 2\n"
        "\n"
        "def main() -> int:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    return 0\n"
    )
    first = lint.detect(_source("lint_move.py", early))[0]
    second = lint.detect(_source("lint_move.py", late))[0]
    assert first.anchor == second.anchor == lint.ANCHOR_ARGPARSE
    assert first.message == second.message
    assert first.path == second.path
    assert first.line != second.line


def test_out_of_scope_paths_ignored() -> None:
    text = "import argparse\n\ndef main() -> int:\n    argparse.ArgumentParser()\n    return 0\n"
    assert not lint.detect(
        SourceFile(
            path="python/larch/other.py",
            text=text,
            lines=tuple(text.splitlines()),
        )
    )


def test_run_rule_unbaselined_debt_exits_one(tmp_path: Path) -> None:
    rel = f"{SCOPE}/lint_demo.py"
    text = (
        "import argparse\n"
        "\n"
        "def main() -> int:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    return 0\n"
    )
    _write_files(tmp_path, {rel: text})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text("[]\n", encoding="utf-8")
    code, out, err = _invoke(
        tmp_path,
        _git_ok_runner(tmp_path, [rel, f"python/{lint.BASELINE_FILENAME}"]),
        paths=[SCOPE],
        baseline_path=baseline,
        strict_stale=True,
    )
    assert code == EXIT_FINDINGS
    assert err == ""
    assert f"{rel}:" in out
    assert lint.MSG_ARGPARSE in out


def test_run_rule_baselined_debt_exits_zero(tmp_path: Path) -> None:
    rel = f"{SCOPE}/lint_demo.py"
    text = (
        "import argparse\n"
        "\n"
        "def main() -> int:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    return 0\n"
    )
    _write_files(tmp_path, {rel: text})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    findings = lint.detect(_source("lint_demo.py", text))
    assert findings
    row = _baseline_row(rel, line=findings[0].line)
    _ = baseline.write_text(json.dumps([row], indent=2) + "\n", encoding="utf-8")
    code, out, err = _invoke(
        tmp_path,
        _git_ok_runner(tmp_path, [rel]),
        paths=[SCOPE],
        baseline_path=baseline,
        strict_stale=True,
    )
    assert code == EXIT_CLEAN
    assert out == ""
    assert err == ""


def test_run_rule_stale_warns_without_strict(tmp_path: Path) -> None:
    rel = f"{SCOPE}/lint_demo.py"
    _write_files(tmp_path, {rel: "def main() -> int:\n    return 0\n"})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text(
        json.dumps([_baseline_row(rel)], indent=2) + "\n",
        encoding="utf-8",
    )
    code, out, err = _invoke(
        tmp_path,
        _git_ok_runner(tmp_path, [rel]),
        paths=[SCOPE],
        baseline_path=baseline,
        strict_stale=False,
    )
    assert code == EXIT_CLEAN
    assert out == ""
    assert "stale baseline row" in err


def test_run_rule_strict_stale_exits_two(tmp_path: Path) -> None:
    rel = f"{SCOPE}/lint_demo.py"
    _write_files(tmp_path, {rel: "def main() -> int:\n    return 0\n"})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text(
        json.dumps([_baseline_row(rel)], indent=2) + "\n",
        encoding="utf-8",
    )
    code, out, err = _invoke(
        tmp_path,
        _git_ok_runner(tmp_path, [rel]),
        paths=[SCOPE],
        baseline_path=baseline,
        strict_stale=True,
    )
    assert code == EXIT_ERROR
    assert out == ""
    assert "stale baseline row" in err


def test_run_rule_reasonless_baseline_exits_two(tmp_path: Path) -> None:
    rel = f"{SCOPE}/lint_demo.py"
    text = (
        "import argparse\n"
        "\n"
        "def main() -> int:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    return 0\n"
    )
    _write_files(tmp_path, {rel: text})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    findings = lint.detect(_source("lint_demo.py", text))
    row = _baseline_row(rel, line=findings[0].line, reason="")
    _ = baseline.write_text(json.dumps([row], indent=2) + "\n", encoding="utf-8")
    code, out, err = _invoke(
        tmp_path,
        _git_ok_runner(tmp_path, [rel]),
        paths=[SCOPE],
        baseline_path=baseline,
        strict_stale=True,
    )
    assert code == EXIT_ERROR
    assert out == ""
    assert "invalid reason" in err


def test_write_requires_initial_reason_for_new_rows(tmp_path: Path) -> None:
    rel = f"{SCOPE}/lint_demo.py"
    text = (
        "import argparse\n"
        "\n"
        "def main() -> int:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    return 0\n"
    )
    _write_files(tmp_path, {rel: text})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text("[]\n", encoding="utf-8")
    code, _out, err = _invoke(
        tmp_path,
        _git_ok_runner(tmp_path, [rel]),
        baseline_path=baseline,
        write_baseline=True,
    )
    assert code == EXIT_ERROR
    assert "initial_reason" in err or "missing baseline reason" in err


def test_write_with_initial_reason_succeeds(tmp_path: Path) -> None:
    rel = f"{SCOPE}/lint_demo.py"
    text = (
        "import argparse\n"
        "\n"
        "def main() -> int:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    return 0\n"
    )
    _write_files(tmp_path, {rel: text})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    _ = baseline.write_text("[]\n", encoding="utf-8")
    before = baseline.read_bytes()
    code, _out, _err = _invoke(
        tmp_path,
        _git_ok_runner(tmp_path, [rel]),
        baseline_path=baseline,
        write_baseline=True,
        initial_reason="seeded for test",
    )
    assert code == EXIT_CLEAN
    after = baseline.read_bytes()
    assert after != before
    rows = json.loads(after.decode("utf-8"))
    assert isinstance(rows, list)
    assert rows
    assert rows[0]["reason"] == "seeded for test"
    assert rows[0]["anchor"] == lint.ANCHOR_ARGPARSE


def test_check_only_leaves_baseline_bytes_unchanged(tmp_path: Path) -> None:
    rel = f"{SCOPE}/lint_demo.py"
    text = (
        "import argparse\n"
        "\n"
        "def main() -> int:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    return 0\n"
    )
    _write_files(tmp_path, {rel: text})
    baseline = tmp_path / "python" / lint.BASELINE_FILENAME
    baseline.parent.mkdir(parents=True, exist_ok=True)
    findings = lint.detect(_source("lint_demo.py", text))
    row = _baseline_row(rel, line=findings[0].line)
    payload = (json.dumps([row], indent=2) + "\n").encode("utf-8")
    _ = baseline.write_bytes(payload)
    code, _out, _err = _invoke(
        tmp_path,
        _git_ok_runner(tmp_path, [rel]),
        paths=[SCOPE],
        baseline_path=baseline,
        strict_stale=True,
    )
    assert code == EXIT_CLEAN
    assert baseline.read_bytes() == payload


def test_cli_argument_errors() -> None:
    assert lint.main(["--initial-reason", ""]) == EXIT_ERROR
    assert lint.main(["--root", "/no/such/repo/for/engine-adoption"]) == EXIT_ERROR


def test_committed_tree_projection_covers_legacy_and_spares_engine() -> None:
    repo = Path(__file__).resolve().parents[3]
    baseline_path = repo / "python" / lint.BASELINE_FILENAME
    assert baseline_path.is_file()
    raw = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert isinstance(raw, list)
    rows = cast("list[dict[str, object]]", raw)
    identities = {
        (row["path"], row["rule_id"], row["message"], row["anchor"]) for row in rows
    }
    live: list[Finding] = []
    for path in sorted((repo / SCOPE).glob("lint_*.py")):
        rel = path.relative_to(repo).as_posix()
        text = path.read_text(encoding="utf-8")
        live.extend(
            lint.detect(
                SourceFile(path=rel, text=text, lines=tuple(text.splitlines()))
            )
        )
    live_ids = {(f.path, f.rule_id, f.message, f.anchor) for f in live}
    assert live_ids == identities
    for clean in (
        f"{SCOPE}/lint_engine_adoption.py",
        f"{SCOPE}/lint_pylint_skip_file.py",
        f"{SCOPE}/lint_unreachable_branch.py",
        f"{SCOPE}/lint_markdown_heading_fence_state.py",
        f"{SCOPE}/lint_kv_codec.py",
        f"{SCOPE}/lint_module_manifest.py",
        f"{SCOPE}/lint_tmpdir_arg_env_fallback.py",
        f"{SCOPE}/lint_self_disarmable_gate.py",
        f"{SCOPE}/lint_keyword_only.py",
        f"{SCOPE}/lint_wire_artifact_pairing.py",
        f"{SCOPE}/lint_renderer_golden_tests.py",
        f"{SCOPE}/lint_guideline_no_exception.py",
    ):
        assert not any(row[0] == clean for row in live_ids)
