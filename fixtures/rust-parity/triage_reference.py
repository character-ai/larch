"""Frozen Python behavior for the issue #8172 `/triage` cutover.

This reproduces `triage inspect`, `triage probe`, and `triage apply` from
`python/larch/issue/triage.py` as they behaved at cutover, restricted to the
paths a hermetic sandbox can reach.

The sandbox has no network, no `gh` credential, an empty `PATH`, and a working
directory that is not a Git repository, so every case here stops before the
first GitHub request and before any Git object is read. What the cases do cover
end to end is the whole surface a caller branches on offline: the `argparse`
scanners and their exact usage and help blocks, the evidence-path and byte-cap
validation, the fixed probe allowlist and the way an absent probe executable is
reported, the inconclusive short circuit, the live-mutation authorization
refusal that must precede every GitHub call, the ISO-8601 and identity
validation, and the `/tmp/claude-triage-*` confinement of the session root and
its artifacts.

The verified mutation itself — the compare-and-swap, the security
reclassification between mutations, the comment idempotency marker, the title
restoration, and the close read-back — sits behind the first authenticated
request. It is covered by the unit tests in
`crates/larch-cli/src/triage_commands.rs`, the grammar tests in
`crates/larch-core/src/issue/triage.rs`, and the mutation-owner tests in
`crates/larch-core/src/issue_mutation.rs` instead.

Deliberate omissions, none of them part of a command contract:

* `logging_util.quiet_init` file routing, which duplicates the contract streams
  into a per-invocation log while leaving the originals in place.
* PEM private-key block swallowing. The secret-family substitution below stands
  in for that pass, and no case here carries a PEM block.

Seven differences are intentional and documented in the pull request:

* The `python-version` probe. Python ran `sys.executable --version`, the
  absolute path of the interpreter that happened to be running the verb; Rust
  runs `python3` from the child's `PATH`, because a Rust owner has no
  interpreter of its own. Both report the host Python version; only the
  argument vector differs. No parity case covers it, because the two resolve
  differently under the sandbox's empty `PATH`.
* The probe environment. Python removed every variable whose name matched
  `TOKEN|KEY|SECRET|PASSWORD|CREDENTIAL|PROXY` from an otherwise inherited
  environment; the Rust runtime passes only its closed inheritance allowlist,
  which is strictly less than the deny-list left behind.
* The issue comment read. Python read the comment bodies twice — once in the
  `gh issue view --json comments` snapshot and once through the paginated
  comment list — and joined both into the security classification. Rust reads
  the comment list once and classifies over that, which is the same text.
* The close read-back. Python asserted the closed issue's `stateReason` was
  `NOT_PLANNED` or empty; the typed Rust close names `not planned` in the
  request itself and proves the read-back is `CLOSED`, and the REST issue model
  carries no state-reason field.
* The repository slug. Python matched `--repo` against a character-class
  regular expression; Rust parses it into the typed repository reference every
  GitHub call already takes, which additionally refuses a bare `.` or `..`
  component and a component past 100 characters. No caller names such a
  repository.
* Fetch bounding. Both fetch with `--no-tags`; Rust reaches it through the
  typed fetch request rather than a hand-built argument vector.
* Filesystem and process error text. Python echoed the `OSError` message for an
  unreadable artifact and the runner's own text for a failed spawn; Rust names
  the same failures with the platform's message and the same exit codes.
"""
# ruff: noqa: FBT001, FBT003, PLR0911, PLR0912, PLR2004 - the frozen scanners return
# and branch exactly as they shipped.

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

EXIT_USAGE = 2
EXIT_AUTHORIZATION = 3
EXIT_PROTECTED = 5
EXIT_REDACTION = 6
EXIT_POSTCONDITION = 8

