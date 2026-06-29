from __future__ import annotations

# ruff: noqa: UP022
# pyright: reportUnusedCallResult=false

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from larch.research import research_eval

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / "python" / "cli.py"


def fake_claude_path(name: str) -> str | None:
    return "/bin/claude" if name == "claude" else None


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["LARCH_QUIET_DISABLE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run([sys.executable, str(CLI), *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=merged, check=False)


def test_validate_research_output_word_count_and_provenance(tmp_path: Path) -> None:
    prose = " ".join(["word"] * 35)
    cited = write(tmp_path / "ok.md", prose + "\nSee python/research_eval.py:1.\n")
    assert research_eval.validate_research_output(cited, min_words=30) == 0
    thin = write(tmp_path / "thin.md", "too short python/research_eval.py:1\n")
    assert research_eval.validate_research_output(thin, min_words=30) == 2
    no_cite = write(tmp_path / "nocite.md", prose + "\n")
    assert research_eval.validate_research_output(no_cite, min_words=30) == 3
    assert research_eval.validate_research_output(no_cite, min_words=30, require_citations=False) == 0


def test_validation_mode_sentinels_and_thresholds(tmp_path: Path) -> None:
    assert research_eval.validate_research_output(write(tmp_path / "no.txt", "NO_ISSUES_FOUND\n"), validation_mode=True) == 0
    assert research_eval.validate_research_output(write(tmp_path / "json.txt", '{"no_issues_found": true}\ntrailing\n'), validation_mode=True) == 0
    assert research_eval.validate_research_output(write(tmp_path / "last.txt", "narration\nNO_ISSUES_FOUND\n"), validation_mode=True) == 0
    assert research_eval.validate_research_output(write(tmp_path / "vote.txt", "FINDING_1: YES\n"), validation_mode=True) == 0
    degraded = write(tmp_path / "deg.txt", "CURSOR_DEGRADED_RESPONSE\n")
    cp = run_cli("eval", "validate-research-output", "--validation-mode", str(degraded))
    assert cp.returncode == 5
    assert "STATUS=CURSOR_EMPTY_RESPONSE" in cp.stdout
    empty = write(tmp_path / "empty.txt", "CURSOR_EMPTY_RESPONSE\n")
    assert research_eval.validate_research_output(empty, validation_mode=True) == 5
    short = write(tmp_path / "short.md", " ".join(["word"] * 31) + "\npython/research_eval.py:1\n")
    assert run_cli("eval", "validate-research-output", "--validation-mode", str(short)).returncode == 0
    assert run_cli("eval", "validate-research-output", "--validation-mode", "--min-words", "10", str(short)).returncode == 0
    assert run_cli("eval", "validate-research-output", str(short)).returncode == 2
    tsv = write(
        tmp_path / "inline.tsv",
        "schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix\n"
        "1\tin_scope\timportant\tcorrectness\tpython/research_eval.py:1\twhat\tbreaks\tfix\n",
    )
    assert research_eval.validate_research_output(tsv, validation_mode=True) == 0


def test_fenced_words_excluded_and_code_fence_counts_as_provenance(tmp_path: Path) -> None:
    body = " ".join(["word"] * 30) + "\n```\ncode here\n```\n"
    path = write(tmp_path / "code.md", body)
    assert research_eval.validate_research_output(path, min_words=30) == 0
    assert research_eval.validate_research_output(path, min_words=31) == 2


def test_structured_jsonl_tsv_and_sentinel(tmp_path: Path) -> None:
    out = tmp_path / "records.jsonl"
    record = {
        "schema_version": 1,
        "scope": "in_scope",
        "severity": "Important",
        "focus_area": "correctness",
        "location": "python/research_eval.py:1",
        "what": "what",
        "scenario_or_breakage": "breaks",
        "suggested_fix": "fix",
    }
    blocking_record = {**record, "severity": "Blocking", "focus_area": "architecture"}
    path = write(tmp_path / "jsonl.txt", json.dumps(record) + "\n" + json.dumps(blocking_record) + "\n")
    assert research_eval.validate_research_output(path, structured_reviewer_mode=True, write_structured=out) == 0
    normalized_jsonl = out.read_text(encoding="utf-8")
    assert '"severity":"important"' in normalized_jsonl
    assert '"severity":"blocking"' in normalized_jsonl
    tsv = write(tmp_path / "records.tsv", "schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix\n1\tout_of_scope\tBlocking\tsecurity\tpython/research_eval.py:1\twhat\tscenario\tfix extra\n")
    assert research_eval.validate_research_output(tsv, structured_reviewer_mode=True, write_structured=out) == 0
    normalized_tsv = out.read_text(encoding="utf-8")
    assert "\tblocking\tsecurity\t" in normalized_tsv
    assert "fix extra" in normalized_tsv
    no = write(tmp_path / "no.txt", '{"no_issues_found": true}\n')
    assert research_eval.validate_research_output(no, structured_reviewer_mode=True, write_structured=out) == 0
    assert out.read_text(encoding="utf-8") == ""
    bad = write(tmp_path / "bad.txt", "not structured\n")
    cp = run_cli("eval", "validate-research-output", "--structured-reviewer-mode", "--write-structured", str(out), str(bad))
    assert cp.returncode == 5
    assert "structured records not found after repair" in cp.stdout


def test_structured_reviewer_no_issues_salvage_paths(tmp_path: Path) -> None:
    out = tmp_path / "records.jsonl"

    # Prose preamble + standalone JSON sentinel -> salvage, empty sidecar.
    assert research_eval.validate_structured_reviewer_output('Looks good to me.\n{"no_issues_found": true}\n', write_structured=out) == 0
    assert out.read_text(encoding="utf-8") == ""

    # Prose preamble + bare NO_ISSUES_FOUND -> salvage, empty sidecar.
    assert research_eval.validate_structured_reviewer_output("All clear.\nNO_ISSUES_FOUND\n", write_structured=out) == 0
    assert out.read_text(encoding="utf-8") == ""

    # Multi-line pretty-printed sentinel (joined-body strict tier 1) -> salvage, empty sidecar.
    assert research_eval.validate_structured_reviewer_output('{\n  "no_issues_found": true\n}\n', write_structured=out) == 0
    assert out.read_text(encoding="utf-8") == ""

    # Two standalone sentinels -> no salvage (exit 5).
    assert research_eval.validate_structured_reviewer_output('{"no_issues_found": true}\n{"no_issues_found": true}\n', write_structured=out) == 5

    # Prose + schema_version-bearing JSON line + lone sentinel -> schema_version guard blocks salvage (exit 5).
    assert (
        research_eval.validate_structured_reviewer_output(
            'Findings below.\n{"schema_version": 1, "scope": "in_scope"}\n{"no_issues_found": true}\n',
            write_structured=out,
        )
        == 5
    )

    # Mixed multiple sentinel lines -> no salvage (exit 5).
    assert research_eval.validate_structured_reviewer_output('NO_ISSUES_FOUND\n{"no_issues_found": true}\n', write_structured=out) == 5

    # Inline JSON embedded in narration (no standalone sentinel) -> no salvage (exit 5).
    assert research_eval.validate_structured_reviewer_output('The tool said {"no_issues_found": true} and stopped.\n', write_structured=out) == 5


def test_structured_reviewer_valid_record_plus_sentinel_keeps_record(tmp_path: Path) -> None:
    out = tmp_path / "records.jsonl"
    record = {
        "schema_version": 1,
        "scope": "in_scope",
        "severity": "important",
        "focus_area": "correctness",
        "location": "python/research_eval.py:1",
        "what": "what",
        "scenario_or_breakage": "breaks",
        "suggested_fix": "fix",
    }
    text = json.dumps(record) + '\n{"no_issues_found": true}\n'
    assert research_eval.validate_structured_reviewer_output(text, write_structured=out) == 0
    normalized = out.read_text(encoding="utf-8")
    assert '"no_issues_found"' not in normalized
    assert '"schema_version":1' in normalized


def test_structured_reviewer_preamble_warning_only_for_per_line_path(tmp_path: Path) -> None:
    out = tmp_path / "records.jsonl"
    # Per-line recovery after a preamble emits the warning on the contract stream (stdout).
    preamble = write(tmp_path / "preamble.txt", 'Everything looks fine.\n{"no_issues_found": true}\n')
    cp = run_cli("eval", "validate-research-output", "--structured-reviewer-mode", "--write-structured", str(out), str(preamble))
    assert cp.returncode == 0
    assert "WARNING=NO_ISSUES_SENTINEL_RECOVERED_AFTER_PREAMBLE" in cp.stdout
    # Joined-body (no preamble) salvage must NOT emit the preamble warning.
    joined = write(tmp_path / "joined.txt", '{\n  "no_issues_found": true\n}\n')
    cp2 = run_cli("eval", "validate-research-output", "--structured-reviewer-mode", "--write-structured", str(out), str(joined))
    assert cp2.returncode == 0
    assert "NO_ISSUES_SENTINEL_RECOVERED_AFTER_PREAMBLE" not in cp2.stdout


def test_structured_tsv_cursor_format_tolerance(tmp_path: Path) -> None:
    out = tmp_path / "records.tsv"
    header = "schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix\n"

    def normalize(text: str) -> str:
        assert research_eval.validate_structured_reviewer_output(text, write_structured=out) == 0
        return out.read_text(encoding="utf-8")

    # Cursor row-index defect: column 1 carries 1, 2, 3, ... instead of the
    # literal schema_version constant. Every row is kept and normalized to "1".
    row_index = normalize(
        header
        + "1\tin_scope\timportant\tcorrectness\tpython/foo.py:1\twhat\tscenario\tfix\n"
        + "2\tin_scope\timportant\tcorrectness\tpython/bar.py:2\twhat\tscenario\tfix\n"
        + "3\tin_scope\timportant\tcorrectness\tpython/baz.py:3\twhat\tscenario\tfix\n"
    )
    kept = [ln for ln in row_index.splitlines() if ln and not ln.startswith("schema_version")]
    assert len(kept) == 3
    assert all(ln.startswith("1\t") for ln in kept)

    # Cursor focus_area defect: completeness maps to code-quality (the single-row
    # C94E1D97 signature) without touching the _ALLOWED_FOCUS enum.
    mapped = normalize(header + "1\tin_scope\timportant\tcompleteness\tpython/foo.py:1\twhat\tscenario\tfix\n")
    kept_mapped = [ln for ln in mapped.splitlines() if ln and not ln.startswith("schema_version")]
    assert len(kept_mapped) == 1
    assert "\tcode-quality\t" in kept_mapped[0]
    assert "completeness" not in kept_mapped[0]

    # Issue #4994 repro end-to-end: a row-index column 1 AND a completeness row
    # now validate instead of dropping the whole slot.
    normalized = normalize(
        header
        + "1\tin_scope\timportant\tcompleteness\tpython/foo.py:1\twhat\tscenario\tfix\n"
        + "2\tin_scope\timportant\tcorrectness\tpython/bar.py:2\twhat\tscenario\tfix\n"
    )
    assert "\tcode-quality\t" in normalized
    assert normalized.count("\n1\t") == 2

    # A focus_area outside both the allowed set and the synonym map is rejected
    # (exit 5), and a non-integer column 1 (prose from a split row) too.
    assert (
        research_eval.validate_structured_reviewer_output(
            header + "1\tin_scope\timportant\tbogus\tpython/foo.py:1\twhat\tscenario\tfix\n", write_structured=out
        )
        == 5
    )
    assert (
        research_eval.validate_structured_reviewer_output(
            header + "prose\tin_scope\timportant\tcorrectness\tpython/foo.py:1\twhat\tscenario\tfix\n", write_structured=out
        )
        == 5
    )


def test_structured_tsv_multiline_row_joining(tmp_path: Path) -> None:
    out = tmp_path / "records.tsv"
    header = "schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix\n"
    text = (
        header
        + "1\tin_scope\timportant\tcorrectness\tpython/foo.py:1\tline one\n"
        + "line two\tbreaks on newline\tfix it\n"
    )
    assert research_eval.validate_structured_reviewer_output(text, write_structured=out) == 0
    normalized = out.read_text(encoding="utf-8")
    assert "line one line two" in normalized
    assert "breaks on newline" in normalized
    assert "fix it" in normalized


def test_structured_tsv_folds_overflow_tabs_into_suggested_fix(tmp_path: Path) -> None:
    out = tmp_path / "records.tsv"
    header = "schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix\n"
    text = header + "1\tin_scope\timportant\tcorrectness\tpython/foo.py:1\twhat\twith\ttab\tfix\n"
    assert research_eval.validate_structured_reviewer_output(text, write_structured=out) == 0
    normalized = out.read_text(encoding="utf-8")
    assert "tab fix" in normalized


def test_structured_tsv_salvages_seven_column_rows(tmp_path: Path) -> None:
    # Issue #5078: a content-valid row that is one tab short (seven columns) must
    # be salvaged rather than dropping the whole reviewer slot as NOT_SUBSTANTIVE.
    out = tmp_path / "records.tsv"
    header = "schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix\n"

    # Trailing delimiter omitted: seven fields, suggested_fix missing -> padded empty.
    seven_col = header + "1\tin_scope\timportant\tcorrectness\tpython/foo.py:1\twhat text\tscenario text\n"
    assert research_eval.validate_structured_reviewer_output(seven_col, write_structured=out) == 0
    kept = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln and not ln.startswith("schema_version")]
    assert len(kept) == 1
    assert kept[0].split("\t")[:7] == ["1", "in_scope", "important", "correctness", "python/foo.py:1", "what text", "scenario text"]

    # A tab collapsed into a run of spaces in the typed region is re-split into eight columns.
    spaced = header + "1\tin_scope\timportant\tcorrectness  python/bar.py:2\twhat\tscenario\tfix\n"
    assert research_eval.validate_structured_reviewer_output(spaced, write_structured=out) == 0
    salvaged = out.read_text(encoding="utf-8")
    assert "\tcorrectness\tpython/bar.py:2\t" in salvaged

    # A seven-column row whose leading typed fields do NOT validate is still rejected.
    bogus = header + "1\tin_scope\timportant\tbogus_focus\tpython/baz.py:3\twhat\tscenario\n"
    assert research_eval.validate_structured_reviewer_output(bogus, write_structured=out) == 5

    # Free-text double-space gap between what and scenario_or_breakage (not trailing pad).
    free_text_gap = (
        header + "1\tin_scope\timportant\tcorrectness\tpython/foo.py:1\twhat text  scenario text\tfix text\n"
    )
    assert research_eval.validate_structured_reviewer_output(free_text_gap, write_structured=out) == 0
    gap_kept = [ln for ln in out.read_text(encoding="utf-8").splitlines() if ln and not ln.startswith("schema_version")]
    assert len(gap_kept) == 1
    gap_fields = gap_kept[0].split("\t")
    assert gap_fields[5] == "what text"
    assert gap_fields[6] == "scenario text"
    assert gap_fields[7] == "fix text"

    # Multi-space prose inside a single free-text field on an under-delimited row is rejected.
    prose_fabrication = (
        header
        + "1\tin_scope\timportant\tcorrectness\tpython/foo.py:1\tconcern A  concern B  concern C  concern D\n"
    )
    assert research_eval.validate_structured_reviewer_output(prose_fabrication, write_structured=out) == 5


