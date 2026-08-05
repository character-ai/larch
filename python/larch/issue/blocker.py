# pyright: reportUnusedCallResult=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false
"""Prose blocker parsing for `/combine-issues`.

Issue #8059 moved blocker discovery to the Rust owner: `blocker all-open` and
its native-dependency and issue-state reads live in
`crates/larch-cli/src/blocker_commands.rs`. `parse_prose_blockers` survives here
because `larch.issue.combine_issues` still scans issue prose in process.
"""

from __future__ import annotations

import re

_KEYWORD_RE = re.compile(
    r"(?:Depends on|Blocked by|Blocked on|Requires|Needs)[ \t]+#([0-9]+)(?:[^0-9]|$)",
    re.IGNORECASE,
)
_CODE_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
_MARKDOWN_PREFIX_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?")
_EXAMPLE_PREFIX_RE = re.compile(r"^(?:example|examples|e\.g\.|eg\.|for example|sample)\b", re.IGNORECASE)
_NEGATION_RE = re.compile(r"\b(?:does\s+not|do\s+not|did\s+not|not|no|never|without)\b", re.IGNORECASE)
_NEGATION_SCOPE_BOUNDARY_RE = re.compile(r"(?:[.;:!?]|\b(?:and|but|however|then|yet)\b)", re.IGNORECASE)


def _has_scoped_negation(prefix: str) -> bool:
    clause = _NEGATION_SCOPE_BOUNDARY_RE.split(prefix)[-1]
    return _NEGATION_RE.search(clause) is not None


def parse_prose_blockers(text: str) -> list[int]:
    """Extract blocker issue numbers from one prose document, failing open."""
    try:
        refs: set[int] = set()
        in_fence = False
        for raw_line in (text or "").splitlines():
            if _CODE_FENCE_RE.match(raw_line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            line = re.sub(r"`[^`\n]*`", "", raw_line).replace("*", "").replace("_", "")
            line = _MARKDOWN_PREFIX_RE.sub("", line).strip()
            if not line or line.startswith("<!--") or _EXAMPLE_PREFIX_RE.match(line):
                continue
            for match in _KEYWORD_RE.finditer(line):
                prefix = line[: match.start()]
                if _has_scoped_negation(prefix):
                    continue
                refs.add(int(match.group(1)))
        return sorted(refs)
    except Exception:
        return []
