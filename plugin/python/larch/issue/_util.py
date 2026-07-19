# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false, reportGeneralTypeIssues=false
# ruff: noqa: B905, FURB167, PERF401, PLC0415, PLR2004, PTH123, RET504, RUF005, RUF007, RUF100, S108, S607, SLF001, UP006, UP015, UP017, UP035, UP037
# pylint: skip-file
"""Shared utilities and data-loading helpers for analyze_issues."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Sequence, Tuple

BODY_CAP = 5 * 1024
PREFIX_RE = re.compile(r"^\s*(?:\[(?:DONE|OOS|IN PROGRESS|STALLED|URGENT)\]\s*)+", re.I)
FILE_RE = re.compile(r"\b[a-z][a-z0-9/_.-]+\.(?:sh|md)\b", re.I)
GROUND_TRUTH_VERDICT_DEFAULT_SINCE_DATE = "2026-06-26"
GROUND_TRUTH_VERDICT_DEFAULT_MIN_RUNS = 150
GROUND_TRUTH_VERDICT_MIN_LARCH_VERSION = "52.1.0"
GROUND_TRUTH_VERDICT_INCENTIVE_ISSUE_NUMBER = 5544

CATEGORY_RULES: Sequence[Tuple[str, Sequence[str]]] = (
    # WHY: explicit Documentation forms (`doc`/`docs`/`documentation`/`documented`/
    # `documenting`) keep `Docker`/`doctrine`/`documentary` from misclassifying as
    # Documentation, which a `doc\w*` stem would do.
    ("Documentation/contract drift", (
        "doc", "docs", "documentation", "documented", "documenting",
        "readme", "contract", "prompt", "instruction", "instructions",
        "schema", "schemas",
    )),
    # WHY: short Bug fix tokens stay strict (\bfix\b, \bbug\b, \berror\b) so they
    # cannot alias inside fixture/prefix/affix/error-prone (etc.). Plurals and
    # common inflections of fix/bug/error are enumerated explicitly so e.g. titles
    # like `Bugs in CI` or `Errors in parser` still classify as Bug fix.
    ("Bug fix", (
        "bug", "bugs",
        "fix", "fixes", "fixed", "fixing",
        "broken", "failure", "error", "errors", "crash", "regression",
    )),
    ("Test coverage", ("test", "tests", "testing", "coverage", "harness", "fixture", "fixtures", "assert")),
    ("Hardening/validation/security", ("security", "secret", "validate", "guard", "permission", "sanitize", "safe")),
    ("Refactor/code clarity", ("refactor", "cleanup", "clarity", "simplify", "rename")),
    ("Determinism/halt-prevention", ("determin", "halt", "timeout", "race", "idempotent", "retry")),
    ("New feature/new skill", ("feature", "skill", "scaffold", "add", "new")),
    ("Performance/token-cost reduction", ("performance", "token", "cost", "speed", "latency", "cache")),
)

# WHY: some CATEGORY_RULES entries are inflectional stems whose original
# substring-matching captured `doc`->"documentation", `determin`->"determinism",
# `validate`->"validation", `sanitize`->"sanitization", etc. Strict word-boundary
# matching (\bKW\b) on those keywords would regress those classifications. Mark
# stems explicitly so the compiled per-category pattern accepts trailing word
# characters (\bKW\w*) for them, while keeping short exact words like fix/add/new
# strict (\bKW\b) so they cannot alias inside fixture/prefix/affix/added/newer.
_STEM_KEYWORDS = frozenset({
    "determin",
    "validate", "sanitize", "simplify",
    "permission", "secret", "feature",
    "scaffold", "failure", "regression",
    "assert", "crash",
    "refactor", "rename",
})


def _keyword_pattern(keyword: str) -> str:
    if keyword in _STEM_KEYWORDS:
        # Trim trailing e/y so `validate`->`validat\w*`, `simplify`->`simplif\w*`.
        stem = re.sub(r"[ey]$", "", keyword)
        return re.escape(stem) + r"\w*"
    return re.escape(keyword) + r"\b"


CATEGORY_PATTERNS: Sequence[Tuple[str, "re.Pattern[str]"]] = tuple(
    (
        category,
        re.compile(
            r"\b(?:" + "|".join(_keyword_pattern(k) for k in keywords) + r")",
            re.I,
        ),
    )
    for category, keywords in CATEGORY_RULES
)

# WHY: load_issues fails the load when more than 5% of input list elements
# are unusable: non-dict elements, dicts with missing/non-numeric `number`,
# or dicts whose parsed `number` collides with a previously-retained row
# (duplicate-number skip — first-occurrence wins). --lenient suppresses only
# the threshold abort; per-element stderr WARN lines are emitted regardless.
LOAD_ISSUES_SKIP_THRESHOLD = 0.05
LOAD_ISSUES_REPR_CAP = 60
_DIGIT_RE = re.compile(r"[0-9]+")

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def issue_text( *,issue: Mapping[str, Any], cap: int = BODY_CAP) -> str:
    return f"{issue.get('title') or ''}\n{(issue.get('body') or '')[:cap]}"


def strip_prefixes(title: str) -> str:
    return PREFIX_RE.sub("", title or "").strip()


def _parse_issue_number(value: Any) -> tuple[int | None, str | None]:
    if value is None:
        return None, "missing"
    if isinstance(value, bool):
        return None, "non-numeric"
    if isinstance(value, int):
        return (value, None) if value > 0 else (None, "non-numeric")
    if isinstance(value, str) and _DIGIT_RE.fullmatch(value):
        try:
            parsed = int(value)
        except (ValueError, OverflowError):
            return None, "non-numeric"
        return (parsed, None) if parsed > 0 else (None, "non-numeric")
    return None, "non-numeric"


def load_issues(path: str, *, lenient: bool = False) -> List[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except Exception as exc:
        raise SystemExit(f"ERROR=Unable to parse issue JSON dump at {path}: {exc}") from exc
    if not isinstance(raw, list):
        raise SystemExit(f"ERROR=Issue JSON dump at {path} is not a list")
    issues: List[Dict[str, Any]] = []
    skipped = 0
    number_to_index: dict[int, int] = {}
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            skipped += 1
            preview = repr(item)
            if len(preview) > LOAD_ISSUES_REPR_CAP:
                preview = preview[: LOAD_ISSUES_REPR_CAP - 3] + "..."
            print(
                f"WARN load_issues: skipping non-dict element at index {index}: {preview}",
                file=sys.stderr,
            )
            continue
        issue = dict(item)
        parsed, reason = _parse_issue_number(issue.get("number"))
        if parsed is None:
            skipped += 1
            preview = repr(issue.get("number"))
            if len(preview) > LOAD_ISSUES_REPR_CAP:
                preview = preview[: LOAD_ISSUES_REPR_CAP - 3] + "..."
            print(
                f"WARN load_issues: skipping issue with {reason} number at index {index}: {preview}",
                file=sys.stderr,
            )
            continue
        if parsed in number_to_index:
            skipped += 1
            prior_index = number_to_index[parsed]
            print(
                f"WARN load_issues: skipping duplicate parsed number {parsed} at index {index} "
                f"(first occurrence at index {prior_index} retained)",
                file=sys.stderr,
            )
            continue
        number_to_index[parsed] = index
        issue["number"] = parsed
        issue["body"] = (issue.get("body") or "")[:BODY_CAP]
        issues.append(issue)
    total = len(raw)
    if not lenient and total > 0 and skipped / total > LOAD_ISSUES_SKIP_THRESHOLD:
        raise SystemExit(
            "ERROR=load_issues skipped "
            f"{skipped}/{total} non-dict, malformed-number, or duplicate-number elements "
            f"({skipped / total * 100:.1f}% > {LOAD_ISSUES_SKIP_THRESHOLD * 100:.0f}% threshold) "
            f"in {path}; pass --lenient to suppress this check"
        )
    return issues


def issue_number(issue: Mapping[str, Any]) -> int:
    """Return the numeric issue number.

    Precondition: issue was produced by load_issues, which guarantees a
    present, positive integer number field.
    """
    return int(issue["number"])


def pr_ref_id(ref: Mapping[str, Any]) -> str:
    for key in ("url", "number", "title"):
        value = ref.get(key)
        if value:
            return str(value)
    return json.dumps(ref, sort_keys=True)
