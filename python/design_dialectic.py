# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
"""Gate C dialectic clarifier helpers for /design.

The clarifier is deliberately fail-open. It binds optional drafter-declared
forks to the exact ``plan.txt`` bytes that produced them, runs a bounded
advisory debate only when Gate C can show it, and never rewrites the plan.
"""

from __future__ import annotations

import argparse
import contextlib
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Sequence



AUTO_CANDIDATES = "dialectic-clarifier-candidates.json"
MANUAL_CANDIDATES = "dialectic-manual-candidates.json"
RAW_PENDING = ".dialectic-raw-pending.json"
STATUS_FILE = "dialectic-clarifier-status.json"
DIGEST_FILE = "dialectic-clarifier-digest.md"
GENERATION_FILE = "dialectic-clarifier-generation.txt"
BALLOT_FILE = "dialectic-ballot.txt"
MANUAL_REQUEST = "dialectic-manual-request.txt"
COMPLETED_GATEC = ".completed/dialectic-gatec-terminal"
MAX_DECISIONS = 2
JUDGE_COUNT = 3
VOTE_THRESHOLD = 2


@dataclass(frozen=True)
class Option:
    key: str
    label: str


@dataclass(frozen=True)
class Candidate:
    id: str
    title: str
    option_a: str
    option_b: str
    tradeoff: str
    drafter_pick: str
    why_this_matters: str


@dataclass(frozen=True)
class CandidateSet:
    plan_fingerprint: str
    decisions: tuple[Candidate, ...]

    @property
    def ordered_ids(self) -> list[str]:
        return [decision.id for decision in self.decisions]


@dataclass(frozen=True)
class DebateOutput:
    decision_id: str
    option_key: str
    text: str
    ok: bool


@dataclass(frozen=True)
class JudgeVote:
    judge: int
    decision_id: str
    token: str


@dataclass(frozen=True)
class DigestRow:
    decision_id: str
    title: str
    option_a: str
    option_b: str
    option_a_steelman: str
    option_b_steelman: str
    drafter_pick: str
    panel_lean: str
    rationale: str
    disposition: str
    thesis_votes: int
    anti_thesis_votes: int


@dataclass(frozen=True)
class StatusSidecar:
    kind: str
    plan_fingerprint: str
    ordered_candidate_ids: tuple[str, ...]
    generation: int
    state: str


class DialecticShapeError(ValueError):
    """Raised for invalid external dialectic JSON/request shape."""


def _plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    return Path(env) if env else Path(__file__).resolve().parents[1]


def _validate_design_tmpdir(design_tmpdir: str | Path) -> Path:
    path = Path(design_tmpdir)
    if not path.is_dir() or path.is_symlink():
        raise DialecticShapeError("design tmpdir must be an existing non-symlink directory")
    return path.resolve()


