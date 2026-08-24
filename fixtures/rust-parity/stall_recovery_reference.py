#!/usr/bin/env python3
"""Frozen Python reference for the issue-8064 through issue-8066 stall-recovery commands."""

from __future__ import annotations

import hashlib
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path


def options(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    index = 0
    while index < len(values):
        arg = values[index]
        if arg.startswith("--") and "=" in arg:
            key, value = arg.split("=", 1)
            parsed[key] = value
            index += 1
        elif arg.startswith("--") and index + 1 < len(values):
            parsed[arg] = values[index + 1]
            index += 2
        else:
            index += 1
    return parsed


def emit(key: str, valid: bool) -> int:
    print(f"{key}={'true' if valid else 'false'}")
    return 0 if valid else 1


def read_last(path: Path, key: str) -> str:
    if not path.is_file() or path.is_symlink():
        return ""
    prefix = f"{key}="
    found = ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            found = line[len(prefix) :].strip("\r")
    return found


def safe_step(value: str, generic: bool) -> bool:
    if generic and value in {"validator", "postplan", "publish", "clarify", "panel", "judge-panel", "step2b", "step3", "step5c"}:
        return True
    return bool(re.fullmatch(r"[2-9]|1[0-5]|(8|9|10|11|12|13|14|15)([a-z][0-9]?|-[a-z0-9]+(-[a-z0-9]+)*)?", value))


def token_valid(value: str, kind: str, generic: bool) -> bool:
    if not value or any(char in value for char in "\n\r {}()[]<>|&;`$"):
        return False
    if not kind:
        return True
    if kind == "outcome":
        return value in {"approved", "approved-partition", "failed-publish"}
    if kind == "step":
        return safe_step(value, generic)
    if kind == "phase":
        return value in {"ship-pr", "ci-initial"} or (generic and value == "publish")
    if kind == "site":
        return value == "ship-pr" or (generic and value == "gate-b")
    if kind == "trigger":
        return value == "main-agent-required" or (generic and value == "failed")
    if kind == "bail":
        return value == "review-required" or (generic and value == "operator-action")
    if kind == "source-script":
        return value == "ship-pr" or (generic and value == "split-path")
    if kind == "root-cause":
        return value in {"larch-defect", "environment", "operator-action"}
    return False


def rewrite(path: Path, updates: dict[str, str]) -> bool:
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            return False
        key, value = line.split("=", 1)
        rows[key] = value.rstrip("\r")
    rows.update(updates)
    path.write_text("".join(f"{key}={value}\n" for key, value in rows.items()), encoding="utf-8")
    return True


def clear(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--implement-tmpdir", os.environ.get("IMPLEMENT_TMPDIR", ".")))
    for name in ("stall-recovery-classification.env", "stall-recovery-issue.env"):
        try:
            (tmpdir / name).unlink()
        except OSError:
            pass
    paths = [tmpdir / name for name in ("ship-pr-state.sh", "finalize-state.sh", "session-env.sh")]
    for path in paths:
        if path.exists() and (path.is_symlink() or not path.is_file() or not rewrite(path, {})):
            print("CLEARED=false")
            return 3
    for path in paths:
        if path.is_file() and not rewrite(path, {
            "STALL_TRACKING": "false", "STALL_STEP": "", "BAIL_REASON": "",
            "IMPLEMENT_BAIL_REASON": "", "EXIT_CODE": "unknown",
        }):
            return emit("CLEARED", False)
    return emit("CLEARED", True)


def seed(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--implement-tmpdir", os.environ.get("IMPLEMENT_TMPDIR", ".")))
    state = tmpdir / "ship-pr-state.sh"
    if state.is_symlink():
        print("SEEDED=false")
        return 3
    if state.is_file() and any(line and not line.startswith("#") and "=" not in line for line in state.read_text(encoding="utf-8", errors="replace").splitlines()):
        print("SEEDED=false")
        return 3
    step = opts.get("--stall-step") or read_last(state, "STALL_STEP") or "8"
    phase = opts.get("--phase") or read_last(state, "PHASE") or "ci-initial"
    step = step if safe_step(step, True) else "unknown"
    phase = phase if phase in {"ci-initial", "publish", "ship-pr"} else "unknown"
    if state.is_file() and state.stat().st_size and any("=" in line for line in state.read_text(encoding="utf-8", errors="replace").splitlines()):
        rewrite(state, {"STALL_TRACKING": "true", "STALL_STEP": step, "PHASE": phase})
        mode = "rewrite"
    else:
        tmpdir.mkdir(parents=True, exist_ok=True)
        state.write_text(
            f"PHASE={phase}\nSTALL_TRACKING=true\nSTALL_STEP={step}\nBAIL_REASON=\nBAIL_FAILURE_DETAIL_LOG=\nEXIT_CODE=4\n",
            encoding="utf-8",
        )
        mode = "seed"
    print("SEEDED=true")
    print(f"SEED_MODE={mode}")
    return 0


def terminal(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--implement-tmpdir", "."))
    state = Path(opts.get("--primary-state-file", str(tmpdir / "design-failure-terminal-state.env")))
    if not state.is_absolute() or state.is_symlink() or not state.is_file():
        return emit("VALID", False)
    try:
        state.resolve().relative_to(tmpdir.resolve())
    except ValueError:
        return emit("VALID", False)
    rows: dict[str, str] = {}
    for raw in state.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            return emit("VALID", False)
        key, value = line.split("=", 1)
        if key in rows:
            return emit("VALID", False)
        rows[key] = value
    required = {"DESIGN_FAILURE_VERSION", "DESIGN_FAILURE_KIND", "FAILURE_OUTCOME", "STALL_STEP", "PHASE", "SITE", "TRIGGER", "BAIL_REASON", "EXIT_CODE", "FAILURE_DETAIL_LOG", "SOURCE_SCRIPT"}
    valid = required <= rows.keys() and all(rows[key] for key in required - {"FAILURE_DETAIL_LOG"})
    valid = valid and rows.get("DESIGN_FAILURE_VERSION") == "1" and rows.get("DESIGN_FAILURE_KIND") == "terminal"
    valid = valid and token_valid(rows.get("STALL_STEP", ""), "step", opts.get("--profile") == "generic")
    return emit("VALID", valid)


def public(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--tmpdir") or opts.get("--implement-tmpdir", "."))
    candidate = Path(opts.get("--public-file", ""))
    corpus = Path(opts.get("--sensitive-corpus-file", ""))
    prefix = opts.get("--artifact-prefix") or "stall-recovery"
    effective = tmpdir / f"{prefix}-sensitive-corpus.public.effective"
    if not candidate.is_absolute() or not candidate.is_file() or candidate.is_symlink() or not corpus.is_absolute() or not corpus.is_file() or corpus.is_symlink():
        return emit("PUBLIC_FILE_VALID", False)
    text = corpus.read_text(encoding="utf-8", errors="replace")
    effective.write_text(text, encoding="utf-8")
    body = candidate.read_text(encoding="utf-8", errors="replace")
    sensitive = any(token.strip() and token.strip() in body for token in text.splitlines())
    if sensitive:
        return emit("PUBLIC_FILE_VALID", False)
    effective.unlink()
    return emit("PUBLIC_FILE_VALID", True)


def dev_clone(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--implement-tmpdir", "."))
    forked = read_last(tmpdir / "ship-pr-state.sh", "FORKED_TARGET") or read_last(tmpdir / "session-env.sh", "FORKED_TARGET")
    root = Path(opts.get("--working-tree-root", ""))
    valid = forked.lower() not in {"1", "true", "yes", "on"} and (root / "skills/implement/SKILL.md").is_file()
    print(f"LARCH_DEV_CLONE={'true' if valid else 'false'}")
    return 0


_EVIDENCE_NAMES = (
    "ship-pr-state.sh", "finalize-state.sh", "session-env.sh", "source-env.sh",
    "execution-issues.md", "run-log-pointer.txt", "plan.txt", "feature-description.txt",
    "issue-body.txt", "composed-plan.md", "final-summary.md", "validate-plan-commands.log",
    "design-log-publish.failure.log", "design-plan-write.failure.log",
    "design-publish-tail.failure.log", "design-publish-tail.stdout.log",
    "design-publish-tail.stderr.log", "design-publish-rename.stderr.log",
    "design-publish-log.stderr.log",
)


def attempts_table(path: Path) -> str:
    count = read_last(path, "attempt_count")
    if not count.isdigit() or int(count) == 0:
        return "| Attempt | Class | Resume hint | Outcome | UTC |\n|---|---|---|---|---|\n| none | n/a | n/a | n/a | n/a |"
    rows = ["| Attempt | Class | Resume hint | Outcome | UTC |", "|---|---|---|---|---|"]
    for index in range(1, int(count) + 1):
        rows.append(
            f"| `{index}` | `{read_last(path, f'attempt.{index}.class') or 'unrecoverable'}` | "
            f"`{read_last(path, f'attempt.{index}.resume_hint') or 'none'}` | "
            f"`{read_last(path, f'attempt.{index}.outcome') or 'failed'}` | "
            f"`{read_last(path, f'attempt.{index}.utc') or 'unknown'}` |"
        )
    return "\n".join(rows)


def compose_issue_input(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--implement-tmpdir", os.environ.get("IMPLEMENT_TMPDIR", ".")))
    class_file = Path(opts.get("--classification-file", str(tmpdir / "stall-recovery-classification.env")))
    attempts = Path(opts.get("--attempts-file", str(tmpdir / "stall-recovery-attempts.env")))
    root = Path(opts.get("--root-cause-file", str(tmpdir / "stall-recovery-root-cause.md")))
    output = Path(opts.get("--output-file", str(tmpdir / "stall-recovery-issue-input.md")))
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR", ""))
    if not (project / "skills/implement/SKILL.md").is_file():
        print("stall-recovery: issue-input surface requires larch dev clone and non-forked target", file=sys.stderr)
        return 1
    kind = opts.get("--report-kind", "terminal-failure")
    failure_class = read_last(class_file, "FAILURE_CLASS") or "unrecoverable"
    step = read_last(class_file, "STALL_STEP") or "unknown"
    phase = read_last(class_file, "PHASE") or "unknown"
    bail = read_last(class_file, "BAIL_REASON") or "none"
    title = read_last(tmpdir / "stall-recovery-title.txt", "") or read_last(root, "summary")
    skill_label = "/implement"
    signature_seed = "\n".join((
        "larch-stall-report-dedup-v1", f"report_kind={kind}", f"failure_class={failure_class}",
        f"step={step}", f"phase={phase}", f"safe_bail_token={bail}",
    ))
    signature = hashlib.sha256(signature_seed.encode()).hexdigest()
    marker = f"<!-- larch-stall:signature={signature} -->"
    rendered_title = f"[BUG] {skill_label} terminal: {title} ({failure_class} at {step})"
    run_id = read_last(tmpdir / "session-env.sh", "LARCH_RUN_ID") or "unknown"
    branch = read_last(tmpdir / "session-env.sh", "BRANCH_NAME") or "unknown"
    root_text = root.read_text(encoding="utf-8", errors="replace")
    parts = [
        f"### {rendered_title}", marker, "", "## Report metadata", "",
        f"- **Report kind**: `{kind}`", f"- **Failure class**: `{failure_class}`",
        f"- **Step**: `{step}`", f"- **Bail reason**: `{bail}`",
        f"- **Run ID**: `{run_id}`", f"- **Branch**: `{branch}`", "- **PR URL**: `unknown`",
        f"- **Resume hint**: `{read_last(class_file, 'RESUME_HINT') or 'none'}`",
        f"\n## Root-cause finding\n\n{root_text}\n",
        f"\n## Attempts\n\n{attempts_table(attempts)}",
    ]
    body = "\n".join(part for part in parts if part) + "\n"
    output.write_text(body, encoding="utf-8")
    (tmpdir / "stall-recovery-tier-a-attempts.md").write_text(attempts_table(attempts) + "\n", encoding="utf-8")
    (tmpdir / "stall-recovery-tier-a-escalation.md").write_text("", encoding="utf-8")
    (tmpdir / "stall-recovery-tier-a-root-cause.md").write_text(root_text, encoding="utf-8")
    print(f"STALL_RECOVERY_REPORT_KIND={kind}")
    print("STALL_RECOVERY_REPORT_TIER=A")
    print(f"STALL_RECOVERY_REPORT_ARTIFACT={output}")
    print(f"STALL_RECOVERY_REPORT_VERDICT={read_last(root, 'verdict')}")
    print(f"REPORT_DEDUP_SIGNATURE={signature}")
    print("DRY_RUN_DECISION=true")
    print("STALL_RECOVERY_REPORT_STATUS=dry-run")
    return 0


def populate_corpus(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--implement-tmpdir", os.environ.get("IMPLEMENT_TMPDIR", ".")))
    corpus = Path(opts.get("--sensitive-corpus-file", str(tmpdir / "stall-recovery-sensitive-corpus.env")))
    sources = [
        corpus,
        Path(opts.get("--classification-file", str(tmpdir / "stall-recovery-classification.env"))),
        Path(opts.get("--attempts-file", str(tmpdir / "stall-recovery-attempts.env"))),
        Path(opts.get("--escalation-ledger-file", str(tmpdir / "stall-recovery-escalation-ledger.tsv"))),
        Path(opts.get("--escalation-fallback-file", str(tmpdir / "stall-recovery-escalation-fallback.tsv"))),
        Path(opts.get("--record-failure-marker", str(tmpdir / "stall-recovery-escalation-record-failure.env"))),
        *(tmpdir / name for name in _EVIDENCE_NAMES),
    ]
    lines: list[str] = []
    for source in sources:
        if source.is_file() and not source.is_symlink():
            text = source.read_text(encoding="utf-8", errors="replace")
            lines.extend(text.splitlines())
            lines.extend(re.findall(r"https?://[^\s`)\]]+", text))
            lines.extend(re.findall(r"git@github\.com:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text))
            lines.extend(re.findall(r"github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text))
            lines.extend(
                match.group(0).strip()
                for match in re.finditer(r"(?:^|[\s`(])/(?:Users|home|private|tmp|var|Volumes)/[^\s`)]+", text, re.MULTILINE)
            )
    corpus.write_text("\n".join(line.strip() for line in lines if line.strip()) + "\n", encoding="utf-8")
    print(f"SENSITIVE_CORPUS_FILE={corpus}")
    return 0


def chat_print(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--implement-tmpdir", os.environ.get("IMPLEMENT_TMPDIR", ".")))
    corpus = Path(opts.get("--sensitive-corpus-file", str(tmpdir / "stall-recovery-sensitive-corpus.env")))
    bounded = Path(opts.get("--bounded-root-cause-file", str(tmpdir / "stall-recovery-bounded-root-cause.md")))
    sensitive = {line.strip() for line in corpus.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()}
    if any(token in bounded.read_text(encoding="utf-8", errors="replace") for token in sensitive):
        print("stall-recovery: bounded root-cause contains sensitive token", file=sys.stderr)
        return 1
    return 2


def dedup(opts: dict[str, str]) -> int:
    _ = opts
    if os.environ.get("LARCH_STALL_RECOVERY_DRY_RUN"):
        print("STALL_RECOVERY_REPORT_STATUS=dry-run")
        return 0
    return 2


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def read_state(path: Path) -> dict[str, str]:
    if not path.is_file() or path.is_symlink():
        return {}
    found: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            found[key] = value.rstrip("\r")
    return found


_TERMINAL_MERGES = {"merged", "admin_merged", "already_merged"}
_STALE_FINALIZE_KEYS = {
    "STALL_TRACKING", "STALL_STEP", "PHASE", "BAIL_REASON",
    "IMPLEMENT_BAIL_REASON", "EXIT_CODE", "BAIL_NEEDS_USER_INPUT",
}


def state_value(ship: dict[str, str], fin: dict[str, str], key: str) -> str:
    return ship.get(key) or fin.get(key, "")


def nonzero_exit(value: str) -> bool:
    try:
        return bool(value.strip() and value.strip() != "unknown" and int(value) != 0)
    except ValueError:
        return False


def failure_signals(ship: dict[str, str], fin: dict[str, str], bail_user: str) -> bool:
    return bool(
        state_value(ship, fin, "BAIL_REASON").strip()
        or state_value(ship, fin, "IMPLEMENT_BAIL_REASON").strip()
        or nonzero_exit(state_value(ship, fin, "EXIT_CODE"))
        or truthy(bail_user)
    )


def clean_ship_recovery(ship: dict[str, str]) -> bool:
    number, url = ship.get("PR_NUMBER", "").strip(), ship.get("PR_URL", "").strip()
    merged = ship.get("MERGE_RESULT", "").strip()
    success = bool((number and number != "0") or (url and url != "N/A") or merged in _TERMINAL_MERGES)
    return bool(success and ship.get("PHASE", "").strip() != "stalled"
                and not ship.get("BAIL_REASON", "").strip()
                and not ship.get("IMPLEMENT_BAIL_REASON", "").strip()
                and not nonzero_exit(ship.get("EXIT_CODE", "")))


def effective_finalize(ship: dict[str, str], fin: dict[str, str]) -> dict[str, str]:
    contains_stall = bool(
        truthy(fin.get("STALL_TRACKING", "false")) or fin.get("STALL_STEP", "").strip()
        or fin.get("PHASE", "").strip() == "stalled" or fin.get("BAIL_REASON", "").strip()
        or fin.get("IMPLEMENT_BAIL_REASON", "").strip() or nonzero_exit(fin.get("EXIT_CODE", ""))
        or truthy(fin.get("BAIL_NEEDS_USER_INPUT", "false"))
    )
    if not (contains_stall and clean_ship_recovery(ship)):
        return fin
    result = dict(fin)
    result.update(dict.fromkeys(_STALE_FINALIZE_KEYS, ""))
    return result


def pr_evidence(ship: dict[str, str], fin: dict[str, str]) -> bool:
    number, url = state_value(ship, fin, "PR_NUMBER").strip(), state_value(ship, fin, "PR_URL").strip()
    return bool((number and number != "0") or (url and url != "N/A"))


def phase_stalled(ship: dict[str, str], fin: dict[str, str], any_stall: bool) -> bool:
    ship_phase, fin_phase = ship.get("PHASE", "").strip(), fin.get("PHASE", "").strip()
    return ship_phase == "stalled" or (fin_phase == "stalled" and (any_stall or ship_phase not in {"ci-initial", "rebase", "pr-create"}))


def healthy_pr(ship: dict[str, str], fin: dict[str, str]) -> bool:
    return bool(not state_value(ship, fin, "BAIL_REASON").strip()
                and not state_value(ship, fin, "IMPLEMENT_BAIL_REASON").strip()
                and state_value(ship, fin, "PHASE").strip() != "stalled"
                and not nonzero_exit(state_value(ship, fin, "EXIT_CODE")))


def safe_step_value(value: str) -> str:
    return value if safe_step(value, True) or value == "unknown" else "unknown"


def safe_phase_value(value: str) -> str:
    allowed = {"checks", "review", "implementation", "impl", "step2", "step5", "step8", "ship", "ship-pr", "pr-prep", "pr-create", "ci-initial", "ci-merge", "evaluate-failure", "force-push-gate", "bump", "merge", "postmerge", "rebase-failed", "plan-write", "publish", "postplan", "clarify-loop", "judge-panel", "validation", "teardown"}
    return value if value in allowed or value == "unknown" else "unknown"


def resume_hint(klass: str, step: str, phase: str, pattern: str) -> str:
    step = safe_step_value(step)
    if klass in {"contract-failure", "same-cause-repeat", "unrecoverable", "submodule-restricted"}:
        return "none"
    if step in {"3", "6", "12d", "bump-branch-guard"}:
        return "checks-commit-route-retry" if step == "3" and pattern in {"checks-leg-abandoned", "checks-child-sigterm"} else "none"
    if step == "2":
        return "step2-impl"
    if step == "5":
        return "checks-commit-route-retry" if pattern == "checks-leg-abandoned" else "step5-review"
    if step in {"8", "9", "10", "11", "12", "13", "14", "15", "rebase-failed"} or re.fullmatch(r"(8|9|10|11|12|13|14|15)([a-z][0-9]?|-[a-z0-9]+(-[a-z0-9]+)*)?", step or ""):
        return "step8-shippr"
    if step != "unknown":
        return "none"
    if phase.startswith("review"):
        return "step5-review"
    if phase.startswith(("impl", "step2")):
        return "step2-impl"
    return "none" if not phase else "step8-shippr"


def classify_text(text: str, bail: str, step: str, detail_valid: bool, exit_code: str, implement: bool) -> tuple[str, str, str]:
    first = bail.partition("\n")[0].lower()
    marker = "migration governance blocked:"
    if implement and marker in first and first.split(marker, 1)[1].strip():
        return "contract-failure", "none", "migration-governance-block"
    if step == "rebase-failed":
        return "transient-infra", "step8-shippr", "rebase-transient"
    if bail == "checks-child-failed" and step in {"3", "6"}:
        try:
            unresolved = exit_code == "unknown" or int(exit_code) < 0
        except ValueError:
            unresolved = True
        if unresolved:
            return "transient-infra", "checks-commit-route-retry", "checks-child-sigterm"
    if step in {"3", "6"}:
        return "contract-failure", "none", "step-contract"
    if step == "merge-loop-iteration-cap":
        return "unrecoverable", "none", "terminal-step"
    direct = {
        "protected-path-edit-required-out-of-scope": ("protected-path", "step2-impl", "protected-path-bail-token"),
        "submodule-edit-required-out-of-scope": ("submodule-restricted", "none", "submodule-restricted-bail-token"),
        "adopted-issue-closed": ("unrecoverable", "none", "terminal-bail"),
        "tracking-init-failed": ("unrecoverable", "none", "terminal-bail"),
        "recovery-out-of-scope": ("unrecoverable", "none", "recovery-out-of-scope"),
    }
    if bail in direct:
        return direct[bail]
    if bail == "ci-fix-exhausted":
        return "unrecoverable", "none", "ci-fix-exhausted-with-detail" if detail_valid else "terminal-bail"
    lower = f"{bail}\n{text}".lower()
    refresh = "pr-create-guideline-outcome-refresh"
    if step == refresh or "preterminal-outcome" in lower or f"stall_step={refresh}" in lower or (refresh in lower and any(token in lower for token in ("pre-terminal", "terminal outcome label", "preterminal"))):
        return "transient-infra", "step8-shippr", "transient-output"
    lint_bails = ("lint-fix-failed", "lint-fix-attempt-cap", "lint-fix-main-agent-required", "lint-fix-commit-failed", "resume-handoff-commit-failed", "review-fix-commit-failed")
    if any(token in lower for token in lint_bails):
        return "lint-failure", "step5-review", "lint-fix-bail-token"
    if "submodule-edit-required-out-of-scope" in lower:
        return "submodule-restricted", "none", "submodule-restricted-bail-token"
    if "protected-path-edit-required-out-of-scope" in lower:
        return "protected-path", "step2-impl", "protected-path-bail-token"
    if any(token in lower for token in ("pytest", "jest", "vitest", "rspec", "go test", "test failed", "failing test", "tests failed", "failed with")):
        return "test-failure", "step2-impl", "test-output"
    if re.search(r"relevant-checks.*fail|lint.*failed", lower) or any(token in lower for token in ("lint-fix", "shellcheck", "markdownlint", "pre-commit", "lint-fix-loop")):
        return "lint-failure", "step5-review", "lint-output"
    dispatch = {"branch-changed", "cap_hit", "codex-runtime-failure", "cursor-bailed-no-reason", "cursor-modified-history", "cursor-runtime-failure", "detached-head-prohibited", "dirty-state-after-timeout", "interactive-subprocess-unsupported", "main-branch-post-dispatch", "main-branch-prohibited", "manifest-missing", "manifest-oos-materialization-failed", "manifest-schema-invalid", "protected-path-modified", "qa-pending-missing", "quota", "redactor-not-executable", "resume-incompatible", "submodule-dirty", "wrapper-validation-failure", "orchestrator-envelope-invalid"}
    if bail in dispatch:
        return "dispatch-failure", "step2-impl", "dispatch-bail-token"
    if re.search(r"envelope-invalid|invalid.*envelope|orchestrator-envelope-invalid|wrapper-validation|step2.*dispatch", lower):
        return "dispatch-failure", "step2-impl", "dispatch-output"
    if re.search(r"rate limit|api rate|network/auth issue|network (error|failure|unavailable)|timed? out|timeout|connection (reset|refused)|temporary failure|tls handshake|dns failure|name resolution|github unavailable|github api unavailable|service unavailable|http 5\d\d", lower):
        return "transient-infra", "step8-shippr", "transient-output"
    return "unrecoverable", "none", "fallback"


def write_values(path: Path, values: dict[str, object]) -> None:
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")


def artifact_path(tmpdir: Path, default_name: str, prefix: str) -> Path:
    if not prefix or prefix == "stall-recovery":
        return tmpdir / default_name
    return tmpdir / f"{prefix}{default_name.removeprefix('stall-recovery')}"


def evidence_digest(evidence: str) -> str:
    return hashlib.sha256(evidence[:2048].encode()).hexdigest()[:16] if evidence else ""


def classification_signature(
    klass: str,
    hint: str,
    step: str,
    phase: str,
    bail: str,
    evidence: str,
    skill: str = "",
) -> str:
    prefix = f"profile=generic\nskill={skill}\n" if skill else ""
    return hashlib.sha256(
        f"{prefix}class={klass}\nhint={hint}\nstep={step}\nphase={phase}\nbail={bail}\nevidence={evidence_digest(evidence)}\n".encode()
    ).hexdigest()


def abandoned_checks_step(tmpdir: Path) -> str:
    root = Path(os.environ.get("LARCH_BGJOB_REGISTRY_ROOT", ""))
    run_id = read_state(tmpdir / "session-env.sh").get("LARCH_RUN_ID", "")
    if not root.is_dir() or not run_id:
        return ""
    for registry_step, stall_step in (
        ("implement-step3-checks", "3"),
        ("implement-checks-step5-self-review", "5"),
        ("implement-step5-self-review", "5"),
    ):
        entry = read_state(root / f"{run_id}-{registry_step}.env")
        if not entry:
            continue
        result = Path(entry.get("RESULT_ENV", ""))
        if not result.is_absolute():
            result = tmpdir / result
        if not result.is_file() or result.is_symlink():
            return stall_step
    return ""


def safe_generic_bail(value: str) -> bool:
    return value in {
        "failed-plan-write", "failed-publish", "failed-postplan", "failed-clarify",
        "failed-judge-panel", "failed-publish-tail", "clarify-hard-halt", "postplan-failed",
        "publish-failed", "publish-tail-failed", "plan-write-failed", "judge-panel-collapse",
        "decompose-panel-retry-exhausted", "validator-autofix-exhausted",
        "validator-autofix-failed", "validator-autofix-unavailable",
        "validator-autofix-skipped-cycle-cap", "operator-action", "panel-init-failed",
    }


def safe_generic_source(value: str) -> bool:
    return value in {
        "split-path", "design-publish", "design-step3-review", "design-step5c", "clarify-loop",
        "prompt-step", "validator", "postplan", "decompose-panel", "bash", "python",
        "codex", "cursor", "claude", "ship-pr", "lint-fix-loop", "run-step5-review",
    }


def classify_generic(opts: dict[str, str], tmpdir: Path) -> int:
    prefix = opts.get("--artifact-prefix", "")
    state_file = Path(opts.get("--primary-state-file", str(artifact_path(tmpdir, "stall-recovery-terminal-state.env", prefix))))
    found = read_state(state_file)
    step, phase = found.get("STALL_STEP", ""), found.get("PHASE", "")
    bail, exit_code = found.get("BAIL_REASON", ""), found.get("EXIT_CODE", "")
    source = found.get("SOURCE_SCRIPT", "")
    evidence = state_file.read_text(encoding="utf-8", errors="replace") if state_file.is_file() else ""
    current_publish = (
        found.get("TRIGGER") == "publish-tail-failed"
        and exit_code == "5"
        and bool(found.get("PUBLISH_ATTEMPT_ID"))
        and found.get("PUBLISH_RC_SOURCE") in {"returned", "exception"}
    )
    if current_publish and found.get("PLAN_WRITE_OK") == "true":
        klass, hint, pattern = "recoverable", "resume-post-plan-publish", "design-publish-tail-current-attempt"
    else:
        klass, _hint, pattern = classify_text(evidence, bail, step, False, exit_code, False)
        hint = "none"
    if prefix == "design-failure":
        skill = "/design"
    elif not prefix:
        skill = "/implement"
    else:
        skill = f"/{prefix.split('-', 1)[0]}"
    signature = classification_signature(klass, hint, step, phase, bail, evidence, skill)
    attempts = opts.get("--attempts-file", "")
    if attempts and klass not in {"contract-failure", "unrecoverable"} and read_last(Path(attempts), "attempt_count") != "0":
        if read_last(Path(attempts), f"attempt.{read_last(Path(attempts), 'attempt_count')}.signature") == signature:
            klass, pattern = "same-cause-repeat", "same-cause-repeat"
    values: dict[str, object] = {
        "FAILURE_CLASS": klass,
        "FAILURE_SIGNATURE": signature,
        "RESUME_HINT": hint,
        "STALL_STEP": safe_step_value(step),
        "PHASE": safe_phase_value(phase),
        "STALL_TRACKING": "true",
        "BAIL_REASON": bail if not bail or safe_generic_bail(bail) else "redacted",
        "BAIL_REASON_RAW": bail,
        "FAILURE_DETAIL_LOG": "",
        "EXIT_CODE": exit_code if re.fullmatch(r"[0-9]+|unknown", exit_code or "") else "unknown",
        "MATCHED_CLASSIFIER_PATTERN": pattern,
        "DISPATCHER": source if safe_generic_source(source) else ("unknown" if not source else "redacted"),
    }
    if current_publish:
        for key in (
            "LATEST_PHASE", "PUBLISH_RC_SOURCE", "PLAN_WRITE_OK", "PUBLISH_OK", "RENAMED",
            "LOG_PUBLISH_ATTEMPTED", "LOG_PUBLISH_COMPLETED", "PR_URL", "RECOVERY_BRANCH",
        ):
            if found.get(key):
                values[key] = found[key]
    path = artifact_path(tmpdir, "stall-recovery-classification.env", prefix)
    write_values(path, values)
    for key, value in values.items():
        print(f"{key}={value}")
    print(f"CLASSIFICATION_FILE={path}")
    return 0


def classify(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--implement-tmpdir", "."))
    if opts.get("--profile") == "generic":
        return classify_generic(opts, tmpdir)
    primary = Path(opts.get("--primary-state-file", str(tmpdir / "ship-pr-state.sh")))
    state = read_state(primary) | read_state(tmpdir / "finalize-state.sh") | read_state(tmpdir / "session-env.sh")
    step = opts.get("--stall-step") or state.get("STALL_STEP", "")
    phase = opts.get("--phase") or state.get("PHASE", "")
    bail = opts.get("--bail-reason") or state.get("BAIL_REASON", "") or state.get("IMPLEMENT_BAIL_REASON", "")
    any_stall = any(truthy(value) for value in (opts.get("--in-memory-stall-tracking", ""), read_state(primary).get("STALL_TRACKING", "false"), read_state(tmpdir / "finalize-state.sh").get("STALL_TRACKING", "false"), read_state(tmpdir / "session-env.sh").get("STALL_TRACKING", "false")))
    abandoned = "" if any_stall else abandoned_checks_step(tmpdir)
    if abandoned:
        any_stall = True
        step = step or abandoned
    evidence = ""
    for name in ("ship-pr-state.sh", "finalize-state.sh", "session-env.sh"):
        path = tmpdir / name
        evidence += "\n" + (path.read_text(encoding="utf-8", errors="replace") if path.is_file() and not path.is_symlink() and path.stat().st_size <= 65_536 else "")
    raw_exit = opts.get("--exit-code") or state.get("EXIT_CODE", "unknown")
    lower = f"{bail}\n{evidence}".lower()
    postmerge = any_stall and phase == "postmerge" and step == "postmerge-flush" and state.get("MERGE_RESULT", "").strip() in _TERMINAL_MERGES
    postmerge_failure = postmerge and any(token in lower for token in ("redaction-failed", "post-merge-refresh-failed", "manifest-recovery-failed", "commit-failed"))
    expected_postmerge = postmerge and "preterminal-outcome" in lower and not postmerge_failure
    if abandoned:
        klass, hint, pattern = "transient-infra", "checks-commit-route-retry", "checks-leg-abandoned"
    elif not any_stall:
        klass, hint, pattern = "unrecoverable", "none", "no-stall"
    elif postmerge_failure:
        klass, hint, pattern = "unrecoverable", "none", "postmerge-flush-failure"
    elif expected_postmerge:
        klass, hint, pattern = "operator-action", "none", "postmerge-flush-expected"
    else:
        klass, _hint, pattern = classify_text(evidence, bail, step, False, raw_exit, True)
        hint = resume_hint(klass, step, phase, pattern)
    signature = classification_signature(klass, hint, step, phase, bail, evidence)
    attempts = opts.get("--attempts-file", "")
    if not expected_postmerge and attempts and klass not in {"contract-failure", "unrecoverable"}:
        attempts_path = Path(attempts)
        count = read_last(attempts_path, "attempt_count")
        if count.isdigit() and count != "0" and read_last(attempts_path, f"attempt.{count}.signature") == signature:
            klass, pattern, hint = "same-cause-repeat", "same-cause-repeat", "none"
    safe_bails = {"protected-path-edit-required-out-of-scope", "submodule-edit-required-out-of-scope", "adopted-issue-closed", "tracking-init-failed", "recovery-out-of-scope", "ci-fix-exhausted", "manifest-missing"}
    dispatcher = opts.get("--dispatcher") or state.get("DISPATCHER", "") or state.get("CODER_TOOL", "")
    values: dict[str, object] = {
        "FAILURE_CLASS": klass,
        "FAILURE_SIGNATURE": signature,
        "RESUME_HINT": hint,
        "STALL_STEP": safe_step_value(step),
        "PHASE": safe_phase_value(phase),
        "STALL_TRACKING": "true" if any_stall else "false",
        "BAIL_REASON": bail if not bail or bail in safe_bails else "redacted",
        "BAIL_REASON_RAW": bail.splitlines()[0] if bail else "",
        "FAILURE_DETAIL_LOG": "",
        "EXIT_CODE": raw_exit if re.fullmatch(r"[0-9]+|unknown", raw_exit or "") else "unknown",
        "MATCHED_CLASSIFIER_PATTERN": pattern,
        "DISPATCHER": dispatcher if dispatcher in {"codex", "cursor", "claude", "bash", "python", "ship-pr", "lint-fix-loop", "run-step5-review"} else ("unknown" if not dispatcher else "redacted"),
    }
    path = tmpdir / "stall-recovery-classification.env"
    write_values(path, values)
    for key, value in values.items():
        print(f"{key}={value}")
    print(f"CLASSIFICATION_FILE={path}")
    return 0


def init_attempts(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--implement-tmpdir", "."))
    path = Path(opts.get("--attempts-file", str(tmpdir / "stall-recovery-attempts.env")))
    if not path.exists():
        write_values(path, {"version": 1, "created_utc": datetime.now(UTC).isoformat(), "attempt_count": 0})
    print(f"ATTEMPTS_FILE={path}")
    print(f"ATTEMPT_COUNT={read_last(path, 'attempt_count') or '0'}")
    return 0


def record_attempt(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--implement-tmpdir", "."))
    path = Path(opts.get("--attempts-file", str(tmpdir / "stall-recovery-attempts.env")))
    now = datetime.now(UTC).isoformat()
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
        count = int(read_last(path, "attempt_count") or "0") + 1
        replaced = any(line.startswith("attempt_count=") for line in lines)
        lines = [f"attempt_count={count}" if line.startswith("attempt_count=") else line for line in lines]
        if not replaced:
            lines.append(f"attempt_count={count}")
    else:
        count = 1
        lines = ["version=1", f"created_utc={now}", "attempt_count=1"]
    lines += [
        f"attempt.{count}.class={opts['--class']}", f"attempt.{count}.signature={opts['--signature']}",
        f"attempt.{count}.resume_hint={opts.get('--resume-hint', 'none')}", f"attempt.{count}.outcome={opts.get('--outcome', 'failed')}",
        f"attempt.{count}.utc={now}", f"last_class={opts['--class']}", f"last_signature={opts['--signature']}",
        f"last_resume_hint={opts.get('--resume-hint', 'none')}", f"last_outcome={opts.get('--outcome', 'failed')}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"ATTEMPT_COUNT={count}")
    return 0


def retry(opts: dict[str, str]) -> int:
    klass = opts["--class"]
    caps = {"transient-infra": (4, "sleep-seconds.sh 5"), "test-failure": (8, "none"), "lint-failure": (8, "none"), "dispatch-failure": (3, "none"), "protected-path": (1, "none"), "same-cause-repeat": (2, "none")}
    attempts, delay = caps.get(klass, (0, "none"))
    print(f"FAILURE_CLASS={klass}\nMAX_ATTEMPTS={attempts}\nRETRY_DELAY={delay}")
    return 0


def normalize_outcome(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--implement-tmpdir", "."))
    ship, raw_fin, ses = (read_state(tmpdir / name) for name in ("ship-pr-state.sh", "finalize-state.sh", "session-env.sh"))
    fin = effective_finalize(ship, raw_fin)
    seed = read_state(tmpdir / "ship-seed-input.env")
    classification = read_state(tmpdir / "stall-recovery-classification.env")
    memory = opts.get("--in-memory-stall-tracking", "") or "false"
    ship_stall = ship.get("STALL_TRACKING", "false")
    raw_fin_stall, fin_stall = raw_fin.get("STALL_TRACKING", "false"), fin.get("STALL_TRACKING", "false")
    ses_stall = ses.get("STALL_TRACKING", "false")
    any_stall = any(truthy(value) for value in (memory, ship_stall, fin_stall, ses_stall))
    merge_result, merge = state_value(ship, fin, "MERGE_RESULT"), state_value(ship, fin, "MERGE")
    pr_number, draft = state_value(ship, fin, "PR_NUMBER"), state_value(ship, fin, "DRAFT") or "false"
    forked = ship.get("FORKED_TARGET") or fin.get("FORKED_TARGET") or ses.get("FORKED_TARGET", "false") or "false"
    ci_passed = state_value(ship, fin, "CI_PASSED") or "false"
    design_done = fin.get("DESIGN_ONLY_DONE", "false") or "false"
    bail_user = state_value(ship, fin, "BAIL_NEEDS_USER_INPUT") or "false"
    terminal_merge = merge_result in _TERMINAL_MERGES
    has_failure = failure_signals(ship, fin, bail_user)
    stall_terminal = (terminal_merge and truthy(memory)) or has_failure or ship.get("PHASE", "").strip() == "stalled" or truthy(fin.get("STALL_TRACKING", "false"))
    if (any_stall or phase_stalled(ship, fin, any_stall)) and stall_terminal:
        outcome = "stalled"
    elif terminal_merge and has_failure:
        outcome = "bailed"
    elif merge_result in {"merged", "admin_merged"}:
        outcome = "merged"
    elif merge_result == "already_merged":
        outcome = "force-merged-externally"
    elif truthy(forked):
        outcome = "forked-dry-run"
    elif truthy(design_done):
        outcome = "design-only"
    elif pr_evidence(ship, fin) and not merge_result and healthy_pr(ship, fin) and not truthy(bail_user):
        outcome = "pr-created-draft" if truthy(draft) else "pr-created"
    elif not pr_evidence(ship, fin) and not merge_result and not has_failure:
        outcome = "shipping"
    else:
        outcome = "bailed"
    if truthy(bail_user) and outcome == "bailed":
        outcome = "bailed-needs-user-input"
    succeeded = outcome in {"merged", "force-merged-externally", "pr-created", "pr-created-draft", "forked-dry-run"} and not any_stall
    merge_downgraded = bool(outcome == "pr-created" and truthy(seed.get("MERGE", "false"))
                            and not truthy(merge) and classification.get("STALL_STEP") == "5"
                            and classification.get("RESUME_HINT") == "step8-shippr"
                            and "panel-failed" in (tmpdir / "execution-issues.md").read_text(encoding="utf-8", errors="replace").lower()
                            if (tmpdir / "execution-issues.md").is_file() else False)
    values = {
        "IMPLEMENT_NORMALIZED_OUTCOME": outcome, "IMPLEMENT_OUTCOME_SUCCEEDED": "true" if succeeded else "false",
        "IMPLEMENT_MERGE_DOWNGRADED": "true" if merge_downgraded else "false", "IMPLEMENT_ANY_STALL_TRACKING": "true" if any_stall else "false",
        "IMPLEMENT_MEMORY_STALL_TRACKING": memory, "IMPLEMENT_SHIP_STALL_TRACKING": ship_stall or "false",
        "IMPLEMENT_FINALIZE_STALL_TRACKING": raw_fin_stall or "false", "IMPLEMENT_SESSION_STALL_TRACKING": ses_stall or "false",
        "IMPLEMENT_MERGE_RESULT": merge_result, "IMPLEMENT_PR_NUMBER": pr_number, "IMPLEMENT_DRAFT": draft, "IMPLEMENT_MERGE": merge,
        "IMPLEMENT_FORKED_TARGET": forked, "IMPLEMENT_CI_PASSED": ci_passed,
        "IMPLEMENT_DESIGN_ONLY_DONE": design_done, "IMPLEMENT_BAIL_NEEDS_USER_INPUT": bail_user,
    }
    for key, value in values.items():
        print(f"{key}={value}")
    return 0


def normalize_issue(opts: dict[str, str]) -> int:
    tmpdir = Path(opts.get("--implement-tmpdir", "."))
    text = Path(opts["--issue-stdout-file"]).read_text(encoding="utf-8", errors="replace")
    values = read_state(Path(opts["--issue-stdout-file"]))
    reason = ""
    if opts.get("--issue-exit-code") is None:
        reason = "issue-exit-code-missing"
    elif opts["--issue-exit-code"] != "0":
        reason = "issue-exit-code"
    elif values.get("ISSUES_FAILED") != "0":
        reason = "issues-failed-invalid" if not values.get("ISSUES_FAILED", "").isdigit() else "issues-failed-nonzero"
    number, url = values.get("ISSUE_1_NUMBER", ""), values.get("ISSUE_1_URL", "")
    duplicate_url = values.get("ISSUE_1_DUPLICATE_OF_URL") or values.get("ISSUE_DUPLICATE_OF_URL", "")
    if (truthy(values.get("ISSUE_1_DUPLICATE", "")) or not number) and re.fullmatch(r"https://github.com/[^/#]+/[^/#]+/issues/\d+", duplicate_url):
        url, number = duplicate_url, duplicate_url.rsplit("/", 1)[1]
    if not reason and not number.isdigit():
        reason = "issue-number-missing"
    if not reason and not re.fullmatch(r"https://github.com/[^/#]+/[^/#]+/issues/\d+", url):
        reason = "issue-url-missing"
    env = tmpdir / "stall-recovery-issue.env"
    if reason:
        env.unlink(missing_ok=True)
        print(f"NORMALIZED=false\nREASON={reason}")
    else:
        write_values(env, {"ISSUE_NUMBER": number, "ISSUE_URL": url})
        print(f"NORMALIZED=true\nISSUE_NUMBER={number}\nISSUE_URL={url}")
    _ = text
    return 0


def normalize_file_report(opts: dict[str, str]) -> int:
    values = read_state(Path(opts["--file-failure-report-env"]))
    status, url = values.get("FILE_FAILURE_REPORT_STATUS", ""), values.get("FILE_FAILURE_REPORT_URL", "")
    reason = values.get("FILE_FAILURE_REPORT_FALLBACK_REASON", "")
    allowed = {"filed", "dry-run", "dedup-comment", "no-match", "fallback-print-required", "lookup-failed-open", "mutation-refused"}
    if status not in allowed:
        status, reason = "fallback-print-required", reason or "helper-status-missing"
    elif status == "mutation-refused":
        status, reason = "fallback-print-required", reason or "unauthorized-mutation"
    print(f"STALL_RECOVERY_REPORT_STATUS={status}")
    if url:
        print(f"STALL_RECOVERY_REPORT_URL={url}")
        match = re.fullmatch(r"https://github.com/[^/#]+/[^/#]+/issues/(\d+)", url)
        if match:
            print(f"STALL_RECOVERY_REPORT_ISSUE_URL={url}\nSTALL_RECOVERY_REPORT_ISSUE_NUMBER={match.group(1)}")
    if reason:
        print(f"STALL_RECOVERY_REPORT_FALLBACK_REASON={reason}")
    return 0


def record_escalation(opts: dict[str, str]) -> int:
    tmpdir = Path(opts["--implement-tmpdir"])
    exit_code = opts.get("--exit-code", "unknown")
    exit_code = exit_code if re.fullmatch(r"[0-9]+|unknown", exit_code) else "unknown"
    dispatcher = opts["--dispatcher"] if opts["--dispatcher"] in {"codex", "cursor", "claude", "bash", "python", "ship-pr", "lint-fix-loop", "run-step5-review"} else "redacted"
    row = f"utc={datetime.now(UTC).isoformat()}\tsite={opts['--site']}\ttrigger={opts['--trigger']}\tstep={opts['--step']}\tphase={opts['--phase']}\tdispatcher={dispatcher}\texit_code={exit_code}\tfailure_detail_log=\n"
    ledger = tmpdir / "stall-recovery-escalation-ledger.tsv"
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(row)
    print(f"ESCALATION_RECORDED=true\nESCALATION_LEDGER_FILE={ledger}")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        return 2
    verb = sys.argv[1]
    opts = options(sys.argv[2:])
    if verb == "classify-text":
        klass, hint, pattern = classify_text(
            opts.get("--text", ""), opts.get("--bail", ""), opts.get("--step", ""),
            opts.get("--detail-valid") == "true", opts.get("--exit-code", ""),
            opts.get("--implement") == "true",
        )
        print(f"FAILURE_CLASS={klass}\nCLASSIFIED_HINT={hint}\nPATTERN={pattern}")
        return 0
    if verb == "classify-text-table":
        header = ("name", "text", "bail", "step", "detail_valid", "exit_code", "implement")
        cases = Path(opts.get("--cases", ""))
        if not cases.is_file() or cases.is_symlink():
            return 2
        rows = cases.read_text(encoding="utf-8").splitlines()
        if not rows or tuple(rows[0].split("\t")) != header:
            return 2
        for row in rows[1:]:
            columns = row.split("\t")
            if len(columns) != len(header) or columns[4] not in {"true", "false"} or columns[6] not in {"true", "false"}:
                return 2
            name, text, bail, step, detail, exit_code, implement = columns
            klass, hint, pattern = classify_text(
                text, bail, step, detail == "true", exit_code, implement == "true",
            )
            print(f"{name}\t{klass}\t{hint}\t{pattern}")
        return 0
    if verb == "validate-token":
        token = opts.get("--token") or opts.get("--value", "")
        return emit("TOKEN_VALID", token_valid(token, opts.get("--token-kind", ""), opts.get("--profile") == "generic"))
    if verb == "validate-terminal-state":
        return terminal(opts)
    if verb == "validate-tier-b-public-file":
        return public(opts)
    if verb == "clear-stall":
        return clear(opts)
    if verb == "seed-terminal-state":
        return seed(opts)
    if verb == "is-larch-dev-clone":
        return dev_clone(opts)
    if verb == "compose-report":
        return compose_issue_input(opts)
    if verb == "populate-sensitive-corpus":
        return populate_corpus(opts)
    if verb == "chat-print":
        return chat_print(opts)
    if verb == "dedup-tier-a-report":
        return dedup(opts)
    if verb == "classify":
        return classify(opts)
    if verb == "init-attempts":
        return init_attempts(opts)
    if verb == "record-attempt":
        return record_attempt(opts)
    if verb == "retry-policy":
        return retry(opts)
    if verb == "normalize-outcome":
        return normalize_outcome(opts)
    if verb == "normalize-issue-env":
        return normalize_issue(opts)
    if verb == "normalize-file-failure-report-env":
        return normalize_file_report(opts)
    if verb == "record-escalation":
        return record_escalation(opts)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