TRIAGE_MARKER_START = "<!-- larch:triage:start -->"
TRIAGE_MARKER_END = "<!-- larch:triage:end -->"
MAX_EVIDENCE_BYTES = 64 * 1024
MAX_PROBE_BYTES = 16 * 1024
TRIAGE_TMP_PREFIX = "claude-triage-"
TMP_ROOT = Path("/tmp")  # noqa: S108 - /triage policy requires canonical /tmp
LIVE_MUTATION_AUTH_KEY = "LARCH_LIVE_MUTATION_OK"
REDACTED_TOKEN = "<REDACTED-TOKEN>"

REPO_RE = re.compile(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+")
UPDATED_AT_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")
LARCH_MARKER_RE = re.compile(r"<!--\s*larch:[\s\S]*?-->", re.IGNORECASE)
EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])")
URL_RE = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
SECRET_RE = re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")


class TriageError(Exception):
    """A user-safe triage failure with a stable exit class."""

    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def redact_outbound(text: str) -> str:
    if not text:
        return text
    out = SECRET_RE.sub(REDACTED_TOKEN, text)
    return out if text.endswith("\n") else out.rstrip("\n")


def flat(text: str) -> str:
    return redact_outbound(text).replace("\r", " ").replace("\n", " ").strip()[:1000]


def private_url(url: str) -> bool:
    from ipaddress import ip_address
    from urllib.parse import urlparse

    host = (urlparse(url.rstrip(".,;:!?")).hostname or "").casefold()
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith((".internal", ".local")):
        return True
    try:
        return ip_address(host).is_private
    except ValueError:
        return False


def sanitize_outbound(text: str) -> str:
    """Redact outbound prose; the block-wrapping half is never reached here."""
    content = LARCH_MARKER_RE.sub(
        lambda match: match.group(0).replace("<!--", "<!--​", 1), text
    )
    content = EMAIL_RE.sub("<REDACTED-PII>", content)
    content = URL_RE.sub(
        lambda match: ("<INTERNAL-URL>" if private_url(match.group(0)) else match.group(0)),
        content,
    )
    content = redact_outbound(content)
    if EMAIL_RE.search(content):
        raise TriageError("outbound PII redaction could not be verified", EXIT_REDACTION)
    return content


# ------------------------------------------------------------------- inspect


def validate_evidence_path(value: str) -> PurePosixPath:
    if not value or "\x00" in value or "\\" in value:
        raise TriageError("evidence path is invalid", EXIT_USAGE)
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value.startswith("-"):
        raise TriageError(
            "evidence path must be a bounded repository-relative path", EXIT_USAGE
        )
    return path


def origin_slug(repo_root: Path) -> str:
    result = run(["git", "-C", str(repo_root), "remote", "get-url", "origin"])
    if result.returncode != 0:
        raise TriageError("fixed origin remote is unavailable", EXIT_POSTCONDITION)
    value = result.stdout.strip()
    patterns = (
        re.compile(r"(?:https://github\.com/|git@github\.com:)([^/\s]+/[^/\s]+?)(?:\.git)?$"),
        re.compile(r"^ssh://git@github\.com/([^/\s]+/[^/\s]+?)(?:\.git)?$"),
    )
    for pattern in patterns:
        match = pattern.match(value)
        if match and REPO_RE.fullmatch(match.group(1)):
            return match.group(1)
    raise TriageError(
        "origin is not a validated GitHub repository remote", EXIT_POSTCONDITION
    )


