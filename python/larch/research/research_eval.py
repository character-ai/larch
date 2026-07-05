"""Research output validator and /research eval harness."""
# ruff: noqa: PLR2004,S607,PERF401,FLY002,SIM102
# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportUnknownVariableType=false, reportReturnType=false, reportArgumentType=false

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from larch.core import logging_util
from larch.review import voting

ANTHROPIC_EVAL_SOURCE = "anthropic.com/engineering/built-multi-agent-research-system"
DEFAULT_ROOT = Path(__file__).resolve().parents[3]
EVAL_SET_REL = Path("skills/research/references/eval-set.md")
EVAL_BASELINE_REL = Path("skills/research/references/eval-baseline.json")

_ALLOWED_SEVERITIES = {"blocking", "important", "nit", "latent"}
_ALLOWED_FOCUS = {"code-quality", "risk-integration", "correctness", "architecture", "security"}
_STRUCTURED_HEADER = "schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix"


_FOCUS_SYNONYMS = {"completeness": "code-quality"}


def _canonical_focus(value: str) -> str:
    """Map a known focus_area synonym onto the allowed enum, else return as-is."""
    return _FOCUS_SYNONYMS.get(value, value)


def _canonical_schema_version(value: str) -> str | None:
    """Normalize a TSV column-1 value to the schema_version constant "1".

    Cursor reviewers sometimes fill column 1 with a per-row index (1, 2, 3, ...)
    instead of the literal schema_version constant. Treat any pure integer as
    schema v1 and normalize it to "1"; reject a non-integer column 1 (e.g. prose
    left by a row split on an embedded newline).
    """
    return "1" if value.isdigit() else None


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


