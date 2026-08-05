"""Frozen Python behavior for the issue #8057 session-lifecycle command cutover.

This reproduces `python/larch/state/session_env.py` as it behaved at cutover for
`session require-plugin-root`, `validate-design-tmpdir`, `write-id`,
`resolve-implement-tmpdir`, and `cleanup-tmpdir`, with two deliberate omissions
that are not part of any command contract:

* `logging_util.quiet_init` file routing. It duplicates stdout and stderr into a
  per-invocation `$TMPDIR/larch-quiet-*.log` while leaving the contract streams
  pointed at the original descriptors, so a caller sees identical bytes either
  way. The Rust owner writes the same bytes without the observability copy.
* Outbound redaction of breadcrumb diagnostics. The Rust owner keeps redaction;
  this reference omits it because the rules rewrite only `/Users/<user>/<repo>/`
  and `/home/<user>/<repo>/` prefixes, which no sandbox path can match.

Three differences are known and intentional, none of them observable to a caller
that branches on exit codes:

* `clap` consumes a lone `--` before the Rust command sees it, so
  `require-plugin-root --` exits 0 in Rust and 2 here. Production callers pass no
  arguments to that verb. The same boundary already applies to the
  `session read-key` and `read-keys` owners from #8056.
* `write-id` mints its identity with a `uuid` v4 in Rust instead of shelling out
  to `uuidgen` and falling back to the parent directory's basename. Both spellings
  satisfy the session-id grammar, the value is opaque, and the verb has no
  production caller.
* `cleanup-tmpdir` refuses a non-directory target with `not a directory: <path>`
  where `shutil.rmtree` raises `[Errno 20] Not a directory: <path>`. Exit code,
  refusal, and the untouched target are identical; only the operating system's
  phrasing differs, so this case stays out of the byte-compared golden matrix.
  The dangling-symlink and live-symlink cases do match byte for byte.
"""
# ruff: noqa: C901, PLR0911, PLR0912, S108

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

IMPLEMENT_SENTINEL_RELS = (
    Path("design-export") / "manifest.env",
    Path("review-round-summary.md"),
    Path(".bump-version-armed"),
    Path(".release-armed"),
)
IMPLEMENT_TMPDIR_TTL_SECONDS = 21600
TMP_FALLBACK = "/tmp"
PLUGIN_ROOT_LITERAL = "${CLAUDE_PLUGIN_ROOT}"


def cache_sessions_root() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        base = xdg
    else:
        home = os.environ.get("HOME", "")
        base = f"{home}/.cache" if home else f"{TMP_FALLBACK}/.cache"
    return Path(base) / "larch" / "sessions"


def allowed_roots() -> tuple[Path, ...]:
    return (
        Path(TMP_FALLBACK),
        Path("/private/tmp"),
        Path("/var/folders"),
        Path("/private/var/folders"),
        cache_sessions_root(),
    )


def implement_roots() -> tuple[Path, ...]:
    return (cache_sessions_root(), Path(TMP_FALLBACK), Path("/private/tmp"))


def resolved(path: Path) -> Path:
    return path.resolve(strict=False)


def under(path: Path, root: Path) -> bool:
    try:
        target, base = resolved(path), resolved(root)
    except OSError:
        return False
    return target == base or base in target.parents


def strictly_under(path: Path, root: Path) -> bool:
    try:
        target, base = resolved(path), resolved(root)
    except OSError:
        return False
    return base in target.parents


def require_plugin_root() -> int:
    value = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if not value:
        print("/design wrapper: CLAUDE_PLUGIN_ROOT is empty; abort", file=sys.stderr)
        return 1
    if value == PLUGIN_ROOT_LITERAL:
        print(
            f"/design wrapper: CLAUDE_PLUGIN_ROOT is the unexpanded template literal {PLUGIN_ROOT_LITERAL}; abort",
            file=sys.stderr,
        )
        return 1
    return 0


def require_plugin_root_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session require-plugin-root", add_help=False)
    parser.parse_args(argv)
    return require_plugin_root()


def split_ancestor_tail(candidate: str) -> tuple[str, str]:
    path = candidate.rstrip("/") or "/"
    tail = ""
    while not Path(path).exists() and path != "/":
        base = Path(path).name
        if base:
            tail = f"{base}/{tail}" if tail else base
        path = str(Path(path).parent) or "/"
    return path, tail