def inspect_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="triage inspect")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--ref", default="refs/heads/main")
    parser.add_argument("--path")
    parser.add_argument("--max-bytes", type=int, default=MAX_EVIDENCE_BYTES)
    try:
        args = parser.parse_args(argv)
        repo_root = Path(args.repo_root).resolve()
        if not repo_root.is_dir():
            raise TriageError("--repo-root is not a directory", EXIT_USAGE)
        if args.path:
            validate_evidence_path(args.path)
        if args.max_bytes < 1 or args.max_bytes > MAX_EVIDENCE_BYTES:
            raise TriageError(
                "--max-bytes is outside the supported evidence cap", EXIT_USAGE
            )
        # Every sandbox case stops inside this call: the working directory is
        # not a repository and `PATH` holds no `git`. Reaching the next line is
        # a fixture defect, so it fails loudly rather than inventing a refusal
        # the command never publishes.
        _ = origin_slug(repo_root)
        print("REFERENCE_REACHED_GIT=true", file=sys.stderr)
        return 99
    except TriageError as exc:
        print("EVIDENCE_STATUS=gap")
        print(f"EVIDENCE_GAP={flat(str(exc))}")
        return exc.exit_code
    except SystemExit:
        return EXIT_USAGE


# --------------------------------------------------------------------- probe


def run(argv: list[str], *, env: dict[str, str] | None = None, timeout: float | None = None):
    try:
        return subprocess.run(  # noqa: S603 - fixed allowlisted argv, no shell
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            env=env,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            argv, 127, "", f"{argv[0]}: command not found\n"
        )


def scrubbed_env() -> dict[str, str]:
    blocked = re.compile(r"(?:TOKEN|KEY|SECRET|PASSWORD|CREDENTIAL|PROXY)", re.IGNORECASE)
    return {key: value for key, value in os.environ.items() if blocked.search(key) is None}


def safe_probe_argv(name: str, values: list[str]) -> list[str]:
    if any(re.search(r"[;&|`$<>\n\r]", value) for value in values):
        raise TriageError("probe arguments contain forbidden shell syntax", EXIT_USAGE)
    if name == "python-version" and not values:
        return [sys.executable, "--version"]
    if name == "git-version" and not values:
        return ["git", "--version"]
    if (
        name == "codex-model-readonly"
        and len(values) == 1
        and re.fullmatch(r"[A-Za-z0-9._-]+", values[0])
    ):
        return [
            "codex",
            "exec",
            "--sandbox",
            "read-only",
            "--model",
            values[0],
            "Reply with OK only.",
        ]
    raise TriageError(
        "probe name or arguments are not in the fixed read-only allowlist", EXIT_USAGE
    )


def probe_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="triage probe")
    parser.add_argument("--name", required=True)
    parser.add_argument("--arg", action="append", default=[])
    parser.add_argument("--max-bytes", type=int, default=MAX_PROBE_BYTES)
    try:
        args = parser.parse_args(argv)
        if args.max_bytes < 1 or args.max_bytes > MAX_PROBE_BYTES:
            raise TriageError("--max-bytes is outside the supported probe cap", EXIT_USAGE)
        command = safe_probe_argv(args.name, list(args.arg))
        result = run(command, env=scrubbed_env(), timeout=30)
        combined = f"{result.stdout}{result.stderr}"
        encoded = combined.encode("utf-8", errors="replace")
        truncated = len(encoded) > args.max_bytes
        output = encoded[: args.max_bytes].decode("utf-8", errors="replace")
        print("PROBE_STATUS=completed" if result.returncode == 0 else "PROBE_STATUS=failed")
        print(f"PROBE_EXIT_CODE={result.returncode}")
        print(f"PROBE_TRUNCATED={'true' if truncated else 'false'}")
        print("PROBE_OUTPUT_BEGIN")
        print(sanitize_outbound(output), end="" if output.endswith("\n") else "\n")
        print("PROBE_OUTPUT_END")
        return 0 if result.returncode == 0 else EXIT_POSTCONDITION
    except TriageError as exc:
        print("PROBE_STATUS=rejected")
        print(f"PROBE_FAILURE={flat(str(exc))}")
        return exc.exit_code
    except SystemExit:
        return EXIT_USAGE


# --------------------------------------------------------------------- apply


def check_live_mutation_auth(*, operator_mode: bool) -> tuple[bool, str]:
    if operator_mode:
        return True, "operator-invoked"
    if os.environ.get(LIVE_MUTATION_AUTH_KEY) == "true":
        return True, "session-authorized"
    return False, "unauthorized-mutation"