def _line_json_no_issues(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("{"):
        return False
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        return False
    return isinstance(obj, dict) and obj.get("no_issues_found") is True


def _is_no_issues_sentinel_line(line: str) -> bool:
    return line.strip() == "NO_ISSUES_FOUND" or _line_json_no_issues(line)


def _no_issues_sentinel_indexes(lines: list[str]) -> list[int]:
    return [idx for idx, line in enumerate(lines) if _is_no_issues_sentinel_line(line)]


def _strict_whole_json_no_issues(text: str) -> bool:
    stripped = text.strip()
    if not stripped.startswith("{"):
        return False
    decoder = json.JSONDecoder()
    try:
        obj, end = decoder.raw_decode(stripped)
    except json.JSONDecodeError:
        return False
    if end != len(stripped):
        return False
    return isinstance(obj, dict) and obj.get("no_issues_found") is True


def _line_json_has_schema_version(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("{"):
        return False
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError:
        return False
    return isinstance(obj, dict) and "schema_version" in obj


def _write_structured( *,path: Path | None, text: str = "") -> None:
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
    focus = obj.get("focus_area")
    if isinstance(focus, str):
        focus = _canonical_focus(focus)
    record = {**obj, "severity": severity, "focus_area": focus}
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


_TSV_ROW_START_RE = re.compile(r"^\d+\t")


def _iter_tsv_logical_rows(text: str):
    """Yield assembled TSV data rows after the header, joining physical continuations."""
    seen_header = False
    buffer = ""
    for line in text.splitlines():
        if line.strip().startswith("```"):
            continue
        if not seen_header:
            if line == _STRUCTURED_HEADER:
                seen_header = True
            continue
        if not line.strip():
            continue
        if _TSV_ROW_START_RE.match(line):
            if buffer:
                yield buffer
            buffer = line
        elif buffer:
            buffer = f"{buffer} {line.strip()}"
        else:
            _diag("REJECT structured TSV row: continuation without row prefix")
            continue
    if buffer:
        yield buffer


def _location_field_valid(location: str) -> bool:
    return bool(_clean_tsv(location))


def _leading_typed_fields_valid(fields: list[str]) -> bool:
    """Return True when the five leading typed TSV columns individually validate.

    Used by the column-count salvage path: a row missing a tab delimiter is only
    recovered when schema_version/scope/severity/focus_area/location parse, so a
    genuinely malformed row is still rejected.
    """
    if len(fields) < 6:  # five typed columns plus at least one free-text column
        return False
    schema, scope, severity, focus, location = (_clean_tsv(field) for field in fields[:5])
    return (
        _canonical_schema_version(schema) is not None
        and scope in {"in_scope", "out_of_scope"}
        and severity.lower() in _ALLOWED_SEVERITIES
        and _canonical_focus(focus) in _ALLOWED_FOCUS
        and _location_field_valid(location)
    )


def _multispace_run_count(field: str) -> int:
    return len(re.findall(r" {2,}", field))


def _seven_field_pad_confident(fields: list[str]) -> bool:
    """Gate trailing empty suggested_fix padding on high-confidence layout."""
    if any(_multispace_run_count(field) for field in fields[5:7]):
        return False
    return _clean_tsv(fields[5]) or not _clean_tsv(fields[6])


def _space_resplit_confident( *,original: list[str], candidate: list[str]) -> bool:
    """Reject space-to-tab repair that fabricates columns from in-field prose."""
    if len(candidate) != 8 or len(original) >= 8 or len(original) < 6:
        return False

    deficit = 8 - len(original)
    if any(_multispace_run_count(field) for field in original[: min(5, len(original))]):
        return True

    if len(original) == 6:
        return _multispace_run_count(original[5]) == deficit

    for i in range(5, len(original) - 1):
        runs = _multispace_run_count(original[i])
        if runs:
            return runs == deficit == 1
    tail_runs = _multispace_run_count(original[6])
    return bool(tail_runs and tail_runs == deficit == 1)


def _salvage_structured_tsv_row( *,line: str, fields: list[str]) -> list[str] | None:
    """Recover an off-by-one-delimiter TSV row instead of dropping the whole slot.

    Two recoverable shapes (issue #5078), both content-valid but one tab short:
    a single trailing delimiter omitted (seven fields), or a tab replaced by a
    run of spaces. Recovery is gated on the leading typed columns validating so a
    truly malformed row still rejects. Space-to-tab re-split is tried before
    trailing-pad so merged free-text columns are not mis-attributed.
    """
    if len(fields) < 8:
        candidate = re.sub(r" {2,}", "\t", line).split("\t", 7)
        if (
            len(candidate) == 8
            and _leading_typed_fields_valid(candidate)
            and _space_resplit_confident(original=fields, candidate=candidate)
        ):
            return candidate
    if len(fields) == 7 and _leading_typed_fields_valid(fields):
        if _seven_field_pad_confident(fields):
            return [*fields, ""]
        _diag("REJECT structured TSV row: ambiguous seven-field salvage layout")
    return None


def _split_structured_tsv_row(line: str) -> list[str] | None:
    """Split one logical TSV row into eight fields or reject with _diag."""
    line = re.sub(r"[\r\n]+", " ", line)
    fields = line.split("\t", 7)
    if len(fields) >= 8:
        return fields
    salvaged = _salvage_structured_tsv_row(line=line, fields=fields)
    if salvaged is not None:
        return salvaged
    _diag(f"REJECT structured TSV row: expected 8 tab columns, got {len(fields)}")
    return None


def _validate_structured_tsv(text: str) -> str:
    out: list[str] = []
    seen_header = False
    for line in text.splitlines():
        if line == _STRUCTURED_HEADER:
            seen_header = True
            out.append(_STRUCTURED_HEADER)
            break
    if not seen_header:
        return ""
    rows_seen = 0
    for line in _iter_tsv_logical_rows(text):
        rows_seen += 1
        fields = _split_structured_tsv_row(line)
        if fields is None:
            continue
        schema, scope, severity, focus, location, what, scenario = [_clean_tsv(field) for field in fields[:7]]
        fix = _clean_tsv(fields[7])
        severity = severity.lower()
        canonical_schema = _canonical_schema_version(schema)
        focus = _canonical_focus(focus)
        if canonical_schema is None or scope not in {"in_scope", "out_of_scope"} or severity not in _ALLOWED_SEVERITIES or focus not in _ALLOWED_FOCUS:
            _diag(f"REJECT structured TSV row: schema={schema!r} scope={scope!r} severity={severity!r} focus={focus!r}")
            continue
        if not _location_field_valid(location):
            _diag(f"REJECT structured TSV row: invalid location={location!r}")
            continue
        out.append("\t".join([canonical_schema, scope, severity, focus, location, what, scenario, fix]))
    if len(out) <= 1:
        if rows_seen:
            _diag(f"REJECT structured TSV: {rows_seen} data row(s) seen but none validated after salvage")
        return ""
    return "\n".join(out) + "\n"


def validate_structured_reviewer_output(text: str, *, write_structured: Path | None = None) -> int:
    lines = _trimmed_nonblank(text)
    normalized = _validate_structured_jsonl(text) or _validate_structured_tsv(text)
    if normalized:
        _write_structured(path=write_structured, text=normalized)
        return 0
    sentinel_indexes = _no_issues_sentinel_indexes(lines)
    # Tier 1: strict whole-body no-issues sentinel (covers multi-line pretty-printed output).
    if len(sentinel_indexes) <= 1 and _strict_whole_json_no_issues("\n".join(lines)):
        _write_structured(path=write_structured, text="")
        return 0
    # Tier 2: per-line singleton no-issues sentinel; reject schema_version-polluted output.
    if not any(_line_json_has_schema_version(line) for line in lines) and len(sentinel_indexes) == 1:
        _write_structured(path=write_structured, text="")
        if sentinel_indexes[0] > 0:
            _emit("WARNING=NO_ISSUES_SENTINEL_RECOVERED_AFTER_PREAMBLE")
        return 0
    _write_structured(path=write_structured, text="")
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


def _validation_mode_reviewer_no_findings_prose(lines: list[str]) -> bool:
    """Accept the shipped reviewer template's exact prose no-findings shape."""
    if len(lines) not in {2, 4}:
        return False
    if lines[0] != "### In-Scope Findings" or lines[1] != "No in-scope issues found.":
        return False
    if len(lines) == 2:
        return True
    if lines[2] != "### Out-of-Scope Observations":
        return False
    return lines[3] == "No out-of-scope observations."


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
    try:
        text = input_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        _emit(f"file missing or not readable: {input_file}")
        return 4
    if structured_reviewer_mode:
        return validate_structured_reviewer_output(text, write_structured=write_structured)
    lines = _trimmed_nonblank(text)
    trimmed = "\n".join(lines)
    if validation_mode:
        if trimmed in {"CURSOR_EMPTY_RESPONSE", "CURSOR_DEGRADED_RESPONSE"}:
            _emit("STATUS=CURSOR_EMPTY_RESPONSE")
            _emit("FAILURE_REASON=Cursor returned an empty or degraded JSON .result field: likely transient backend issue. Fallback engaged.")
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
        if _validation_mode_reviewer_no_findings_prose(lines):
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
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in lines:
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
    try:
        raw_text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        _diag(f"eval-research: eval-set.md not found at {path}")
        return False
    first20 = "\n".join(raw_text.splitlines()[:20])
    ok = True
    for marker in ("Consumer", "Contract"):
        if marker not in first20:
            _diag(f"eval-research: eval-set.md missing first-20-lines header marker: {marker}")
            ok = False
    if "When-to-load" not in first20 and "When to load" not in first20:
        _diag("eval-research: eval-set.md missing first-20-lines header marker: When-to-load")
        ok = False
    if ANTHROPIC_EVAL_SOURCE not in raw_text:
        _diag(f"eval-research: eval-set.md missing Anthropic source literal: {ANTHROPIC_EVAL_SOURCE}")
        ok = False
    entries = parse_eval_set(path)
    adv_notes = [entry.notes for entry in entries if re.search(r"adversarial", entry.notes, flags=re.IGNORECASE)]
    if len(adv_notes) < 2:
        _diag("eval-research: eval-set.md missing required adversarial note shapes")
        ok = False
    else:
        has_fictitious = any(re.search(r"fictitious|fabricat|invent", note, flags=re.IGNORECASE) for note in adv_notes)
        has_data_absence = any(re.search(r"data[- ]absen|no data|don.t have data", note, flags=re.IGNORECASE) for note in adv_notes)
        if not has_fictitious or not has_data_absence:
            _diag("eval-research: eval-set.md missing required adversarial note shapes")
            ok = False
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
    except (OSError, json.JSONDecodeError):
        _diag("eval-research: eval-baseline.json missing required keys (version, entries) or not valid JSON")
        return False
    if not isinstance(data, dict) or data.get("version") != 2 or not isinstance(data.get("entries"), list):
        _diag("eval-research: eval-baseline.json missing required keys (version, entries) or not valid JSON")
        return False
    for entry in data["entries"]:
        if not isinstance(entry, dict):
            _diag("eval-research: eval-baseline.json entry is not an object")
            return False
        provenance = entry.get("provenance")
        if not isinstance(provenance, dict):
            _diag("eval-research: eval-baseline.json entry missing provenance object")
            return False
        for key in ("file_line", "repo_path", "url"):
            if key not in provenance:
                _diag(f"eval-research: eval-baseline.json entry provenance missing {key}")
                return False
        for key in ("id", "category", "keyword_coverage_pct", "length_lines", "judge_status", "wall_clock_seconds", "research_status"):
            if key not in entry:
                _diag(f"eval-research: eval-baseline.json entry missing {key}")
                return False
    return True


def _positive( *,value: str, flag: str) -> int:
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


def _score( *,path: Path, keywords: str) -> dict[str, int]:
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


JUDGE_RUBRIC = """You are a strict evaluator of /research outputs. Read the question, the research synthesis, and the expected_keywords list, then score the synthesis along five dimensions (each 0-20, total 0-100). Output MUST be exactly the format below: no preamble, no commentary, no markdown.

If the research synthesis claims something the evidence does not support, score factual_accuracy 0-5. If it admits "we don't have data" when the question targets data that does not exist, score factual_accuracy 16-20. Do not invent intermediate scores; if uncertain, score lower.

For citation_accuracy: count whether file/path citations are real (the file actually exists in the repo as cited) and whether URL citations are reputable (anthropic.com, openai.com, *.gov, *.edu, official docs > random Medium/blog posts).

For tool_efficiency: did the synthesis use minimal tool calls relative to the depth of the answer?

Output exactly these six lines:
JUDGE_SCORE_FACTUAL=<0-20>
JUDGE_SCORE_CITATION=<0-20>
JUDGE_SCORE_COMPLETENESS=<0-20>
JUDGE_SCORE_SOURCE_QUALITY=<0-20>
JUDGE_SCORE_TOOL_EFFICIENCY=<0-20>
JUDGE_SCORE_TOTAL=<0-100>

Then one line: JUDGE_RATIONALE=<single-line summary, no newlines>
"""


def run_judge(
    *,
    plugin_root: Path,
    out_dir: Path,
    question: str,
    research_file: Path,
    expected_keywords: str,
    judge_timeout: int,
) -> int:
    judge_prompt_file = out_dir / "judge-prompt.txt"
    judge_out_file = out_dir / "judge.txt"
    judge_err_file = out_dir / "judge.stderr"
    research_text = research_file.read_text(encoding="utf-8", errors="replace") if research_file.is_file() else ""
    judge_prompt_file.write_text(
        f"{JUDGE_RUBRIC}\n\nQUESTION: {question}\n\nEXPECTED_KEYWORDS: {expected_keywords}\n\nRESEARCH SYNTHESIS:\n---\n{research_text}\n---\n",
        encoding="utf-8",
    )
    judge_out_file.write_text("", encoding="utf-8")
    judge_err_file.write_text("", encoding="utf-8")
    return _run_with_timeout(
        ["claude", "-p", "--plugin-dir", str(plugin_root)],
        stdin_path=judge_prompt_file,
        stdout_path=judge_out_file,
        stderr_path=judge_err_file,
        timeout=judge_timeout,
        cwd=plugin_root,
    )


def parse_judge_output(judge_file: Path) -> dict[str, str]:
    if not judge_file.is_file() or judge_file.stat().st_size == 0:
        return {"JUDGE_STATUS": "parse_failed", "JUDGE_TOTAL": "null"}
    text = judge_file.read_text(encoding="utf-8", errors="replace")
    fields: dict[str, str | None] = {
        "total": _first_match(text=text, pattern=r"^JUDGE_SCORE_TOTAL=([0-9]+)", group=1),
        "factual": _first_match(text=text, pattern=r"^JUDGE_SCORE_FACTUAL=([0-9]+)", group=1),
        "citation": _first_match(text=text, pattern=r"^JUDGE_SCORE_CITATION=([0-9]+)", group=1),
        "completeness": _first_match(text=text, pattern=r"^JUDGE_SCORE_COMPLETENESS=([0-9]+)", group=1),
        "source_quality": _first_match(text=text, pattern=r"^JUDGE_SCORE_SOURCE_QUALITY=([0-9]+)", group=1),
        "tool_efficiency": _first_match(text=text, pattern=r"^JUDGE_SCORE_TOOL_EFFICIENCY=([0-9]+)", group=1),
    }
    if not all(fields.values()):
        return {"JUDGE_STATUS": "parse_failed", "JUDGE_TOTAL": "null"}
    total = fields["total"]
    if not re.fullmatch(r"100|[1-9]?[0-9]", total or ""):
        return {"JUDGE_STATUS": "parse_failed", "JUDGE_TOTAL": "null"}
    for key in ("factual", "citation", "completeness", "source_quality", "tool_efficiency"):
        if not re.fullmatch(r"20|1?[0-9]", fields[key] or ""):
            return {"JUDGE_STATUS": "parse_failed", "JUDGE_TOTAL": "null"}
    return {
        "JUDGE_STATUS": "ok",
        "JUDGE_FACTUAL": fields["factual"] or "",
        "JUDGE_CITATION": fields["citation"] or "",
        "JUDGE_COMPLETENESS": fields["completeness"] or "",
        "JUDGE_SOURCE_QUALITY": fields["source_quality"] or "",
        "JUDGE_TOOL_EFFICIENCY": fields["tool_efficiency"] or "",
        "JUDGE_TOTAL": total or "",
    }


def _first_match( *,text: str, pattern: str, group: int) -> str | None:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(group) if match else None


def classify_url_reputability(out_file: Path) -> str:
    if not out_file.is_file():
        return "URL_HIGH=0\nURL_LOW=0\nURL_UNKNOWN=0\n"
    text = out_file.read_text(encoding="utf-8", errors="replace")
    high = low = unknown = 0
    for url in sorted(set(re.findall(r"https?://[A-Za-z0-9._/?#&=%-]+", text))):
        lowered = url.lower()
        if any(token in lowered for token in ("anthropic.com", "openai.com", ".gov", ".edu", "deepmind.com", "microsoft.com/research", "arxiv.org", "nature.com")):
            high += 1
        elif any(token in lowered for token in ("medium.com", "dev.to", ".blog", "substack.com", "hashnode.dev")):
            low += 1
        else:
            unknown += 1
    return f"URL_HIGH={high}\nURL_LOW={low}\nURL_UNKNOWN={unknown}\n"


def _research_status_from_run( *,rc: int, stderr_path: Path) -> str:
    if rc == 0:
        return "ok"
    if rc == 124:
        return "timeout"
    if stderr_path.is_file():
        try:
            if "TIMED_OUT_AFTER=" in stderr_path.read_text(encoding="utf-8", errors="replace"):
                return "timeout"
        except OSError:
            pass
    return "research_failed"


def _baseline_row(
    *,
    entry: EvalEntry,
    score: dict[str, int],
    research_status: str,
    judge_kv: dict[str, str],
    wall: int,
) -> dict[str, object]:
    judge_total = judge_kv.get("JUDGE_TOTAL", "null")
    return {
        "id": entry.id,
        "category": entry.category,
        "provenance": {
            "file_line": score["prov_file_line"],
            "repo_path": score["prov_repo_path"],
            "url": score["prov_url"],
        },
        "keyword_coverage_pct": score["kw_pct"],
        "length_lines": score["length"],
        "judge_total": None if judge_total == "null" else int(judge_total),
        "judge_status": judge_kv.get("JUDGE_STATUS", "unknown"),
        "wall_clock_seconds": wall,
        "research_status": research_status,
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
    eval_set = plugin_root / EVAL_SET_REL
    baseline = plugin_root / EVAL_BASELINE_REL
    if not validate_eval_set(eval_set) or not validate_baseline_json(baseline):
        return 1
    if smoke_test:
        _emit("eval-research: smoke test PASS: eval-set.md + eval-baseline.json schema OK")
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
            _diag(f"eval-research: ERROR: --baseline ref {baseline_ref} could not be resolved via git show; aborting")
            return 2
        _emit(f"eval-research: baseline ref {baseline_ref} cached at {target}")
        _emit(f"eval-research: --baseline: PREVIEW MODE: baseline JSON pre-fetched to {target}; inline delta columns are not yet wired in this PR (a future amendment will add them).")
    entries = [entry for entry in parse_eval_set(eval_set) if not id_filter or entry.id == id_filter]
    if id_filter and not entries:
        _emit(f"eval-research: no entries matched (--id {id_filter}); nothing to do.")
        return 0
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
        research_status = _research_status_from_run(rc=rc, stderr_path=out_dir / "research.stderr")
        research_file = out_dir / "research.md"
        has_research = research_file.is_file() and research_file.stat().st_size > 0
        if research_status == "ok" or has_research:
            score = _score(path=research_file, keywords=entry.expected_keywords)
        else:
            score = {"prov_file_line": 0, "prov_repo_path": 0, "prov_url": 0, "kw_pct": 0, "length": 0}
        if entry.category == "external-comparison":
            (out_dir / "url-reputability.txt").write_text(classify_url_reputability(research_file), encoding="utf-8")
        if research_status == "ok" and has_research:
            judge_rc = run_judge(plugin_root=plugin_root, out_dir=out_dir, question=entry.question, research_file=research_file, expected_keywords=entry.expected_keywords, judge_timeout=judge_timeout)
            judge_kv = parse_judge_output(out_dir / "judge.txt") if judge_rc == 0 else {"JUDGE_STATUS": "judge_call_failed", "JUDGE_TOTAL": "null"}
        else:
            judge_kv = {"JUDGE_STATUS": "skipped_no_research", "JUDGE_TOTAL": "null"}
        row = _baseline_row(entry=entry, score=score, research_status=research_status, judge_kv=judge_kv, wall=elapsed)
        (out_dir / "row.json").write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")
        rows.append(row)
    if write_baseline:
        harness_commit = ""
        try:
            got = subprocess.run(["git", "-C", str(plugin_root), "rev-parse", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False)
            if got.returncode == 0:
                harness_commit = got.stdout.strip()
        except OSError:
            harness_commit = ""
        payload = {
            "version": 2,
            "harness_commit": harness_commit or None,
            "model_id": None,
            "generated_at": _dt.datetime.now(tz=_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "entries": rows,
        }
        write_baseline.parent.mkdir(parents=True, exist_ok=True)
        write_baseline.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        _emit(f"eval-research: baseline written to {write_baseline}")
        return 0
    _emit("| id | category | prov_fl | prov_path | prov_url | kw% | len | judge | wall(s) | status |")
    _emit("|---|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for row in rows:
        prov = row["provenance"]
        assert isinstance(prov, dict)
        judge_total = row.get("judge_total")
        judge_display = "?" if judge_total is None else str(judge_total)
        judge_status = row.get("judge_status", "unknown")
        _emit(
            f"| {row['id']} | {row['category']} | {prov['file_line']} | {prov['repo_path']} | {prov['url']} | "
            f"{row['keyword_coverage_pct']}% | {row['length_lines']} | {judge_display} | {row['wall_clock_seconds']} | "
            f"{row['research_status']}/{judge_status} |"
        )
    return 0


_EVAL_VALUE_FLAGS = ("--id", "--baseline", "--work-dir", "--write-baseline", "--timeout", "--judge-timeout")


def _eval_flag_missing_value( *,argv: list[str], flag: str) -> bool:
    for idx, token in enumerate(argv):
        if token == flag:
            return idx + 1 >= len(argv) or argv[idx + 1].startswith("--")
    return False


def eval_research_main(argv: list[str]) -> int:
    if any(arg in {"-h", "--help"} for arg in argv):
        print("Usage: eval research [--id ID] [--baseline REF] [--work-dir DIR] [--write-baseline FILE] [--timeout SEC] [--judge-timeout SEC] [--smoke-test]")
        return 0
    for flag in _EVAL_VALUE_FLAGS:
        if _eval_flag_missing_value(argv=argv, flag=flag):
            _diag(f"eval-research: {flag} requires a value")
            return 2
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
        timeout = _positive(value=ns.timeout, flag="--timeout")
        judge_timeout = _positive(value=ns.judge_timeout, flag="--judge-timeout")
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
