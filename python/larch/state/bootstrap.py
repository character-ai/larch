# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false
"""/implement Step 0 bootstrap and routing-envelope helpers."""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from larch.calibration.difficulty import resolve_step2_effective_difficulty
from larch.state import session_env
from larch.core import config, external_defaults, proc, rust_runtime
from larch import io as larch_io
from larch.core import logging_util, redact
from larch.core.repo_roots import larch_entrypoint
from larch.calibration import difficulty
from larch.design import plan_grammar, plan_quality
from larch.git import gh, git, pr, pr_body
from larch.report import run_log_batch, run_logs
from larch.agents import agents

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PS = shutil.which("ps") or "/bin/ps"
BOOTSTRAP_CONTRACT_FAILURE = 2
ROUTING_KEYS: tuple[str, ...] = (
    "IMPLEMENT_TMPDIR",
    "IMPLEMENT_BAIL_REASON",
    "STALL_TRACKING",
    "PLAN_FILE",
    "coder",
    "coder_fallback",
    "REPO_UNAVAILABLE",
    "DEFERRED",
    "ISSUE_NUMBER",
    "REPO",
    "REPO_ROOT",
    "CODEX_BINARY_FOUND",
    "CURSOR_BINARY_FOUND",
    "codex_available",
    "cursor_available",
    "RUN_ID",
    "BRANCH_NAME",
    "BRANCH_ACTION",
    "SELF_REVIEW_REQUESTED",
    "SELF_IMPLEMENT_REQUESTED",
    "DESIGN_DIFFICULTY",
    "DEGRADED",
    "BOTH_DOWN",
    "CODEX_STATE",
    "CURSOR_STATE",
    "DEGRADED_PROMPT_REQUIRED",
    "DEGRADED_HARD_FAIL",
    "BOOTSTRAP_NEXT",
    "ROUTE",
    "CHECKPOINT_NEXT",
    "REBASE_RC",
    "REBASE_OUTCOME",
    "CONFLICT_FILES",
    "REBASE_ERROR",
    "SKIPPED_ALREADY_PUSHED",
    "SKIPPED_ALREADY_FRESH",
)
_KEY_RE = re.compile(r"^[A-Za-z0-9_]+$")
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class BootstrapExit(Exception):
    def __init__(self, code: int) -> None:
        self.code = code


def _emit_kv(*, key: str, value: str) -> None:
    logging_util.emit_kv(key=key, value=value.replace("\n", " ").replace("\r", " "))


def _err(message: str) -> None:
    print(message, file=sys.stderr)


def _resolve_repo_root() -> str:
    """Resolve the operator repo root once at the bootstrap trust boundary (#6880)."""
    return (os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
            or os.environ.get("REPO_ROOT", "").strip()
            or str(Path.cwd()))


def _valid_run_id(value: str) -> bool:
    return bool(value) and _RUN_ID_RE.fullmatch(value) is not None


def _valid_issue(value: str) -> bool:
    return bool(value) and value.isdigit()


def _checkpoint_status(lines: list[str]) -> str:
    for line in lines:
        if line.startswith("STATUS="):
            return line.removeprefix("STATUS=")
    return "unknown"


def _dirty_tree_checkpoint() -> list[str]:
    """Read the Rust-owned checkpoint envelope at the bootstrap boundary."""
    return list(rust_runtime.dirty_tree_checkpoint(proc).lines)


def _atomic_text(*, path: Path, text: str) -> None:
    larch_io.atomic_write(path=path, text=text, temp_name=f"{path.name}.tmp.{os.getpid()}")




def _read_simple_kv(*, path: Path, key: str) -> str:
    return larch_io.read_kv(path=path, key=key, first_match=True, cr_strip="suffix", reject_symlink=True, on_error_default=True)


def _bool_text(*, value: str, default: str = "false") -> str:
    if value in {"true", "false"}:
        return value
    return default


def _merge_write_ship_seed_input(*, tmpdir: str, values: dict[str, str], only_missing: bool) -> None:
    if not tmpdir:
        return
    path = Path(tmpdir) / "ship-seed-input.env"
    existing: dict[str, str] = {}
    if path.is_file() and not path.is_symlink():
        try:
            existing = larch_io.parse_kv(path.read_text(encoding="utf-8", errors="replace"), skip_comments=True, cr_strip="rstrip")
        except OSError:
            existing = {}
    data = dict(existing)
    for key, value in values.items():
        if only_missing and data.get(key):
            continue
        data[key] = value
    ordered = ("MERGE", "DRAFT", "FORKED_TARGET", "NO_ADMIN_FALLBACK", "NO_LOGS_COMMIT", "DIFFICULTY_OVERRIDE", "DEFERRED", "MANIFEST_PATH", "TOOL_LABEL")
    text = "".join(f"{key}={data.get(key, '')}\n" for key in ordered if key in data)
    _atomic_text(path=path, text=text)


def _read_key(*, path: Path, key: str, default: str = "") -> str:
    try:
        text = larch_io.read_text(path, errors="replace", reject_cr=True)
        value = larch_io.kv_value(text=text, key=key, default=default, duplicate_policy="first")
        return default if value == "" else value
    except (OSError, ValueError):
        return default


