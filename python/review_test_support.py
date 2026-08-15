"""Shared helpers for review CLI pytest harnesses."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "python" / "cli.py"
GIT = shutil.which("git") or "git"


def run_review(
    *args: str,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    quiet_disable: bool = True,
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    for key in ("IMPLEMENT_TMPDIR", "SESSION_ENV_PATH"):
        _ = merged.pop(key, None)
    if quiet_disable:
        merged["LARCH_QUIET_DISABLE"] = "1"
    else:
        _ = merged.pop("LARCH_QUIET_DISABLE", None)
    if env:
        merged.update(env)
    migrated = {"aggregate-findings", "prune-nit-findings", "reviewer-prune"}
    if args and args[0] in migrated:
        _ = merged.setdefault("CLAUDE_PLUGIN_ROOT", str(ROOT))
        return subprocess.run(
            [str(ROOT / "scripts" / "larch.sh"), "review", *args],
            cwd=cwd or ROOT,
            env=merged,
            text=True,
            capture_output=True,
            check=False,
        )
    return subprocess.run(
        [sys.executable, str(CLI), "review", *args],
        cwd=cwd or ROOT,
        env=merged,
        text=True,
        capture_output=True,
        check=False,
    )


def kv_get(*, stdout: str, key: str) -> str | None:
    prefix = f"{key}="
    for line in stdout.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    return None


def write_executable(*, path: Path, body: str) -> None:
    _ = path.write_text(body, encoding="utf-8")
    path.chmod(0o755)



def write_aggregate_dispatch_stub(path: Path, *, merge_kind: str = "merge", mode: str = "ok") -> None:
    exhausted_output = """Aggregator narrative: pseudo-heading plus attestation must fail validation.

### FINDING_1 not-a-valid-heading-line

LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED

"""
    write_executable(
        path=path,
        body=f"""#!/usr/bin/env bash
set -euo pipefail
slots=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slots-file) slots="${{2:?}}"; shift 2 ;;
    --codex-present|--cursor-present|--mode|--diff-file|--plan-file|--feature-file|--scope-files|--description-text) shift 2 ;;
    --require-result-pattern) shift 2 ;;
    *) shift 1 ;;
  esac
done
[[ -n "$slots" && -f "$slots" ]] || exit 2
out=$(jq -r '.output' "$slots")
stub_mode="{mode}"
case "$stub_mode" in
  fail_dispatch)
    printf 'DISPATCH_OK=false\\nALL_OUTPUT_FILES=\\nALL_OUTPUT_FILES_PATH=\\nALL_OUTPUT_TOOLS=\\n'
    ;;
  ok)
    case "{merge_kind}" in
      merge)
        cat > "$out" <<'EOF'
### FINDING_1: merged title
- **Reviewer(s)**: cursor-a-output.txt, cursor-b-output.txt, cursor-c-output.txt
- **Severity**: nit
- **Concern**: normalized concern
- **Suggested revision**: fix

EOF
        ;;
      malformed)
        cat > "$out" <<'EOF'
### FINDING_1: bad
- **Concern**: missing reviewer line
- **Suggested revision**: n/a

EOF
        ;;
      validation_exhausted)
        cat > "$out" <<'EOF'
{exhausted_output.rstrip()}
EOF
        ;;
    esac
    paths_out="${{slots}}.output-files"
    printf '%s\\n' "$out" > "$paths_out"
    printf 'DISPATCH_OK=true\\nALL_OUTPUT_FILES=%s\\nALL_OUTPUT_FILES_PATH=%s\\nALL_OUTPUT_TOOLS=cursor\\n' "$out" "$paths_out"
    ;;
esac
""",
    )


def write_aggregate_counting_dispatch_stub(
    path: Path,
    *,
    counter_file: Path,
    fail_attempts: int,
    fail_body: str,
    success_body: str,
    env_log: Path | None = None,
) -> None:
    """Dispatch stub that emits ``fail_body`` for the first ``fail_attempts`` invocations, then
    ``success_body``. Each invocation increments ``counter_file`` so a test can assert how many
    aggregator dispatches the bounded validation-retry loop performed. When supplied, ``env_log``
    records the panel-payload byte count for each invocation.
    """
    env_log_write = (
        f'printf \'%s\\n\' "${{LARCH_PANEL_PAYLOAD_BYTES:-0}}" >> "{env_log}"\n'
        if env_log is not None
        else ""
    )
    write_executable(
        path=path,
        body=f"""#!/usr/bin/env bash
set -euo pipefail
slots=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slots-file) slots="${{2:?}}"; shift 2 ;;
    --require-result-pattern) shift 2 ;;
    --codex-present|--cursor-present|--mode|--diff-file|--plan-file|--feature-file|--scope-files|--description-text) shift 2 ;;
    *) shift 1 ;;
  esac
done
[[ -n "$slots" && -f "$slots" ]] || exit 2
out=$(jq -r '.output' "$slots")
counter="{counter_file}"
n=0
[[ -f "$counter" ]] && n=$(cat "$counter")
n=$((n + 1))
printf '%s' "$n" > "$counter"
{env_log_write}if [[ "$n" -le {fail_attempts} ]]; then
  cat > "$out" <<'FAILBODY'
{fail_body}
FAILBODY
else
  cat > "$out" <<'OKBODY'
{success_body}
OKBODY
fi
paths_out="${{slots}}.output-files"
printf '%s\\n' "$out" > "$paths_out"
printf 'DISPATCH_OK=true\\nALL_OUTPUT_FILES=%s\\nALL_OUTPUT_FILES_PATH=%s\\nALL_OUTPUT_TOOLS=cursor\\n' "$out" "$paths_out"
""",
    )


def init_git_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _ = subprocess.run([GIT, "init", "-q"], cwd=path, check=True)
    _ = subprocess.run([GIT, "config", "user.email", "test@example.com"], cwd=path, check=True)
    _ = subprocess.run([GIT, "config", "user.name", "Test User"], cwd=path, check=True)
    _ = subprocess.run([GIT, "config", "commit.gpgsign", "false"], cwd=path, check=True)
    _ = (path / "src").mkdir(exist_ok=True)
    _ = (path / "src" / "main.py").write_text("original\n", encoding="utf-8")
    _ = subprocess.run([GIT, "add", "src/main.py"], cwd=path, check=True)
    _ = subprocess.run([GIT, "commit", "-qm", "init"], cwd=path, check=True)
    _ = (path / "src" / "main.py").write_text("changed\n", encoding="utf-8")
    _ = subprocess.run([GIT, "add", "src/main.py"], cwd=path, check=True)
    _ = subprocess.run([GIT, "commit", "-qm", "feature"], cwd=path, check=True)
