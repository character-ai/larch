"""Stall recovery report helpers shared by /implement and /design."""

# pyright: reportUnusedCallResult=false
# pyright: reportPrivateUsage=false
# pyright: reportUnusedImport=false

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from larch.core import config

# ---------------------------------------------------------------------------
# Imports from submodules
# ---------------------------------------------------------------------------
from larch.state._tokens import (
    _REPO_ROOT,
    _safe_bail_reason_value,
    _safe_token,
    _truthy,
    emit,
    read_kv,
)
from larch.state._detail_log import MAX_OPTIONAL_EVIDENCE_BYTES  # noqa: F401  # pylint: disable=unused-import
from larch.state._escalation import _validate_artifact_prefix, record_escalation
from larch.state._validate import validate_token, validate_terminal_state
from larch.state._classify import (
    classify,
    init_attempts,
    record_attempt,
    retry_policy,
)
from larch.state._normalize import (
    normalize_file_failure_report_env,
    normalize_issue_env,
    normalize_outcome,
)
from larch.state._normalize import normalized_outcome_values  # noqa: F401  # pylint: disable=unused-import
from larch.state._corpus import populate_sensitive_corpus, validate_tier_b_public_file
from larch.state._corpus import _sensitive_value_is_allowlisted  # noqa: F401  # pylint: disable=unused-import
from larch.state._corpus import build_sensitive_corpus_from_evidence  # noqa: F401  # pylint: disable=unused-import
from larch.state._state_mgmt import clear_stall, seed_terminal_state
from larch.state._report import (
    _doc_allowlist_lines,
    _doc_retry_policy_lines,
    _retry_policy_lines,
    chat_print,
    compose_report,
    dedup_tier_a_report,
)
from larch.state._report import _redact_text  # noqa: F401  # pylint: disable=unused-import

# ---------------------------------------------------------------------------
# Module-level constants (CLI-specific)
# ---------------------------------------------------------------------------

_CODE_ALLOWLIST_LINES = """chat-print	report_kind	REPORT_KIND	enum
chat-print	failing_step	STALL_STEP	enum
chat-print	failing_phase	PHASE	enum
chat-print	failure_class	FAILURE_CLASS	enum
chat-print	bail_reason	BAIL_REASON	expanded-bail-token-union
chat-print	exit_code	EXIT_CODE	integer-or-unknown
chat-print	dispatcher	DISPATCHER	enum
chat-print	matched_classifier_pattern	MATCHED_CLASSIFIER_PATTERN	enum
chat-print	larch_version	larch-version	token
chat-print	run_id	RUN_ID	token-or-unknown
chat-print	attempt_table	attempts-file	allowlisted-attempt-fields
chat-print	escalation_site	escalation-ledger	enum
chat-print	escalation_trigger	escalation-ledger	enum
chat-print	fallback_escalation_marker	escalation-fallback	present-marker
chat-print	record_failure_marker	record-failure-marker	present-marker
chat-print	record_escalation_tool_failure	execution-issues	present-marker
chat-print	bounded_root_cause	bounded-root-cause-file	validated-larch-internal-prose
""".strip().splitlines()

_GLOBAL_STALL_FLAGS = frozenset({
    "--profile",
    "--artifact-prefix",
    "--implement-tmpdir",
    "--primary-state-file",
    "--finalize-state-file",
    "--session-env-file",
})

# ---------------------------------------------------------------------------
# Functions that remain in this module
# ---------------------------------------------------------------------------