def _atomic_write_text(*, path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        Path(tmp_name).replace(path)
    except Exception:
        with contextlib.suppress(FileNotFoundError):
            Path(tmp_name).unlink()
        raise


def _atomic_write_json(*, path: Path, payload: object) -> None:
    _atomic_write_text(path=path, text=json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _safe_unlink(path: Path) -> None:
    with contextlib.suppress(FileNotFoundError):
        path.unlink()


def plan_fingerprint(design_tmpdir: str | Path) -> str:
    design = _validate_design_tmpdir(design_tmpdir)
    plan = design / "plan.txt"
    if not plan.is_file():
        raise DialecticShapeError("plan.txt missing")
    return hashlib.sha256(plan.read_bytes()).hexdigest()


def _read_json_file(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _coerce_text(value: object, *, field: str) -> str:
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, dict):
        pieces: list[str] = []
        for key in ("label", "summary", "description", "text"):
            item = value.get(key)
            if isinstance(item, str) and item.strip():
                pieces.append(item.strip())
        text = ": ".join(pieces).strip()
    else:
        text = ""
    if not text:
        raise DialecticShapeError(f"{field} must be non-empty text")
    return text


def _slugify(*, value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or fallback


def _parse_candidate(item: object, *, index: int) -> Candidate:
    if not isinstance(item, dict):
        raise DialecticShapeError("each decision must be an object")
    title = _coerce_text(item.get("title"), field="title")
    option_a = _coerce_text(item.get("option_a"), field="option_a")
    option_b = _coerce_text(item.get("option_b"), field="option_b")
    if option_a == option_b:
        raise DialecticShapeError("option_a and option_b must differ")
    tradeoff = _coerce_text(item.get("tradeoff"), field="tradeoff")
    why = _coerce_text(item.get("why_this_matters"), field="why_this_matters")
    raw_pick = item.get("drafter_pick")
    if raw_pick not in {"option_a", "option_b"}:
        raise DialecticShapeError("drafter_pick must be option_a or option_b")
    raw_id = item.get("id")
    if isinstance(raw_id, str) and raw_id.strip():
        ident = _slugify(value=raw_id, fallback=f"decision-{index}")
    else:
        ident = _slugify(value=title, fallback=f"decision-{index}")
    return Candidate(
        id=ident,
        title=title,
        option_a=option_a,
        option_b=option_b,
        tradeoff=tradeoff,
        drafter_pick=str(raw_pick),
        why_this_matters=why,
    )


def normalize_candidates_payload(payload: object, *, fingerprint: str | None = None, require_fingerprint: bool = False) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise DialecticShapeError("candidate payload must be an object")
    fp = payload.get("plan_fingerprint")
    if require_fingerprint:
        if not isinstance(fp, str) or not fp.strip():
            raise DialecticShapeError("plan_fingerprint is required")
        if fingerprint is not None and fp != fingerprint:
            raise DialecticShapeError("plan_fingerprint does not match current plan")
        fingerprint = fp
    if fingerprint is None:
        fingerprint = fp if isinstance(fp, str) and fp else ""
    decisions_raw = payload.get("decisions")
    if not isinstance(decisions_raw, list):
        raise DialecticShapeError("decisions must be a list")
    decisions = [_parse_candidate(item, index=i + 1) for i, item in enumerate(decisions_raw[:MAX_DECISIONS])]
    if not decisions:
        raise DialecticShapeError("decisions must contain at least one decision")
    return {
        "plan_fingerprint": fingerprint,
        "decisions": [asdict(decision) for decision in decisions],
    }


def parse_candidate_set(path: Path, *, current_fingerprint: str | None = None) -> CandidateSet:
    payload = _read_json_file(path)
    normalized = normalize_candidates_payload(payload, fingerprint=current_fingerprint, require_fingerprint=True)
    decisions = tuple(Candidate(**item) for item in normalized["decisions"])  # type: ignore[arg-type]
    return CandidateSet(plan_fingerprint=str(normalized["plan_fingerprint"]), decisions=decisions)


def validate_candidates_content(content: str, *, current_fingerprint: str | None = None, require_fingerprint: bool = False) -> dict[str, object]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise DialecticShapeError(f"invalid JSON: {exc.msg}") from exc
    return normalize_candidates_payload(payload, fingerprint=current_fingerprint, require_fingerprint=require_fingerprint)


def candidates_fingerprint_valid(design_tmpdir: str | Path) -> bool:
    design = _validate_design_tmpdir(design_tmpdir)
    path = design / AUTO_CANDIDATES
    if not path.is_file():
        return False
    try:
        current = plan_fingerprint(design)
        parse_candidate_set(path, current_fingerprint=current)
    except (OSError, json.JSONDecodeError, DialecticShapeError):
        return False
    return True


def _skip_approve_requested(design: Path) -> bool:
    run_params = design / "run-params.json"
    if not run_params.is_file():
        return False
    try:
        payload = json.loads(run_params.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict) and payload.get("skip_approve_requested") is True


def read_generation(design_tmpdir: str | Path) -> int:
    design = _validate_design_tmpdir(design_tmpdir)
    path = design / GENERATION_FILE
    if not path.is_file():
        return 0
    try:
        return max(0, int(path.read_text(encoding="utf-8").strip() or "0"))
    except ValueError:
        return 0


def bump_generation(design_tmpdir: str | Path) -> int:
    design = _validate_design_tmpdir(design_tmpdir)
    value = read_generation(design) + 1
    _atomic_write_text(path=design / GENERATION_FILE, text=f"{value}\n")
    return value


def write_if_generation_matches(*, design_tmpdir: str | Path, generation: int, writer_fn: Callable[[], None]) -> bool:
    design = _validate_design_tmpdir(design_tmpdir)
    if read_generation(design) != generation:
        return False
    writer_fn()
    return True


def _status_from_file(path: Path) -> StatusSidecar | None:
    if not path.is_file():
        return None
    try:
        payload = _read_json_file(path)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    ids = payload.get("ordered_candidate_ids")
    if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
        return None
    try:
        generation = int(payload.get("generation", 0))
    except (TypeError, ValueError):
        generation = 0
    kind = payload.get("kind")
    fingerprint = payload.get("plan_fingerprint")
    state = payload.get("state", "")
    if not isinstance(kind, str) or not isinstance(fingerprint, str) or not isinstance(state, str):
        return None
    return StatusSidecar(kind=kind, plan_fingerprint=fingerprint, ordered_candidate_ids=tuple(ids), generation=generation, state=state)


def _cached_digest_valid(*, design: Path, candidates: CandidateSet, kind: str) -> bool:
    digest = design / DIGEST_FILE
    status = _status_from_file(design / STATUS_FILE)
    return bool(
        digest.is_file()
        and status is not None
        and status.kind == kind
        and status.plan_fingerprint == candidates.plan_fingerprint
        and list(status.ordered_candidate_ids) == candidates.ordered_ids
        and status.generation == read_generation(design)
        and status.state in {"complete", "fallback"}
    )


def _load_valid_candidates(design: Path, *, manual: bool = False) -> CandidateSet | None:
    path = design / (MANUAL_CANDIDATES if manual else AUTO_CANDIDATES)
    if not path.is_file():
        return None
    try:
        return parse_candidate_set(path, current_fingerprint=plan_fingerprint(design))
    except (OSError, json.JSONDecodeError, DialecticShapeError):
        return None


def should_defer_load_clarifier_reference(design_tmpdir: str | Path) -> bool:
    design = _validate_design_tmpdir(design_tmpdir)
    if _skip_approve_requested(design):
        return False
    auto = _load_valid_candidates(design)
    if auto is not None:
        return True
    manual = _load_valid_candidates(design, manual=True)
    return manual is not None and _cached_digest_valid(design=design, candidates=manual, kind="manual")


def _candidate_ids(candidates: CandidateSet) -> list[str]:
    return [candidate.id for candidate in candidates.decisions]


def _write_status(design: Path, *, kind: str, candidates: CandidateSet, generation: int, state: str, extra: dict[str, object] | None = None) -> None:  # noqa: PLR0913
    payload: dict[str, object] = {
        "kind": kind,
        "plan_fingerprint": candidates.plan_fingerprint,
        "ordered_candidate_ids": _candidate_ids(candidates),
        "generation": generation,
        "state": state,
    }
    if extra:
        payload.update(extra)
    _atomic_write_json(path=design / STATUS_FILE, payload=payload)


def _preserve_manual_status(design: Path) -> bool:
    manual = _load_valid_candidates(design, manual=True)
    return bool(manual is not None and _cached_digest_valid(design=design, candidates=manual, kind="manual"))


def clear_stale(design_tmpdir: str | Path, *, reason: str) -> int:
    del reason
    design = _validate_design_tmpdir(design_tmpdir)
    current = ""
    with contextlib.suppress(DialecticShapeError, OSError):
        current = plan_fingerprint(design)
    auto_valid = False
    if current and (design / AUTO_CANDIDATES).is_file():
        with contextlib.suppress(Exception):
            parse_candidate_set(design / AUTO_CANDIDATES, current_fingerprint=current)
            auto_valid = True
    if not auto_valid:
        _safe_unlink(design / AUTO_CANDIDATES)
        _safe_unlink(design / RAW_PENDING)
    manual_preserved = _preserve_manual_status(design) if current else False
    status = _status_from_file(design / STATUS_FILE)
    status_valid = bool(
        status is not None
        and current
        and status.plan_fingerprint == current
        and ((status.kind == "auto" and auto_valid) or (status.kind == "manual" and manual_preserved))
    )
    if not status_valid:
        _safe_unlink(design / STATUS_FILE)
        _safe_unlink(design / DIGEST_FILE)
    if not manual_preserved:
        _safe_unlink(design / MANUAL_CANDIDATES)
        _safe_unlink(design / MANUAL_REQUEST)
    return 0


def _promote_from_content(design: Path, *, content: str, output: Path) -> dict[str, object]:
    normalized = validate_candidates_content(content, current_fingerprint=plan_fingerprint(design), require_fingerprint=False)
    normalized["plan_fingerprint"] = plan_fingerprint(design)
    _atomic_write_json(path=output, payload=normalized)
    return normalized


def promote_candidates(design_tmpdir: str | Path, *, raw_dialectic_file: str | Path | None = None) -> int:
    design = _validate_design_tmpdir(design_tmpdir)
    raw = Path(raw_dialectic_file) if raw_dialectic_file else design / RAW_PENDING
    if not raw.is_file():
        print("DIALECTIC_CANDIDATES_WRITTEN=false")
        print("DIALECTIC_CANDIDATES_FAIL_REASON=absent")
        return 0
    try:
        _promote_from_content(design, content=raw.read_text(encoding="utf-8"), output=design / AUTO_CANDIDATES)
    except (OSError, DialecticShapeError) as exc:
        print("DIALECTIC_CANDIDATES_WRITTEN=false")
        print(f"DIALECTIC_CANDIDATES_FAIL_REASON={_kv_safe(str(exc))}")
        return 0
    _safe_unlink(raw)
    print("DIALECTIC_CANDIDATES_WRITTEN=true")
    return 0


def write_candidates(design_tmpdir: str | Path, *, content_file: str | Path) -> int:
    design = _validate_design_tmpdir(design_tmpdir)
    source = Path(content_file)
    if not source.is_file():
        print("DIALECTIC_CANDIDATES_WRITTEN=false")
        print("DIALECTIC_CANDIDATES_FAIL_REASON=content-file-missing")
        return 2
    try:
        _promote_from_content(design, content=source.read_text(encoding="utf-8"), output=design / AUTO_CANDIDATES)
    except (OSError, DialecticShapeError) as exc:
        print("DIALECTIC_CANDIDATES_WRITTEN=false")
        print(f"DIALECTIC_CANDIDATES_FAIL_REASON={_kv_safe(str(exc))}")
        return 2
    print("DIALECTIC_CANDIDATES_WRITTEN=true")
    return 0


def _kv_safe(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.:-]+", "-", value).strip("-")[:160] or "invalid"


def _touch_gatec(design: Path) -> None:
    path = design / COMPLETED_GATEC
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def _append_execution_issue(*, design: Path, message: str) -> None:
    path = design / "execution-issues.md"
    existing = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    prefix = "" if existing.endswith("\n") or not existing else "\n"
    _atomic_write_text(path=path, text=existing + prefix + f"- **Dialectic clarifier warning**: {message}\n")


def _budget_seconds() -> float:
    raw = os.environ.get("LARCH_DIALECTIC_BUDGET_SECONDS", "300")
    try:
        value = float(raw)
    except ValueError:
        value = 300.0
    return min(600.0, max(1.0, value))


def _escape_untrusted_line(line: str) -> str:
    cleaned = line.replace("```", "`\u200b``")
    if re.match(r"^(?:LARCH_[A-Z0-9_]*|[A-Z][A-Z0-9_]*=.*)$", cleaned):
        cleaned = "\\" + cleaned
    return "> " + cleaned


def _escape_untrusted(text: str) -> str:
    lines = text.splitlines() or [""]
    return "\n".join(_escape_untrusted_line(line) for line in lines)


_ATTRIBUTION_RE = re.compile(
    r"\b(?:Anthropic|Sonnet|Opus|Haiku|Cursor|Codex|Claude)\b",
    re.IGNORECASE,
)


def _strip_attribution(text: str) -> str:
    return _ATTRIBUTION_RE.sub("", text)


def _sanitize_display_field(text: str) -> str:
    cleaned = " ".join(text.splitlines()).strip()
    cleaned = cleaned.replace("```", "`\u200b``")
    if re.match(r"^(?:LARCH_[A-Z0-9_]*|[A-Z][A-Z0-9_]*=.*)$", cleaned):
        cleaned = "\\" + cleaned
    return cleaned


def _option_text(*, decision: Candidate, option_key: str) -> str:
    return decision.option_a if option_key == "option_a" else decision.option_b


def _other_option(option_key: str) -> str:
    return "option_b" if option_key == "option_a" else "option_a"


def _slot_prompt(*, role: str, decision: Candidate, option_key: str = "") -> str:
    if role == "debater":
        return (
            "You are a read-only /design dialectic clarifier debater. "
            "Return a compact steelman for the assigned option only. Do not use tools.\n\n"
            f"Decision: {decision.title}\n"
            f"Option A: {decision.option_a}\n"
            f"Option B: {decision.option_b}\n"
            f"Tradeoff: {decision.tradeoff}\n"
            f"Assigned option: {option_key} = {_option_text(decision=decision, option_key=option_key)}\n"
        )
    return ""


def _ballot_text(*, candidates: CandidateSet, steelmen: dict[tuple[str, str], str]) -> str:
    lines = ["You are a judge on a three-agent dialectic clarifier panel.", "Vote THESIS or ANTI_THESIS for each DECISION_N.", ""]
    for idx, decision in enumerate(candidates.decisions, 1):
        chosen = decision.drafter_pick
        alternative = _other_option(chosen)
        defense_a_role = "THESIS" if idx % 2 == 1 else "ANTI_THESIS"
        defense_b_role = "ANTI_THESIS" if defense_a_role == "THESIS" else "THESIS"
        role_to_key = {"THESIS": chosen, "ANTI_THESIS": alternative}
        lines.extend(
            [
                f"DECISION_{idx}: {decision.id}",
                f"Title: {decision.title}",
                f"THESIS means current-plan choice: {_option_text(decision=decision, option_key=chosen)}",
                f"ANTI_THESIS means alternative: {_option_text(decision=decision, option_key=alternative)}",
                f"Defense A ({defense_a_role}): {_strip_attribution(steelmen.get((decision.id, role_to_key[defense_a_role]), '(no defense)'))}",
                f"Defense B ({defense_b_role}): {_strip_attribution(steelmen.get((decision.id, role_to_key[defense_b_role]), '(no defense)'))}",
                "",
            ]
        )
    lines.append("Return one line per item: DECISION_N: THESIS|ANTI_THESIS - short reason")
    return "\n".join(lines) + "\n"


def _launcher_argv(*, design: Path, prompt: Path, output: Path, timeout: int, task_kind: str) -> list[str]:
    return [
        sys.executable,
        str(_plugin_root() / "python" / "cli.py"),
        "agent",
        "launch-claude-subprocess",
        "--prompt-file",
        str(prompt),
        "--output-file",
        str(output),
        "--timeout",
        str(timeout),
        "--timing-task-kind",
        task_kind,
        "--allow-root",
        str(design),
    ]


def _launch_claude_slot(argv: list[str]) -> subprocess.Popen[str]:
    return subprocess.Popen(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)


def _kill_process_group(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=2)


def _run_slot_batch(slots: list[tuple[str, Path, list[str]]], *, deadline: float) -> tuple[dict[str, str], bool]:
    launched: list[tuple[str, Path, subprocess.Popen[str]]] = []
    outputs: dict[str, str] = {}
    try:
        for name, output, argv in slots:
            try:
                launched.append((name, output, _launch_claude_slot(argv)))
            except OSError:
                return outputs, False
        for name, output, proc_obj in launched:
            remaining = max(0.01, deadline - time.monotonic())
            try:
                proc_obj.communicate(timeout=remaining)
            except subprocess.TimeoutExpired:
                return outputs, False
            if proc_obj.returncode == 0 and output.is_file():
                text = output.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    outputs[name] = text
        return outputs, True
    finally:
        for _, _, proc_obj in launched:
            _kill_process_group(proc_obj)


def _parse_judge_votes(text: str, *, judge: int, candidates: CandidateSet) -> list[JudgeVote]:
    seen: dict[tuple[int, str], str] = {}
    id_by_num = {str(idx): decision.id for idx, decision in enumerate(candidates.decisions, 1)}
    for line in text.splitlines():
        match = re.search(r"DECISION[_ -]?(\d+)\s*:?\s*(THESIS|ANTI_THESIS)\b", line, re.IGNORECASE)
        if not match:
            continue
        decision_id = id_by_num.get(match.group(1))
        if not decision_id:
            continue
        key = (judge, decision_id)
        token = match.group(2).upper()
        prior = seen.get(key)
        if prior is not None:
            if prior != token:
                del seen[key]
            continue
        seen[key] = token
    return [JudgeVote(judge=judge, decision_id=decision_id, token=token) for (judge, decision_id), token in seen.items()]


def _digest_from_rows(rows: list[DigestRow]) -> str:
    lines = [
        "## Dialectic Clarifier (advisory, untrusted)",
        "",
        "This digest is display-only. Approve final design keeps the current plan. Use Discuss further to change it.",
    ]
    for row in rows:
        lines.extend(
            [
                "",
                f"### Decision: {_sanitize_display_field(row.title)}",
                f"- **Candidate id**: `{_sanitize_display_field(row.decision_id)}`",
                f"- **Drafter pick**: {_sanitize_display_field(row.drafter_pick)}",
                f"- **Panel lean (advisory)**: {_sanitize_display_field(row.panel_lean)}",
                f"- **Disposition**: {_sanitize_display_field(row.disposition)}",
                f"- **Vote tally**: THESIS={row.thesis_votes} ANTI_THESIS={row.anti_thesis_votes}",
                "- **Option A steelman**:",
                _escape_untrusted(row.option_a_steelman),
                "- **Option B steelman**:",
                _escape_untrusted(row.option_b_steelman),
                "- **Panel rationale (advisory)**:",
                _escape_untrusted(row.rationale),
                "- **Operator note**: Approve keeps current plan; Discuss further to change it.",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _run_debate(design: Path, *, candidates: CandidateSet, kind: str, generation: int) -> tuple[str, bool, list[DigestRow]]:  # noqa: C901, PLR0912, PLR0915
    budget = _budget_seconds()
    deadline = time.monotonic() + budget
    prompt_dir = design / ".dialectic-prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    slots: list[tuple[str, Path, list[str]]] = []
    timeout = max(1, int(min(120, budget / 2)))
    for decision in candidates.decisions:
        for option_key in ("option_a", "option_b"):
            name = f"debater-{decision.id}-{option_key}"
            prompt = prompt_dir / f"{name}.txt"
            output = design / f"dialectic-{name}.txt"
            _atomic_write_text(path=prompt, text=_slot_prompt(role="debater", decision=decision, option_key=option_key))
            slots.append((name, output, _launcher_argv(design=design, prompt=prompt, output=output, timeout=timeout, task_kind="claude_dialectic")))
    debater_outputs, debaters_ok = _run_slot_batch(slots, deadline=deadline)
    if not debaters_ok:
        bump_generation(design)
        return "Dialectic clarifier exceeded its debater budget; continuing without blocking Gate C.", False, []
    steelmen: dict[tuple[str, str], str] = {}
    for decision in candidates.decisions:
        for option_key in ("option_a", "option_b"):
            text = debater_outputs.get(f"debater-{decision.id}-{option_key}") or f"No complete steelman was produced for {_option_text(decision=decision, option_key=option_key)}."
            steelmen[(decision.id, option_key)] = _strip_attribution(text)
    ballot = _ballot_text(candidates=candidates, steelmen=steelmen)
    _atomic_write_text(path=design / BALLOT_FILE, text=ballot)
    judge_slots: list[tuple[str, Path, list[str]]] = []
    for judge in range(1, JUDGE_COUNT + 1):
        name = f"judge-{judge}"
        prompt = prompt_dir / f"{name}.txt"
        output = design / f"dialectic-{name}.txt"
        _atomic_write_text(path=prompt, text=ballot)
        judge_slots.append((name, output, _launcher_argv(design=design, prompt=prompt, output=output, timeout=timeout, task_kind="claude_dialectic")))
    judge_outputs, judges_ok = _run_slot_batch(judge_slots, deadline=deadline)
    if not judges_ok:
        bump_generation(design)
        return "Dialectic clarifier exceeded its judge budget; continuing without blocking Gate C.", False, []
    votes: list[JudgeVote] = []
    for judge in range(1, JUDGE_COUNT + 1):
        votes.extend(_parse_judge_votes(judge_outputs.get(f"judge-{judge}", ""), judge=judge, candidates=candidates))
    rows: list[DigestRow] = []
    for decision in candidates.decisions:
        thesis_votes = sum(1 for vote in votes if vote.decision_id == decision.id and vote.token == "THESIS")
        anti_votes = sum(1 for vote in votes if vote.decision_id == decision.id and vote.token == "ANTI_THESIS")
        chosen = decision.drafter_pick
        alternative = _other_option(chosen)
        if thesis_votes + anti_votes == 0:
            lean_key = chosen
            disposition = "fallback-to-synthesis"
            rationale = "Judge output was malformed or absent, so the current plan remains the advisory fallback."
        elif anti_votes >= VOTE_THRESHOLD:
            lean_key = alternative
            disposition = "voted"
            rationale = "At least two judges preferred the alternative side."
        elif thesis_votes >= VOTE_THRESHOLD:
            lean_key = chosen
            disposition = "voted"
            rationale = "At least two judges preferred the current-plan side."
        else:
            lean_key = chosen
            disposition = "fallback-to-synthesis"
            rationale = "The judge panel did not reach a threshold, so the current plan remains the advisory fallback."
        rows.append(
            DigestRow(
                decision_id=decision.id,
                title=decision.title,
                option_a=decision.option_a,
                option_b=decision.option_b,
                option_a_steelman=steelmen.get((decision.id, "option_a"), ""),
                option_b_steelman=steelmen.get((decision.id, "option_b"), ""),
                drafter_pick=f"{chosen} ({_option_text(decision=decision, option_key=chosen)})",
                panel_lean=f"{lean_key} ({_option_text(decision=decision, option_key=lean_key)})",
                rationale=rationale,
                disposition=disposition,
                thesis_votes=thesis_votes,
                anti_thesis_votes=anti_votes,
            )
        )
    digest = _digest_from_rows(rows)

    def writer() -> None:
        _atomic_write_text(path=design / DIGEST_FILE, text=digest)
        _write_status(design, kind=kind, candidates=candidates, generation=generation, state="complete", extra={"rows": [asdict(row) for row in rows]})

    if not write_if_generation_matches(design_tmpdir=design, generation=generation, writer_fn=writer):
        return "Dialectic clarifier generation changed before digest write; stale output ignored.", False, []
    return digest, True, rows


def _infer_manual_drafter_pick(*, design: Path, title: str, option_a: str, option_b: str) -> str:
    auto = _load_valid_candidates(design)
    if auto is not None:
        slug = _slugify(value=title, fallback="manual-decision")
        for decision in auto.decisions:
            if decision.id == slug or decision.title.strip().lower() == title.strip().lower():
                return decision.drafter_pick
            if {decision.option_a, decision.option_b} == {option_a, option_b}:
                if decision.drafter_pick == "option_a":
                    return "option_a" if decision.option_a == option_a else "option_b"
                return "option_b" if decision.option_b == option_b else "option_a"
    plan_text = ""
    with contextlib.suppress(OSError):
        plan_text = (design / "plan.txt").read_text(encoding="utf-8", errors="replace")
    a_in = option_a in plan_text
    b_in = option_b in plan_text
    if b_in and not a_in:
        return "option_b"
    if a_in and not b_in:
        return "option_a"
    return "option_a"


def _run_gatec(design: Path, *, probe_only: bool = False) -> int:
    candidates = _load_valid_candidates(design)
    manual = _load_valid_candidates(design, manual=True)
    manual_cached = bool(manual is not None and _cached_digest_valid(design=design, candidates=manual, kind="manual"))
    auto_cached = bool(candidates is not None and _cached_digest_valid(design=design, candidates=candidates, kind="auto"))
    required = bool(candidates is not None and not _skip_approve_requested(design) and not auto_cached and not manual_cached)
    if probe_only:
        print(f"DIALECTIC_GATEC_DEBATE_REQUIRED={str(required).lower()}")
        return 0
    if candidates is None:
        clear_stale(design, reason="gatec-stale-check")
        return 0
    if manual_cached and manual is not None:
        print((design / DIGEST_FILE).read_text(encoding="utf-8", errors="replace"), end="")
        return 0
    if _skip_approve_requested(design):
        if auto_cached:
            print((design / DIGEST_FILE).read_text(encoding="utf-8", errors="replace"), end="")
        return 0
    if auto_cached:
        print((design / DIGEST_FILE).read_text(encoding="utf-8", errors="replace"), end="")
        return 0
    generation = bump_generation(design)
    _write_status(design, kind="auto", candidates=candidates, generation=generation, state="running")
    digest_or_warning, ok, _rows = _run_debate(design, candidates=candidates, kind="auto", generation=generation)
    if ok:
        print(digest_or_warning, end="")
    else:
        _append_execution_issue(design=design, message=digest_or_warning)
        print(f"**⚠ Dialectic clarifier skipped:** {digest_or_warning}")
    return 0


def gatec_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py design dialectic-gatec")
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--probe-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        design = _validate_design_tmpdir(args.design_tmpdir)
    except DialecticShapeError as exc:
        print(f"dialectic-gatec: {exc}", file=sys.stderr)
        return 2
    try:
        return _run_gatec(design, probe_only=args.probe_only)
    finally:
        with contextlib.suppress(Exception):
            _touch_gatec(design)


def _manual_shape_help() -> str:
    return "Use Other as `debate <decision>: <option A> vs <option B>` or `debate <candidate-id>` when current candidates are fingerprint-valid."


def _manual_candidates_from_request(*, design: Path, request: str) -> CandidateSet:
    current = plan_fingerprint(design)
    text = request.strip()
    id_match = re.fullmatch(r"(?is)debate(?:-this)?\s+([A-Za-z0-9_.:-]+)", text)
    if id_match:
        auto = _load_valid_candidates(design)
        if auto is None:
            raise DialecticShapeError(_manual_shape_help())
        ident = id_match.group(1)
        for decision in auto.decisions:
            if decision.id == ident:
                return CandidateSet(plan_fingerprint=current, decisions=(decision,))
        raise DialecticShapeError(_manual_shape_help())
    match = re.match(r"(?is)^debate(?:-this)?\s+(.+?)\s*:\s*(.+?)\s+vs\s+(.+?)\s*$", text)
    if not match:
        raise DialecticShapeError(_manual_shape_help())
    title = match.group(1).strip()
    option_a = match.group(2).strip()
    option_b = match.group(3).strip()
    drafter_pick = _infer_manual_drafter_pick(design=design, title=title, option_a=option_a, option_b=option_b)
    payload = {
        "plan_fingerprint": current,
        "decisions": [
            {
                "id": _slugify(value=title, fallback="manual-decision"),
                "title": title,
                "option_a": option_a,
                "option_b": option_b,
                "tradeoff": "Manual Gate C debate request.",
                "drafter_pick": drafter_pick,
                "why_this_matters": "The operator requested on-demand dialectic clarification at Gate C.",
            }
        ],
    }
    normalized = normalize_candidates_payload(payload, fingerprint=current, require_fingerprint=True)
    return CandidateSet(plan_fingerprint=current, decisions=tuple(Candidate(**item) for item in normalized["decisions"]))  # type: ignore[arg-type]


def manual_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py design dialectic-manual")
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--request-file", default="")
    parser.add_argument("--request", default="")
    args = parser.parse_args(argv)
    try:
        design = _validate_design_tmpdir(args.design_tmpdir)
    except DialecticShapeError as exc:
        print(f"dialectic-manual: {exc}", file=sys.stderr)
        return 2
    if args.request_file:
        request_path = Path(args.request_file)
        if not request_path.is_file():
            print(_manual_shape_help())
            return 0
        request = request_path.read_text(encoding="utf-8", errors="replace")
    else:
        request = args.request
    try:
        candidates = _manual_candidates_from_request(design=design, request=request)
    except DialecticShapeError as exc:
        print(str(exc))
        return 0
    _atomic_write_json(path=design / MANUAL_CANDIDATES, payload={"plan_fingerprint": candidates.plan_fingerprint, "decisions": [asdict(item) for item in candidates.decisions]})
    generation = bump_generation(design)
    _write_status(design, kind="manual", candidates=candidates, generation=generation, state="running")
    digest_or_warning, ok, _rows = _run_debate(design, candidates=candidates, kind="manual", generation=generation)
    if ok:
        print(digest_or_warning, end="")
    else:
        _append_execution_issue(design=design, message=digest_or_warning)
        print(f"**⚠ Dialectic clarifier skipped:** {digest_or_warning}")
    return 0


def validate_candidates_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py design dialectic-validate-candidates")
    parser.add_argument("--content-file", default="")
    parser.add_argument("--design-tmpdir", default="")
    parser.add_argument("--require-fingerprint", action="store_true")
    args = parser.parse_args(argv)
    content = Path(args.content_file).read_text(encoding="utf-8") if args.content_file else sys.stdin.read()
    current = plan_fingerprint(args.design_tmpdir) if args.design_tmpdir else None
    try:
        normalized = validate_candidates_content(content, current_fingerprint=current, require_fingerprint=args.require_fingerprint)
    except DialecticShapeError as exc:
        print(f"DIALECTIC_CANDIDATES_VALID=false\nDIALECTIC_CANDIDATES_FAIL_REASON={_kv_safe(str(exc))}")
        return 1
    print("DIALECTIC_CANDIDATES_VALID=true")
    print(json.dumps(normalized, separators=(",", ":")))
    return 0


def promote_candidates_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py design dialectic-promote-candidates")
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--raw-dialectic-file", default="")
    args = parser.parse_args(argv)
    return promote_candidates(args.design_tmpdir, raw_dialectic_file=args.raw_dialectic_file or None)


def write_candidates_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py design dialectic-write-candidates")
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--content-file", required=True)
    args = parser.parse_args(argv)
    return write_candidates(args.design_tmpdir, content_file=args.content_file)


def clear_stale_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py design dialectic-clear-stale")
    parser.add_argument("--design-tmpdir", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args(argv)
    try:
        return clear_stale(args.design_tmpdir, reason=args.reason)
    except DialecticShapeError as exc:
        print(f"dialectic-clear-stale: {exc}", file=sys.stderr)
        return 2


__all__ = [
    "Candidate",
    "CandidateSet",
    "DebateOutput",
    "DigestRow",
    "JudgeVote",
    "Option",
    "StatusSidecar",
    "bump_generation",
    "candidates_fingerprint_valid",
    "clear_stale",
    "plan_fingerprint",
    "read_generation",
    "should_defer_load_clarifier_reference",
    "validate_candidates_content",
    "write_if_generation_matches",
]