def test_structured_tsv_accepts_non_file_location(tmp_path: Path) -> None:
    out = tmp_path / "records.tsv"
    header = "schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix\n"
    for location in ("Testing strategy", "plan.txt"):
        text = header + f"1\tin_scope\timportant\tcorrectness\t{location}\twhat\tscenario\tfix\n"
        assert research_eval.validate_structured_reviewer_output(text, write_structured=out) == 0
        normalized = out.read_text(encoding="utf-8")
        assert f"\t{location}\t" in normalized


def test_structured_jsonl_completeness_synonym(tmp_path: Path) -> None:
    out = tmp_path / "records.jsonl"
    record = {
        "schema_version": 1,
        "scope": "in_scope",
        "severity": "important",
        "focus_area": "completeness",
        "location": "python/research_eval.py:1",
        "what": "what",
        "scenario_or_breakage": "breaks",
        "suggested_fix": "fix",
    }
    path = write(tmp_path / "jsonl.txt", json.dumps(record) + "\n")
    assert research_eval.validate_research_output(path, structured_reviewer_mode=True, write_structured=out) == 0
    normalized = out.read_text(encoding="utf-8")
    assert '"focus_area":"code-quality"' in normalized
    assert "completeness" not in normalized


def test_eval_set_and_baseline_schema() -> None:
    assert research_eval.validate_eval_set(ROOT / "skills/research/references/eval-set.md")
    assert research_eval.validate_baseline_json(ROOT / "skills/research/references/eval-baseline.json")
    assert research_eval.ANTHROPIC_EVAL_SOURCE == "anthropic.com/engineering/built-multi-agent-research-system"


