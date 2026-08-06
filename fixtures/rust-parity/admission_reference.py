"""Frozen Python behavior for the issue #8059 admission and gate cutover.

This reproduces `python/larch/state/admission.py`, the `session entry-gate` and
`session check-live-mutation-auth` entrypoints in
`python/larch/state/session_env.py`, and `blocker all-open` in
`python/larch/issue/blocker.py` as they behaved at cutover, restricted to the
paths a hermetic sandbox can reach.

Deliberate omissions, none of them part of a command contract:

* `logging_util.quiet_init` file routing. It duplicates stdout and stderr into a
  per-invocation `$TMPDIR/larch-quiet-*.log` while leaving the contract streams
  pointed at the original descriptors, so a caller sees identical bytes either
  way. The Rust owner writes the same bytes without the observability copy.
* Every branch that needs a reachable GitHub API or a real repository: the
  `admission gate` issue read and its lifecycle-prefix ladder, the `blocker
  all-open` dependency and prose reads, and the `admission preflight` fetch,
  sync, and rebase steps. The sandbox has no `gh`, no `git`, and no network, so
  each command stops at the refusal this reference reproduces. The Rust owner's
  unit tests cover the ladder those branches feed.

One known difference is intentional and outside every command contract:
`admission fork-env` reports a failed bootstrap-tmpdir creation with the
operating system's own phrasing, so Rust emits `No such file or directory (os
error 2) at path "..."` where Python emitted `[Errno 2] No such file or
directory: '...'`. The exit code, the leading `admission fork-env: could not
create bootstrap tmpdir: ` prefix, and the untouched filesystem are identical.
The success path matches exactly, including the `0700` directory and the `0600`
`caller-env.sh`.

One environment limit is worth naming: the parity sandbox root is itself created
below the host temporary root, which is an allowlisted mutation-session root, so
no path inside the sandbox can express "outside every canonical root". The
outside-root case therefore uses an absolute path under `/usr`, and the
real-directory version of that rejection lives in the
`refuses_a_canonically_named_root_outside_the_allowlist` unit test in
`crates/larch-adapters/src/github/mutation_auth.rs`.
"""
# ruff: noqa: C901, PLR0911, PLR0912, S108, S603, S607

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

TMP_FALLBACK = "/tmp"
TMP_ROOT = Path(TMP_FALLBACK)
BOOL_VALUES = {"true", "false"}
SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
LIVE_MUTATION_AUTH_KEY = "LARCH_LIVE_MUTATION_OK"
LIVE_MUTATION_TEST_DENY_KEY = "LARCH_ISSUE_MUTATION_DENY"
LIVE_MUTATION_REFUSAL_REASON = "unauthorized-mutation"
EXIT_MUTATION_REFUSED = 5


def emit_kv(key: str, value: str) -> None:
    print(f"{key}={value}")


def single_line(value: str) -> str:
    return re.sub(r" +", " ", value.replace("\r", " ").replace("\n", " ")).strip()


def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(argv, capture_output=True, text=True, errors="replace", check=False)
    except OSError as exc:
        return subprocess.CompletedProcess(argv, 127, "", f"{exc}\n")


def cache_sessions_root() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        base = xdg
    else:
        home = os.environ.get("HOME", "")
        base = f"{home}/.cache" if home else f"{TMP_FALLBACK}/.cache"
    return Path(base) / "larch" / "sessions"


def resolved(path: Path) -> Path:
    return path.resolve(strict=False)


def strictly_under(*, path: Path, root: Path) -> bool:
    try:
        return resolved(root) in resolved(path).parents
    except OSError:
        return False


# ---------------------------------------------------------------- entry gate