def canonical_prefix(prefix: Path) -> str:
    try:
        value = prefix.resolve(strict=True) if prefix.is_dir() else prefix
    except OSError:
        value = prefix
    return f"{str(value).rstrip('/')}/"


def validate_design_tmpdir(candidate: str) -> tuple[bool, str]:
    if not candidate:
        return False, "design-tmpdir: path is required"
    if "\n" in candidate or "\r" in candidate:
        return False, "design-tmpdir: path must not contain newline or carriage return"
    if not candidate.startswith("/"):
        return False, "Invalid --design-tmpdir: must be an absolute path"
    if any(segment in {".", ".."} for segment in candidate.split("/") if segment):
        return False, "design-tmpdir: path must not contain '.' or '..' segments"
    ancestor, tail = split_ancestor_tail(candidate)
    try:
        resolved_ancestor = Path(ancestor).resolve(strict=True)
    except OSError:
        return False, "design-tmpdir: parent resolution failed"
    target = resolved_ancestor / tail if tail else resolved_ancestor
    cand = Path(candidate)
    if cand.exists():
        if cand.is_symlink() and not cand.is_dir():
            return False, "design-tmpdir: leaf symlink must resolve to a directory"
        if not cand.is_dir():
            return False, "design-tmpdir: path must name a directory"
        try:
            target = cand.resolve(strict=True)
        except OSError:
            if cand.is_symlink():
                return False, "design-tmpdir: leaf symlink must resolve to a directory"
    allow = [
        canonical_prefix(cache_sessions_root()),
        canonical_prefix(Path(os.environ["TMPDIR"])) if os.environ.get("TMPDIR") else "",
        canonical_prefix(Path(TMP_FALLBACK)),
    ]
    comparable = f"{str(target).rstrip('/')}/"
    if not any(prefix and comparable.startswith(prefix) for prefix in allow):
        return False, f"design-tmpdir: path not under allowlist after resolution: {target}"
    return True, ""