def test_eval_smoke_and_no_claude_requirement(tmp_path: Path) -> None:
    env = {"PATH": str(tmp_path), "CLAUDE_PLUGIN_ROOT": str(ROOT)}
    cp = run_cli("eval", "research", "--smoke-test", env=env)
    assert cp.returncode == 0
    assert "smoke test PASS" in cp.stdout
    full = run_cli("eval", "research", "--id", "does-not-matter", env=env)
    assert full.returncode == 3
    assert "required tool missing: claude" in full.stderr


def test_eval_research_prompt_and_write_baseline_with_stubbed_claude(tmp_path: Path) -> None:
    stub = tmp_path / "claude"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        "input=$(cat)\n"
        "if grep -q 'JUDGE_SCORE_TOTAL' <<<\"$input\"; then\n"
        "  printf 'JUDGE_SCORE_TOTAL=80\\nJUDGE_SCORE_FACTUAL=16\\nJUDGE_SCORE_CITATION=16\\nJUDGE_SCORE_COMPLETENESS=16\\nJUDGE_SCORE_SOURCE_QUALITY=16\\nJUDGE_SCORE_TOOL_EFFICIENCY=16\\nJUDGE_RATIONALE=ok\\n'\n"
        "else\n"
        "  printf 'Result with python/research_eval.py:1 and https://example.com plus keyword architecture.\\n'\n"
        "fi\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    work = tmp_path / "work"
    baseline = tmp_path / "baseline.json"
    env = {"PATH": f"{tmp_path}:{os.environ.get('PATH','')}", "CLAUDE_PLUGIN_ROOT": str(ROOT)}
    cp = run_cli("eval", "research", "--id", "where-defined-rebase-push", "--work-dir", str(work), "--write-baseline", str(baseline), "--timeout", "5", "--judge-timeout", "5", env=env)
    assert cp.returncode == 0
    prompt = next(work.glob("*/prompt.txt")).read_text(encoding="utf-8")
    assert prompt.startswith("/larch:research --no-issue ")
    data = json.loads(baseline.read_text(encoding="utf-8"))
    assert data["version"] == 2
    assert data["generated_at"]
    assert isinstance(data["entries"], list)
    assert data["entries"]
    entry = data["entries"][0]
    assert entry["research_status"] == "ok"
    assert "provenance" in entry
    assert "judge_status" in entry


