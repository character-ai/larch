# pyright: reportUnusedCallResult=false
"""Secret and tmpdir-path redaction (parity with scripts/redact-*.sh)."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import config

# Line-local secret families (byte-for-byte ports of python3 python/cli.py redact secrets sed -E)
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

# --- Pre-flush log-gate secret families (parity with python3 python/cli.py redact scrub-log-secrets) ---
# High-precision prefixed patterns NOT covered by the base families above.
# `crsr_` is the confirmed Cursor key prefix; `key_{32,}` is the hedge for
# Cursor admin keys that avoids matching ordinary `key_` identifiers (which
# carry underscores and rarely run 32 unbroken alphanumerics).
_CURSOR_RE = re.compile(r"crsr_[A-Za-z0-9_-]{20,}|key_[A-Za-z0-9]{32,}")
_SLACK_RE = re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")
_GOOGLE_API_RE = re.compile(r"AIza[0-9A-Za-z_-]{35}")
_STRIPE_LIVE_RE = re.compile(r"(?:sk|rk)_live_[0-9A-Za-z]{16,}")
_GITLAB_PAT_RE = re.compile(r"glpat-[0-9A-Za-z_-]{20,}")

_EXTRA_SECRET_FAMILIES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("cursor-api-key", _CURSOR_RE),
    ("slack-token", _SLACK_RE),
    ("google-api-key", _GOOGLE_API_RE),
    ("stripe-live-key", _STRIPE_LIVE_RE),
    ("gitlab-pat", _GITLAB_PAT_RE),
)

# Base families re-detected for backstop counting; their scrubbing is performed
# by the PEM-aware pass (_redact_secrets_pem). The PEM detector matches the
# BEGIN marker anywhere (not line-anchored) for occurrence counting.
_PEM_DETECT_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
_BASE_SECRET_FAMILIES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("anthropic-openai-key", _SK_RE),
    ("github-token", _GH_RE),
    ("aws-akia", _AKIA_RE),
    ("jwt", _JWT_RE),
    ("pem-private-key", _PEM_DETECT_RE),
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
            rf'(^|{_BOUNDARY})/(private/)?tmp/+({_NOT_PATH}+/)*larch-report-tokens[.-][^/\s"\\]+',
            _ML,
        ),
        rf"\1{config.REDACTED_TMPDIR}",
    ),
    (
        re.compile(
            rf"(^|{_BOUNDARY})/(private/)?var/folders/[^/]+/[^/]+/T/"
            rf'({_NOT_PATH}+/)*larch-report-tokens[.-][^/\s"\\]+',
            _ML,
        ),
        rf"\1{config.REDACTED_TMPDIR}",
    ),
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
    line = _CURSOR_RE.sub(config.REDACTED_TOKEN, line)
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


def redact_tmpdir_paths(text: str) -> str:
    for pattern, repl in _TMPDIR_PATTERNS:
        text = pattern.sub(repl, text)
    for pattern, repl in _OPERATOR_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def _redact_tmpdir_paths(text: str) -> str:
    return redact_tmpdir_paths(text)


def redact_secrets_only(text: str) -> str:
    """Redact secret families only; preserve tmpdir and operator paths."""
    out, _ = _redact_secrets_pem(text)
    if out and not out.endswith("\n"):
        out += "\n"
    return out


def redact(text: str) -> str:
    """Redact secrets and session tmpdir literals; idempotent."""
    paths_out = _redact_tmpdir_paths(text)
    paths_out, _ = _redact_secrets_pem(paths_out)
    # Parity with python3 python/cli.py redact secrets awk: line-oriented output ends with newline.
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


def redact_secrets_outbound(text: str) -> str:
    """Redact secret families only; preserve tmpdir and operator repo paths."""
    if not text:
        return text
    out, _ = scrub_log_secrets(text)
    if text.endswith("\n"):
        return out
    return out.rstrip("\n")


def scrub_log_secrets(text: str) -> tuple[str, dict[str, int]]:
    """Scrub secret-shaped values from run-log text before a flush commit
    (parity with python3 python/cli.py redact scrub-log-secrets).

    Returns ``(scrubbed_text, findings)`` where ``findings`` maps a family name
    to its occurrence count in the ORIGINAL text. Base families
    (sk-/GitHub/AWS/JWT/PEM) are scrubbed by the python3 python/cli.py redact secrets-equivalent
    PEM-aware pass; the extra prefixed families (Cursor et al.) by additional
    substitutions. Unlike :func:`redact`, this does NOT rewrite session tmpdir
    paths — it is a secret gate, not a path normaliser.
    """
    findings: dict[str, int] = {}
    for name, pattern in (*_BASE_SECRET_FAMILIES, *_EXTRA_SECRET_FAMILIES):
        count = len(pattern.findall(text))
        if count:
            findings[name] = count
    scrubbed, _ = _redact_secrets_pem(text)
    for _, pattern in _EXTRA_SECRET_FAMILIES:
        scrubbed = pattern.sub(config.REDACTED_TOKEN, scrubbed)
    return scrubbed, findings


def redact_breadcrumb_file(*, input_path: Path, output_path: Path, state_file: Path) -> None:
    """Apply path redaction, then PEM-aware secret redaction for breadcrumb logs."""
    _ = state_file
    text = input_path.read_text(encoding="utf-8", errors="replace")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(redact_secrets_only(redact_tmpdir_paths(text)), encoding="utf-8")


def _streaming_redact(*, stdin_text: str, state_file: Path) -> str:
    in_pem = False
    if state_file.is_file():
        try:
            in_pem = "in_pem=1" in state_file.read_text(encoding="utf-8")
        except OSError:
            in_pem = False
    out: list[str] = []
    for raw in _split_on_newline_only(stdin_text):
        line = raw.rstrip("\n")
        newline = "\n" if raw.endswith("\n") else ""
        if in_pem:
            if _PEM_END_RE.match(line):
                in_pem = False
            continue
        if _PEM_BEGIN_RE.match(line):
            out.append(config.REDACTED_PRIVATE_KEY + newline)
            in_pem = True
            continue
        out.append(_redact_line_local(raw))
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(f"in_pem={1 if in_pem else 0}\n", encoding="utf-8")
    if in_pem:
        print(
            "WARN: python3 python/cli.py redact secrets: unterminated PEM block (streaming)",
            file=sys.stderr,
        )
    return "".join(out)


def main_secrets(argv: list[str]) -> int:
    streaming = False
    state_file = ""
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--streaming":
            streaming = True
            idx += 1
        elif arg == "--state-file":
            if idx + 1 >= len(argv):
                print("redact secrets: --state-file requires a value", file=sys.stderr)
                return 2
            state_file = argv[idx + 1]
            idx += 2
        elif arg.startswith("--state-file="):
            state_file = arg.split("=", 1)[1]
            idx += 1
        else:
            print(f"redact secrets: unknown option: {arg}", file=sys.stderr)
            return 2
    text = sys.stdin.read()
    if streaming:
        if not state_file:
            print("redact secrets: --streaming requires --state-file", file=sys.stderr)
            return 2
        sys.stdout.write(_streaming_redact(stdin_text=text, state_file=Path(state_file)))
        return 0
    sys.stdout.write(redact_secrets_only(text))
    return 0


def main_tmpdir_paths(argv: list[str]) -> int:
    if argv:
        print(f"redact tmpdir-paths: unknown option: {argv[0]}", file=sys.stderr)
        return 2
    sys.stdout.write(redact_tmpdir_paths(sys.stdin.read()))
    return 0


def scrub_log_directory(directory: Path) -> tuple[int, int]:
    total = 0
    files = 0
    for path in sorted(directory.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        scrubbed, findings = scrub_log_secrets(text)
        if not findings:
            continue
        _, residual = scrub_log_secrets(scrubbed)
        if residual:
            raise RuntimeError(f"secret survived scrubbing in {path}")
        path.write_text(scrubbed, encoding="utf-8")
        total += sum(findings.values())
        files += 1
    return total, files


def main_scrub_log_secrets(argv: list[str]) -> int:
    directory = ""
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg in {"--dir", "--log-root", "--path"}:
            if idx + 1 >= len(argv):
                print(f"python3 python/cli.py redact scrub-log-secrets: {arg} requires a value", file=sys.stderr)
                return 2
            directory = argv[idx + 1]
            idx += 2
        else:
            if directory:
                print(f"python3 python/cli.py redact scrub-log-secrets: unknown option: {arg}", file=sys.stderr)
                return 2
            directory = arg
            idx += 1
    if not directory:
        print("python3 python/cli.py redact scrub-log-secrets: directory is required", file=sys.stderr)
        return 2
    root = Path(directory)
    if not root.exists():
        print(f"python3 python/cli.py redact scrub-log-secrets: directory not found: {root}", file=sys.stderr)
        return 2
    try:
        violations, files = scrub_log_directory(root)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    print(f"LARCH_SECRET_SCRUB_VIOLATIONS={violations}")
    print(f"LARCH_SECRET_SCRUB_FILES={files}")
    return 0


def _discover_submodule_paths(cwd: Path) -> set[str]:
    paths: set[str] = set()
    gitmodules = cwd / ".gitmodules"
    if gitmodules.is_file():
        for line in gitmodules.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.startswith("path") and "=" in stripped:
                _, _, value = stripped.partition("=")
                if value.strip():
                    paths.add(value.strip().strip("/"))
    result = subprocess.run(
        ["git", "submodule", "foreach", "--quiet", "printf '%s\\n' \"$sm_path\""],  # noqa: S607
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        paths.update(line.strip().strip("/") for line in result.stdout.splitlines() if line.strip())
    return paths


def discover_submodule_paths(cwd: Path) -> set[str]:
    return _discover_submodule_paths(cwd)


def scrub_submodule_paths(*, input_path: Path, output_path: Path, log_path: Path) -> tuple[int, bool]:
    text = input_path.read_text(encoding="utf-8", errors="replace")
    repo = Path.cwd()
    submodules = discover_submodule_paths(repo)
    scrubbed_count = 0
    audit: list[str] = []
    blocks = re.split(r"(?=^### FINDING_)", text, flags=re.MULTILINE)
    out_blocks: list[str] = []
    for block in blocks:
        if not block.startswith("### FINDING_"):
            out_blocks.append(block)
            continue
        matched = False
        for sub in sorted(submodules, key=len, reverse=True):
            escaped = re.escape(sub)
            # Label match: production findings use the markdown-bold
            # `- **Location**:` / `- **File**:` form (the plain `Location:` form
            # is also tolerated). The path may be the bare submodule dir, carry a
            # `:line` suffix, or point inside the submodule, so require only a
            # non-path-token boundary after it rather than a trailing slash.
            label_match = re.search(
                rf"(?m)^\s*-?\s*(?:\*\*)?(Location|File)(?:\*\*)?:\s*{escaped}(?![A-Za-z0-9_.-])",
                block,
            )
            # Inline match: the submodule path appearing as a complete path token
            # anywhere in the block (bare dir, `:line` suffix, or deeper path),
            # not only when followed by a trailing slash.
            inline_match = re.search(rf"(?<![A-Za-z0-9_.-]){escaped}(?![A-Za-z0-9_.-])", block)
            if label_match or inline_match:
                matched = True
                break
        if matched:
            scrubbed_count += 1
            audit.append(block.splitlines()[0])
            continue
        out_blocks.append(block)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("".join(out_blocks), encoding="utf-8")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(audit) + ("\n" if audit else ""), encoding="utf-8")
    return scrubbed_count, True


def main_scrub_submodule_paths(argv: list[str]) -> int:
    input_path = ""
    output_path = ""
    log_path = ""
    idx = 0
    while idx < len(argv):
        arg = argv[idx]
        if arg == "--input" and idx + 1 < len(argv):
            input_path = argv[idx + 1]
            idx += 2
        elif arg == "--output" and idx + 1 < len(argv):
            output_path = argv[idx + 1]
            idx += 2
        elif arg == "--log" and idx + 1 < len(argv):
            log_path = argv[idx + 1]
            idx += 2
        else:
            print(f"scrub-submodule-paths.sh: unknown or incomplete option: {arg}", file=sys.stderr)
            return 2
    if not input_path or not output_path or not log_path:
        print("scrub-submodule-paths.sh: --input, --output, and --log are required", file=sys.stderr)
        return 2
    try:
        count, ok = scrub_submodule_paths(input_path=Path(input_path), output_path=Path(output_path), log_path=Path(log_path))
    except OSError as exc:
        print(f"scrub-submodule-paths.sh: {exc}", file=sys.stderr)
        print("SCRUB_COUNT=0")
        print("SCRUB_OK=false")
        return 2
    print(f"SCRUB_COUNT={count}")
    print(f"SCRUB_OK={'true' if ok else 'false'}")
    return 0
