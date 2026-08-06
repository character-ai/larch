#!/usr/bin/env python3
# pyright: reportPrivateUsage=false, reportArgumentType=false
# The run-log verbs deliberately reuse the shared private helpers in
# `larch.report.run_log_batch` / `run_log_manifest` rather than restating their
# behavior, and the manifest record crosses this module as an opaque value.
"""Verified-bootstrap test double for Rust-owned agent and run-log commands.

Python integration tests exercise their callers through ``scripts/larch.sh``,
which needs a version-matching executable that a Python-only test run does not
build. This executable supplies the narrow command behavior those caller tests
need; the real command contracts live in Rust integration tests
(``crates/larch-cli/tests/``).

The ``run-log`` verbs delegate to the surviving `larch.report.run_log_batch`
and `larch.report.run_log_manifest` helpers, which the still-Python flush,
archive, and publication verbs also use, so the double stays short and cannot
drift into a second implementation.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ARG_PAIR_SIZE = 2
ENV_CLAUDE_PLUGIN_ROOT = "CLAUDE_PLUGIN_ROOT"
GENERATORS_TSV_COLUMNS = 2
GIT = shutil.which("git") or "git"


def _plugin_root() -> Path:
    return Path(os.environ[ENV_CLAUDE_PLUGIN_ROOT])


def _version() -> str:
    manifest = _plugin_root() / ".claude-plugin" / "plugin.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    return str(payload["version"])


def _target() -> str:
    targets = {
        ("Darwin", "arm64"): "aarch64-apple-darwin",
        ("Darwin", "aarch64"): "aarch64-apple-darwin",
        ("Darwin", "x86_64"): "x86_64-apple-darwin",
        ("Darwin", "amd64"): "x86_64-apple-darwin",
        ("Linux", "arm64"): "aarch64-unknown-linux-gnu",
        ("Linux", "aarch64"): "aarch64-unknown-linux-gnu",
        ("Linux", "x86_64"): "x86_64-unknown-linux-gnu",
        ("Linux", "amd64"): "x86_64-unknown-linux-gnu",
    }
    return targets[(platform.system(), platform.machine())]


def _classify_path(path: str, generated: set[str]) -> str:
    if not path or path.startswith("/") or ".." in path:
        return "generic"
    if path in generated:
        return "generated-only"
    base = Path(path).name
    if (
        re.fullmatch(r"scripts/test-.*\.(?:sh|py)", path)
        or re.fullmatch(r"skills/[^/]+/scripts/test-.*\.sh", path)
        or re.fullmatch(r"[^/]+/(?:tests|test)/[^/]+\.(?:sh|py|go|bats)", path)
        or re.fullmatch(r"(?:test_.*|.*_test|.*\.test)\.(?:sh|py|go)", base)
        or base.endswith(".bats")
    ):
        return "test-only"
    if (
        re.fullmatch(r"docs/[^/]+\.(?:md|txt|rst|adoc)", path)
        or re.fullmatch(r"scripts/[^/]+\.md", path)
        or path in {"README.md", "SECURITY.md", "AGENTS.md", "CLAUDE.md", "KARPATHY_CLAUDE.md"}
    ):
        return "docs-only"
    return "generic"


def _classify(arguments: list[str]) -> int:
    if len(arguments) != 1:
        return 2
    diff = Path(arguments[0])
    if not diff.is_file():
        return 2
    manifest = _plugin_root() / "scripts" / "generators.tsv"
    generated = {
        columns[1]
        for line in manifest.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
        if len(columns := line.split("\t")) == GENERATORS_TSV_COLUMNS and columns[1]
    }
    mode = ""
    for line in diff.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.fullmatch(r"diff --git a/([^\s]+) b/([^\s]+)", line)
        if line.startswith("diff --git ") and match is None:
            print("DIFF_MODE=generic")
            return 0
        if match is None:
            continue
        old_mode = _classify_path(match.group(1), generated)
        new_mode = _classify_path(match.group(2), generated)
        if old_mode != new_mode or old_mode == "generic" or (mode and mode != old_mode):
            print("DIFF_MODE=generic")
            return 0
        mode = old_mode
    print(f"DIFF_MODE={mode or 'generic'}")
    return 0


def _wait(arguments: list[str]) -> int:
    timeout = 1_860
    sentinels = arguments[:]
    if len(sentinels) >= ARG_PAIR_SIZE and sentinels[0] == "--timeout":
        timeout = int(sentinels[1])
        sentinels = sentinels[2:]
    interval = float(os.environ.get("WAIT_FOR_REVIEWERS_POLL_INTERVAL", "5"))
    deadline = time.monotonic() + timeout
    while any(not Path(raw_path).is_file() for raw_path in sentinels) and time.monotonic() < deadline:
        time.sleep(min(interval, max(0.0, deadline - time.monotonic())))
    for index, raw_path in enumerate(sentinels, start=1):
        path = Path(raw_path)
        name = path.name.removesuffix(".done")
        if not path.is_file():
            print(f"TIMEOUT {index} {name}")
            continue
        code = "".join(path.read_text(encoding="utf-8", errors="replace").split())
        print(f"DONE {index} {name}: exit={code if code.isdigit() and code else 'unknown'}")
    return 0


def _git(arguments: list[str]) -> str:
    result = subprocess.run(  # lint-subprocess-via-runner: ok standalone bootstrap test double must not import the runtime package
        [GIT, *arguments], check=False, text=True, capture_output=True
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "git command failed")
    return result.stdout


def _gather(arguments: list[str]) -> int:
    if len(arguments) != ARG_PAIR_SIZE or arguments[0] != "--output-dir":
        return 1
    output = Path(arguments[1])
    if not output.is_dir():
        return 1
    try:
        origin_main = subprocess.run(  # lint-subprocess-via-runner: ok standalone bootstrap test double must not import the runtime package
            [GIT, "rev-parse", "--verify", "--quiet", "origin/main"],
            check=False,
            text=True,
            capture_output=True,
        )
        base = "origin/main" if origin_main.returncode == 0 and origin_main.stdout.strip() else "main"
        merge_base = _git(["merge-base", "HEAD", base]).strip()
        paths = ["--", ".", ":(exclude)larch-logs/**"]
        diff = _git(["diff", "-U20", f"{merge_base}...HEAD", *paths])
        file_list = _git(["diff", f"{merge_base}...HEAD", "--name-only", *paths])
        commit_log = _git(["log", f"{merge_base}..HEAD", "--oneline", *paths])
    except RuntimeError as error:
        print(f"gather-branch-context.sh: {error}", file=sys.stderr)
        return 1
    diff_file = output / "diff.txt"
    file_list_file = output / "file-list.txt"
    commit_log_file = output / "commit-log.txt"
    _ = diff_file.write_text(diff, encoding="utf-8")
    _ = file_list_file.write_text(file_list, encoding="utf-8")
    _ = commit_log_file.write_text(commit_log, encoding="utf-8")
    print(f"DIFF_FILE={diff_file}")
    print(f"FILE_LIST_FILE={file_list_file}")
    print(f"COMMIT_LOG_FILE={commit_log_file}")
    print(f"COMMIT_COUNT={len(commit_log.splitlines())}")
    return 0


def _compose(arguments: list[str]) -> int:
    values = dict(zip(arguments[::2], arguments[1::2], strict=False))
    record = values.get("--structured-record", "")
    output = values.get("--output", "")
    if not record or not output:
        return 2
    target = Path(output)
    _ = target.write_text(f"## Structured collector record\n\n{record}\n", encoding="utf-8")
    target.chmod(0o600)
    return 0


def _run_external_agent(arguments: list[str]) -> int:
    """Minimal Rust-command double for Python callers that retry an artifact."""
    output = ""
    capture_stdout = False
    capture_stdout_only = False
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--":
            index += 1
            break
        if argument == "--output" and index + 1 < len(arguments):
            output = arguments[index + 1]
            index += 2
        elif argument in {"--tool", "--timeout", "--stderr-sink"} and index + 1 < len(arguments):
            index += 2
        elif argument == "--capture-stdout":
            capture_stdout = True
            index += 1
        elif argument == "--capture-stdout-only":
            capture_stdout_only = True
            index += 1
        else:
            return 1
    command = arguments[index:]
    if not output or not command or Path(command[0]).name not in {"claude", "codex", "cursor"}:
        return 1
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    stdout_handle = target.open("wb") if capture_stdout or capture_stdout_only else None
    stderr_handle = target.with_suffix(target.suffix + ".diag").open("wb") if capture_stdout_only else None
    try:
        result = subprocess.run(
            command,
            check=False,
            stdout=stdout_handle,
            stderr=subprocess.STDOUT if capture_stdout else stderr_handle,
        )
    finally:
        if stdout_handle is not None:
            stdout_handle.close()
        if stderr_handle is not None:
            stderr_handle.close()
    _ = target.with_suffix(target.suffix + ".done").write_text(
        f"{result.returncode}\n", encoding="utf-8"
    )
    return result.returncode


def _flag(arguments: list[str], name: str, default: str = "") -> str:
    """Read one long option, accepting both the split and inline `=` spellings."""
    for index, token in enumerate(arguments):
        if token == name and index + 1 < len(arguments):
            return arguments[index + 1]
        if token.startswith(f"{name}="):
            return token[len(name) + 1 :]
    return default


def _append_execution_issue(*, log: Path, category: str, entry: str) -> None:
    """Append `entry` under `### category`, matching the Rust composer."""
    log.parent.mkdir(parents=True, exist_ok=True)
    text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    header = f"### {category}"
    lines = text.splitlines()
    if header in lines:
        out: list[str] = []
        inserted = False
        in_target = False
        for line in lines:
            if line == header:
                in_target = True
                out.append(line)
                continue
            if in_target and line.startswith("### "):
                if not inserted:
                    out.extend(["", entry.rstrip("\n")])
                    inserted = True
                in_target = False
            out.append(line)
        if in_target and not inserted:
            out.extend(["", entry.rstrip("\n")])
        rendered = "\n".join(out) + "\n"
    else:
        prefix = "\n" if text else ""
        rendered = text.rstrip("\n") + prefix + header + "\n\n" + entry.rstrip("\n") + "\n"
    _ = log.write_text(rendered, encoding="utf-8")


def _bind_larch_package() -> None:
    """Make `larch.*` importable in this detached bootstrap process.

    The double is executed by `scripts/larch.sh`, which exports the plugin root
    but no `PYTHONPATH`, so the shared run-log helpers need an explicit path.
    """
    package_root = str(_plugin_root() / "python")
    if package_root not in sys.path:
        sys.path.insert(0, package_root)


def _log_envelope(*, path: Path | None, written: bool, unchanged: bool, error: str = "") -> None:
    size = path.stat().st_size if path is not None and path.is_file() else 0
    digest = ""
    if path is not None and path.is_file():
        import hashlib  # noqa: PLC0415 - deferred so the module imports without the runtime package

        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    print(f"LOG_WRITTEN={'true' if written else 'false'}")
    print(f"LOG_PATH={path if path is not None else ''}")
    print(f"BYTES={size}")
    print(f"SHA256={digest}")
    print("COMMIT_SHA=")
    print(f"UNCHANGED={'true' if unchanged else 'false'}")
    if error:
        print(f"ERROR={error}")


def _identity(arguments: list[str]) -> tuple[Path, str, str]:
    _bind_larch_package()
    from larch.report import run_log_batch  # noqa: PLC0415 - deferred until _bind_larch_package puts the package on sys.path

    log_root = run_log_batch._resolve_log_root(_flag(arguments, "--log-root"))  # noqa: SLF001 - test double reuses the shared resolver
    return log_root, _flag(arguments, "--skill"), _flag(arguments, "--run-id")


def _run_log_init(arguments: list[str]) -> int:
    _bind_larch_package()
    from larch.report import run_log_manifest  # noqa: PLC0415 - deferred until _bind_larch_package puts the package on sys.path

    log_root, skill, run_id = _identity(arguments)
    path = run_log_manifest._manifest_cli_path(log_root=log_root, skill=skill, run_id=run_id)  # noqa: SLF001 - test double reuses the shared path owner
    if path.is_file():
        _log_envelope(path=path, written=False, unchanged=True)
        return 0
    issue = _flag(arguments, "--issue")
    if issue and not issue.isdigit():
        _log_envelope(path=None, written=False, unchanged=False, error=f"invalid issue: {issue}")
        return 1
    manifest = run_log_manifest.Manifest.synthesize_v2(
        skill=skill,
        run_id=run_id,
        extra={
            "parent_skill": _flag(arguments, "--parent-skill") or None,
            "parent_run_id": _flag(arguments, "--parent-run-id") or None,
            "issue_number": int(issue) if issue else None,
        },
    )
    run_log_manifest._write_manifest_v2(path=path, data=manifest.to_json(existing=None))  # noqa: SLF001 - test double reuses the shared writer
    _log_envelope(path=path, written=True, unchanged=False)
    return 0


def _run_log_batch_command(arguments: list[str], *, append: bool) -> int:
    _bind_larch_package()
    from larch.report import run_log_batch  # noqa: PLC0415 - deferred until _bind_larch_package puts the package on sys.path

    log_root, skill, run_id = _identity(arguments)
    batch = _flag(arguments, "--batch")
    source = _flag(arguments, "--record-file" if append else "--input-file")
    writer = run_log_batch._append_batch if append else run_log_batch._write_batch  # noqa: SLF001 - test double reuses the shared batch writers
    key = "record_file" if append else "input_file"
    try:
        path, written, unchanged = writer(
            log_root=log_root, skill=skill, run_id=run_id, batch=batch, **{key: source}
        )
    except ValueError as error:
        _log_envelope(path=None, written=False, unchanged=False, error=str(error))
        return 1
    except OSError as error:
        _log_envelope(path=None, written=False, unchanged=False, error=str(error))
        return 2
    _log_envelope(path=path, written=written, unchanged=unchanged)
    return 0


def _run_log_write(arguments: list[str]) -> int:
    return _run_log_batch_command(arguments, append=False)


def _run_log_append(arguments: list[str]) -> int:
    return _run_log_batch_command(arguments, append=True)


def _run_log_exists(arguments: list[str]) -> int:
    _bind_larch_package()
    from larch.report import run_log_batch  # noqa: PLC0415 - deferred until _bind_larch_package puts the package on sys.path

    log_root, skill, run_id = _identity(arguments)
    batch = _flag(arguments, "--batch")
    if batch not in run_log_batch._LARCH_LOG_BATCHES:  # noqa: SLF001 - test double reuses the shared registry
        _log_envelope(path=None, written=False, unchanged=False, error=f"unknown batch: {batch}")
        return 1
    path = run_log_batch._batch_path(log_root=log_root, skill=skill, run_id=run_id, batch=batch)  # noqa: SLF001 - test double reuses the shared path owner
    _log_envelope(path=path, written=False, unchanged=path.exists())
    return 0


def _run_log_write_round(arguments: list[str]) -> int:
    _bind_larch_package()
    from larch.report import run_log_batch  # noqa: PLC0415 - deferred until _bind_larch_package puts the package on sys.path

    log_root, skill, run_id = _identity(arguments)
    round_number = _flag(arguments, "--round")
    source = Path(_flag(arguments, "--source-dir"))
    if not round_number.isdigit() or int(round_number) <= 0:
        _log_envelope(path=None, written=False, unchanged=False, error="--round must be a positive integer")
        return 1
    if not source.is_dir():
        _log_envelope(path=None, written=False, unchanged=False, error=f"source directory not found: {source}")
        return 1
    dest = run_log_batch._run_dir(log_root=log_root, skill=skill, run_id=run_id) / f"round-{round_number}"  # noqa: SLF001 - test double reuses the shared path owner
    dest.mkdir(parents=True, exist_ok=True)
    written = False
    for item in sorted(source.iterdir()):
        if not item.is_file() or item.is_symlink():
            continue
        name = item.name
        if run_log_batch._is_round_sidecar_file(name) or not run_log_batch._round_artifact_included(name):  # noqa: SLF001 - test double reuses the shared filters
            continue
        content = run_log_batch._stage_round_artifact(src=item, name=name)  # noqa: SLF001 - test double reuses the shared staging transform
        out = dest / name
        if not out.exists() or out.read_text(encoding="utf-8", errors="replace") != content:
            run_log_batch._atomic_write(path=out, content=content)  # noqa: SLF001 - test double reuses the shared writer
            written = True
    _log_envelope(path=dest, written=written, unchanged=not written)
    return 0


def _missing_required_files(*, run_dir: Path, manifest_tsv: Path, manifest: object) -> list[str]:
    """Return the reachable required-file rows that are absent from `run_dir`."""
    from larch.report import run_log_manifest  # noqa: PLC0415 - deferred until _bind_larch_package puts the package on sys.path

    missing: list[str] = []
    for line in manifest_tsv.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if not parts or parts[0] == "relative_path":
            continue
        relative_path = parts[0]
        if not run_log_manifest._verify_condition_reached(  # noqa: SLF001 - test double reuses the shared reachability chain
            condition=parts[1] if len(parts) > 1 else "always",
            run_dir=run_dir,
            manifest_data=manifest,
            manifest_status=run_log_manifest._manifest_field(manifest=manifest, key="status"),  # noqa: SLF001 - test double reuses the shared field reader
            manifest_pr_number=run_log_manifest._manifest_field(manifest=manifest, key="pr_number"),  # noqa: SLF001 - test double reuses the shared field reader
        ):
            continue
        if "*" in relative_path:
            if not any(hit.is_file() for hit in run_dir.glob(relative_path)):
                missing.append(relative_path)
        elif not (run_dir / relative_path).is_file():
            missing.append(relative_path)
    return missing


def _run_log_verify_completeness(arguments: list[str]) -> int:
    _bind_larch_package()
    from larch.report import run_log_manifest  # noqa: PLC0415 - deferred until _bind_larch_package puts the package on sys.path

    if not arguments:
        print("MISSING=manifest", file=sys.stderr)
        return 1
    run_dir = Path(arguments[0])
    if not run_dir.is_dir():
        print(f"verify-completeness: run dir not found: {run_dir}", file=sys.stderr)
        return 1
    manifest_tsv = Path(
        os.environ.get("LARCH_VERIFY_MANIFEST")
        or _plugin_root() / "docs" / "run-logs-required-files.tsv"
    )
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file() or not manifest_tsv.is_file():
        print("MISSING=manifest")
        return 1
    try:
        manifest = run_log_manifest.Manifest.from_json(run_log_manifest._read_manifest_v2(manifest_path))  # noqa: SLF001 - test double reuses the shared reader
    except (OSError, json.JSONDecodeError, TypeError):
        print("MISSING=manifest")
        return 1
    missing = _missing_required_files(run_dir=run_dir, manifest_tsv=manifest_tsv, manifest=manifest)
    if missing:
        print("MISSING=" + ",".join(missing))
        return 1
    print("OK")
    return 0


def _retry_suffix(retry_count: str, transient_retry_count: str) -> str:
    """Mirror the Rust owner's retry annotation; both counters include attempt 1."""
    if retry_count and transient_retry_count:
        parts = [
            f"{label}={value}"
            for label, value in (
                ("auth-retries", int(retry_count) - 1),
                ("transient-retries", int(transient_retry_count) - 1),
            )
            if value > 0
        ]
        return ", " + ", ".join(parts) if parts else ""
    return f", retries={retry_count}" if retry_count else ""