def test_eval_baseline_ref_validation_and_missing_values(tmp_path: Path) -> None:
    env = {"PATH": str(tmp_path), "CLAUDE_PLUGIN_ROOT": str(ROOT)}
    assert run_cli("eval", "research", "--baseline", "bad ref", "--smoke-test", env=env).returncode == 2
    assert run_cli("eval", "research", "--baseline", "--smoke-test", env=env).returncode == 2
    assert "requires a value" in run_cli("eval", "research", "--baseline", "--smoke-test", env=env).stderr
    assert run_cli("eval", "research", "--work-dir", "--smoke-test", env=env).returncode == 2
    assert run_cli("eval", "research", "--timeout", "abc", "--smoke-test", env=env).returncode == 2
    assert run_cli("eval", "validate-research-output").returncode == 1


def test_eval_id_no_match_exits_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(research_eval.shutil, "which", fake_claude_path)
    assert research_eval.eval_research(plugin_root=ROOT, id_filter="does-not-exist", work_dir=tmp_path) == 0


def test_eval_baseline_git_show_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(research_eval.shutil, "which", fake_claude_path)
    baseline_json = '{"version":2,"harness_commit":null,"model_id":null,"generated_at":null,"entries":[]}\n'

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if argv[:4] == ["git", "-C", str(ROOT), "show"]:
            stdout = kwargs.get("stdout")
            if stdout is not None:
                stdout.write(baseline_json)  # type: ignore[union-attr]
            return subprocess.CompletedProcess(argv, 0, stdout=baseline_json, stderr="")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="missing")

    monkeypatch.setattr(research_eval.subprocess, "run", fake_run)
    assert research_eval.eval_research(plugin_root=ROOT, baseline_ref="main", work_dir=tmp_path, id_filter="missing-id") == 0