def entry_gate(
    *,
    mode: str,
    is_main: str,
    is_user_branch: str,
    user_prefix: str,
    branch_info_supplied: str | None,
) -> tuple[str, str]:
    if mode not in {"implement", "design"}:
        raise ValueError(f"invalid mode: {mode}")
    if not user_prefix:
        raise ValueError("--user-prefix must be non-empty")
    if is_main not in BOOL_VALUES:
        raise ValueError(f"invalid value for --is-main: {is_main}")
    if is_user_branch not in BOOL_VALUES:
        raise ValueError(f"invalid value for --is-user-branch: {is_user_branch}")
    if mode == "implement" and branch_info_supplied is not None:
        raise ValueError("--branch-info-supplied not allowed for mode=implement")
    branch_info = branch_info_supplied or "false"
    if branch_info not in BOOL_VALUES:
        raise ValueError(f"invalid value for --branch-info-supplied: {branch_info}")
    if (mode == "design" and branch_info == "true") or is_user_branch == "true":
        return "continue", "true"
    return "strict", "false"


def entry_gate_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session entry-gate", add_help=False)
    parser.add_argument("--mode", default="")
    parser.add_argument("--current-branch", default="")
    parser.add_argument("--is-main", default="")
    parser.add_argument("--is-user-branch", default="")
    parser.add_argument("--user-prefix", default="")
    parser.add_argument("--branch-info-supplied", default=None)
    try:
        args, extra = parser.parse_known_args(argv)
    except SystemExit:
        return 4

    def fail(message: str) -> int:
        print(f"GATE_ERROR={message}", file=sys.stderr)
        return 4

    if extra:
        return fail(f"unknown argument: {extra[0]}")
    supplied = {
        "--mode": "--mode" in argv,
        "--current-branch": "--current-branch" in argv,
        "--user-prefix": "--user-prefix" in argv,
        "--is-main": "--is-main" in argv,
        "--is-user-branch": "--is-user-branch" in argv,
    }
    for flag, was_supplied in supplied.items():
        if not was_supplied:
            return fail(f"missing required flag {flag}")
    try:
        gate, skip_branch_check = entry_gate(
            mode=args.mode,
            is_main=args.is_main,
            is_user_branch=args.is_user_branch,
            user_prefix=args.user_prefix,
            branch_info_supplied=args.branch_info_supplied,
        )
    except ValueError as exc:
        return fail(str(exc))
    emit_kv("ENTRY_GATE", gate)
    emit_kv("SKIP_BRANCH_CHECK", skip_branch_check)
    return 0


# -------------------------------------------------- live-mutation authorization


def is_canonical_mutation_session_root(path: Path) -> bool:
    try:
        target = path.resolve(strict=True)
    except OSError:
        return False
    if not target.is_dir() or not re.fullmatch(r"claude-(?:design|implement)-[A-Za-z0-9._-]+", target.name):
        return False
    roots = (
        cache_sessions_root(),
        TMP_ROOT,
        Path("/private/tmp"),
        Path("/var/folders"),
        Path("/private/var/folders"),
    )
    return any(strictly_under(path=target, root=root) for root in roots)


def check_live_mutation_auth(*, context_file: Path, run_id: str, trusted_root: Path) -> bool:
    if os.environ.get(LIVE_MUTATION_TEST_DENY_KEY) == "true":
        return False
    try:
        ctx = Path(context_file)
        if not ctx.exists() or not ctx.is_file() or ctx.is_symlink():
            return False
        if not is_canonical_mutation_session_root(trusted_root):
            return False
        if ctx.parent.resolve() != trusted_root.resolve():
            return False
        auth_value = ""
        ctx_run_id = ""
        for raw in ctx.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export "):].lstrip()
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key == LIVE_MUTATION_AUTH_KEY:
                auth_value = value
            elif key == "LARCH_RUN_ID":
                ctx_run_id = value
        if auth_value != "true":
            return False
        if not ctx_run_id or not SAFE_RUN_ID_RE.fullmatch(ctx_run_id):
            return False
        return run_id == ctx_run_id
    except OSError:
        return False