def _append_failure(arguments: list[str]) -> int:
    log = Path(_flag(arguments, "--log"))
    category = _flag(arguments, "--category")
    if not log.name or not category:
        print("FAILED=true")
        return 1
    exit_code = _flag(arguments, "--exit-code")
    output_file = Path(_flag(arguments, "--output-file"))
    body = (
        output_file.read_text(encoding="utf-8", errors="replace")
        if output_file.is_file() and output_file.stat().st_size
        else f"no diagnostics captured (exit {exit_code})\n"
    )
    verdict = _flag(arguments, "--verdict")
    suffix = f", {verdict}" if verdict else ""
    suffix += _retry_suffix(
        _flag(arguments, "--retry-count"), _flag(arguments, "--transient-retry-count")
    )
    entry = (
        f"- **Step {_flag(arguments, '--site')}: {_flag(arguments, '--tool')} "
        f"{_flag(arguments, '--status-label', 'failed')} (exit {exit_code}{suffix})**:\n"
        "  ```\n"
        f"{body.rstrip()}\n"
        "  ```\n"
    )
    _append_execution_issue(log=log, category=category, entry=entry)
    print("APPENDED=true")
    print(f"LOG={log}")
    return 0


def _append_entry(arguments: list[str]) -> int:
    log = Path(_flag(arguments, "--log"))
    category = _flag(arguments, "--category")
    entry_file = _flag(arguments, "--entry-file")
    entry = (
        Path(entry_file).read_text(encoding="utf-8", errors="replace")
        if entry_file
        else _flag(arguments, "--entry")
    )
    if not log.name or not category or not entry:
        print("FAILED=true")
        return 1
    _append_execution_issue(log=log, category=category, entry=entry)
    print("APPENDED=true")
    print(f"LOG={log}")
    return 0


def main(arguments: list[str]) -> int:
    result = 2
    if arguments == ["--version"]:
        print(f"larch {_version()}")
        result = 0
    elif arguments == ["bootstrap", "self-check"]:
        print(json.dumps({"schema_version": 1, "version": _version(), "target": _target()}, separators=(",", ":")))
        result = 0
    else:
        handlers = {
            ("agent", "classify-diff"): _classify,
            ("agent", "wait-reviewers"): _wait,
            ("agent", "gather-branch-context"): _gather,
            ("agent", "compose-collector-failure-log"): _compose,
            ("agent", "run-external-agent"): _run_external_agent,
            ("run-log", "append-failure"): _append_failure,
            ("run-log", "append-entry"): _append_entry,
            ("run-log", "init"): _run_log_init,
            ("run-log", "write"): _run_log_write,
            ("run-log", "append"): _run_log_append,
            ("run-log", "exists"): _run_log_exists,
            ("run-log", "write-round"): _run_log_write_round,
            ("run-log", "verify-completeness"): _run_log_verify_completeness,
        }
        handler = handlers.get((arguments[0], arguments[1])) if len(arguments) >= ARG_PAIR_SIZE else None
        if handler is not None:
            result = handler(arguments[2:])
    return result


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
