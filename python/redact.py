"""Secret and tmpdir-path redaction (parity with scripts/redact-*.sh)."""

from __future__ import annotations

import re

import config

# Line-local secret families (byte-for-byte ports of redact-secrets.sh sed -E)
_SK_RE = re.compile(r"sk-(ant-)?[A-Za-z0-9_-]{20,}")
_GH_RE = re.compile(
    r"(ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}",
)
_AKIA_RE = re.compile(r"AKIA[0-9A-Z]{16}")
_JWT_RE = re.compile(
    r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
)
_PEM_ANCHOR = r"^[\t \v\f\r>]*"
_PEM_BEGIN_RE = re.compile(
    rf"{_PEM_ANCHOR}-----BEGIN [A-Z ]*PRIVATE KEY-----",
)
_PEM_END_RE = re.compile(
    rf"{_PEM_ANCHOR}-----END [A-Z ]*PRIVATE KEY-----",
)
_UNTERMINATED_MARKER = (
    "[content truncated — unterminated PEM block; tail of body dropped for safety]"
)

_SESSION_SUFFIX = (
    r"(claude|larch)-(implement|design|review|research|fix-issue|issue)-[A-Za-z0-9_.-]+"
)
_BOUNDARY = r"[^A-Za-z0-9_./-]"
_NOT_PATH = r"[^/\s\"\\]"
_USER_SEG = r"[^/\s\"\\]+"
_REPO_SLASH = r"[^/\s\"\\]+"
_REPO_COMMA = r"[^/\s\"\\,]+"
_REPO_SEMI = r"[^/\s\"\\;]+"
_REPO_COLON = r"[^/\s\"\\:]+"
_REPO_BRACE = r"[^/\s\"\\\"}]+"
_REPO_QUOTE_COMMA = r"[^/\s\"\\\"},]+"
_REPO_QUOTE_END = r"[^/\s\"\\\"]+"
_REPO_EOL = r"[^/\s\"\\]+"

_ML = re.MULTILINE

_TMPDIR_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            rf"(^|{_BOUNDARY})/(private/)?tmp/+({_NOT_PATH}+/)*{_SESSION_SUFFIX}",
            _ML,
        ),
        rf"\1{config.REDACTED_TMPDIR}",
    ),
    (
        re.compile(
            rf"(^|{_BOUNDARY})/(private/)?var/folders/[^/]+/[^/]+/T/"
            rf"({_NOT_PATH}+/)*{_SESSION_SUFFIX}",
            _ML,
        ),
        rf"\1{config.REDACTED_TMPDIR}",
    ),
    (
        re.compile(
            rf"(^|{_BOUNDARY})/({_NOT_PATH}+/)*larch/sessions/{_SESSION_SUFFIX}",
            _ML,
        ),
        rf"\1{config.REDACTED_TMPDIR}",
    ),
    (
        re.compile(
            rf"(\\n)/({_NOT_PATH}+/)*larch/sessions/{_SESSION_SUFFIX}",
            _ML,
        ),
        rf"\1{config.REDACTED_TMPDIR}",
    ),
    (
        re.compile(
            rf"(\\n)/(private/)?tmp/+({_NOT_PATH}+/)*{_SESSION_SUFFIX}",
            _ML,
        ),
        rf"\1{config.REDACTED_TMPDIR}",
    ),
    (
        re.compile(
            rf"(\\n)/(private/)?var/folders/[^/]+/[^/]+/T/"
            rf"({_NOT_PATH}+/)*{_SESSION_SUFFIX}",
            _ML,
        ),
        rf"\1{config.REDACTED_TMPDIR}",
    ),
)