def is_larch_dev_clone(args: argparse.Namespace) -> int:
    tmpdir = Path(args.implement_tmpdir)
    forked = read_kv(path=tmpdir / "ship-pr-state.sh", key="FORKED_TARGET") or read_kv(path=tmpdir / "session-env.sh", key="FORKED_TARGET")
    if forked and _truthy(forked):
        emit(key="LARCH_DEV_CLONE", value="false")
        return 0
    root = getattr(args, "working_tree_root", "") or ""
    if not root:
        completed = subprocess.run(["/usr/bin/git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False)
        root = completed.stdout.strip() if completed.returncode == 0 else ""
    dev_clone = bool(root) and (Path(root) / "skills" / "implement" / "SKILL.md").is_file()
    emit(key="LARCH_DEV_CLONE", value="true" if dev_clone else "false")
    return 0


def lint_subcommand(rest: list[str]) -> int:
    _ = rest
    tsv_path = _REPO_ROOT / "python" / "stall-recovery-report-allowlists.tsv"
    if not tsv_path.is_file():
        print(f"stall-recovery: missing allowlist TSV: {tsv_path}", file=sys.stderr)
        return 1
    tsv_lines = [line for line in tsv_path.read_text(encoding="utf-8").splitlines()[1:] if line.strip()]
    code_lines = sorted(_CODE_ALLOWLIST_LINES)
    doc_lines = sorted(_doc_allowlist_lines())
    if sorted(tsv_lines) != code_lines:
        print("stall-recovery: allowlist drift between TSV and code", file=sys.stderr)
        return 1
    if doc_lines and sorted(tsv_lines) != doc_lines:
        print("stall-recovery: allowlist drift between TSV and doc", file=sys.stderr)
        return 1
    retry_doc = sorted(_doc_retry_policy_lines())
    retry_code = sorted(_retry_policy_lines())
    if retry_doc and retry_doc != retry_code:
        print("stall-recovery: retry-policy drift between code and doc", file=sys.stderr)
        return 1
    compound_safe = _safe_token(kind="trigger", value="ci-local-unfixable:job_1,job-2", generic=False)
    compound_bad = _safe_token(kind="trigger", value="ci-local-unfixable:../../secret", generic=False)
    if not compound_safe or compound_bad:
        print("stall-recovery: ci-local-unfixable compound grammar drift", file=sys.stderr)
        return 1
    for token in config.STALL_RECOVERY_BAIL_REASON_TOKENS:
        if not _safe_bail_reason_value(token, generic=False):
            print(f"stall-recovery: runtime bail token not render-safe: {token}", file=sys.stderr)
            return 1
    emit(key="LINT_OK", value="true")
    return 0


def _parse_leading_global_flags(argv: list[str]) -> tuple[list[str], dict[str, str] | None]:
    globals_dict: dict[str, str] = {}
    idx = 0
    while idx < len(argv) and argv[idx] in _GLOBAL_STALL_FLAGS:
        flag = argv[idx]
        if idx + 1 >= len(argv):
            print(f"stall-recovery: {flag} requires a value", file=sys.stderr)
            return argv, None
        key = flag[2:].replace("-", "_")
        globals_dict[key] = argv[idx + 1]
        idx += 2
    prefix = globals_dict.get("artifact_prefix", "")
    if prefix and not _validate_artifact_prefix(prefix):
        print("stall-recovery: --artifact-prefix must be a simple dash token", file=sys.stderr)
        return argv[idx:], None
    return argv[idx:], globals_dict


def _global_default(*, globals_dict: dict[str, str] | None, key: str, fallback: str = "") -> str:
    if globals_dict and key in globals_dict:
        return globals_dict[key]
    return fallback


def _add_implement_tmpdir_arg(*, p: argparse.ArgumentParser, globals_dict: dict[str, str] | None) -> None:
    p.add_argument(
        "--implement-tmpdir",
        default=_global_default(globals_dict=globals_dict, key="implement_tmpdir", fallback=os.environ.get("IMPLEMENT_TMPDIR", ".")),
    )


def _add_compose_report_args(*, p: argparse.ArgumentParser, globals_dict: dict[str, str] | None) -> None:
    p.add_argument("--report-kind", default="terminal-failure")
    p.add_argument("--surface", default="chat-print")
    p.add_argument("--attempts-file", default="")
    p.add_argument("--classification-file", default="")
    p.add_argument("--escalation-ledger-file", default="")
    p.add_argument("--escalation-fallback-file", default="")
    p.add_argument("--record-failure-marker", default="")
    p.add_argument("--root-cause-file", default="")
    p.add_argument("--bounded-root-cause-file", default="")
    p.add_argument("--title-file", default="")
    p.add_argument("--sensitive-corpus-file", default="")
    p.add_argument("--output-file")
    p.add_argument("--profile", default=_global_default(globals_dict=globals_dict, key="profile", fallback="implement"))
    p.add_argument("--artifact-prefix", default=_global_default(globals_dict=globals_dict, key="artifact_prefix", fallback=""))
    p.add_argument("--primary-state-file", default=_global_default(globals_dict=globals_dict, key="primary_state_file", fallback=""))
    p.add_argument("--finalize-state-file", default=_global_default(globals_dict=globals_dict, key="finalize_state_file", fallback=""))
    p.add_argument("--session-env-file", default=_global_default(globals_dict=globals_dict, key="session_env_file", fallback=""))


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    rest, globals_dict = _parse_leading_global_flags(argv)
    if globals_dict is None:
        return 2
    if not rest:
        print("stall-recovery: missing subcommand", file=sys.stderr)
        return 2
    sub, sub_argv = rest[0], rest[1:]
    p = argparse.ArgumentParser(prog=f"cli.py stall-recovery {sub}")
    _add_implement_tmpdir_arg(p=p, globals_dict=globals_dict)
    if sub == "classify":
        p.add_argument("--failure-detail-log")
        p.add_argument("--attempts-file")
        p.add_argument("--bail-reason", default="")
        p.add_argument("--in-memory-stall-tracking")
        p.add_argument("--primary-state-file", default=_global_default(globals_dict=globals_dict, key="primary_state_file", fallback=""))
        p.add_argument("--finalize-state-file", default=_global_default(globals_dict=globals_dict, key="finalize_state_file", fallback=""))
        p.add_argument("--session-env-file", default=_global_default(globals_dict=globals_dict, key="session_env_file", fallback=""))
        p.add_argument("--artifact-prefix", default=_global_default(globals_dict=globals_dict, key="artifact_prefix", fallback=""))
        p.add_argument("--profile", default=_global_default(globals_dict=globals_dict, key="profile", fallback="implement"))
        p.add_argument("--stall-step", default="")
        p.add_argument("--phase", default="")
        p.add_argument("--exit-code", default="")
        p.add_argument("--dispatcher", default="")
        ns, _ = p.parse_known_args(sub_argv)
        return classify(ns)
    if sub == "init-attempts":
        p.add_argument("--attempts-file")
        ns, _ = p.parse_known_args(sub_argv)
        return init_attempts(ns)
    if sub == "record-attempt":
        p.add_argument("--attempts-file")
        p.add_argument("--class", dest="failure_class", required=True)
        p.add_argument("--signature", required=True)
        p.add_argument("--resume-hint", default="none")
        p.add_argument("--outcome", default="failed")
        ns, _ = p.parse_known_args(sub_argv)
        return record_attempt(ns)
    if sub == "retry-policy":
        p.add_argument("--class", dest="failure_class", required=True)
        ns, _ = p.parse_known_args(sub_argv)
        return retry_policy(ns)
    if sub == "normalize-outcome":
        p.add_argument("--in-memory-stall-tracking", default="")
        ns, _ = p.parse_known_args(sub_argv)
        return normalize_outcome(ns)
    if sub == "normalize-issue-env":
        p.add_argument("--issue-stdout-file", required=True)
        p.add_argument("--issue-exit-code")
        ns, _ = p.parse_known_args(sub_argv)
        return normalize_issue_env(ns)
    if sub == "record-escalation":
        p.add_argument("--site", required=True)
        p.add_argument("--trigger", required=True)
        p.add_argument("--step", required=True)
        p.add_argument("--phase", required=True)
        p.add_argument("--dispatcher", required=True)
        p.add_argument("--exit-code", default="unknown")
        p.add_argument("--failure-detail-log", default="")
        p.add_argument("--artifact-prefix", default=_global_default(globals_dict=globals_dict, key="artifact_prefix", fallback=""))
        p.add_argument("--profile", default=_global_default(globals_dict=globals_dict, key="profile", fallback="implement"))
        ns, _ = p.parse_known_args(sub_argv)
        return record_escalation(ns)
    if sub == "dedup-tier-a-report":
        p.add_argument("--body-file", default="")
        p.add_argument("--attempts-file", default="")
        p.add_argument("--escalation-ledger-file", default="")
        p.add_argument("--root-cause-file", default="")
        p.add_argument("--artifact-prefix", default=_global_default(globals_dict=globals_dict, key="artifact_prefix", fallback=""))
        ns, _ = p.parse_known_args(sub_argv)
        return dedup_tier_a_report(ns)
    if sub == "compose-report":
        _add_compose_report_args(p=p, globals_dict=globals_dict)
        ns, _ = p.parse_known_args(sub_argv)
        return compose_report(ns)
    if sub == "validate-token":
        p.add_argument("--token", default="")
        p.add_argument("--value", default="")
        p.add_argument("--token-kind", default="")
        p.add_argument("--profile", default=_global_default(globals_dict=globals_dict, key="profile", fallback="implement"))
        p.add_argument("--artifact-prefix", default=_global_default(globals_dict=globals_dict, key="artifact_prefix", fallback=""))
        ns, _ = p.parse_known_args(sub_argv)
        ns.token = ns.token or ns.value
        return validate_token(ns)
    if sub == "validate-terminal-state":
        p.add_argument("--primary-state-file", default=_global_default(globals_dict=globals_dict, key="primary_state_file", fallback=""))
        p.add_argument("--profile", default=_global_default(globals_dict=globals_dict, key="profile", fallback="implement"))
        p.add_argument("--artifact-prefix", default=_global_default(globals_dict=globals_dict, key="artifact_prefix", fallback=""))
        ns, _ = p.parse_known_args(sub_argv)
        return validate_terminal_state(ns)
    if sub == "validate-tier-b-public-file":
        p.add_argument("--public-file", required=True)
        p.add_argument("--tmpdir")
        p.add_argument("--sensitive-corpus-file", default="")
        p.add_argument("--profile", default=_global_default(globals_dict=globals_dict, key="profile", fallback="implement"))
        p.add_argument("--artifact-prefix", default=_global_default(globals_dict=globals_dict, key="artifact_prefix", fallback=""))
        ns, _ = p.parse_known_args(sub_argv)
        return validate_tier_b_public_file(ns)
    if sub == "clear-stall":
        ns, _ = p.parse_known_args(sub_argv)
        return clear_stall(ns)
    if sub == "seed-terminal-state":
        p.add_argument("--stall-step")
        p.add_argument("--phase")
        ns, _ = p.parse_known_args(sub_argv)
        return seed_terminal_state(ns)
    if sub == "chat-print":
        _add_compose_report_args(p=p, globals_dict=globals_dict)
        ns, _ = p.parse_known_args(sub_argv)
        return chat_print(ns)
    if sub == "is-larch-dev-clone":
        p.add_argument("--working-tree-root", default="")
        ns, _ = p.parse_known_args(sub_argv)
        return is_larch_dev_clone(ns)
    if sub == "normalize-file-failure-report-env":
        p.add_argument("--file-failure-report-env", required=True)
        ns, _ = p.parse_known_args(sub_argv)
        return normalize_file_failure_report_env(ns)
    if sub == "populate-sensitive-corpus":
        p.add_argument("--sensitive-corpus-file", default="")
        p.add_argument("--classification-file", default="")
        p.add_argument("--attempts-file", default="")
        p.add_argument("--escalation-ledger-file", default="")
        p.add_argument("--escalation-fallback-file", default="")
        p.add_argument("--record-failure-marker", default="")
        p.add_argument("--artifact-prefix", default=_global_default(globals_dict=globals_dict, key="artifact_prefix", fallback=""))
        ns, _ = p.parse_known_args(sub_argv)
        return populate_sensitive_corpus(ns)
    if sub == "lint":
        return lint_subcommand(sub_argv)
    print(f"stall-recovery: unknown subcommand: {sub}", file=sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# Entry points (called via larch/cli.py dispatch table)
# ---------------------------------------------------------------------------


def init_attempts_main(argv: list[str] | None = None) -> int:
    return main(["init-attempts", *(argv or [])])


def classify_main(argv: list[str] | None = None) -> int:
    return main(["classify", *(argv or [])])


def record_escalation_main(argv: list[str] | None = None) -> int:
    return main(["record-escalation", *(argv or [])])


def normalize_outcome_main(argv: list[str] | None = None) -> int:
    return main(["normalize-outcome", *(argv or [])])


def compose_report_main(argv: list[str] | None = None) -> int:
    return main(["compose-report", *(argv or [])])


def dedup_tier_a_report_main(argv: list[str] | None = None) -> int:
    return main(["dedup-tier-a-report", *(argv or [])])


def normalize_file_failure_report_env_main(argv: list[str] | None = None) -> int:
    return main(["normalize-file-failure-report-env", *(argv or [])])


def normalize_issue_env_main(argv: list[str] | None = None) -> int:
    return main(["normalize-issue-env", *(argv or [])])


def validate_token_main(argv: list[str] | None = None) -> int:
    return main(["validate-token", *(argv or [])])


def validate_terminal_state_main(argv: list[str] | None = None) -> int:
    return main(["validate-terminal-state", *(argv or [])])


def validate_tier_b_public_file_main(argv: list[str] | None = None) -> int:
    return main(["validate-tier-b-public-file", *(argv or [])])


def populate_sensitive_corpus_main(argv: list[str] | None = None) -> int:
    return main(["populate-sensitive-corpus", *(argv or [])])


def chat_print_main(argv: list[str] | None = None) -> int:
    return main(["chat-print", *(argv or [])])


def record_attempt_main(argv: list[str] | None = None) -> int:
    return main(["record-attempt", *(argv or [])])


def retry_policy_main(argv: list[str] | None = None) -> int:
    return main(["retry-policy", *(argv or [])])


def is_larch_dev_clone_main(argv: list[str] | None = None) -> int:
    return main(["is-larch-dev-clone", *(argv or [])])


def clear_stall_main(argv: list[str] | None = None) -> int:
    return main(["clear-stall", *(argv or [])])


def seed_terminal_state_main(argv: list[str] | None = None) -> int:
    return main(["seed-terminal-state", *(argv or [])])


def lint_main(argv: list[str] | None = None) -> int:
    return main(["lint", *(argv or [])])