def _single_line(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\r", " ").replace("\n", " ")).strip()


@dataclass(frozen=True)
class BootstrapOptions:
    up_to_phase: str
    caller_env: str = ""
    issue_number: str = ""
    forked_target: str = "false"
    merge_requested: str = "false"
    draft_requested: str = "false"
    no_admin_fallback: str = "false"
    no_logs_commit: str = "false"
    force_requested: str = "false"
    self_review_requested: str = "false"
    self_implement_requested: str = "false"
    difficulty_override: str = ""
    upstream_repo: str = ""
    run_id: str = ""
    preflight_tmpdir: str = ""
    coder_opt: str = ""
    resume_plan_tail: bool = False
    skip_codex_probe: bool = False
    skip_cursor_probe: bool = False
    non_interactive: str = ""


# Mutable state: fields (coder / branch_name / repo / run_id / deferred / ...) are set as bootstrap phases run.
@dataclass
class BootstrapState:
    opts: BootstrapOptions
    current_branch: str = ""
    is_main: str = ""
    is_user_branch: str = ""
    user_prefix: str = ""
    entry_gate: str = ""
    skip_branch_check: str = ""
    implement_tmpdir: str = field(default_factory=lambda: os.environ.get("IMPLEMENT_TMPDIR", ""))
    session_id: str = ""
    repo: str = ""
    repo_unavailable: str = "false"
    codex_present: str = ""
    cursor_present: str = ""
    claude_binary_found: str = ""
    codex_binary_found: str = ""
    cursor_binary_found: str = ""
    codex_available: str = ""
    cursor_available: str = ""
    issue_number_resolved: str = ""
    run_id: str = ""
    branch_selected: str = ""
    deferred: str = "false"
    stall_tracking: str = "false"
    branch_name: str = ""
    branch_action: str = ""
    plan_file: str = ""
    coder: str = ""
    coder_fallback: str = ""
    implement_bail_reason: str = ""

    def emit_step_failed(self, value: str) -> None:
        _emit_kv(key="STEP_FAILED", value=value)
        raise BootstrapExit(2)

    def emit_tmp_step_failed(self, value: str) -> None:
        _emit_kv(key="IMPLEMENT_TMPDIR", value=self.implement_tmpdir)
        self.emit_step_failed(value)

    def session_env(self) -> Path:
        return Path(self.implement_tmpdir) / "session-env.sh"

    def read_session(self, *, key: str, default: str = "") -> str:
        if self.session_env().is_file():
            return _read_key(path=self.session_env(), key=key, default=default)
        return default

    def resolve_run_id(self) -> str:
        for candidate in (self.opts.run_id, self.run_id):
            if _valid_run_id(candidate):
                return candidate
        sid = Path(self.implement_tmpdir) / "session-id"
        if sid.is_file():
            value = sid.read_text(encoding="utf-8", errors="replace").strip()
            if _valid_run_id(value):
                return value
        if _valid_run_id(self.session_id):
            return self.session_id
        return ""


def _write_base_session_env(st: BootstrapState) -> None:
    prior_claude_source = st.read_session(key="LARCH_CLAUDE_SOURCE_FILE")
    prior_auto_mode = st.read_session(key="LARCH_AUTO_MODE")
    prior_dynamic_archetypes = st.read_session(key="LARCH_DYNAMIC_ARCHETYPES_MAX")
    claude_source = prior_claude_source
    claude_source_path = Path(st.implement_tmpdir) / "claude-source.env"
    if not claude_source and claude_source_path.is_file():
        claude_source = str(claude_source_path)
    base = session_env.WriteEnvParams(
        output=str(st.session_env()),
        repo=st.repo,
        repo_root=_resolve_repo_root(),
        repo_unavailable=st.repo_unavailable or "false",
        codex_present=st.codex_present,
        cursor_present=st.cursor_present,
        claude_binary_found=st.claude_binary_found,
        codex_binary_found=st.codex_binary_found,
        cursor_binary_found=st.cursor_binary_found,
        timing_ledger=str(Path(st.implement_tmpdir) / "timing-ledger.tsv"),
        token_session_id=st.session_id,
        claude_source_file=claude_source,
        prev_implement_tmpdir=st.implement_tmpdir,
        auto_mode=prior_auto_mode,
        dynamic_archetypes=prior_dynamic_archetypes if prior_dynamic_archetypes in {"0", "1"} else "",
        run_id=st.run_id if _valid_run_id(st.run_id) else "",
        forked_target=st.opts.forked_target,
        live_mutation_ok="true",
    )
    sidecar = session_env.WriteEnvParams(
        output=str(Path(st.implement_tmpdir) / "plugin-root.env"),
        repo_unavailable=None,
        plugin_root_only=True,
        value=str(_REPO_ROOT),
    )
    for params in (base, sidecar):
        if session_env.run_write_env(params).returncode != 0:
            # Raises BootstrapExit, so the sidecar never runs after a base failure.
            st.emit_step_failed("write-session-env")


def _persist_run_flags(st: BootstrapState) -> bool:
    if not st.implement_tmpdir:
        return True
    persisted = proc.run([
        str(larch_entrypoint(_REPO_ROOT)), "session", "persist-run-flags",
        "--implement-tmpdir", st.implement_tmpdir,
        "--no-issues", "false",
        "--force-requested", st.opts.force_requested,
        "--self-review-requested", st.opts.self_review_requested,
        "--self-implement-requested", st.opts.self_implement_requested,
        "--difficulty-override", st.opts.difficulty_override,
    ])
    if persisted.returncode != 0:
        st.stall_tracking = "true"
        st.implement_bail_reason = "run-flags-persist-failed"
        return False
    return True


def _self_subagents_only(opts: BootstrapOptions) -> bool:
    return opts.self_review_requested == "true" and opts.self_implement_requested == "true"
def _phase_tracking(st: BootstrapState) -> None:
    if st.repo_unavailable == "true":
        st.branch_selected = "repo-unavailable-skip"
        st.deferred = "true"
        return
    if st.opts.forked_target == "true":
        st.branch_selected = "forked-target-skip"
        st.deferred = "true"
        return
    sentinel = Path(st.implement_tmpdir) / "parent-issue.md"
    if sentinel.is_file():
        read = rust_runtime.tracking_issue_read_sentinel(
            proc,
            sentinel=str(sentinel),
        )
        if not read.failed and read.adopted == "true":
            issue = read.issue_number
            run_id = read.run_id
            if st.opts.issue_number and issue != st.opts.issue_number:
                if st.opts.resume_plan_tail:
                    st.emit_step_failed("resume-plan-tail-sentinel")
                with contextlib.suppress(OSError):
                    sentinel.unlink()
            elif not st.opts.issue_number:
                st.emit_step_failed("issue-number-required-for-resume")
            elif _valid_issue(issue) and _valid_run_id(run_id):
                st.branch_selected = "branch-1-resume"
                st.issue_number_resolved = issue
                st.run_id = run_id
                if st.opts.resume_plan_tail:
                    return
                dirty_lines = _dirty_tree_checkpoint()
                if _checkpoint_status(dirty_lines) in {"dirty", "unknown"}:
                    st.implement_bail_reason = "dirty-tree"
                    return
                _perform_tracking_side_effects(st, write_sentinel=False)
                return
        elif st.opts.resume_plan_tail:
            st.emit_step_failed("resume-plan-tail-sentinel")
    elif st.opts.resume_plan_tail and not ((Path(st.implement_tmpdir) / "plan.txt").is_file() and (Path(st.implement_tmpdir) / "feature-description.txt").is_file()):
        st.emit_step_failed("resume-plan-tail-sentinel")

    if not st.opts.issue_number:
        return
    if st.opts.resume_plan_tail and (Path(st.implement_tmpdir) / "plan.txt").is_file():
        st.issue_number_resolved = st.opts.issue_number
        st.run_id = st.resolve_run_id()
        st.branch_selected = "branch-2-adopt"
        st.deferred = "true"
        return
    _adopt_tracking_issue(st)


def _adopt_tracking_issue(st: BootstrapState) -> None:
    state = rust_runtime.issue_state(proc, issue=st.opts.issue_number)
    if state.failed:
        st.emit_step_failed("get-issue-state")
        return
    if state.is_pr:
        st.implement_bail_reason = "adopted-issue-is-pr"
        return
    if state.state == "CLOSED":
        st.implement_bail_reason = "adopted-issue-closed"
        return
    if state.state != "OPEN":
        st.emit_step_failed("get-issue-state")
        return
    dirty_lines = _dirty_tree_checkpoint()
    if _checkpoint_status(dirty_lines) in {"dirty", "unknown"}:
        st.implement_bail_reason = "dirty-tree"
        return
    st.branch_selected = "branch-2-adopt"
    st.issue_number_resolved = st.opts.issue_number
    st.run_id = st.resolve_run_id()
    _perform_tracking_side_effects(st, write_sentinel=True)


def _tracking_bail(*, st: BootstrapState, detail: str, result: object | None = None) -> None:
    st.stall_tracking = "true"
    st.implement_bail_reason = "tracking-init-failed"
    if st.implement_tmpdir:
        text = detail + "\n"
        if result is not None:
            text += str(result)
        with contextlib.suppress(OSError):
            (Path(st.implement_tmpdir) / "tracking-init-failed.stderr.log").write_text(text, encoding="utf-8")


def _difficulty_prior_from_preflight(st: BootstrapState) -> str:
    if not st.opts.preflight_tmpdir:
        return ""
    plan = Path(st.opts.preflight_tmpdir) / "plan-from-issue.txt"
    if not plan.is_file():
        return ""
    try:
        return difficulty.plan_difficulty(plan.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return ""


def _persist_difficulty_prior(st: BootstrapState, tier: str) -> None:
    if not st.implement_tmpdir:
        return
    path = Path(st.implement_tmpdir) / "difficulty-prior.env"
    value = tier if difficulty.tier_valid(tier) else ""
    text = f"DESIGN_DIFFICULTY={value}\n"
    with contextlib.suppress(OSError):
        _atomic_text(path=path, text=text)


def _write_initial_difficulty_record(st: BootstrapState, tier: str) -> None:
    if not st.implement_tmpdir or not _valid_run_id(st.run_id):
        return
    tmpdir = Path(st.implement_tmpdir)
    out = tmpdir / difficulty.DIFFICULTY_RECORD_BASENAME
    fallback = difficulty.DifficultyRating(
        predicted_tier="MODERATE", confidence="medium",
        rationale="initial record seeded before implement rating", adjusted_tier="MODERATE",
    )
    design = (difficulty.DifficultyRating(tier, "medium", "design wire metadata", tier)
              if difficulty.tier_valid(tier) else None)
    try:
        record = difficulty.build_record(
            rater="fallback", rater_tool="bootstrap", rater_model="unknown",
            design_rating=design, fallback_rating=fallback, changed_paths=(),
            override_tier=st.opts.difficulty_override,
            override_source="operator" if difficulty.tier_valid(st.opts.difficulty_override) else "",
        )
        difficulty.write_record(out, record)
    except (OSError, ValueError):
        return
    with contextlib.suppress(OSError, ValueError):
        run_logs.log_write(log_root=tmpdir / "larch-logs", skill="implement", run_id=st.run_id,
                           batch="difficulty-rating", input_file=str(out))


def _perform_tracking_side_effects(st: BootstrapState, *, write_sentinel: bool) -> bool:
    if not _valid_issue(st.issue_number_resolved):
        _tracking_bail(st=st, detail="invalid issue number")
        return False
    if not _valid_run_id(st.run_id):
        _tracking_bail(st=st, detail="invalid or empty run id")
        return False
    _write_base_session_env(st)
    try:
        _ = run_logs.log_init(
            log_root=Path(st.implement_tmpdir) / "larch-logs", skill="implement",
            run_id=st.run_id, issue=st.issue_number_resolved,
        )
    except (OSError, ValueError) as exc:
        _tracking_bail(st=st, detail="run-log init failed", result=exc)
        return False
    # Emit plan-review tally (stub or preflight candidate) before later Step 0
    # bailouts can skip _phase_plan; _phase_plan overwrites when a real tally exists.
    prior = _difficulty_prior_from_preflight(st)
    _persist_difficulty_prior(st, prior)
    _write_initial_difficulty_record(st, prior)
    _publish_plan_review_tally(st)
    if not _persist_run_flags(st):
        return False
    post = pr_body.post_tracking_issue(
        Path(st.implement_tmpdir),
        issue_number=st.issue_number_resolved if write_sentinel else "",
        run_id=st.run_id, adopted="true", force_requested=st.opts.force_requested,
    )
    if post.exit_code != 0:
        st.deferred = "true"
        return False
    if not post.posted:
        st.deferred = "true"
    return True


def _preflight_labels_sha256(value: object) -> str:
    """Hash the exact admission-relevant label-name set from preflight."""
    if not isinstance(value, list):
        raise TypeError("preflight issue labels unavailable")
    names: list[str] = []
    for row in value:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            raise TypeError("preflight issue labels unavailable")
        name = row["name"]
        if not name:
            raise ValueError("preflight issue labels unavailable")
        names.append(name)
    if len(names) != len(set(names)):
        raise ValueError("preflight issue labels unavailable")
    digest = hashlib.sha256()
    for name in sorted(names):
        encoded = name.encode()
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def _activate_tracking_lease(st: BootstrapState) -> bool:
    """Atomically create the verified lease and active title in Rust."""
    activated = False
    repo = ""
    post_body_path: Path | None = None
    try:
        from larch.issue import migration_governance  # noqa: PLC0415 - keep bootstrap imports acyclic

        repo_root = _resolve_repo_root()
        base_target = (
            "upstream/main" if st.opts.forked_target == "true" else "origin/main"
        )
        base_target_sha = git.rev_parse(
            proc, base_target, cwd=repo_root
        )
        repo = (
            st.opts.upstream_repo
            if st.opts.forked_target == "true"
            else st.repo
        ) or gh.resolve_repo(proc) or ""
        if not repo:
            raise OSError("repository unavailable for implementation lease")
        issue_json_path = Path(st.opts.preflight_tmpdir) / "issue.json"
        issue_snapshot = json.loads(issue_json_path.read_text(encoding="utf-8"))
        if not isinstance(issue_snapshot, dict):
            raise OSError("preflight issue freshness identity unavailable")
        expected_updated_at = issue_snapshot.get("updatedAt", "")
        expected_body = issue_snapshot.get("body", "")
        expected_title = issue_snapshot.get("title", "")
        expected_labels_sha256 = _preflight_labels_sha256(
            issue_snapshot.get("labels")
        )
        if (
            not isinstance(expected_updated_at, str)
            or not expected_updated_at
            or not isinstance(expected_body, str)
            or not expected_body
            or not isinstance(expected_title, str)
            or not expected_title
        ):
            raise OSError("preflight issue freshness identity unavailable")
        pre_verdict = migration_governance.evaluate_governance_gate(
            proc,
            issue=st.issue_number_resolved,
            repo=repo,
            body=expected_body,
            repo_root=Path(repo_root).resolve(),
            cwd=repo_root,
            head_sha=base_target_sha,
        )
        if not pre_verdict.ok:
            reasons = ",".join(pre_verdict.blocking_reasons) or "unknown"
            raise OSError(f"implementation-lease-admission-refused:{reasons}")
        post_body_path = Path(st.implement_tmpdir) / "tracking-lease-post-body.md"
        larch_io.atomic_write(
            path=post_body_path,
            text="",
            prefix="tracking-lease-post-body.",
            mode=0o600,
        )
        renamed = rust_runtime.tracking_issue_rename(
            proc,
            issue=st.issue_number_resolved,
            state="implementing",
            repo=repo,
            run_id=st.run_id,
            lease_branch=st.branch_name,
            head_sha=base_target_sha,
            expected_updated_at=expected_updated_at,
            expected_body_sha256=hashlib.sha256(expected_body.encode()).hexdigest(),
            expected_title_sha256=hashlib.sha256(expected_title.encode()).hexdigest(),
            expected_labels_sha256=expected_labels_sha256,
            cwd=repo_root,
        )
        if renamed.failed:
            raise OSError(renamed.error or "tracking-issue rename failed")
        activated = True
        post_read = rust_runtime.tracking_issue_read_body(
            proc,
            issue=st.issue_number_resolved,
            output_file=str(post_body_path),
            repo=repo,
            cwd=repo_root,
        )
        if post_read.failed:
            raise OSError(post_read.error or "tracking-issue post-admission read failed")
        post_body = post_body_path.read_text(encoding="utf-8")
        post_verdict = migration_governance.evaluate_governance_gate(
            proc,
            issue=st.issue_number_resolved,
            repo=repo,
            body=post_body,
            repo_root=Path(repo_root).resolve(),
            cwd=repo_root,
            head_sha=base_target_sha,
        )
        if not post_verdict.ok:
            reasons = ",".join(post_verdict.blocking_reasons) or "unknown"
            raise OSError(f"implementation-lease-post-admission-refused:{reasons}")
    except Exception as exc:
        terminal_detail = ""
        if activated and repo:
            try:
                terminal = rust_runtime.tracking_issue_rename(
                    proc,
                    issue=st.issue_number_resolved,
                    state="stalled",
                    repo=repo,
                    run_id=st.run_id,
                )
                if terminal.failed:
                    terminal_detail = f"; terminal lease update failed: {terminal.error}"
            except Exception as terminal_exc:
                terminal_detail = f"; terminal lease update failed: {terminal_exc}"
        _tracking_bail(
            st=st,
            detail=f"implementation lease activation failed{terminal_detail}",
            result=exc,
        )
        return False
    finally:
        if post_body_path is not None:
            with contextlib.suppress(OSError):
                post_body_path.unlink(missing_ok=True)
    return True


def _append_execution_issue_entry(*, log: Path, category: str, entry: str) -> bool:
    try:
        run_log_batch.append_execution_issue(log_file=log, category=category, entry=entry)
    except OSError:
        return False
    return True


def _append_failure_with_entry_fallback(
    st: BootstrapState,
    *,
    site: str,
    tool: str,
    exit_code: str,
    category: str,
    output_file: Path,
    status_label: str,
) -> bool:
    log = Path(st.implement_tmpdir) / "execution-issues.md"
    try:
        run_logs.log_append_failure(
            log=log, site=site, tool=tool, exit_code=exit_code, category=category,
            output_file=output_file, status_label=status_label, redact_body=True,
        )
        return True
    except (OSError, ValueError):
        pass
    body = "no diagnostics captured"
    with contextlib.suppress(OSError):
        if output_file.is_file() and output_file.stat().st_size:
            body = output_file.read_text(encoding="utf-8", errors="replace").rstrip() or body
    body = _redact_text(body, implement_tmpdir=st.implement_tmpdir)
    entry = (
        f"- **Step {site}: {tool} {status_label} (exit {exit_code}; append-failure fallback)**:\n"
        "  ```\n"
        f"{body}\n"
        "  ```\n"
    )
    return _append_execution_issue_entry(log=log, category=category, entry=entry)


def _append_force_bypass(st: BootstrapState) -> bool:
    if st.opts.force_requested != "true" or not st.opts.preflight_tmpdir:
        return True
    source = Path(st.opts.preflight_tmpdir) / "force-bypass.log"
    sentinel = Path(st.implement_tmpdir) / ".force-bypass-log-consumed"
    if not source.is_file() or sentinel.exists():
        return True
    try:
        text = source.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    expected_issue = st.issue_number_resolved or st.opts.issue_number
    canonical = {"missing-designed-prefix"}
    valid = bool(text.strip())
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = re.fullmatch(r"BYPASS kind=([a-z-]+) issue=([0-9]+)", stripped)
        if not match or match.group(1) not in canonical or match.group(2) != expected_issue:
            valid = False
            break
    if not valid:
        redacted = Path(st.implement_tmpdir) / "force-bypass.invalid-format.redacted.log"
        try:
            redacted.write_text(
                "Invalid force bypass log redacted.\n"
                f"EXPECTED_ISSUE={expected_issue}\n"
                "EXIT_CODE=99\n",
                encoding="utf-8",
            )
        except OSError:
            return False
        if not _append_failure_with_entry_fallback(
            st,
            site="implement-bootstrap force-bypass-log",
            tool="/implement --force preflight",
            exit_code="99",
            category="Warnings",
            output_file=redacted,
            status_label="invalid-format",
        ):
            return False
    sentinel.write_text("", encoding="utf-8")
    return True


_PLAN_PROVENANCE_PREFIXES = ("review_status:", "rounds_completed:", "difficulty:")


def _strip_plan_provenance_headers(text: str) -> str:
    lines = text.splitlines(keepends=True)
    trailers = plan_grammar.parse_final_trailers(text, require_diff_lines=True)
    if not trailers.matches:
        return text
    start = trailers.start_line - 1
    remove = {
        start + idx
        for idx, match in enumerate(trailers.matches)
        if match.key in {"review_status", "rounds_completed", "difficulty"}
    }
    if not remove:
        return text
    return "".join(line for idx, line in enumerate(lines) if idx not in remove)


def _create_feature_branch(st: BootstrapState, *, feature_file: Path) -> bool:
    if st.opts.forked_target == "true" or st.is_user_branch == "true" or not feature_file.is_file():
        return True
    title = feature_file.read_text(encoding="utf-8", errors="replace").splitlines()[0:1]
    raw = title[0] if title else "issue"
    slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]", "-", raw.lower())).strip("-")[:40].rstrip("-") or "issue"
    branch_name = f"{st.user_prefix}/{slug}-{st.issue_number_resolved}" if st.user_prefix and st.issue_number_resolved else ""
    if not branch_name:
        return True
    created = pr.create_branch(proc, branch=branch_name)
    if created.exit_code != 0:
        st.stall_tracking = "true"
        st.implement_bail_reason = "branch-create-failed"
        return False
    st.branch_action = created.action
    return True


def _phase_plan(st: BootstrapState) -> None:
    st.plan_file = str(Path(st.implement_tmpdir) / "plan.txt")
    feature_file = Path(st.implement_tmpdir) / "feature-description.txt"
    if st.opts.resume_plan_tail:
        if not _append_force_bypass(st):
            st.emit_tmp_step_failed("force-bypass-log")
        if not _persist_run_flags(st):
            return
    elif not _materialize_initial_plan(st, feature_file=feature_file):
        return
    dirty_lines = _dirty_tree_checkpoint()
    if _checkpoint_status(dirty_lines) in {"dirty", "unknown"}:
        st.implement_bail_reason = "dirty-tree"
        return
    if not _create_feature_branch(st, feature_file=feature_file):
        return
    with contextlib.suppress(Exception):
        st.branch_name = git.current_branch(proc)
    if not st.branch_name:
        st.stall_tracking = "true"
        st.implement_bail_reason = "branch-create-failed"
        return
    if st.opts.forked_target != "true" and not _activate_tracking_lease(st):
        return
    issue = st.issue_number_resolved or st.opts.issue_number
    title = feature_file.read_text(encoding="utf-8", errors="replace").splitlines()[0] if feature_file.is_file() else "planned change"
    goal = f"Implement issue #{issue}: {title or 'planned change'}."
    plan_goals = plan_quality.compose_plan_goals_test(
        plan_text=Path(st.plan_file).read_text(encoding="utf-8", errors="replace"), goal_text=goal,
    )
    plan_goals_path = Path(st.implement_tmpdir) / "plan-goals-test.md"
    plan_goals_path.write_text(plan_goals, encoding="utf-8")
    (Path(st.implement_tmpdir) / "run-step1-plan-log.out").write_text("", encoding="utf-8")
    with contextlib.suppress(OSError, ValueError):
        run_logs.log_write(log_root=Path(st.implement_tmpdir) / "larch-logs", skill="implement",
                           run_id=st.run_id, batch="plan-goals-test", input_file=str(plan_goals_path))
    _publish_plan_review_tally(st)
    _upsert_plan_summary(st)
    _err(f"→ step0: branch {st.branch_name} + plan logged")


def _materialize_initial_plan(st: BootstrapState, *, feature_file: Path) -> bool:
    snapshot = Path(st.implement_tmpdir) / "untracked-baseline.z"
    if not snapshot.exists():
        _ = proc.run([str(larch_entrypoint(_REPO_ROOT)), "git", "snapshot-untracked", "--output", str(snapshot), "--nul"])
    if not _append_force_bypass(st):
        st.emit_tmp_step_failed("force-bypass-log")
    plan_src = Path(st.opts.preflight_tmpdir) / "plan-from-issue.txt"
    try:
        plan_text = plan_src.read_text(encoding="utf-8", errors="replace")
        _persist_difficulty_prior(st, difficulty.plan_difficulty(plan_text))
        Path(st.plan_file).write_text(_strip_plan_provenance_headers(plan_text), encoding="utf-8")
    except OSError as exc:
        (Path(st.implement_tmpdir) / "copy-plan.stderr.log").write_text(str(exc), encoding="utf-8")
        st.emit_tmp_step_failed("copy-plan")
    if st.opts.forked_target == "true" and not st.opts.upstream_repo:
        (Path(st.implement_tmpdir) / "gh-issue-view.stderr.log").write_text(
            "--forked requires UPSTREAM_REPO before gh issue view\n", encoding="utf-8"
        )
        st.emit_tmp_step_failed("gh-issue-view")
    view_repo = st.opts.upstream_repo if st.opts.forked_target == "true" else None
    view_result = gh.issue_view_template_read(
        proc, st.issue_number_resolved or st.opts.issue_number, "title,body",
        "{{.title}}\n\n{{.body}}", repo=view_repo,
    )
    if view_result.returncode != 0:
        (Path(st.implement_tmpdir) / "gh-issue-view.stderr.log").write_text(view_result.stderr, encoding="utf-8")
        st.emit_tmp_step_failed("gh-issue-view")
    feature_file.write_text(view_result.stdout, encoding="utf-8")
    return _persist_run_flags(st)


def _publish_plan_review_tally(st: BootstrapState) -> None:
    if not _valid_run_id(st.run_id):
        return
    preflight = Path(st.opts.preflight_tmpdir) if st.opts.preflight_tmpdir else Path()
    for candidate in (
        preflight / "plan-review-tally.json",
        preflight / "voting-tally.json",
        Path(st.implement_tmpdir) / "plan-review-tally.json",
    ):
        if candidate.is_file():
            _write_plan_review_tally_batch(st=st, source=candidate)
            return
    # /implement plan review runs in /design, so no upstream tally is materialized on
    # this path. Emit a stub anyway so the run-log completeness manifest
    # (plan-review-tally.json, condition `always`) is satisfied and the committed
    # artifact points readers back to the /design run for the real ballots.
    stub = Path(st.implement_tmpdir) / "plan-review-tally-stub.json"
    try:
        stub.write_text(_plan_review_tally_stub_json(), encoding="utf-8")
    except OSError:
        return
    _write_plan_review_tally_batch(st=st, source=stub)


def _plan_review_tally_stub_json() -> str:
    record: dict[str, object] = {
        "schema_version": 2,
        "phase": "plan-review",
        "batch": "plan-review-tally",
        "mode": "simple",
        "rounds": 0,
        "accepted_count": 0,
        "rejected_count": 0,
        "exonerated_count": 0,
        "body": (
            "Plan review completed in the /design phase; see the /design run "
            "artifacts for the ballots. No plan-review voting ran in this "
            "/implement run."
        ),
    }
    return json.dumps(record, separators=(",", ":"))


def _write_plan_review_tally_batch(*, st: BootstrapState, source: Path) -> None:
    with contextlib.suppress(OSError, ValueError):
        run_logs.log_write(log_root=Path(st.implement_tmpdir) / "larch-logs", skill="implement",
                           run_id=st.run_id, batch="plan-review-tally", input_file=str(source))


def _upsert_plan_summary(st: BootstrapState) -> None:
    issue = st.issue_number_resolved or st.opts.issue_number
    if not issue or not _valid_run_id(st.run_id) or not st.plan_file:
        return
    content = Path(st.implement_tmpdir) / "summary-plan.md"
    try:
        plan_text = Path(st.plan_file).read_text(encoding="utf-8", errors="replace")
        content.write_text(plan_text[:12000], encoding="utf-8")
    except OSError:
        return
    try:
        result = rust_runtime.tracking_issue_upsert_summary(
            proc,
            issue=issue,
            marker=f"<!-- larch:plan v1 runid={st.run_id} -->",
            content_file=str(content),
            repo=(st.opts.upstream_repo if st.opts.forked_target == "true" else st.repo),
            run_id=st.run_id,
        )
        if result.failed:
            return
    except OSError:
        return


def _record_coder_fallback(*, st: BootstrapState, reason: str) -> None:
    if st.coder_fallback != "true" or not st.implement_tmpdir:
        return
    warning = "**⚠ Cursor and Codex unavailable — implementing with Claude subagent (larch:claude-implementer).**\n"
    _err(warning.rstrip("\n"))
    diag = Path(st.implement_tmpdir) / "coder-fallback-warning.txt"
    with contextlib.suppress(OSError):
        diag.write_text(f"{warning}REASON={reason}\n", encoding="utf-8")
    if diag.is_file():
        with contextlib.suppress(OSError, ValueError):
            run_logs.log_append_failure(
                log=Path(st.implement_tmpdir) / "execution-issues.md",
                site="implement-bootstrap coder-select", tool="phase_coder_select",
                exit_code="0", category="Warnings", output_file=diag,
                status_label="fallback", redact_body=True,
            )
    if _valid_run_id(st.run_id):
        with contextlib.suppress(OSError):
            _ = proc.run([
                str(larch_entrypoint(_REPO_ROOT)), "run-log", "manifest",
                "--log-root", str(Path(st.implement_tmpdir) / "larch-logs"),
                "--skill", "implement", "--run-id", st.run_id,
                "--field", "coder_fallback=true",
            ])


def _record_explicit_coder_unavailable(*, st: BootstrapState, requested: str, selected: str) -> None:
    if not st.implement_tmpdir:
        return
    warning = f"**⚠ Requested {requested} implementer unavailable — using {selected}.**\n"
    _err(warning.rstrip("\n"))
    diag = Path(st.implement_tmpdir) / f"{requested}-unavailable-warning.txt"
    with contextlib.suppress(OSError):
        diag.write_text(f"{warning}REQUESTED={requested}\nSELECTED={selected}\n", encoding="utf-8")
    if diag.is_file():
        with contextlib.suppress(OSError, ValueError):
            run_logs.log_append_failure(
                log=Path(st.implement_tmpdir) / "execution-issues.md",
                site="implement-bootstrap coder-select", tool="phase_coder_select",
                exit_code="0", category="Warnings", output_file=diag,
                status_label="fallback", redact_body=True,
            )


def _phase_coder(st: BootstrapState) -> None:
    if st.implement_bail_reason or st.stall_tracking == "true":
        return
    if st.repo_unavailable == "true" or not st.plan_file or not Path(st.plan_file).is_file() or not (Path(st.implement_tmpdir) / "feature-description.txt").is_file():
        return
    if st.opts.self_implement_requested == "true" or st.opts.coder_opt == "claude":
        st.coder = "claude"
    else:
        if st.opts.coder_opt in {"codex", "cursor"}:
            other = "cursor" if st.opts.coder_opt == "codex" else "codex"
            order = [st.opts.coder_opt, other, "claude"]
        else:
            effective_difficulty = resolve_step2_effective_difficulty(Path(st.implement_tmpdir))
            order = list(
                config.CODER_TOOL_ORDER_BY_DIFFICULTY.get(
                    effective_difficulty,
                    external_defaults.tool_order("implement.step2_coder"),
                )
            )
        for candidate in order:
            if candidate == "codex" and st.codex_available != "true":
                continue
            if candidate == "cursor" and st.cursor_available != "true":
                continue
            st.coder = candidate
            break
        if not st.coder:
            st.coder = "claude"
        if st.coder == "claude":
            st.coder_fallback = "true"
    requested_available = (
        (st.opts.coder_opt == "codex" and st.codex_available == "true")
        or (st.opts.coder_opt == "cursor" and st.cursor_available == "true")
    )
    if st.opts.coder_opt in {"codex", "cursor"} and st.coder != st.opts.coder_opt and not requested_available:
        _record_explicit_coder_unavailable(st=st, requested=st.opts.coder_opt, selected=st.coder)
    if st.coder_fallback == "true":
        _record_coder_fallback(st=st, reason="requested external coder unavailable")
    _err(f"→ step0: coder={st.coder}")


def _emit_final(st: BootstrapState) -> None:
    for key, value in (
        ("CURRENT_BRANCH", st.current_branch),
        ("IS_MAIN", st.is_main),
        ("IS_USER_BRANCH", st.is_user_branch),
        ("USER_PREFIX", st.user_prefix),
        ("ENTRY_GATE", st.entry_gate),
        ("SKIP_BRANCH_CHECK", st.skip_branch_check),
        ("IMPLEMENT_TMPDIR", st.implement_tmpdir),
        ("SESSION_ID", st.session_id),
        ("CLAUDE_BINARY_FOUND", st.claude_binary_found),
        ("CODEX_BINARY_FOUND", st.codex_binary_found),
        ("CURSOR_BINARY_FOUND", st.cursor_binary_found),
        ("REPO", st.repo),
        ("REPO_UNAVAILABLE", st.repo_unavailable),
        ("REPO_ROOT", st.read_session(key="REPO_ROOT") or _resolve_repo_root()),
        ("codex_available", st.codex_available),
        ("cursor_available", st.cursor_available),
        ("ISSUE_NUMBER", st.issue_number_resolved or st.opts.issue_number),
        ("RUN_ID", st.run_id),
        ("BRANCH_SELECTED", st.branch_selected),
        ("DEFERRED", st.deferred),
        ("STALL_TRACKING", st.stall_tracking),
        ("BRANCH_NAME", st.branch_name),
        ("BRANCH_ACTION", st.branch_action),
        ("PLAN_FILE", st.plan_file),
        ("FORCE_REQUESTED", st.opts.force_requested),
        ("SELF_REVIEW_REQUESTED", st.opts.self_review_requested),
        ("SELF_IMPLEMENT_REQUESTED", st.opts.self_implement_requested),
        ("DIFFICULTY_OVERRIDE", st.opts.difficulty_override),
        ("coder", st.coder),
        ("coder_fallback", st.coder_fallback),
        ("IMPLEMENT_BAIL_REASON", st.implement_bail_reason),
    ):
        _emit_kv(key=key, value=value)


def _run_bootstrap_after_infra(st: BootstrapState) -> int:
    """Continue the tracking/plan owner after Rust has published session state.

    `bootstrap invoke` owns the session-infrastructure phase in Rust.  The
    tracking-issue, plan, and implementer-selection phases remain with #7681,
    the `/implement` owner, until their dedicated migration leaf lands. The
    handoff file is Rust-authored, session-confined state; this function never
    recreates a session or re-runs the entry gate.
    """
    opts = st.opts
    try:
        if opts.up_to_phase in {"tracking", "plan", "coder", "all"}:
            _phase_tracking(st)
            if _valid_run_id(st.run_id):
                _write_base_session_env(st)
        if (
            opts.up_to_phase in {"plan", "coder", "all"}
            and not st.implement_bail_reason
            and st.stall_tracking != "true"
            and st.repo_unavailable != "true"
        ):
            _phase_plan(st)
        if (
            opts.up_to_phase in {"coder", "all"}
            and not st.implement_bail_reason
            and st.stall_tracking != "true"
        ):
            _phase_coder(st)
        _emit_final(st)
        return 0
    except BootstrapExit as exc:
        return exc.code
    except Exception as exc:
        _emit_kv(key="STEP_FAILED", value="internal-error")
        if st.implement_tmpdir:
            with contextlib.suppress(OSError):
                (Path(st.implement_tmpdir) / "bootstrap-internal-error.log").write_text(
                    _single_line(str(exc)) + "\n", encoding="utf-8"
                )
        return BOOTSTRAP_CONTRACT_FAILURE


def _restore_infra_state(*, opts: BootstrapOptions, infra_file: Path) -> BootstrapState | None:
    """Read the Rust bootstrap handoff without trusting a symlinked file."""
    if not infra_file.is_file() or infra_file.is_symlink():
        return None
    try:
        fields = larch_io.parse_kv(
            infra_file.read_text(encoding="utf-8", errors="replace"),
            key_pattern=_KEY_RE.pattern,
            duplicate_policy="last",
        )
    except (OSError, ValueError):
        return None
    tmpdir = fields.get("IMPLEMENT_TMPDIR", "")
    session_id = fields.get("SESSION_ID", "")
    tmpdir_path = Path(tmpdir)
    if (
        not tmpdir
        or not tmpdir_path.is_absolute()
        or tmpdir_path.is_symlink()
        or not tmpdir_path.is_dir()
        or infra_file.parent != tmpdir_path
        or not session_id
    ):
        return None
    st = BootstrapState(opts, implement_tmpdir=tmpdir)
    for field_name, key in (
        ("current_branch", "CURRENT_BRANCH"),
        ("is_main", "IS_MAIN"),
        ("is_user_branch", "IS_USER_BRANCH"),
        ("user_prefix", "USER_PREFIX"),
        ("entry_gate", "ENTRY_GATE"),
        ("skip_branch_check", "SKIP_BRANCH_CHECK"),
        ("session_id", "SESSION_ID"),
        ("repo", "REPO"),
        ("repo_unavailable", "REPO_UNAVAILABLE"),
        ("codex_present", "CODEX_PRESENT"),
        ("cursor_present", "CURSOR_PRESENT"),
        ("claude_binary_found", "CLAUDE_BINARY_FOUND"),
        ("codex_binary_found", "CODEX_BINARY_FOUND"),
        ("cursor_binary_found", "CURSOR_BINARY_FOUND"),
        ("codex_available", "codex_available"),
        ("cursor_available", "cursor_available"),
        ("run_id", "RUN_ID"),
    ):
        setattr(st, field_name, fields.get(key, ""))
    return st


def _filtered_envelope(text: str, *, resume: bool) -> str:
    lines: list[str] = []
    for key, value in larch_io.parse_kv(text, skip_comments=True, cr_strip="rstrip").items():
        if not _KEY_RE.fullmatch(key) or key not in ROUTING_KEYS:
            continue
        if resume and key in {"coder", "coder_fallback"} and not value:
            continue
        lines.append(f"{key}={value}")
    return "\n".join(lines) + ("\n" if lines else "")


def _routing_file_trusted(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _restore_resume_coder(*, data: dict[str, str], routing_file: Path, tmpdir: str) -> None:
    if data.get("coder"):
        return
    sources: list[Path] = []
    if routing_file.exists() and _routing_file_trusted(routing_file):
        sources.append(routing_file)
    sources.extend((Path(tmpdir) / "session-env.sh", Path(tmpdir) / "run-flags.sh"))
    for path in sources:
        if not path.is_file():
            continue
        try:
            prior = _parse_env_lines(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        for key in ("coder", "coder_fallback"):
            if prior.get(key) and not data.get(key):
                data[key] = prior[key]
        if data.get("coder"):
            return
    for path in (Path(tmpdir) / "session-env.sh", Path(tmpdir) / "run-flags.sh"):
        if not path.is_file():
            continue
        if not data.get("coder"):
            value = _read_key(path=path, key="coder", default="")
            if value in {"claude", "codex", "cursor"}:
                data["coder"] = value
        if not data.get("coder_fallback"):
            value = _read_key(path=path, key="coder_fallback", default="")
            if value:
                data["coder_fallback"] = value
        if data.get("coder"):
            return


def _step2_blockers(data: dict[str, str]) -> bool:
    if data.get("REPO_UNAVAILABLE") == "true":
        return True
    plan = data.get("PLAN_FILE", "")
    if not plan or not Path(plan).is_file():
        return True
    tmpdir = data.get("IMPLEMENT_TMPDIR", "")
    if not tmpdir:
        return False
    tmp = Path(tmpdir)
    return not (tmp / "plan.txt").is_file() or not (tmp / "feature-description.txt").is_file()


def _preserve_resume_routing(*, envelope: str, routing_file: Path) -> str:
    if not routing_file.is_file() or routing_file.is_symlink():
        return envelope
    try:
        prior = _parse_env_lines(routing_file.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return envelope
    data = _parse_env_lines(envelope)
    changed = False
    for key in ("coder", "coder_fallback"):
        if not data.get(key) and prior.get(key):
            data[key] = prior[key]
            changed = True
    if not changed:
        return envelope
    lines = [f"{key}={data[key]}" for key in ROUTING_KEYS if data.get(key)]
    return "\n".join(lines) + ("\n" if lines else "")


def _redact_text(text: str, *, implement_tmpdir: str = "") -> str:
    _ = implement_tmpdir
    try:
        return redact.redact(text)
    except Exception:
        return "diagnostic redaction failed\n"


def _redact_file(path: Path, *, implement_tmpdir: str = "") -> str:
    if not path.is_file():
        return ""
    return _redact_text(path.read_text(encoding="utf-8", errors="replace"), implement_tmpdir=implement_tmpdir)


def _invoke_error(*, step_failed: str, out: str, implement_tmpdir: str) -> None:
    lines = [line for line in out.splitlines() if line.startswith(("STEP_FAILED=", "GATE_ERROR=", "PREFLIGHT_ERROR="))]
    for line in lines:
        print(line, file=sys.stderr)
    messages = {
        "session-entry-gate": "**⚠ /implement: internal Step 0 contract violation in session-entry-gate.sh. Aborting.**",
        "session-setup": "**⚠ /implement requires clean main to start. To continue, choose one of: (a) `git checkout main && git status` clean → re-run; (b) check out or create a `<USER_PREFIX>/*` feature branch and re-run. This bypass covers branch position and main-sync only; stash cleanliness still applies on feature branches; (c) commit or stash uncommitted changes on `main` first; (d) clear a non-empty stash with `git stash pop` to restore and commit, or `git stash drop` to discard.**",
        "get-issue-state": "**⚠ /implement Step 0 tracking: could not verify the adopted issue state. Aborting.**",
        "issue-number-required-for-resume": "**⚠ /implement Step 0 tracking: --issue-number is required to resume an adopted tracking sentinel. Re-run `/implement <issue-N>` for the sentinel's issue.**",
        "copy-plan": "**⚠ /implement Step 0 plan materialization: could not copy the preflight plan into the implement session. Aborting.**",
        "gh-issue-view": "**⚠ /implement Step 0 plan materialization: could not read the issue title/body. Aborting.**",
        "resume-plan-tail-sentinel": "**⚠ /implement Step 0 dirty-tree recovery: the resume tail could not validate tracking state from the existing session artifacts. Restore or inspect `$IMPLEMENT_TMPDIR`, then restart `/implement`.**",
        "create-branch": "**⚠ /implement Step 0: could not verify branch state before bootstrap. Aborting.**",
        "write-session-env": "**⚠ /implement Step 0: could not write session environment. Aborting.**",
        "larch-run": "**⚠ /implement Step 0: could not write the session launcher. Aborting.**",
        "degraded-both-down-hard-fail": "**⚠ /implement Step 0: both Codex and Cursor are unavailable after health probes. Aborting.**",
        "force-bypass-log": "**⚠ /implement Step 0: force bypass log handling failed. Aborting.**",
    }
    if step_failed in {"copy-plan", "gh-issue-view"} and implement_tmpdir:
        log = Path(implement_tmpdir) / ("copy-plan.stderr.log" if step_failed == "copy-plan" else "gh-issue-view.stderr.log")
        if log.is_file():
            sys.stderr.write(_redact_file(log, implement_tmpdir=implement_tmpdir))
    if step_failed == "absorbed-degraded-gate" and out.strip():
        detail = out if out.endswith("\n") else out + "\n"
        sys.stderr.write(detail)
    print(messages.get(step_failed, f"**⚠ /implement Step 0 bootstrap failed at step={step_failed or 'unknown'}. Aborting.**"), file=sys.stderr)


def _str_bool(value: str) -> str:
    return value if value in {"true", "false"} else ""


def _envelope_text(data: dict[str, str]) -> str:
    lines = [f"{key}={data[key]}" for key in ROUTING_KEYS if data.get(key)]
    return "\n".join(lines) + ("\n" if lines else "")


_GATE_STDERR_KV_PREFIXES: tuple[str, ...] = (
    "DEGRADED=",
    "BOTH_DOWN=",
    "CODEX_STATE=",
    "CURSOR_STATE=",
    "PRESENCE_INPUT_EMPTY=",
    "DEGRADED_HARD_FAIL=",
)


def _parent_invocation_non_interactive() -> bool:
    def ps_query(*, field: str, pid_value: int) -> subprocess.CompletedProcess[str] | None:
        try:
            return subprocess.run(
                [_PS, "-o", field, "-p", str(pid_value)],
                capture_output=True,
                text=True,
                errors="replace",
                check=False,
            )
        except OSError:
            return None

    pid = os.getppid()
    visited: set[int] = set()
    for _ in range(8):
        if pid <= 1 or pid in visited:
            break
        visited.add(pid)
        comm = ps_query(field="comm=", pid_value=pid)
        if comm is None:
            return False
        if comm.returncode == 0:
            comm_name = comm.stdout.strip().lower()
            if comm_name in {"cron", "crond"} or "cron" in comm_name:
                return True
        args = ps_query(field="args=", pid_value=pid)
        if args is None:
            return False
        if args.returncode == 0:
            args_line = args.stdout.strip()
            if args_line:
                lower = args_line.lower()
                if "<<autonomous-loop" in lower:
                    return True
                if re.search(r"\bclaude\b", lower) and re.search(r"(?:\s|^)(?:-p\b|--print\b)", lower):
                    return True
        ppid = ps_query(field="ppid=", pid_value=pid)
        if ppid is None:
            return False
        if ppid.returncode != 0:
            break
        try:
            pid = int(ppid.stdout.strip())
        except ValueError:
            break
    return False


def _resolve_non_interactive(
    *, explicit: str,
    env: Mapping[str, str] | None = None,
) -> bool:
    if explicit in {"true", "false"}:
        return explicit == "true"
    runtime = env or os.environ
    for key in ("LARCH_SKILL_NON_INTERACTIVE", "LARCH_AUTONOMOUS_LOOP", "LARCH_EVAL_RUN", "LARCH_CRON"):
        if runtime.get(key, "") == "true":
            return True
    if runtime.get("CLAUDE_CODE_SUBAGENT", "").lower() in {"1", "true", "yes"}:
        return True
    return _parent_invocation_non_interactive()


def _continue_predicate(data: dict[str, str]) -> bool:
    if data.get("IMPLEMENT_BAIL_REASON"):
        return False
    if data.get("STALL_TRACKING") == "true":
        return False
    if _step2_blockers(data):
        return False
    return bool(data.get("coder"))


def _bootstrap_next(data: dict[str, str], *, continue_tail_attempted: bool) -> str:
    next_step = "cleanup"
    if data.get("DEGRADED_PROMPT_REQUIRED") == "true":
        next_step = "degraded-prompt"
    else:
        route = data.get("ROUTE", "")
        bail_reason = data.get("IMPLEMENT_BAIL_REASON", "")
        if route in {"conflict", "bail"} and not _step2_blockers(data):
            next_step = "rebase-routing"
        elif bail_reason == "dirty-tree":
            next_step = "dirty-recovery"
        elif _step2_blockers(data) or bail_reason or data.get("STALL_TRACKING") == "true":
            next_step = "cleanup"
        elif continue_tail_attempted and route not in {"continue", "conflict", "bail"}:
            next_step = "rebase-routing"
        elif route == "continue" and data.get("coder"):
            next_step = "step2"
    return next_step


def _merge_tail_routing_and_next(
    data: dict[str, str],
    *,
    tail: ContinueTailResult,
    continue_tail_attempted: bool,
) -> None:
    data.update({key: value for key, value in tail.routing.items() if value})
    data["BOOTSTRAP_NEXT"] = _bootstrap_next(data, continue_tail_attempted=continue_tail_attempted)


@dataclass(frozen=True)
class ContinueTailResult:
    routing: dict[str, str] = field(default_factory=dict)
    advisory_lines: list[str] = field(default_factory=list)
    contract_failure: bool = False
    step_failed: str = ""
    failure_detail: str = ""


def _refresh_gate_probe(st: BootstrapState) -> str | None:
    try:
        result = agents.check_reviewers()
    except OSError:
        try:
            result = agents.check_reviewers()
        except OSError:
            return "absorbed-gate-probe-refresh-failed"
    kv = result.kv()
    st.codex_present = kv.get("CODEX_PRESENT", st.codex_present)
    st.cursor_present = kv.get("CURSOR_PRESENT", st.cursor_present)
    st.codex_binary_found = kv.get("CODEX_BINARY_FOUND", st.codex_binary_found)
    st.cursor_binary_found = kv.get("CURSOR_BINARY_FOUND", st.cursor_binary_found)
    return None

def _run_1r_probe(st: BootstrapState, *, forked_target: str) -> tuple[dict[str, str], list[str], int]:
    result = rust_runtime.checkpoint_probe(
        proc,
        step_prefix="1.r",
        short_name="plan materialization",
        forked_target=forked_target if forked_target in {"true", "false"} else "false",
    )
    routing = dict(result.routing)
    advisory = list(result.advisory_lines)
    routing["REBASE_RC"] = str(result.exit_code)
    route = routing.get("ROUTE", "")
    if route not in {"continue", "conflict", "bail"}:
        routing["ROUTE"] = "bail"
        routing["CHECKPOINT_NEXT"] = "load-routing"
        routing.setdefault("REBASE_OUTCOME", "failed")
        error = _single_line(result.stderr or f"probe rc {result.exit_code}")
        routing["REBASE_ERROR"] = _redact_text(error, implement_tmpdir=st.implement_tmpdir)
    elif routing.get("CHECKPOINT_NEXT", "") not in {"continue", "load-routing"}:
        routing["CHECKPOINT_NEXT"] = "load-routing"
    return routing, advisory, result.exit_code


def _run_absorbed_continue_tail(
  data: dict[str, str],
  *,
  opts: BootstrapOptions,
  non_interactive: bool,
) -> ContinueTailResult:
    if not _continue_predicate(data):
        return ContinueTailResult()
    tmpdir = data.get("IMPLEMENT_TMPDIR", "")
    if not tmpdir:
        return ContinueTailResult(contract_failure=True, step_failed="absorbed-continue-tail")
    st = BootstrapState(opts, implement_tmpdir=tmpdir)
    st.codex_present = data.get("CODEX_PRESENT", st.codex_present)
    st.cursor_present = data.get("CURSOR_PRESENT", st.cursor_present)
    st.codex_binary_found = data.get("CODEX_BINARY_FOUND", st.codex_binary_found)
    st.cursor_binary_found = data.get("CURSOR_BINARY_FOUND", st.cursor_binary_found)
    if _self_subagents_only(opts):
        probe_routing, advisory, _probe_rc = _run_1r_probe(st, forked_target=opts.forked_target)
        routing = {
            "DEGRADED": "false",
            "BOTH_DOWN": "false",
            "DEGRADED_PROMPT_REQUIRED": "false",
        }
        routing.update({key: value for key, value in probe_routing.items() if value})
        if _step2_blockers({**data, **routing}):
            routing.pop("ROUTE", None)
        return ContinueTailResult(routing=routing, advisory_lines=advisory)
    probe_failed = _refresh_gate_probe(st)
    if probe_failed:
        return ContinueTailResult(contract_failure=True, step_failed=probe_failed)
    forked_target = opts.forked_target if opts.forked_target in {"true", "false"} else "false"
    sentinel = Path(tmpdir) / ".degraded-tools-gate-prompted"
    sentinel_exists = sentinel.is_file()
    gate = agents.degraded_tools_result(
        skill="implement", codex_present=st.codex_present, cursor_present=st.cursor_present,
        codex_binary_found=st.codex_binary_found or "unknown",
        cursor_binary_found=st.cursor_binary_found or "unknown",
    )
    gate_routing = {
        "DEGRADED": str(gate.degraded).lower(), "CODEX_STATE": gate.codex_state,
        "CURSOR_STATE": gate.cursor_state, "BOTH_DOWN": str(gate.both_down).lower(),
    }
    if gate.both_down:
        gate_routing["DEGRADED_HARD_FAIL"] = "true"
    if gate.presence_input_empty:
        gate_routing["PRESENCE_INPUT_EMPTY"] = "true"
    explanation_lines = list(gate.explanation)
    explanation_text = "\n".join(explanation_lines).strip()
    both_down_seen = "BOTH_DOWN" in gate_routing
    both_down = gate_routing.get("BOTH_DOWN", "")
    degraded = gate_routing.get("DEGRADED", "false") == "true"
    routing: dict[str, str] = {
        "DEGRADED": gate_routing.get("DEGRADED", "false"),
        "CODEX_STATE": gate_routing.get("CODEX_STATE", ""),
        "CURSOR_STATE": gate_routing.get("CURSOR_STATE", ""),
        "DEGRADED_PROMPT_REQUIRED": "false",
    }
    if gate_routing.get("DEGRADED_HARD_FAIL") == "true":
        routing["DEGRADED_HARD_FAIL"] = "true"
    if gate_routing.get("BOTH_DOWN") in {"true", "false"}:
        routing["BOTH_DOWN"] = gate_routing["BOTH_DOWN"]
    if gate_routing.get("PRESENCE_INPUT_EMPTY") == "true":
        _append_execution_issue_entry(
            log=Path(tmpdir) / "execution-issues.md",
            category="Warnings",
            entry="- **Step 0 degraded-tools gate**: PRESENCE_INPUT_EMPTY=true (caller rehydration warning)\n",
        )
    prompt_required = False
    run_probe = True
    if degraded:
        if not explanation_text:
            return ContinueTailResult(contract_failure=True, step_failed="absorbed-degraded-explanation-missing")
        if not both_down_seen:
            if non_interactive:
                return ContinueTailResult(contract_failure=True, step_failed="absorbed-both-down-missing")
            for line in explanation_lines:
                _err(line)
            prompt_required = True
            run_probe = False
        elif both_down == "false":
            if not sentinel_exists:
                for line in explanation_lines:
                    _err(line)
                prompt_required = True
                run_probe = False
        elif both_down == "true":
            for line in explanation_lines:
                _err(line)
            routing["DEGRADED_HARD_FAIL"] = "true"
            return ContinueTailResult(
                routing=routing,
                contract_failure=True,
                step_failed="degraded-both-down-hard-fail",
                failure_detail=explanation_text,
            )
        else:
            if non_interactive:
                return ContinueTailResult(contract_failure=True, step_failed="absorbed-both-down-missing")
            for line in explanation_lines:
                _err(line)
            prompt_required = True
            run_probe = False
    advisory: list[str] = []
    if prompt_required:
        routing["DEGRADED_PROMPT_REQUIRED"] = "true"
    elif run_probe:
        probe_routing, probe_advisory, _probe_rc = _run_1r_probe(st, forked_target=forked_target)
        routing.update({key: value for key, value in probe_routing.items() if value})
        if _step2_blockers({**data, **routing}):
            routing.pop("ROUTE", None)
        advisory.extend(probe_advisory)
    return ContinueTailResult(routing=routing, advisory_lines=advisory)


def continuation_main(argv: list[str]) -> int:
    """Run the non-session bootstrap phases after the Rust infra handoff.

    This internal `/implement` continuation is intentionally not the legacy
    ``bootstrap invoke`` command.  Its explicit owner is the later implement
    migration umbrella; Rust owns the public bootstrap command and calls this
    only after it has atomically created or rehydrated the session state. The
    remaining owner is #7681.
    """
    os.environ["LARCH_QUIET_DISABLE"] = "1"
    parser = argparse.ArgumentParser(prog="bootstrap invoke", add_help=True)
    parser.add_argument("--infra-file", required=True)
    parser.add_argument("--mode", required=True, choices=["initial", "resume"])
    parser.add_argument("--issue-number", default="")
    parser.add_argument("--forked-target", default="", choices=["", "true", "false"])
    parser.add_argument("--merge-requested", default="", choices=["", "true", "false"])
    parser.add_argument("--draft-requested", default="", choices=["", "true", "false"])
    parser.add_argument("--no-admin-fallback", default="", choices=["", "true", "false"])
    parser.add_argument("--no-logs-commit", default="", choices=["", "true", "false"])
    parser.add_argument("--upstream-repo", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--coder", default="", choices=["", "claude", "codex", "cursor"])
    parser.add_argument("--preflight-tmpdir", default="")
    parser.add_argument("--caller-env", default="")
    parser.add_argument("--force-requested", default="", choices=["", "true", "false"])
    parser.add_argument("--self-review-requested", default="", choices=["", "true", "false"])
    parser.add_argument("--self-implement-requested", default="", choices=["", "true", "false"])
    parser.add_argument("--non-interactive", default="", choices=["", "true", "false"])
    parser.add_argument("--difficulty", default="", choices=["", "TRIVIAL", "MODERATE", "HARD"])
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 1 if int(exc.code or 0) != 0 else 0
    env = os.environ
    infra_file = Path(args.infra_file)
    try:
        infra_values = larch_io.parse_kv(
            infra_file.read_text(encoding="utf-8", errors="replace"),
            key_pattern=_KEY_RE.pattern,
            duplicate_policy="last",
        )
    except (OSError, ValueError):
        print("bootstrap invoke: Rust infrastructure handoff is unavailable", file=sys.stderr)
        return 2
    issue = args.issue_number or env.get("TARGET_ISSUE_NUMBER") or env.get("ISSUE_NUMBER", "")
    caller_env = args.caller_env or env.get("CALLER_ENV_PATH") or env.get("SESSION_ENV_PATH", "")
    preflight = args.preflight_tmpdir or env.get("PREFLIGHT_TMPDIR", "")
    forked = args.forked_target or env.get("forked_target") or (env.get("FORKED_TARGET", "") if not env.get("forked_target") else "") or "false"
    upstream = args.upstream_repo or env.get("UPSTREAM_REPO", "")
    run_id = args.run_id or env.get("RUN_ID", "")
    implement_tmpdir_env = infra_values.get("IMPLEMENT_TMPDIR", "") or env.get("IMPLEMENT_TMPDIR", "")
    if implement_tmpdir_env:
        env["IMPLEMENT_TMPDIR"] = implement_tmpdir_env
    seed_file = Path(implement_tmpdir_env) / "ship-seed-input.env" if implement_tmpdir_env else Path()
    resume_seed = args.mode == "resume"
    merge_requested = (
        args.merge_requested
        or _str_bool(env.get("merge", ""))
        or _str_bool(env.get("MERGE", ""))
        or (_read_simple_kv(path=seed_file, key="MERGE") if resume_seed else "")
        or "false"
    )
    draft_requested = (
        args.draft_requested
        or _str_bool(env.get("draft", ""))
        or _str_bool(env.get("DRAFT", ""))
        or (_read_simple_kv(path=seed_file, key="DRAFT") if resume_seed else "")
        or "false"
    )
    no_admin_fallback = (
        args.no_admin_fallback
        or _str_bool(env.get("no_admin_fallback", ""))
        or _str_bool(env.get("NO_ADMIN_FALLBACK", ""))
        or (_read_simple_kv(path=seed_file, key="NO_ADMIN_FALLBACK") if resume_seed else "")
        or "false"
    )
    no_logs_commit = (
        args.no_logs_commit
        or _str_bool(env.get("no_logs_commit", ""))
        or _str_bool(env.get("NO_LOGS_COMMIT", ""))
        or (_read_simple_kv(path=seed_file, key="NO_LOGS_COMMIT") if resume_seed else "")
        or "false"
    )
    force = args.force_requested or _str_bool(env.get("force_requested", "")) or "false"
    self_review = args.self_review_requested or _str_bool(env.get("self_review", "")) or "false"
    self_implement = args.self_implement_requested or _str_bool(env.get("self_implement", "")) or "false"
    difficulty_override = args.difficulty or env.get("difficulty", "") or env.get("DIFFICULTY_OVERRIDE", "")
    non_interactive = args.non_interactive or _str_bool(env.get("non_interactive", "")) or ""
    coder = "" if args.mode == "resume" else (args.coder or env.get("coder", ""))
    if args.mode == "resume" and not env.get("IMPLEMENT_TMPDIR", ""):
        print("bootstrap invoke: --mode resume requires exported IMPLEMENT_TMPDIR", file=sys.stderr)
        return 1
    opts = BootstrapOptions(
        up_to_phase="coder" if args.mode == "initial" else "plan",
        caller_env=caller_env,
        issue_number=issue,
        forked_target=forked if forked in {"true", "false"} else "false",
        merge_requested=_bool_text(value=merge_requested),
        draft_requested=_bool_text(value=draft_requested),
        no_admin_fallback=_bool_text(value=no_admin_fallback),
        no_logs_commit=_bool_text(value=no_logs_commit),
        force_requested=force if force in {"true", "false"} else "false",
        self_review_requested=self_review if self_review in {"true", "false"} else "false",
        self_implement_requested=self_implement if self_implement in {"true", "false"} else "false",
        difficulty_override=difficulty_override if difficulty_override in {"TRIVIAL", "MODERATE", "HARD"} else "",
        upstream_repo=upstream,
        run_id=run_id,
        preflight_tmpdir=preflight,
        coder_opt=coder if coder in {"claude", "codex", "cursor"} else "",
        resume_plan_tail=args.mode == "resume",
        non_interactive=non_interactive,
    )
    restored = _restore_infra_state(opts=opts, infra_file=infra_file)
    if restored is None:
        print("bootstrap invoke: Rust infrastructure handoff is invalid", file=sys.stderr)
        return 2
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = _run_bootstrap_after_infra(restored)
    out = buf.getvalue()
    if rc == BOOTSTRAP_CONTRACT_FAILURE:
        kv = larch_io.parse_kv(out, skip_comments=True, cr_strip="rstrip")
        _invoke_error(step_failed=kv.get("STEP_FAILED", ""), out=out, implement_tmpdir=kv.get("IMPLEMENT_TMPDIR", ""))
        return 2
    if rc != 0:
        return rc
    tmpdir = larch_io.parse_kv(out, skip_comments=True, cr_strip="rstrip").get("IMPLEMENT_TMPDIR", "")
    if not tmpdir:
        print("bootstrap invoke: bootstrap success missing IMPLEMENT_TMPDIR", file=sys.stderr)
        return 1
    envelope = _filtered_envelope(out, resume=args.mode == "resume")
    routing_file = Path(tmpdir) / "bootstrap-routing.env"
    routing_trusted = _routing_file_trusted(routing_file)
    if args.mode == "resume" and routing_trusted:
        envelope = _preserve_resume_routing(envelope=envelope, routing_file=routing_file)
    data = _parse_env_lines(envelope)
    if args.mode == "resume":
        _restore_resume_coder(data=data, routing_file=routing_file, tmpdir=tmpdir)
    continue_tail_attempted = _continue_predicate(data)
    tail = _run_absorbed_continue_tail(
        data,
        opts=opts,
        non_interactive=_resolve_non_interactive(explicit=non_interactive, env=env),
    )
    if tail.contract_failure:
        _emit_kv(key="STEP_FAILED", value=tail.step_failed or "absorbed-continue-tail")
        _invoke_error(step_failed=tail.step_failed or "absorbed-continue-tail", out=tail.failure_detail, implement_tmpdir=tmpdir)
        return 2
    _merge_tail_routing_and_next(data, tail=tail, continue_tail_attempted=continue_tail_attempted)
    envelope = _envelope_text(data)
    try:
        _merge_write_ship_seed_input(
            tmpdir=tmpdir,
            values={
                "MERGE": _bool_text(value=opts.merge_requested),
                "DRAFT": _bool_text(value=opts.draft_requested),
                "FORKED_TARGET": _bool_text(value=opts.forked_target),
                "NO_ADMIN_FALLBACK": _bool_text(value=opts.no_admin_fallback),
                "NO_LOGS_COMMIT": _bool_text(value=opts.no_logs_commit),
                "DIFFICULTY_OVERRIDE": opts.difficulty_override,
                "DEFERRED": _bool_text(value=data.get("DEFERRED", "false")),
            },
            only_missing=args.mode == "resume",
        )
    except OSError as exc:
        print(f"bootstrap invoke: could not write ship-seed-input.env ({exc})", file=sys.stderr)
        if args.mode == "initial":
            return 2

    def _emit_envelope() -> None:
        sys.stdout.write(envelope)
        for line in tail.advisory_lines:
            sys.stdout.write(line + "\n")

    if routing_file.is_symlink():
        print("bootstrap invoke: refusing to overwrite symlinked bootstrap-routing.env (stdout envelope emitted)", file=sys.stderr)
        _emit_envelope()
        return 0
    if routing_file.exists() and not routing_file.is_file():
        print("bootstrap invoke: refusing to overwrite non-regular bootstrap-routing.env (stdout envelope emitted)", file=sys.stderr)
        _emit_envelope()
        return 0
    try:
        _atomic_text(path=routing_file, text=envelope)
    except OSError as exc:
        print(f"bootstrap invoke: could not write bootstrap-routing.env ({exc}); stdout envelope emitted", file=sys.stderr)
        _emit_envelope()
        return 0
    _emit_envelope()
    return 0


def _parse_env_lines(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text, allowed_keys=ROUTING_KEYS, key_pattern=_KEY_RE.pattern)