def test_validate_research_output_unreadable_exits_four(tmp_path: Path) -> None:
    path = tmp_path / "secret.md"
    path.write_text("x\n", encoding="utf-8")
    path.chmod(0o000)
    try:
        assert research_eval.validate_research_output(path) == 4
    finally:
        path.chmod(0o644)


def test_parse_judge_output_fail_closed(tmp_path: Path) -> None:
    judge = tmp_path / "judge.txt"
    judge.write_text("not a judge response\n", encoding="utf-8")
    parsed = research_eval.parse_judge_output(judge)
    assert parsed["JUDGE_STATUS"] == "parse_failed"
    assert parsed["JUDGE_TOTAL"] == "null"


def test_classify_url_reputability_counts(tmp_path: Path) -> None:
    path = write(tmp_path / "research.md", "https://anthropic.com/a https://medium.com/b https://example.com/c\n")
    text = research_eval.classify_url_reputability(path)
    assert "URL_HIGH=1" in text
    assert "URL_LOW=1" in text
    assert "URL_UNKNOWN=1" in text


def test_research_status_timeout_mapping(tmp_path: Path) -> None:
    stderr = tmp_path / "research.stderr"
    stderr.write_text("TIMED_OUT_AFTER=5\n", encoding="utf-8")
    assert research_eval._research_status_from_run(rc=124, stderr_path=stderr) == "timeout"  # pyright: ignore[reportPrivateUsage]
    assert research_eval._research_status_from_run(rc=1, stderr_path=stderr) == "timeout"  # pyright: ignore[reportPrivateUsage]


