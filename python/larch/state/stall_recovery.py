"""Stall recovery report helpers shared by /implement and /design."""

# pyright: reportUnusedCallResult=false
# pyright: reportPrivateUsage=false
# pyright: reportUnusedImport=false

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from larch.core import config

# ---------------------------------------------------------------------------
# Imports from submodules
# ---------------------------------------------------------------------------
from larch.state._tokens import (
    _REPO_ROOT,
    _safe_bail_reason_value,
    _safe_token,
    emit,
)
from larch.state._detail_log import MAX_OPTIONAL_EVIDENCE_BYTES  # noqa: F401  # pylint: disable=unused-import
from larch.state._escalation import _validate_artifact_prefix, record_escalation_checked
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
_TEST_COMPAT_SUBPROCESS = subprocess  # Tests patch the historical module-level process seam.

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

_ALLOWLIST_TABLE_COLUMNS = 4
_RETRY_POLICY_TABLE_COLUMNS = 3

# ---------------------------------------------------------------------------
# Functions that remain in this module
# ---------------------------------------------------------------------------


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


def _retry_policy_lines() -> list[str]:
    classes = (
        "transient-infra", "test-failure", "lint-failure", "dispatch-failure", "protected-path",
        "submodule-restricted", "ci-fix-exhausted", "same-cause-repeat", "contract-failure", "recoverable",
        "unrecoverable",
    )
    return [
        f"{klass}\t{max_attempts}\t{delay}"
        for klass in classes
        for max_attempts, delay in [config.RETRY_POLICY_CAPS[klass]]
    ]


def _doc_allowlist_lines() -> list[str]:
    contract = _REPO_ROOT / "python" / "stall-recovery-report.md"
    if not contract.is_file():
        return []
    lines: list[str] = []
    in_block = False
    for raw in contract.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.strip() == "<!-- stall-recovery-allowlist:begin -->":
            in_block = True
            continue
        if raw.strip() == "<!-- stall-recovery-allowlist:end -->":
            break
        if not in_block or "|" not in raw or raw.lstrip().startswith("surface"):
            continue
        parts = [part.strip() for part in raw.strip().strip("|").split("|")]
        if len(parts) >= _ALLOWLIST_TABLE_COLUMNS and parts[0] not in {"---", "surface"}:
            lines.append("\t".join(parts[:_ALLOWLIST_TABLE_COLUMNS]))
    return lines


def _doc_retry_policy_lines() -> list[str]:
    contract = _REPO_ROOT / "python" / "stall-recovery-report.md"
    if not contract.is_file():
        return []
    lines: list[str] = []
    in_table = False
    for raw in contract.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.strip() == "| failure_class | attempts | delay |":
            in_table = True
            continue
        if in_table and raw.strip().startswith("|---"):
            continue
        if in_table and raw.strip().startswith("| "):
            parts = [part.strip().strip("`") for part in raw.strip().strip("|").split("|")]
            if len(parts) >= _RETRY_POLICY_TABLE_COLUMNS:
                lines.append(f"{parts[0]}\t{parts[1]}\t{parts[2]}")
            continue
        if in_table:
            break
    return lines


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
        return record_escalation_checked(ns)
    if sub == "normalize-file-failure-report-env":
        p.add_argument("--file-failure-report-env", required=True)
        ns, _ = p.parse_known_args(sub_argv)
        return normalize_file_failure_report_env(ns)
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


def normalize_file_failure_report_env_main(argv: list[str] | None = None) -> int:
    return main(["normalize-file-failure-report-env", *(argv or [])])


def normalize_issue_env_main(argv: list[str] | None = None) -> int:
    return main(["normalize-issue-env", *(argv or [])])


def record_attempt_main(argv: list[str] | None = None) -> int:
    return main(["record-attempt", *(argv or [])])


def retry_policy_main(argv: list[str] | None = None) -> int:
    return main(["retry-policy", *(argv or [])])


def lint_main(argv: list[str] | None = None) -> int:
    return main(["lint", *(argv or [])])
