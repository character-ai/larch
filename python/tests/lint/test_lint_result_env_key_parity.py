from __future__ import annotations

import contextlib
import io
import json
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from larch.lint import lint_result_env_key_parity as lrp
from larch.lint.engine import (
    EXIT_CLEAN,
    EXIT_ERROR,
    EXIT_FINDINGS,
    Finding,
    SourceFile,
    run_rule,
)
from tests.lint.test_lint_engine import (
    _git_ok_runner,  # type: ignore[reportPrivateUsage]  # shared helper from sibling lint test module
    _write_files,  # type: ignore[reportPrivateUsage]  # shared helper from sibling lint test module
)

if TYPE_CHECKING:
    import pytest

REL_A = "python/larch/writer_a.py"
REL_B = "python/larch/writer_b.py"


def _writer_src(basename: str, keys: list[str], *, pragma: bool = False, dynamic: bool = False) -> str:
    open_line = "    phase_driver_write_result_env("
    if pragma:
        open_line += "  # lint-result-env-key-parity: ok fixture divergence"
    if dynamic:
        kv_line = "        kvs=rows,"
    else:
        items = ", ".join(f'("{key}", "value")' for key in keys)
        kv_line = f"        kvs=[{items}],"
    return (
        "from pathlib import Path\n"
        "\n"
        "def emit(tmpdir: Path, rows: list) -> None:\n"
        f"{open_line}\n"
        f'        path=tmpdir / "{basename}",\n'
        f"{kv_line}\n"
        "    )\n"
    )


def _source(rel: str, text: str) -> SourceFile:
    return SourceFile(path=rel, text=text, lines=tuple(text.splitlines()))


def _findings(sources: Sequence[SourceFile]) -> list[Finding]:
    prepared = lrp.prepare_corpus(sources)
    collected: list[Finding] = []
    for source in sources:
        collected.extend(lrp.detect(source, prepared=prepared))
    return collected


def _finding_row(finding: Finding, *, reason: str = "grandfathered") -> dict[str, object]:
    return {
        "path": finding.path,
        "line": finding.line,
        "rule_id": finding.rule_id,
        "message": finding.message,
        "reason": reason,
        "anchor": finding.anchor,
    }


def _seed_baseline(root: Path, rows: list[dict[str, object]]) -> Path:
    path = root / "python" / lrp.BASELINE_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return path


def _run(
    root: Path,
    tracked: Sequence[str],
    *,
    baseline_path: Path,
    write_baseline: bool = False,
    initial_reason: str | None = None,
) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = run_rule(
            lrp.build_rule(),
            root,
            _git_ok_runner(root, tracked),
            baseline_path=baseline_path,
            write_baseline=write_baseline,
            initial_reason=initial_reason,
        )
    return code, stdout.getvalue(), stderr.getvalue()


# --- detection (corpus prepare + per-source detect) ---------------------------


def test_identical_key_sets_produce_no_finding() -> None:
    sources = [
        _source(REL_A, _writer_src("slot.env", ["A", "B"])),
        _source(REL_B, _writer_src("slot.env", ["A", "B"])),
    ]
    assert not _findings(sources)


def test_missing_key_names_basename_path_and_key() -> None:
    sources = [
        _source(REL_A, _writer_src("slot.env", ["A", "B"])),
        _source(REL_B, _writer_src("slot.env", ["A"])),
    ]
    findings = _findings(sources)
    assert len(findings) == 1
    finding = findings[0]
    assert finding.path == REL_B
    assert finding.rule_id == lrp.RULE_ID
    assert finding.message == "slot.env writer missing key B present in sibling writers"
    assert finding.anchor == "slot.env:B"


def test_optional_key_suppresses_violation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(lrp.OPTIONAL_KEYS, "slot.env", frozenset({"B"}))
    sources = [
        _source(REL_A, _writer_src("slot.env", ["A", "B"])),
        _source(REL_B, _writer_src("slot.env", ["A"])),
    ]
    assert not _findings(sources)


def test_dynamic_kv_argument_is_skipped_without_violation() -> None:
    sources = [
        _source(REL_A, _writer_src("slot.env", ["A", "B"])),
        _source(REL_B, _writer_src("slot.env", [], dynamic=True)),
    ]
    assert not _findings(sources)


def test_single_writer_is_never_a_violation() -> None:
    sources = [_source(REL_A, _writer_src("solo.env", ["A", "B", "C"]))]
    assert not _findings(sources)