def test_eval_set_failure_matrix(tmp_path: Path) -> None:
    bad = write(tmp_path / "bad.md", "### eval-1: ok\n- **question**: q?\n")
    assert research_eval.validate_eval_set(bad) is False
    dup = write(
        tmp_path / "dup.md",
        "**Consumer**: x\n**Contract**: y\n**When to load**: z\n"
        f"{research_eval.ANTHROPIC_EVAL_SOURCE}\n\n"
        "### eval-1: dup-id\n- **question**: q?\n- **category**: lookup\n- **expected_provenance_count**: 1\n- **expected_keywords**: k\n- **notes**: n\n"
        "### eval-2: dup-id\n- **question**: q2?\n- **category**: lookup\n- **expected_provenance_count**: 1\n- **expected_keywords**: k\n- **notes**: n\n",
    )
    assert research_eval.validate_eval_set(dup) is False
    missing_adv = write(
        tmp_path / "adv.md",
        "**Consumer**: x\n**Contract**: y\n**When to load**: z\n"
        + "\n".join(
            f"### eval-{i}: item-{i}\n- **question**: q?\n- **category**: lookup\n- **expected_provenance_count**: 1\n- **expected_keywords**: k\n- **notes**: n\n"
            for i in range(1, 21)
        )
        + "\n",
    )
    assert research_eval.validate_eval_set(missing_adv) is False