def validate_design_tmpdir_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session validate-design-tmpdir", add_help=False)
    parser.add_argument("path", nargs="?", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    plugin_rc = require_plugin_root()
    if plugin_rc != 0:
        return plugin_rc
    ok, message = validate_design_tmpdir(args.path)
    if not ok:
        print(message, file=sys.stderr)
        return 2
    return 0


def assert_no_symlink_path_or_ancestors(path: Path) -> None:
    current = path
    while True:
        if current.is_symlink():
            raise OSError(f"refusing symlinked path or ancestor: {current}")
        if current == current.parent:
            return
        current = current.parent


def write_id(output: Path) -> None:
    if not any(under(output, root) for root in allowed_roots()):
        raise OSError(f"output path not under allowed session root: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    parent = output.parent
    if not (parent.exists() and parent.is_dir() and not parent.is_symlink()):
        raise OSError(f"output parent is not a writable directory: {parent}")
    if output.is_file() and output.stat().st_size > 0:
        return
    check = output if output.is_absolute() else Path.cwd() / output
    assert_no_symlink_path_or_ancestors(check)
    result = subprocess.run(["uuidgen"], capture_output=True, text=True, check=False)  # noqa: S603, S607
    session_id = result.stdout.strip() if result.returncode == 0 else ""
    temp = output.with_suffix(output.suffix + ".tmp")
    temp.write_text((session_id or output.parent.name) + "\n", encoding="utf-8")
    temp.chmod(0o600)
    temp.replace(output)


def write_id_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session write-id", add_help=False)
    parser.add_argument("--output", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        print("FAILED=true")
        print("ERROR=unknown flag")
        return 1
    if not args.output:
        print("FAILED=true")
        print("ERROR=--output is required")
        return 1
    try:
        write_id(Path(args.output))
    except OSError as error:
        print("FAILED=true")
        print(f"ERROR={error}")
        return 1
    return 0


def first_raw_key(path: Path, key: str) -> str | None:
    text = path.read_bytes().decode("utf-8", errors="replace")
    if "\r" in text:
        raise ValueError(f"session env file contains carriage return: {path}")
    for line in text.split("\n"):
        name, separator, value = line.partition("=")
        if separator and name == key:
            return value
    return None


def implement_ttl() -> int:
    raw = os.environ.get("LARCH_IMPLEMENT_TMPDIR_TTL_SECONDS", str(IMPLEMENT_TMPDIR_TTL_SECONDS))
    return int(raw) if raw.isdigit() else IMPLEMENT_TMPDIR_TTL_SECONDS


def resolve_implement_tmpdir(hook_cwd: str, now: int) -> str:
    if not hook_cwd:
        return ""
    best = ""
    best_mtime = -1
    session_id = os.environ.get("LARCH_TOKEN_SESSION_ID", "")
    for root in implement_roots():
        try:
            candidates = list(root.glob("claude-implement-*")) if root.is_dir() else []
        except OSError:
            continue
        for candidate in candidates:
            try:
                if not candidate.is_dir():
                    continue
                sentinel = next(
                    (candidate / rel for rel in IMPLEMENT_SENTINEL_RELS if (candidate / rel).is_file()),
                    None,
                )
                if sentinel is None:
                    continue
                keepalive = candidate / ".larch-keepalive"
                if not keepalive.is_file():
                    continue
                if first_raw_key(keepalive, "CLONE_PATH") != hook_cwd:
                    continue
                session_match = False
                if session_id:
                    if first_raw_key(keepalive, "SESSION_ID") != session_id:
                        continue
                    session_match = True
                mtime = int(sentinel.stat().st_mtime)
            except (OSError, ValueError):
                continue
            if not session_match:
                ttl = implement_ttl()
                if ttl > 0 and (now <= 0 or now - mtime >= ttl):
                    continue
            text = str(candidate)
            if mtime > best_mtime or (mtime == best_mtime and (not best or text < best)):
                best_mtime, best = mtime, text
    return best


def resolve_implement_tmpdir_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session resolve-implement-tmpdir", add_help=False)
    parser.add_argument("--cwd", default="")
    try:
        args = parser.parse_args(argv)
        value = resolve_implement_tmpdir(args.cwd, int(datetime.now(tz=UTC).timestamp()))
    except (OSError, ValueError, SystemExit) as error:
        print(f"resolve-implement-tmpdir: {error}", file=sys.stderr)
        return 1
    if value:
        sys.stdout.write(value)
    return 0


def cleanup_tmpdir_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="session cleanup-tmpdir", add_help=False)
    parser.add_argument("--dir", dest="dir", default="")
    parser.add_argument("pos", nargs="?")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        print("Usage: cleanup-tmpdir.sh --dir <path>", file=sys.stderr)
        return 1
    target = args.dir or args.pos or ""
    if not target:
        print("ERROR: --dir is required and must be non-empty", file=sys.stderr)
        return 1
    if not any(strictly_under(Path(target), root) for root in allowed_roots()):
        print(
            f"ERROR: --dir must be under /tmp/, /private/tmp/, /var/folders/, or {cache_sessions_root()}/ (got: {target})",
            file=sys.stderr,
        )
        return 1
    audit_log = Path(os.environ.get("TMPDIR", TMP_FALLBACK)) / "larch-cleanup-audit.log"
    stamp = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    parent = "?"
    try:
        probe = subprocess.run(  # noqa: S603, S607
            ["ps", "-o", "comm=", "-p", str(os.getppid())], capture_output=True, text=True, check=False
        )
        parent = re.sub(r"\s+", "_", probe.stdout.strip()) or "?"
    except OSError:
        parent = "?"
    try:
        with audit_log.open("a", encoding="utf-8") as handle:
            handle.write(f"{stamp} pid={os.getpid()} ppid={os.getppid()} parent={parent} dir={target}\n")
    except OSError:
        pass
    path = Path(target)
    if not path.exists():
        return 0
    try:
        shutil.rmtree(path)
    except OSError as error:
        print(f"ERROR: cleanup-tmpdir failed: {error}", file=sys.stderr)
        return 1
    if path.exists():
        print(f"ERROR: cleanup-tmpdir failed: directory still exists: {target}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    command, *arguments = sys.argv[1:]
    handlers = {
        "require-plugin-root": require_plugin_root_main,
        "validate-design-tmpdir": validate_design_tmpdir_main,
        "write-id": write_id_main,
        "resolve-implement-tmpdir": resolve_implement_tmpdir_main,
        "cleanup-tmpdir": cleanup_tmpdir_main,
    }
    handler = handlers.get(command)
    return handler(arguments) if handler else 2


if __name__ == "__main__":
    raise SystemExit(main())