# --- engine run (discovery, pragma, baseline) ---------------------------------


def test_pragma_on_call_line_suppresses_violation(tmp_path: Path) -> None:
    _write_files(
        tmp_path,
        {
            REL_A: _writer_src("slot.env", ["A", "B"]),
            REL_B: _writer_src("slot.env", ["A"], pragma=True),
        },
    )
    baseline_path = _seed_baseline(tmp_path, [])
    code, out, _err = _run(tmp_path, [REL_A, REL_B], baseline_path=baseline_path)
    assert code == EXIT_CLEAN
    assert out == ""


def test_unbaselined_violation_exits_one(tmp_path: Path) -> None:
    _write_files(
        tmp_path,
        {REL_A: _writer_src("slot.env", ["A", "B"]), REL_B: _writer_src("slot.env", ["A"])},
    )
    baseline_path = _seed_baseline(tmp_path, [])
    code, out, _err = _run(tmp_path, [REL_A, REL_B], baseline_path=baseline_path)
    assert code == EXIT_FINDINGS
    assert f"{REL_B}:" in out
    assert "slot.env writer missing key B present in sibling writers" in out


def test_baseline_record_suppresses_and_shrinks(tmp_path: Path) -> None:
    sources = [
        _source(REL_A, _writer_src("slot.env", ["A", "B"])),
        _source(REL_B, _writer_src("slot.env", ["A"])),
    ]
    findings = _findings(sources)
    _write_files(
        tmp_path,
        {REL_A: _writer_src("slot.env", ["A", "B"]), REL_B: _writer_src("slot.env", ["A"])},
    )

    baseline_path = _seed_baseline(tmp_path, [_finding_row(findings[0])])
    code, _out, _err = _run(tmp_path, [REL_A, REL_B], baseline_path=baseline_path)
    assert code == EXIT_CLEAN

    _ = _seed_baseline(tmp_path, [])
    code, _out, _err = _run(tmp_path, [REL_A, REL_B], baseline_path=baseline_path)
    assert code == EXIT_FINDINGS


def test_write_seeds_reason_and_check_then_passes(tmp_path: Path) -> None:
    _write_files(
        tmp_path,
        {REL_A: _writer_src("slot.env", ["A", "B"]), REL_B: _writer_src("slot.env", ["A"])},
    )
    baseline_path = _seed_baseline(tmp_path, [])

    code, _out, _err = _run(
        tmp_path,
        [REL_A, REL_B],
        baseline_path=baseline_path,
        write_baseline=True,
        initial_reason="grandfathered divergent writers",
    )
    assert code == EXIT_CLEAN
    rows = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert len(rows) == 1
    assert rows[0]["path"] == REL_B
    assert rows[0]["anchor"] == "slot.env:B"
    assert rows[0]["reason"] == "grandfathered divergent writers"

    code, _out, _err = _run(tmp_path, [REL_A, REL_B], baseline_path=baseline_path)
    assert code == EXIT_CLEAN


def test_write_without_initial_reason_for_new_violation_exits_2(tmp_path: Path) -> None:
    _write_files(
        tmp_path,
        {REL_A: _writer_src("slot.env", ["A", "B"]), REL_B: _writer_src("slot.env", ["A"])},
    )
    baseline_path = _seed_baseline(tmp_path, [])
    code, _out, _err = _run(
        tmp_path, [REL_A, REL_B], baseline_path=baseline_path, write_baseline=True
    )
    assert code == EXIT_ERROR


def test_malformed_baseline_reason_exits_2(tmp_path: Path) -> None:
    sources = [
        _source(REL_A, _writer_src("slot.env", ["A", "B"])),
        _source(REL_B, _writer_src("slot.env", ["A"])),
    ]
    findings = _findings(sources)
    _write_files(
        tmp_path,
        {REL_A: _writer_src("slot.env", ["A", "B"]), REL_B: _writer_src("slot.env", ["A"])},
    )
    baseline_path = _seed_baseline(tmp_path, [_finding_row(findings[0], reason="")])
    code, _out, _err = _run(tmp_path, [REL_A, REL_B], baseline_path=baseline_path)
    assert code == EXIT_ERROR


def test_main_empty_initial_reason_exits_2() -> None:
    assert lrp.main(["--initial-reason", ""]) == EXIT_ERROR


def test_main_missing_repository_exits_2() -> None:
    assert lrp.main(["--root", "/no/such/repo/for/result-env-key-parity"]) == EXIT_ERROR