def test_eval_baseline_git_show_unresolved_ref(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(research_eval.shutil, "which", fake_claude_path)

    def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if argv[:4] == ["git", "-C", str(ROOT), "show"]:
            return subprocess.CompletedProcess(argv, 1, stdout="", stderr="fatal: bad revision")
        return subprocess.CompletedProcess(argv, 1, stdout="", stderr="missing")

    monkeypatch.setattr(research_eval.subprocess, "run", fake_run)
    assert research_eval.eval_research(plugin_root=ROOT, baseline_ref="v9.9.9", work_dir=tmp_path, id_filter="missing-id") == 2


def test_quiet_contract_stream_for_eval_research_smoke(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("LARCH_QUIET_DISABLE", None)
    env["IMPLEMENT_TMPDIR"] = str(tmp_path)
    env["PATH"] = str(tmp_path)
    env["CLAUDE_PLUGIN_ROOT"] = str(ROOT)
    got = subprocess.run(
        [sys.executable, str(CLI), "eval", "research", "--smoke-test"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert got.returncode == 0
    assert "smoke test PASS" in got.stdout
    quiet_logs = list(tmp_path.glob("larch-quiet-*.log"))
    assert quiet_logs
    log_text = quiet_logs[0].read_text(encoding="utf-8")
    assert "smoke test PASS" not in log_text
    assert "smoke test PASS" not in got.stderr


def test_quiet_contract_stream_for_eval_validator(tmp_path: Path) -> None:
    path = write(tmp_path / "ok.md", " ".join(["word"] * 31) + "\npython/research_eval.py:1\n")
    env = os.environ.copy()
    env.pop("LARCH_QUIET_DISABLE", None)
    env["IMPLEMENT_TMPDIR"] = str(tmp_path)
    got = subprocess.run(
        [sys.executable, str(CLI), "eval", "validate-research-output", "--min-words", "999", str(path)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert got.returncode == 2
    assert "body too thin" in got.stdout
    quiet_logs = list(tmp_path.glob("larch-quiet-*.log"))
    assert quiet_logs
    assert "body too thin" not in quiet_logs[0].read_text(encoding="utf-8")
    assert "body too thin" not in got.stderr


def _make_words(n: int) -> str:
    return " ".join(f"lorem{i}" for i in range(n))


@pytest.mark.parametrize(
    ("label", "body", "expected", "kwargs"),
    [
        ("https url", _make_words(250) + "\nSee https://example.com/doc for context.\n", 0, {}),
        ("makefile line", _make_words(250) + "\nSee Makefile:42 for the target.\n", 0, {}),
        ("extensionless path", _make_words(250) + "\nSee kernel/spin.lock for the lockfile.\n", 0, {}),
        ("empty fence non-provenance", _make_words(250) + "\n```\n```\n", 3, {}),
        ("spin.lock false positive", _make_words(250) + "\nIn concurrency theory the spin.lock primitive is the simplest of all locking abstractions.\n", 3, {}),
        ("raw.txt false positive", _make_words(250) + "\nConversion pipelines often store the raw.txt format unchanged through transit.\n", 3, {}),
        ("bare cargo.lock false positive", _make_words(250) + "\nRust projects ship a Cargo.lock that pins dependency versions.\n", 3, {}),
        ("invalid colon ref", _make_words(250) + "\nReference: file.md:garbage — bare colon followed by non-digits.\n", 3, {}),
        ("invalid slash ref", _make_words(250) + "\nReference: file.md/child — slash-suffix bypass attempt.\n", 3, {}),
        ("validation-mode uncited", _make_words(40) + "\n", 3, {"validation_mode": True}),
        ("validation-mode exonerate ballot", "FINDING_1: EXONERATE\n", 0, {"validation_mode": True}),
        ("header-only tsv", "schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix\n", 2, {"validation_mode": True}),
    ],
)
def test_validate_research_output_provenance_and_validation_matrix(
    tmp_path: Path, label: str, body: str, expected: int, kwargs: dict[str, object]
) -> None:
    _ = label
    path = write(tmp_path / "case.txt", body)
    assert research_eval.validate_research_output(path, **kwargs) == expected  # type: ignore[arg-type]
