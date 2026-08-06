"""Python-owned lint checks for the stall-recovery contract."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import sys

from larch.core import config
from larch.state._tokens import _REPO_ROOT, _safe_bail_reason_value, _safe_token, emit

_CODE_ALLOWLIST_LINES = """chat-print\treport_kind\tREPORT_KIND\tenum
chat-print\tfailing_step\tSTALL_STEP\tenum
chat-print\tfailing_phase\tPHASE\tenum
chat-print\tfailure_class\tFAILURE_CLASS\tenum
chat-print\tbail_reason\tBAIL_REASON\texpanded-bail-token-union
chat-print\texit_code\tEXIT_CODE\tinteger-or-unknown
chat-print\tdispatcher\tDISPATCHER\tenum
chat-print\tmatched_classifier_pattern\tMATCHED_CLASSIFIER_PATTERN\tenum
chat-print\tlarch_version\tlarch-version\ttoken
chat-print\trun_id\tRUN_ID\ttoken-or-unknown
chat-print\tattempt_table\tattempts-file\tallowlisted-attempt-fields
chat-print\tescalation_site\tescalation-ledger\tenum
chat-print\tescalation_trigger\tescalation-ledger\tenum
chat-print\tfallback_escalation_marker\tescalation-fallback\tpresent-marker
chat-print\trecord_failure_marker\trecord-failure-marker\tpresent-marker
chat-print\trecord_escalation_tool_failure\texecution-issues\tpresent-marker
chat-print\tbounded_root_cause\tbounded-root-cause-file\tvalidated-larch-internal-prose
""".strip().splitlines()

_ALLOWLIST_TABLE_COLUMNS = 4
_RETRY_POLICY_TABLE_COLUMNS = 3


def _retry_policy_lines() -> list[str]:
    classes = (
        "transient-infra",
        "test-failure",
        "lint-failure",
        "dispatch-failure",
        "protected-path",
        "submodule-restricted",
        "ci-fix-exhausted",
        "same-cause-repeat",
        "contract-failure",
        "recoverable",
        "unrecoverable",
    )
    return [
        f"{failure_class}\t{max_attempts}\t{delay}"
        for failure_class in classes
        for max_attempts, delay in [config.RETRY_POLICY_CAPS[failure_class]]
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


def lint_subcommand(rest: list[str]) -> int:
    _ = rest
    tsv_path = _REPO_ROOT / "python" / "stall-recovery-report-allowlists.tsv"
    if not tsv_path.is_file():
        print(f"stall-recovery: missing allowlist TSV: {tsv_path}", file=sys.stderr)
        return 1
    tsv_lines = [line for line in tsv_path.read_text(encoding="utf-8").splitlines()[1:] if line.strip()]
    if sorted(tsv_lines) != sorted(_CODE_ALLOWLIST_LINES):
        print("stall-recovery: allowlist drift between TSV and code", file=sys.stderr)
        return 1
    doc_lines = sorted(_doc_allowlist_lines())
    if doc_lines and sorted(tsv_lines) != doc_lines:
        print("stall-recovery: allowlist drift between TSV and doc", file=sys.stderr)
        return 1
    retry_doc = sorted(_doc_retry_policy_lines())
    retry_code = sorted(_retry_policy_lines())
    if retry_doc and retry_doc != retry_code:
        print("stall-recovery: retry-policy drift between code and doc", file=sys.stderr)
        return 1
    compound_safe = _safe_token(
        kind="trigger",
        value="ci-local-unfixable:job_1,job-2",
        generic=False,
    )
    compound_bad = _safe_token(
        kind="trigger",
        value="ci-local-unfixable:../../secret",
        generic=False,
    )
    if not compound_safe or compound_bad:
        print("stall-recovery: ci-local-unfixable compound grammar drift", file=sys.stderr)
        return 1
    for token in config.STALL_RECOVERY_BAIL_REASON_TOKENS:
        if not _safe_bail_reason_value(token, generic=False):
            print(f"stall-recovery: runtime bail token not render-safe: {token}", file=sys.stderr)
            return 1
    emit(key="LINT_OK", value="true")
    return 0


def lint_main(argv: list[str] | None = None) -> int:
    return lint_subcommand(list(argv or []))