def check_live_mutation_auth_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session check-live-mutation-auth", add_help=False)
    parser.add_argument("--context-file", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--trusted-root", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1
    authorized = check_live_mutation_auth(
        context_file=Path(args.context_file),
        run_id=args.run_id,
        trusted_root=Path(args.trusted_root),
    )
    return 0 if authorized else EXIT_MUTATION_REFUSED


# ------------------------------------------------------------------- admission


def normal_issue(value: str) -> int | None:
    if not value or not value.isdigit():
        return None
    number = int(value, 10)
    return number if number > 0 else None


def validate_repo_slug(value: str) -> bool:
    if not value or "\n" in value or "\r" in value:
        return False
    if value.startswith(("--", "/")) or "../" in value or "\\" in value:
        return False
    parts = value.split("/")
    if len(parts) != 2:
        return False
    return all(part and part not in {".", ".."} for part in parts)


def resolve_repo() -> str:
    result = run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"])
    if result.returncode == 0:
        candidate = result.stdout.strip()
        if candidate and validate_repo_slug(candidate):
            return candidate
    origin = run(["git", "remote", "get-url", "origin"])
    if origin.returncode != 0:
        return ""
    url = origin.stdout.strip().removesuffix(".git")
    for prefix in ("git@github.com:", "https://github.com/", "ssh://git@github.com/"):
        if url.startswith(prefix):
            candidate = url[len(prefix):]
            return candidate if validate_repo_slug(candidate) else ""
    return ""


def gate_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="admission gate", add_help=True)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--repo", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        if int(exc.code or 0) != 0:
            emit_kv("ADMISSION_ERROR", single_line("argument validation failed"))
            return 2
        return 0
    issue = normal_issue(args.issue)
    if issue is None:
        emit_kv("ADMISSION_ERROR", single_line("--issue must be a positive integer"))
        return 2
    repo = args.repo or resolve_repo()
    if not repo:
        emit_kv("ADMISSION_ERROR", single_line("could not resolve repo (gh repo view failed)"))
        return 2
    emit_kv("ADMISSION_ERROR", single_line("gh issue view failed"))
    return 2


def preflight_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="admission preflight", add_help=False)
    parser.add_argument("--skip-branch-check", action="store_true")
    parser.add_argument("--skip-clean-check", action="store_true")
    try:
        args, rest = parser.parse_known_args(argv)
    except SystemExit:
        return 3
    if rest:
        parser.print_usage(sys.stderr)
        print(f"Unknown option: {rest[0]}", file=sys.stderr)
        return 3
    if not args.skip_branch_check:
        result = run(["git", "symbolic-ref", "--short", "HEAD"])
        current = result.stdout.strip() if result.returncode == 0 else ""
        if current != "main":
            emit_kv("PREFLIGHT", single_line("fail"))
            emit_kv(
                "PREFLIGHT_ERROR",
                single_line(
                    f"Not on main branch (on '{current}'). Switch to main first, or pass --skip-branch-check."
                ),
            )
            return 1
    emit_kv("PREFLIGHT", single_line("fail"))
    emit_kv("PREFLIGHT_ERROR", single_line("git fetch origin main failed."))
    return 3


def fork_env_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="admission fork-env", add_help=True)
    parser.add_argument("--tmpdir", default="")
    try:
        _args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if int(exc.code or 0) != 0 else 0
    upstream = run(["git", "remote", "get-url", "upstream"])
    if upstream.returncode != 0:
        print("--forked requires the clone to be configured for the fork-PR workflow:", file=sys.stderr)
        print("  origin -> your fork; upstream -> the upstream repo.", file=sys.stderr)
        print("See docs/forked.md for the full remote-add walkthrough;", file=sys.stderr)
        print("the minimum is:", file=sys.stderr)
        print("  git remote add upstream <https-or-ssh-url-of-upstream-repo>", file=sys.stderr)
        return 1
    print("github-remote-repo.sh: cannot parse remote", file=sys.stderr)
    return 2


def all_open_blockers_main(_argv: list[str]) -> int:
    # Every offline path converges here: no issue number, no resolvable
    # repository, or an unreachable API all emit the same empty row and exit 0.
    emit_kv("BLOCKERS", "")
    return 0


COMMANDS = {
    "entry-gate": entry_gate_main,
    "check-live-mutation-auth": check_live_mutation_auth_main,
    "admission-gate": gate_main,
    "admission-preflight": preflight_main,
    "admission-fork-env": fork_env_main,
    "blocker-all-open": all_open_blockers_main,
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in COMMANDS:
        print(f"admission_reference: unknown command {argv[0] if argv else ''}", file=sys.stderr)
        return 64
    return COMMANDS[argv[0]](argv[1:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
