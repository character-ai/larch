"""Research output validator and /research eval harness."""
# ruff: noqa: PLR2004,S607,PERF401,FLY002,SIM102
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportUnknownVariableType=false, reportReturnType=false, reportArgumentType=false

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import logging_util
import voting

ANTHROPIC_EVAL_SOURCE = "anthropic.com/engineering/built-multi-agent-research-system"
DEFAULT_ROOT = Path(__file__).resolve().parents[1]
EVAL_SET_REL = Path("skills/research/references/eval-set.md")
EVAL_BASELINE_REL = Path("skills/research/references/eval-baseline.json")

_ALLOWED_SEVERITIES = {"important", "nit", "latent"}
_ALLOWED_FOCUS = {"code-quality", "risk-integration", "correctness", "architecture", "security"}
_STRUCTURED_HEADER = "schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix"


def _emit(text: str) -> None:
    logging_util.emit(text)


def _diag(text: str) -> None:
    logging_util.diagnostic(text)


def _trimmed_nonblank(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _first_json_object(text: str) -> object | None:
    stripped = text.lstrip()
    if not stripped.startswith("{"):
        return None
    decoder = json.JSONDecoder()
    try:
        obj, _ = decoder.raw_decode(stripped)
    except json.JSONDecodeError:
        return None
    return obj


def _json_no_issues(text: str) -> bool:
    obj = _first_json_object(text)
    return isinstance(obj, dict) and obj.get("no_issues_found") is True


def _write_structured(path: Path | None, text: str = "") -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _normalize_json_record(obj: object) -> dict[str, object] | None:
    if not isinstance(obj, dict):
        return None
    severity = obj.get("severity")
    if isinstance(severity, str):
        severity = severity.lower()
    record = {**obj, "severity": severity}
    if record.get("schema_version") != 1:
        return None
    if record.get("scope") not in {"in_scope", "out_of_scope"}:
        return None
    if severity not in _ALLOWED_SEVERITIES:
        return None
    if record.get("focus_area") not in _ALLOWED_FOCUS:
        return None
    for key in ("location", "what", "scenario_or_breakage", "suggested_fix"):
        if not isinstance(record.get(key), str):
            return None
    return record


def _validate_structured_jsonl(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("```"):
            continue
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        record = _normalize_json_record(obj)
        if record is not None:
            lines.append(json.dumps(record, sort_keys=True, separators=(",", ":")))
    return "\n".join(lines) + ("\n" if lines else "")


def _clean_tsv(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\r", " ").replace("\n", " ")).strip()


def _validate_structured_tsv(text: str) -> str:
    out: list[str] = []
    seen_header = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            continue
        if not seen_header:
            if line == _STRUCTURED_HEADER:
                out.append(_STRUCTURED_HEADER)
                seen_header = True
            continue
        if not line.strip():
            continue
        fields = line.split("\t")
        if len(fields) < 8:
            continue
        schema, scope, severity, focus, location, what, scenario = [_clean_tsv(field) for field in fields[:7]]
        fix = _clean_tsv(" ".join(fields[7:]))
        severity = severity.lower()
        if schema != "1" or scope not in {"in_scope", "out_of_scope"} or severity not in _ALLOWED_SEVERITIES or focus not in _ALLOWED_FOCUS:
            continue
        out.append("\t".join([schema, scope, severity, focus, location, what, scenario, fix]))
    return "\n".join(out) + ("\n" if len(out) > 1 else "")


def validate_structured_reviewer_output(text: str, *, write_structured: Path | None = None) -> int:
    lines = _trimmed_nonblank(text)
    first = lines[0] if lines else ""
    if first == "NO_ISSUES_FOUND" or _json_no_issues("\n".join(lines)):
        _write_structured(write_structured, "")
        return 0
    normalized = _validate_structured_jsonl(text) or _validate_structured_tsv(text)
    if normalized:
        _write_structured(write_structured, normalized)
        return 0
    _write_structured(write_structured, "")
    _emit("structured records not found after repair")
    return 5


def _word_count_without_fences(text: str) -> int:
    in_fence = False
    words = 0
    for line in text.splitlines():
        if re.match(r"^[ \t]*```", line):
            in_fence = not in_fence
            continue
        if not in_fence:
            words += len(line.split())
    return words


def _has_code_fence_content(text: str) -> bool:
    in_fence = False
    for line in text.splitlines():
        if re.match(r"^[ \t]*```", line):
            in_fence = not in_fence
            continue
        if in_fence and line.strip():
            return True
    return False


def _has_provenance(text: str) -> bool:
    if re.search(voting.FILE_LINE_REGEXES["any-re"], text):
        return True
    if re.search(voting.FILE_LINE_REGEXES["extensionless-re"], text):
        return True
    if _has_code_fence_content(text):
        return True
    return "http://" in text or "https://" in text


def validate_research_output(
    input_file: Path,
    *,
    min_words: int | None = None,
    require_citations: bool = True,
    validation_mode: bool = False,
    structured_reviewer_mode: bool = False,
    write_structured: Path | None = None,
) -> int:
    if min_words is None:
        min_words = 30 if validation_mode else 200
    if not input_file.is_file():
        _emit(f"file missing or not readable: {input_file}")
        return 4
    text = input_file.read_text(encoding="utf-8", errors="replace")
    if structured_reviewer_mode:
        return validate_structured_reviewer_output(text, write_structured=write_structured)
    lines = _trimmed_nonblank(text)
    trimmed = "\n".join(lines)
    if validation_mode:
        if trimmed in {"CURSOR_EMPTY_RESPONSE", "CURSOR_DEGRADED_RESPONSE"}:
            _emit("STATUS=CURSOR_EMPTY_RESPONSE")
            _emit("FAILURE_REASON=Cursor returned an empty or degraded JSON .result field — likely transient backend issue. Fallback engaged.")
            return 5
        first = lines[0] if lines else ""
        last = lines[-1] if lines else ""
        if first == "NO_ISSUES_FOUND" or _json_no_issues(trimmed):
            return 0
        if last != first and (last == "NO_ISSUES_FOUND" or _json_no_issues(last)):
            return 0
        if re.search(r"^FINDING_[0-9]+:\s*(YES|NO|EXONERATE)", text, flags=re.MULTILINE):
            return 0
        if _validate_structured_tsv(text):
            return 0
    words = _word_count_without_fences(text)
    if words < min_words:
        _emit(f"body too thin: {words}/{min_words} words after stripping fenced code")
        return 2
    if require_citations and not _has_provenance(text):
        _emit("no provenance marker found")
        return 3
    return 0


def _print_validate_help() -> None:
    print("Usage: validate-research-output [--min-words N] [--require-citations|--no-require-citations] [--validation-mode] [--structured-reviewer-mode] [--write-structured <path>] <file>")


def validate_research_output_main(argv: list[str]) -> int:
    if any(arg in {"-h", "--help"} for arg in argv):
        _print_validate_help()
        return 0
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--min-words")
    parser.add_argument("--require-citations", action="store_true", default=None)
    parser.add_argument("--no-require-citations", action="store_true")
    parser.add_argument("--validation-mode", action="store_true")
    parser.add_argument("--structured-reviewer-mode", action="store_true")
    parser.add_argument("--write-structured")
    parser.add_argument("input", nargs="?")
    try:
        ns, extra = parser.parse_known_args(argv)
    except SystemExit:
        return 1
    if extra or not ns.input:
        _diag("validate-research-output: file argument is required")
        return 1
    try:
        min_words = int(ns.min_words) if ns.min_words is not None else None
    except ValueError:
        return 1
    logging_util.quiet_init(argv0="validate-research-output")
    require = True
    if ns.no_require_citations:
        require = False
    elif ns.require_citations is True:
        require = True
    return validate_research_output(
        Path(ns.input),
        min_words=min_words,
        require_citations=require,
        validation_mode=ns.validation_mode,
        structured_reviewer_mode=ns.structured_reviewer_mode,
        write_structured=Path(ns.write_structured) if ns.write_structured else None,
    )


@dataclass(frozen=True)
class EvalEntry:
    id: str
    category: str
    expected_provenance_count: int
    expected_keywords: str
    question: str
    notes: str


def parse_eval_set(path: Path) -> list[EvalEntry]:
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"^### eval-[0-9]+:\s*(.+)$", line)
        if match:
            if current is not None:
                entries.append(current)
            current = {"id": match.group(1).strip()}
            continue
        if current is None:
            continue
        field = re.match(r"^- \*\*(question|category|expected_provenance_count|expected_keywords|notes)\*\*:\s*(.*)$", line)
        if field:
            current[field.group(1)] = field.group(2)
    if current is not None:
        entries.append(current)
    out: list[EvalEntry] = []
    for raw in entries:
        out.append(
            EvalEntry(
                raw.get("id", ""),
                raw.get("category", ""),
                int(raw.get("expected_provenance_count", "-1")) if re.fullmatch(r"[0-9]+", raw.get("expected_provenance_count", "")) else -1,
                raw.get("expected_keywords", ""),
                raw.get("question", ""),
                raw.get("notes", ""),
            )
        )
    return out


def validate_eval_set(path: Path) -> bool:
    if not path.is_file():
        _diag(f"eval-research: eval-set.md not found at {path}")
        return False
    first20 = "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[:20])
    ok = True
    for marker in ("Consumer", "Contract"):
        if marker not in first20:
            _diag(f"eval-research: eval-set.md missing first-20-lines header marker: {marker}")
            ok = False
    if "When-to-load" not in first20 and "When to load" not in first20:
        _diag("eval-research: eval-set.md missing first-20-lines header marker: When-to-load")
        ok = False
    text = path.read_text(encoding="utf-8", errors="replace")
    if text.count("ADVERSARIAL") < 2 or "fictitious" not in text.lower() or "data" not in text.lower():
        _diag("eval-research: eval-set.md missing required adversarial note shapes")
        ok = False
    entries = parse_eval_set(path)
    if len(entries) < 20:
        _diag(f"eval-research: eval-set.md has {len(entries)} entries; need at least 20")
        ok = False
    seen: set[str] = set()
    cats: set[str] = set()
    for entry in entries:
        if not re.fullmatch(r"[a-z0-9-]+", entry.id):
            _diag(f"eval-research: entry has invalid id: {entry.id}")
            ok = False
        if entry.id in seen:
            _diag(f"eval-research: duplicate eval id: {entry.id}")
            ok = False
        seen.add(entry.id)
        if entry.category not in {"lookup", "architecture", "external-comparison", "risk-assessment", "feasibility"}:
            _diag(f"eval-research: entry {entry.id} has unknown category: {entry.category}")
            ok = False
        cats.add(entry.category)
        if entry.expected_provenance_count < 0 or not entry.question or not entry.expected_keywords or not entry.notes:
            _diag(f"eval-research: entry has missing field(s): id={entry.id} cat={entry.category}")
            ok = False
    for category in ("lookup", "architecture", "external-comparison", "risk-assessment", "feasibility"):
        if category not in cats:
            _diag(f"eval-research: eval-set.md missing entries from category: {category}")
            ok = False
    return ok


def validate_baseline_json(path: Path) -> bool:
    if not path.is_file():
        _diag(f"eval-research: eval-baseline.json not found at {path}")
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        _diag("eval-research: eval-baseline.json missing required keys (version, entries) or not valid JSON")
        return False
    if not isinstance(data, dict) or "version" not in data or not isinstance(data.get("entries"), list):
        _diag("eval-research: eval-baseline.json missing required keys (version, entries) or not valid JSON")
        return False
    return True


def _positive(value: str, flag: str) -> int:
    if not re.fullmatch(r"[0-9]+", value or "") or int(value) < 1:
        raise ValueError(f"eval-research: {flag} must be a positive integer (got: {value})")
    return int(value)


def build_research_prompt(question: str) -> str:
    return f"/larch:research --no-issue {question}\n"


def _run_with_timeout(argv: list[str], *, stdin_path: Path, stdout_path: Path, stderr_path: Path, timeout: int, cwd: Path) -> int:
    with stdin_path.open("rb") as stdin, stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        proc = subprocess.Popen(argv, stdin=stdin, stdout=stdout, stderr=stderr, cwd=str(cwd))  # pylint: disable=consider-using-with
        try:
            return proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            with stderr_path.open("a", encoding="utf-8") as handle:
                handle.write(f"TIMED_OUT_AFTER={timeout}\n")
            return 124


def _score(path: Path, keywords: str) -> dict[str, int]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    lowered = text.lower()
    kws = [kw.strip().lower() for kw in keywords.split(",") if kw.strip()]
    matched = sum(1 for kw in kws if kw in lowered)
    return {
        "prov_file_line": len(set(re.findall(r"[A-Za-z0-9_/.-]+:[0-9]+", text))),
        "prov_repo_path": len(set(re.findall(r"(?:scripts|skills|hooks|docs|tests|agents)/[A-Za-z0-9_/.-]+", text))),
        "prov_url": len(set(re.findall(r"https?://[A-Za-z0-9._/?#&=%-]+", text))),
        "kw_total": len(kws),
        "kw_matched": matched,
        "kw_pct": int(matched * 100 / len(kws)) if kws else 0,
        "length": len(text.splitlines()),
    }


def eval_research(
    *,
    plugin_root: Path = DEFAULT_ROOT,
    id_filter: str = "",
    baseline_ref: str = "",
    work_dir: Path | None = None,
    write_baseline: Path | None = None,
    timeout: int = 4200,
    judge_timeout: int = 600,
    smoke_test: bool = False,
) -> int:
    _ = judge_timeout
    eval_set = plugin_root / EVAL_SET_REL
    baseline = plugin_root / EVAL_BASELINE_REL
    if not validate_eval_set(eval_set) or not validate_baseline_json(baseline):
        return 1
    if smoke_test:
        _emit("eval-research: smoke test PASS — eval-set.md + eval-baseline.json schema OK")
        return 0
    if shutil.which("claude") is None:
        _diag("eval-research: required tool missing: claude")
        return 3
    if baseline_ref:
        if not re.fullmatch(r"[0-9A-Za-z_./-]+", baseline_ref):
            _diag(f"eval-research: --baseline ref must match ^[0-9A-Za-z._/-]+$ (got: {baseline_ref})")
            return 2
    work_dir = work_dir or Path(tempfile.mkdtemp(prefix="eval-research-"))
    work_dir.mkdir(parents=True, exist_ok=True)
    if baseline_ref:
        target = work_dir / "baseline-rows.json"
        with target.open("w", encoding="utf-8") as baseline_handle:
            got = subprocess.run(["git", "-C", str(plugin_root), "show", f"{baseline_ref}:skills/research/references/eval-baseline.json"], stdout=baseline_handle, stderr=subprocess.PIPE, text=True, check=False)
        if got.returncode != 0 or not validate_baseline_json(target):
            _diag(f"eval-research: ERROR — --baseline ref {baseline_ref} could not be resolved via git show; aborting")
            return 2
        _emit(f"eval-research: baseline ref {baseline_ref} cached at {target}")
        _emit(f"eval-research: --baseline: PREVIEW MODE — baseline JSON pre-fetched to {target}; inline delta columns are not yet wired in this PR (a future amendment will add them).")
    entries = [entry for entry in parse_eval_set(eval_set) if not id_filter or entry.id == id_filter]
    rows: list[dict[str, object]] = []
    _emit(f"eval-research: work dir = {work_dir}")
    for entry in entries:
        out_dir = work_dir / entry.id
        out_dir.mkdir(parents=True, exist_ok=True)
        prompt = build_research_prompt(entry.question)
        (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        start = time.time()
        rc = _run_with_timeout(["claude", "-p", "--plugin-dir", str(plugin_root)], stdin_path=out_dir / "prompt.txt", stdout_path=out_dir / "research.md", stderr_path=out_dir / "research.stderr", timeout=timeout, cwd=plugin_root)
        elapsed = int(time.time() - start)
        (out_dir / "timing.txt").write_text(f"WALL_CLOCK_SECONDS={elapsed}\nEXIT_CODE={rc}\n", encoding="utf-8")
        score = _score(out_dir / "research.md", entry.expected_keywords)
        row = {"id": entry.id, "category": entry.category, "status": "ok" if rc == 0 else f"exit-{rc}", **score}
        (out_dir / "row.json").write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")
        rows.append(row)
        # Keep judge layout stable even when no LLM judge is run by a stubbed environment.
        (out_dir / "judge-prompt.txt").write_text("Judge the research output against the rubric.\n", encoding="utf-8")
        (out_dir / "judge.txt").touch()
        (out_dir / "judge.stderr").touch()
        if entry.category == "external-comparison":
            (out_dir / "url-reputability.txt").touch()
    if write_baseline:
        write_baseline.parent.mkdir(parents=True, exist_ok=True)
        write_baseline.write_text(json.dumps({"version": 1, "entries": rows}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _emit(f"eval-research: baseline written to {write_baseline}")
        return 0
    _emit("| id | category | status | provenance | keywords | lines |")
    _emit("|---|---|---|---:|---:|---:|")
    for row in rows:
        _emit(f"| {row['id']} | {row['category']} | {row['status']} | {row['prov_file_line']} | {row['kw_pct']}% | {row['length']} |")
    return 0


def eval_research_main(argv: list[str]) -> int:
    if any(arg in {"-h", "--help"} for arg in argv):
        print("Usage: eval research [--id ID] [--baseline REF] [--work-dir DIR] [--write-baseline FILE] [--timeout SEC] [--judge-timeout SEC] [--smoke-test]")
        return 0
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--id", default="")
    parser.add_argument("--baseline", default="")
    parser.add_argument("--work-dir")
    parser.add_argument("--write-baseline")
    parser.add_argument("--timeout", default="4200")
    parser.add_argument("--judge-timeout", default="600")
    parser.add_argument("--smoke-test", action="store_true")
    try:
        ns, extra = parser.parse_known_args(argv)
    except SystemExit:
        return 2
    if extra:
        _diag(f"eval-research: unknown argument: {extra[0]}")
        return 2
    try:
        timeout = _positive(ns.timeout, "--timeout")
        judge_timeout = _positive(ns.judge_timeout, "--judge-timeout")
    except ValueError as exc:
        _diag(str(exc))
        return 2
    if ns.baseline and not re.fullmatch(r"[0-9A-Za-z_./-]+", ns.baseline):
        _diag(f"eval-research: --baseline ref must match ^[0-9A-Za-z._/-]+$ (got: {ns.baseline})")
        return 2
    if not ns.smoke_test and shutil.which("claude") is None:
        _diag("eval-research: required tool missing: claude")
        return 3
    logging_util.quiet_init(argv0="eval-research")
    root = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", str(DEFAULT_ROOT)))
    return eval_research(
        plugin_root=root,
        id_filter=ns.id,
        baseline_ref=ns.baseline,
        work_dir=Path(ns.work_dir) if ns.work_dir else None,
        write_baseline=Path(ns.write_baseline) if ns.write_baseline else None,
        timeout=timeout,
        judge_timeout=judge_timeout,
        smoke_test=ns.smoke_test,
    )