def canonical_tmp_root(value: str) -> Path:
    root = Path(value)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise TriageError("triage root must be an existing regular directory", EXIT_USAGE)
    resolved = root.resolve()
    if resolved.parent != TMP_ROOT.resolve() or not resolved.name.startswith(
        TRIAGE_TMP_PREFIX
    ):
        raise TriageError(
            "triage root must be a canonical /tmp/claude-triage-* directory", EXIT_USAGE
        )
    return resolved


def artifact_path(path_value: str, *, root: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise TriageError("triage artifact must be a regular non-symlink file", EXIT_USAGE)
    resolved = path.resolve()
    if resolved.parent != root:
        raise TriageError("triage artifact escaped the canonical triage root", EXIT_USAGE)
    return resolved


def failure(kind: str, message: str) -> None:
    print(f"TRIAGE_FAILURE={kind}", file=sys.stderr)
    print(f"ERROR={flat(message)}", file=sys.stderr)


def apply_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="triage apply")
    parser.add_argument("issue", type=int)
    parser.add_argument("--repo", required=True)
    parser.add_argument(
        "--verdict",
        required=True,
        choices=("valid", "already-fixed", "duplicate", "invalid", "inconclusive"),
    )
    parser.add_argument("--expected-updated-at", required=True)
    parser.add_argument("--triage-root", required=True)
    parser.add_argument("--body-file")
    parser.add_argument("--comment-file")
    parser.add_argument("--canonical-duplicate", type=int)
    parser.add_argument("--operator-invoked", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.issue < 1 or REPO_RE.fullmatch(args.repo) is None:
            raise TriageError("issue and repository arguments are invalid", EXIT_USAGE)
        if UPDATED_AT_RE.fullmatch(args.expected_updated_at) is None:
            raise TriageError(
                "--expected-updated-at must be an ISO-8601 UTC timestamp", EXIT_USAGE
            )
        if args.verdict == "inconclusive":
            print("TRIAGE_VERDICT=inconclusive")
            print("ISSUE_UPDATED=false")
            print("TRIAGE_FAILURE=none")
            return 0
        auth_ok, auth_reason = check_live_mutation_auth(
            operator_mode=bool(args.operator_invoked)
        )
        if not auth_ok:
            raise TriageError(
                f"live mutation authorization refused: {auth_reason}", EXIT_AUTHORIZATION
            )
        root = canonical_tmp_root(args.triage_root)
        selected_file = args.body_file if args.verdict == "valid" else args.comment_file
        if not selected_file:
            raise TriageError(
                "verdict requires the matching body/comment artifact", EXIT_USAGE
            )
        artifact = artifact_path(selected_file, root=root)
        _ = artifact.read_text(encoding="utf-8", errors="replace")
        # The next step is the first GitHub read, which no sandbox case can
        # reach: there is no credential and no network. Reaching this line is a
        # fixture defect, so it fails loudly.
        print("REFERENCE_REACHED_GITHUB=true", file=sys.stderr)
        return 99
    except TriageError as exc:
        kinds = {
            EXIT_AUTHORIZATION: "authorization",
            EXIT_PROTECTED: "protected-state",
            EXIT_REDACTION: "redaction",
        }  # the remaining classes sit behind the first GitHub request
        failure(kinds.get(exc.exit_code, "validation"), str(exc))
        print("ISSUE_UPDATED=false")
        return exc.exit_code
    except SystemExit:
        return EXIT_USAGE
    except OSError as exc:
        failure("validation", str(exc))
        print("ISSUE_UPDATED=false")
        return EXIT_USAGE


COMMANDS = {
    "triage-inspect": inspect_main,
    "triage-probe": probe_main,
    "triage-apply": apply_main,
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in COMMANDS:
        print(f"unknown reference command: {argv[:1]}", file=sys.stderr)
        return 64
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