_OPERATOR_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            rf"(^|{_BOUNDARY})(/Users|/home)/({_USER_SEG})/({_REPO_SLASH})/",
            _ML,
        ),
        rf"\1{config.REDACTED_OPERATOR_REPO}/",
    ),
    (
        re.compile(
            rf"(^|{_BOUNDARY})(/Users|/home)/({_USER_SEG})/({_REPO_COMMA}),",
            _ML,
        ),
        rf"\1{config.REDACTED_OPERATOR_REPO},",
    ),
    (
        re.compile(
            rf"(^|{_BOUNDARY})(/Users|/home)/({_USER_SEG})/({_REPO_SEMI});",
            _ML,
        ),
        rf"\1{config.REDACTED_OPERATOR_REPO};",
    ),
    (
        re.compile(
            rf"(^|{_BOUNDARY})(/Users|/home)/({_USER_SEG})/({_REPO_COLON}):",
            _ML,
        ),
        rf"\1{config.REDACTED_OPERATOR_REPO}:",
    ),
    (
        re.compile(
            rf"(^|{_BOUNDARY})(/Users|/home)/({_USER_SEG})/({_REPO_BRACE})\"}}",
            _ML,
        ),
        rf'\1{config.REDACTED_OPERATOR_REPO}"}}',
    ),
    (
        re.compile(
            rf"(^|{_BOUNDARY})(/Users|/home)/({_USER_SEG})/({_REPO_QUOTE_COMMA})\",",
            _ML,
        ),
        rf'\1{config.REDACTED_OPERATOR_REPO}",',
    ),
    (
        re.compile(
            rf"(^|{_BOUNDARY})(/Users|/home)/({_USER_SEG})/({_REPO_QUOTE_END})\"$",
            _ML,
        ),
        rf'\1{config.REDACTED_OPERATOR_REPO}"',
    ),
    (
        re.compile(
            rf"(^|{_BOUNDARY})(/Users|/home)/({_USER_SEG})/({_REPO_EOL})$",
            _ML,
        ),
        rf"\1{config.REDACTED_OPERATOR_REPO}",
    ),
    (
        re.compile(
            rf"(\\n)(/Users|/home)/({_USER_SEG})/({_REPO_SLASH})/",
            _ML,
        ),
        rf"\1{config.REDACTED_OPERATOR_REPO}/",
    ),
    (
        re.compile(
            rf"(\\n)(/Users|/home)/({_USER_SEG})/({_REPO_COMMA}),",
            _ML,
        ),
        rf"\1{config.REDACTED_OPERATOR_REPO},",
    ),
    (
        re.compile(
            rf"(\\n)(/Users|/home)/({_USER_SEG})/({_REPO_SEMI});",
            _ML,
        ),
        rf"\1{config.REDACTED_OPERATOR_REPO};",
    ),
    (
        re.compile(
            rf"(\\n)(/Users|/home)/({_USER_SEG})/({_REPO_COLON}):",
            _ML,
        ),
        rf"\1{config.REDACTED_OPERATOR_REPO}:",
    ),
    (
        re.compile(
            rf"(\\n)(/Users|/home)/({_USER_SEG})/({_REPO_BRACE})\"}}",
            _ML,
        ),
        rf'\1{config.REDACTED_OPERATOR_REPO}"}}',
    ),
    (
        re.compile(
            rf"(\\n)(/Users|/home)/({_USER_SEG})/({_REPO_QUOTE_COMMA})\",",
            _ML,
        ),
        rf'\1{config.REDACTED_OPERATOR_REPO}",',
    ),
    (
        re.compile(
            rf"(\\n)(/Users|/home)/({_USER_SEG})/({_REPO_QUOTE_END})\"$",
            _ML,
        ),
        rf'\1{config.REDACTED_OPERATOR_REPO}"',
    ),
    (
        re.compile(
            rf"(\\n)(/Users|/home)/({_USER_SEG})/({_REPO_EOL})$",
            _ML,
        ),
        rf"\1{config.REDACTED_OPERATOR_REPO}",
    ),
)


def _split_on_newline_only(text: str) -> list[str]:
    """Split on LF only (bash redact-secrets stream model)."""
    if not text:
        return []
    parts = text.split("\n")
    lines: list[str] = []
    for index, part in enumerate(parts):
        if index < len(parts) - 1:
            lines.append(part + "\n")
        elif part:
            lines.append(part)
    return lines


def _redact_line_local(line: str) -> str:
    line = _SK_RE.sub(config.REDACTED_TOKEN, line)
    line = _GH_RE.sub(config.REDACTED_TOKEN, line)
    line = _AKIA_RE.sub(config.REDACTED_TOKEN, line)
    return _JWT_RE.sub(config.REDACTED_TOKEN, line)


def _redact_secrets_pem(text: str) -> tuple[str, bool]:
    """Apply PEM swallowing; return (text, saw_unterminated)."""
    lines = _split_on_newline_only(text)
    if not lines and text:
        lines = [text]
    out: list[str] = []
    in_pem = False
    unterminated = False
    for line in lines:
        logical = line.rstrip("\n")
        if in_pem:
            if _PEM_END_RE.match(logical):
                in_pem = False
            continue
        if _PEM_BEGIN_RE.match(logical):
            out.append(config.REDACTED_PRIVATE_KEY + ("\n" if line.endswith("\n") else ""))
            in_pem = True
            continue
        out.append(_redact_line_local(line))
    if in_pem:
        unterminated = True
        suffix = "\n" if (out and out[-1].endswith("\n")) or not out else ""
        out.append(_UNTERMINATED_MARKER + suffix)
    return "".join(out), unterminated


def _redact_tmpdir_paths(text: str) -> str:
    for pattern, repl in _TMPDIR_PATTERNS:
        text = pattern.sub(repl, text)
    for pattern, repl in _OPERATOR_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def redact(text: str) -> str:
    """Redact secrets and session tmpdir literals; idempotent."""
    paths_out = _redact_tmpdir_paths(text)
    paths_out, _ = _redact_secrets_pem(paths_out)
    # Parity with redact-secrets.sh awk: line-oriented output ends with newline.
    if paths_out and not paths_out.endswith("\n"):
        paths_out += "\n"
    return paths_out


def redact_outbound(text: str) -> str:
    """Redact outbound diagnostics; preserve caller newline intent."""
    if not text:
        return text
    out = redact(text)
    if text.endswith("\n"):
        return out
    return out.rstrip("\n")
