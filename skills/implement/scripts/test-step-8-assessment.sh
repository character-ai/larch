#!/usr/bin/env bash
# test-step-8-assessment.sh — offline harness for Step 8 assessment bgjob adapter.
# shellcheck disable=SC2016 # single-quoted strings are intentional source literals.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/step-8-assessment.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
PASS=0
FAIL=0
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-step-8-assessment.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

pass() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains() {
  local n=$1 h=$2 l=$3
  if printf '%s' "$h" | grep -Fq -- "$n"; then pass "$l"; else fail "$l (missing: $n)"; fi
}
assert_not_contains() {
  local n=$1 h=$2 l=$3
  if printf '%s' "$h" | grep -Fq -- "$n"; then fail "$l (unexpected: $n)"; else pass "$l"; fi
}
assert_rc() {
  local a=$1 e=$2 l=$3
  if [ "$a" -eq "$e" ]; then pass "$l"; else fail "$l (expected rc=$e got rc=$a)"; fi
}
assert_no_raw_stderr() {
  local dir=$1 label=$2 found
  found=$(find "$dir" -maxdepth 1 -name 'architectural-assessment-stderr.*' -print -quit)
  if [ -z "$found" ]; then pass "$label"; else fail "$label (found: $found)"; fi
}

# --- static pins ---
helper_text=$(cat "$HELPER")
assert_contains 'bgjob start' "$helper_text" 'static: foreground wrapper starts bgjob'
assert_contains 'STEP="implement-step8-assessment"' "$helper_text" 'static: bgjob step slug pinned'
assert_contains '--budget-s "$BUDGET_S"' "$helper_text" 'static: budget var used on start'
assert_contains 'BUDGET_S=5700' "$helper_text" 'static: --budget-s 5700 pin via BUDGET_S'
assert_contains '--bgjob-child' "$helper_text" 'static: bgjob child argv present'
assert_contains 'architectural-assessment run' "$helper_text" 'static: child invokes Piece 2 CLI'
assert_contains 'ASSESSMENT_ERROR=active-stale-identity-mismatch' "$helper_text" 'static: active stale mismatch error'
assert_contains 'max-wait-s 0' "$helper_text" 'static: zero-duration rejoin probe'
assert_contains 'WAIT_CHUNK_S=270' "$helper_text" 'static: blocking wait chunk'
assert_contains 'normalize_kinds' "$helper_text" 'static: imports Piece 2 normalize_kinds'
assert_contains 'validate_materialization' "$helper_text" 'static: imports Piece 2 validate_materialization'
assert_not_contains 'next_untried_tier' "$helper_text" 'static: adapter does not select model lanes'
assert_not_contains 'CODEX_BINARY_FOUND' "$helper_text" 'static: adapter does not probe Codex availability'
assert_not_contains 'CURSOR_BINARY_FOUND' "$helper_text" 'static: adapter does not probe Cursor availability'
assert_not_contains 'CLAUDE_BINARY_FOUND' "$helper_text" 'static: adapter does not probe Claude availability'
assert_contains 'PYTHONPATH="$CLAUDE_PLUGIN_ROOT/python' "$helper_text" 'static: exports plugin PYTHONPATH'
assert_contains 'os.fdopen(int(sys.argv[1]), "wb", closefd=False)' "$helper_text" 'static: child writes stderr through inherited descriptor'
assert_not_contains 'Path(sys.argv[1]).open("wb")' "$helper_text" 'static: child cannot recreate removed stderr path'
assert_not_contains 'declare -A' "$helper_text" 'static: no associative arrays'
assert_not_contains 'nameref' "$helper_text" 'static: no namerefs'
assert_not_contains 'mapfile' "$helper_text" 'static: no mapfile'

# --- fake plugin + stub modules ---
FAKE_PLUGIN="$TMP_ROOT/plugin"
mkdir -p "$FAKE_PLUGIN/python/larch/bgjob" "$FAKE_PLUGIN/python/larch/implement" \
  "$FAKE_PLUGIN/skills/implement/scripts"
cp "$HELPER" "$FAKE_PLUGIN/skills/implement/scripts/step-8-assessment.sh"
chmod +x "$FAKE_PLUGIN/skills/implement/scripts/step-8-assessment.sh"
# Point SCRIPT_DIR resolution: run the copy under fake plugin so child argv uses fake path,
# OR run real helper with CLAUDE_PLUGIN_ROOT=fake. Child argv embeds SCRIPT_DIR of the
# invoked script — use the real helper path and stub cli to rewrite child execution.
HELPER_UNDER_TEST="$HELPER"

cat >"$FAKE_PLUGIN/python/larch/__init__.py" <<'PY'
# stub package
PY
cat >"$FAKE_PLUGIN/python/larch/bgjob/__init__.py" <<'PY'
# stub package
PY
cat >"$FAKE_PLUGIN/python/larch/implement/__init__.py" <<'PY'
# stub package
PY

cat >"$FAKE_PLUGIN/python/larch/implement/architectural_assessment.py" <<'PY'
"""Harness stub for Piece 2 normalize_kinds / validate_materialization."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


_KIND_ORDER = ("invariants", "guidelines")


@dataclass(frozen=True)
class MaterializedEvidence:
    kind: str
    head_sha: str
    base_ref: str
    diff_path: Path
    diff_text: str
    diff_fingerprint: str
    knowledge_path: Path
    knowledge_sha256: str
    identifiers: frozenset[str]


def normalize_kinds(raw_kinds):
    requested = set(raw_kinds)
    supported = set(_KIND_ORDER)
    if not requested:
        raise ValueError("at least one --kind is required")
    unknown = requested - supported
    if unknown:
        raise ValueError(f"unsupported assessment kind: {sorted(unknown)[0]}")
    return tuple(kind for kind in _KIND_ORDER if kind in requested)


def validate_materialization(*, kind: str, repo_root: Path, implement_tmpdir: Path) -> MaterializedEvidence:
    meta = implement_tmpdir / f"architectural-{kind if kind != 'guidelines' else 'guideline'}-materialize.env"
    if kind == "invariants":
        meta = implement_tmpdir / "architectural-invariant-materialize.env"
    else:
        meta = implement_tmpdir / "architectural-guideline-materialize.env"
    if meta.is_symlink() or not meta.is_file():
        raise ValueError(f"invalid materialization for {kind}")
    rows = {}
    for line in meta.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        rows[key] = value
    for key in ("HEAD_SHA", "BASE_REF", "DIFF_FINGERPRINT"):
        if not rows.get(key):
            raise ValueError(f"incomplete {kind} materialization metadata")
    return MaterializedEvidence(
        kind=kind,
        head_sha=rows["HEAD_SHA"],
        base_ref=rows["BASE_REF"],
        diff_path=implement_tmpdir / "diff.txt",
        diff_text="",
        diff_fingerprint=rows["DIFF_FINGERPRINT"],
        knowledge_path=repo_root / "ARCH.txt",
        knowledge_sha256="0" * 64,
        identifiers=frozenset(),
    )
PY

cat >"$FAKE_PLUGIN/python/larch/bgjob/registry.py" <<'PY'
"""Harness stub registry controlled by IMPLEMENT_TMPDIR/.test-registry-state."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass
class _Liveness:
    live: bool
    reason: str = "ok"


@dataclass
class _Entry:
    result_env: Path


def read_for(*, tmpdir: Path, step: str, run_id: str | None = None):
    state_path = tmpdir / ".test-registry-state"
    state = state_path.read_text(encoding="utf-8").strip() if state_path.is_file() else "absent"
    path = tmpdir / "bgjob" / f"{step}.registry.env"
    if state == "absent":
        return path, None
    entry = _Entry(result_env=tmpdir / "bgjob" / f"{step}.result.env")
    return path, entry


def child_liveness(entry):
    tmpdir = Path(os.environ["IMPLEMENT_TMPDIR"])
    state = (tmpdir / ".test-registry-state").read_text(encoding="utf-8").strip()
    return _Liveness(live=(state == "live"))


def daemon_liveness(entry):
    return child_liveness(entry)


def unlink_entry(path: Path) -> None:
    if path.is_symlink():
        return
    try:
        path.unlink()
    except FileNotFoundError:
        pass
PY

# Shared stub cli.py — behavior driven by control files under IMPLEMENT_TMPDIR.
cat >"$FAKE_PLUGIN/python/cli.py" <<'PY'
#!/usr/bin/env python3
"""Harness stub cli for bgjob + architectural-assessment."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _impl() -> Path:
    return Path(os.environ["IMPLEMENT_TMPDIR"])


def _log(name: str, text: str) -> None:
    path = _impl() / name
    path.write_text(text if not path.exists() else path.read_text(encoding="utf-8") + text, encoding="utf-8")


def bgjob_start(argv: list[str]) -> int:
    _log("bgjob-start-argv.txt", "\n".join(argv) + "\n---\n")
    # Record whether architectural-assessment appears in start argv (must not).
    if "architectural-assessment" in argv:
        (_impl() / "bad-direct-assessment-start.txt").write_text("yes\n", encoding="utf-8")
    step = ""
    budget = ""
    merge = ""
    i = 0
    while i < len(argv):
        if argv[i] == "--step" and i + 1 < len(argv):
            step = argv[i + 1]
        if argv[i] == "--budget-s" and i + 1 < len(argv):
            budget = argv[i + 1]
        if argv[i] == "--merge-result-env" and i + 1 < len(argv):
            merge = argv[i + 1]
        i += 1
    (_impl() / "bgjob-start-meta.txt").write_text(
        f"STEP={step}\nBUDGET={budget}\nMERGE={merge}\n", encoding="utf-8"
    )
    # Optionally run child inline when control says so.
    mode = (_impl() / ".test-start-mode").read_text(encoding="utf-8").strip() if (_impl() / ".test-start-mode").is_file() else "record-only"
    if mode == "run-child":
        # Find --bgjob-child script path after --
        if "--" in argv:
            child = argv[argv.index("--") + 1 :]
            env = os.environ.copy()
            # Execute child with same env; child writes merge-result.
            import subprocess

            completed = subprocess.run(child, env=env, check=False, capture_output=True, text=True)
            (_impl() / "child-stdout.txt").write_text(completed.stdout, encoding="utf-8")
            (_impl() / "child-stderr.txt").write_text(completed.stderr, encoding="utf-8")
            (_impl() / "child-rc.txt").write_text(str(completed.returncode), encoding="utf-8")
            # Synthesize result env from merge env on success-ish paths.
            merge_path = Path(merge) if merge else None
            result = _impl() / "bgjob" / "implement-step8-assessment.result.env"
            rows = {}
            if merge_path and merge_path.is_file():
                for line in merge_path.read_text(encoding="utf-8").splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        rows[k] = v
            rc = "0" if completed.returncode == 0 else "1"
            if (_impl() / ".test-force-bgjob-rc").is_file():
                rc = (_impl() / ".test-force-bgjob-rc").read_text(encoding="utf-8").strip()
            body = [
                f"BGJOB_RC={rc}",
                "STEP=implement-step8-assessment",
            ]
            for key in (
                "ASSESSMENT_REQUESTED_KINDS",
                "ASSESSMENT_COVERED_FINGERPRINT",
                "ASSESSMENT_STATUS",
                "ASSESSMENT_ATTEMPT",
                "ASSESSMENT_RESULTS",
                "ASSESSMENT_CHILD_DETAIL",
            ):
                if key in rows:
                    body.append(f"{key}={rows[key]}")
            result.write_text("\n".join(body) + "\n", encoding="utf-8")
            # Mark registry dead after child completes.
            (_impl() / ".test-registry-state").write_text("absent\n", encoding="utf-8")
    print(f"BGJOB_STATUS=STARTED STEP=implement-step8-assessment PGID=4242")
    return 0


def bgjob_wait(argv: list[str]) -> int:
    _log("bgjob-wait-argv.txt", "\n".join(argv) + "\n---\n")
    max_wait = "270"
    if "--max-wait-s" in argv:
        max_wait = argv[argv.index("--max-wait-s") + 1]
    counter_path = _impl() / ".test-wait-count"
    count = int(counter_path.read_text(encoding="utf-8")) if counter_path.is_file() else 0
    count += 1
    counter_path.write_text(str(count), encoding="utf-8")
    script = (_impl() / ".test-wait-script").read_text(encoding="utf-8").splitlines() if (_impl() / ".test-wait-script").is_file() else []
    # Each line: COUNT:STATUS[:RC]
    for line in script:
        if not line or line.startswith("#"):
            continue
        parts = line.split(":", 2)
        if int(parts[0]) != count:
            continue
        status = parts[1]
        rc = parts[2] if len(parts) > 2 else "0"
        if status == "WAIT":
            print("BGJOB_STATUS=WAIT")
            print("ELAPSED_S=0")
            return 0
        if status == "DEAD":
            print("BGJOB_STATUS=DEAD")
            print("BGJOB_DIAG=daemon-dead")
            return 0
        # DONE: emit from result env when present
        result = _impl() / "bgjob" / "implement-step8-assessment.result.env"
        print("BGJOB_STATUS=DONE")
        print(f"BGJOB_RC={rc}")
        print("STEP=implement-step8-assessment")
        if result.is_file():
            for row in result.read_text(encoding="utf-8").splitlines():
                if row.startswith("ASSESSMENT_") or row.startswith("STEP="):
                    print(row)
        return 0
    # Default: DONE from result env
    result = _impl() / "bgjob" / "implement-step8-assessment.result.env"
    rc = "0"
    if result.is_file():
        for row in result.read_text(encoding="utf-8").splitlines():
            if row.startswith("BGJOB_RC="):
                rc = row.split("=", 1)[1]
    print("BGJOB_STATUS=DONE")
    print(f"BGJOB_RC={rc}")
    print("STEP=implement-step8-assessment")
    if result.is_file():
        for row in result.read_text(encoding="utf-8").splitlines():
            if row.startswith("ASSESSMENT_"):
                print(row)
    return 0


def assessment_run(argv: list[str]) -> int:
    _log("assessment-run-argv.txt", "\n".join(argv) + "\n---\n")
    (_impl() / "assessment-run-called.txt").write_text("yes\n", encoding="utf-8")
    canned = _impl() / ".test-assessment-stdout"
    stderr = _impl() / ".test-assessment-stderr"
    if stderr.is_file():
        sys.stderr.write(stderr.read_text(encoding="utf-8"))
    stderr_bytes = _impl() / ".test-assessment-stderr-bytes"
    if stderr_bytes.is_file():
        sys.stderr.buffer.write(b"x" * int(stderr_bytes.read_text(encoding="utf-8").strip()))
    sleep_for = _impl() / ".test-assessment-sleep"
    if sleep_for.is_file():
        import time
        time.sleep(float(sleep_for.read_text(encoding="utf-8").strip()))
    if (_impl() / ".test-corrupt-merge").is_file():
        merge = _impl() / "bgjob" / "implement-step8-assessment.merge.env"
        merge.unlink(missing_ok=True)
        merge.mkdir()
    if canned.is_file():
        sys.stdout.write(canned.read_text(encoding="utf-8"))
        rc_file = _impl() / ".test-assessment-rc"
        return int(rc_file.read_text(encoding="utf-8").strip()) if rc_file.is_file() else 0
    print("ARCHITECTURAL_ASSESSMENT_STATUS=ok")
    print("ARCHITECTURAL_ASSESSMENT_RESULTS=guidelines:deterministic-clean")
    return 0


def sanitize_detail(argv: list[str]) -> int:
    if (_impl() / ".test-sanitizer-fail").is_file():
        print("sanitizer failed", file=sys.stderr)
        return 1
    import re

    text = sys.stdin.read()
    (_impl() / ".test-sanitizer-input-size").write_text(str(len(text.encode("utf-8"))), encoding="utf-8")
    text = text.replace(os.environ["IMPLEMENT_TMPDIR"], "<implement-tmpdir>")
    text = text.replace(str(_impl()), "<implement-tmpdir>")
    text = re.sub(r"ghp_[A-Za-z0-9_]{20,}", "<REDACTED-TOKEN>", text)
    print(text.replace("\r", " ").replace("\n", " ").strip()[:500])
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "bgjob" and argv[1] == "start":
        return bgjob_start(argv)
    if len(argv) >= 2 and argv[0] == "bgjob" and argv[1] == "wait":
        return bgjob_wait(argv)
    if len(argv) >= 2 and argv[0] == "architectural-assessment" and argv[1] == "run":
        return assessment_run(argv)
    if len(argv) >= 2 and argv[0] == "architectural-assessment" and argv[1] == "sanitize-detail":
        return sanitize_detail(argv)
    print(f"stub cli: unhandled {argv}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
PY
chmod +x "$FAKE_PLUGIN/python/cli.py"

# python3 wrapper: route fake-plugin cli.py to stub; else real python for heredocs.
REAL_PYTHON=$(command -v python3)
STUB_BIN="$TMP_ROOT/bin"
mkdir -p "$STUB_BIN"
cat >"$STUB_BIN/python3" <<EOF
#!/usr/bin/env bash
set -euo pipefail
if [ "\${#}" -ge 1 ] && [ "\$1" = "$FAKE_PLUGIN/python/cli.py" ]; then
  shift
  exec "$REAL_PYTHON" "$FAKE_PLUGIN/python/cli.py" "\$@"
fi
exec "$REAL_PYTHON" "\$@"
EOF
chmod +x "$STUB_BIN/python3"

setup_impl() {
  local name=$1
  IMPL_TMP="$TMP_ROOT/$name"
  rm -rf "$IMPL_TMP"
  mkdir -p "$IMPL_TMP/bgjob" "$IMPL_TMP/repo/.git"
  printf 'REPO_ROOT=%s\n' "$IMPL_TMP/repo" >"$IMPL_TMP/session-env.sh"
  printf 'export CLAUDE_PLUGIN_ROOT=%s\n' "$FAKE_PLUGIN" >"$IMPL_TMP/plugin-root.env"
  printf 'absent\n' >"$IMPL_TMP/.test-registry-state"
  printf 'NEXT_ACTION=assessments\nDETAIL=guidelines,invariants\n' >"$IMPL_TMP/.ship-route-exit-handoff.env"
  # Materialization fixtures (stub reads these)
  cat >"$IMPL_TMP/architectural-invariant-materialize.env" <<'ENV'
STATUS=present
HEAD_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
BASE_REF=origin/main
DIFF_FINGERPRINT=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
DIFF_SNAPSHOT=x
INVARIANTS_STATUS=present
INVARIANTS_PATH=x
ENV
  cat >"$IMPL_TMP/architectural-guideline-materialize.env" <<'ENV'
STATUS=present
HEAD_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
BASE_REF=origin/main
DIFF_FINGERPRINT=cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc
DIFF_SNAPSHOT=x
GUIDELINES_STATUS=present
GUIDELINES_PATH=x
ENV
  rm -f "$IMPL_TMP/.test-wait-count" "$IMPL_TMP/bgjob-start-argv.txt" \
    "$IMPL_TMP/bgjob-wait-argv.txt" "$IMPL_TMP/assessment-run-called.txt" \
    "$IMPL_TMP/bad-direct-assessment-start.txt"
  printf 'record-only\n' >"$IMPL_TMP/.test-start-mode"
}

expected_fingerprint() {
  # Mirror adapter preimage: invariants then guidelines (Piece 2 order)
  local preimage
  preimage=$(printf '%s\n%s' \
    'invariants|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|origin/main|bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb' \
    'guidelines|aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|origin/main|cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc')
  printf '%s' "$preimage" | shasum -a 256 | awk '{print $1}'
}

run_helper() {
  PATH="$STUB_BIN:$PATH" \
    IMPLEMENT_TMPDIR="$IMPL_TMP" \
    CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" \
    bash "$HELPER_UNDER_TEST" "$@"
}

# --- fingerprint grammar ---
setup_impl fp
FP_EXPECTED=$(expected_fingerprint)
FP_OUT=$(PATH="$STUB_BIN:$PATH" IMPLEMENT_TMPDIR="$IMPL_TMP" CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" \
  ASSESSMENT_RAW_KINDS="guidelines,invariants" REPO_ROOT="$IMPL_TMP/repo" \
  "$REAL_PYTHON" <<'PY'
import hashlib, os, sys
from pathlib import Path
plugin_root = Path(os.environ["CLAUDE_PLUGIN_ROOT"])
sys.path.insert(0, str(plugin_root / "python"))
from larch.implement.architectural_assessment import normalize_kinds, validate_materialization
raw = [p for p in os.environ["ASSESSMENT_RAW_KINDS"].split(",") if p]
kinds = normalize_kinds(raw)
repo = Path(os.environ["REPO_ROOT"])
tmpdir = Path(os.environ["IMPLEMENT_TMPDIR"])
lines = []
for kind in kinds:
    ev = validate_materialization(kind=kind, repo_root=repo, implement_tmpdir=tmpdir)
    lines.append(f"{kind}|{ev.head_sha}|{ev.base_ref}|{ev.diff_fingerprint}")
preimage = "\n".join(lines)
print(hashlib.sha256(preimage.encode("utf-8")).hexdigest())
PY
)
if [ "$FP_OUT" = "$FP_EXPECTED" ]; then
  pass 'fingerprint: shared helper digest matches harness preimage'
else
  fail "fingerprint: digest mismatch got=$FP_OUT expected=$FP_EXPECTED"
fi

# --- fresh start ---
setup_impl fresh
# After start, wait returns DONE with complete from synthesized result — use run-child
printf 'run-child\n' >"$IMPL_TMP/.test-start-mode"
printf 'ARCHITECTURAL_ASSESSMENT_STATUS=ok\nARCHITECTURAL_ASSESSMENT_RESULTS=invariants:clean,guidelines:deterministic-clean\n' \
  >"$IMPL_TMP/.test-assessment-stdout"
# Wait script: first wait after start → DONE
printf '1:DONE:0\n' >"$IMPL_TMP/.test-wait-script"
set +e
FRESH_OUT=$(run_helper 2>"$TMP_ROOT/fresh.err")
FRESH_RC=$?
set -e
assert_rc "$FRESH_RC" 0 'fresh: exits 0'
assert_contains 'BGJOB_STATUS=STARTED' "$FRESH_OUT" 'fresh: prints STARTED once'
assert_contains 'ASSESSMENT_STATUS=complete' "$FRESH_OUT" 'fresh: terminal complete'
assert_contains 'ASSESSMENT_REQUESTED_KINDS=invariants,guidelines' "$FRESH_OUT" 'fresh: reversed detail order accepts canonical adapter kinds'
assert_contains 'ASSESSMENT_RESULTS=invariants:clean,guidelines:deterministic-clean' "$FRESH_OUT" 'fresh: multi-kind results'
assert_contains 'implement-step8-assessment' "$(cat "$IMPL_TMP/bgjob-start-meta.txt")" 'fresh: step slug'
assert_contains 'BUDGET=5700' "$(cat "$IMPL_TMP/bgjob-start-meta.txt")" 'fresh: budget 5700'
assert_contains '--bgjob-child' "$(cat "$IMPL_TMP/bgjob-start-argv.txt")" 'fresh: wrapper-child argv'
assert_contains 'step-8-assessment.sh' "$(cat "$IMPL_TMP/bgjob-start-argv.txt")" 'fresh: child script path'
if [ -e "$IMPL_TMP/bad-direct-assessment-start.txt" ]; then
  fail 'fresh: architectural-assessment must not be direct bgjob start command'
else
  pass 'fresh: assessment CLI not direct bgjob command'
fi
if [ -f "$IMPL_TMP/assessment-run-called.txt" ]; then
  pass 'fresh: assessment run invoked from child'
else
  fail 'fresh: assessment run not invoked from child'
fi

# --- child stderr is sanitized, forwarded, and removed ---
setup_impl child-detail
printf 'run-child\n' >"$IMPL_TMP/.test-start-mode"
printf 'ARCHITECTURAL_ASSESSMENT_STATUS=ok\nARCHITECTURAL_ASSESSMENT_RESULTS=invariants:clean,guidelines:clean\n' \
  >"$IMPL_TMP/.test-assessment-stdout"
TOKEN="ghp_""abcdefghijklmnopqrstuvwxyz1234"
printf 'launcher failed\n%s %s %0600d\n' "$IMPL_TMP" "$TOKEN" 0 >"$IMPL_TMP/.test-assessment-stderr"
set +e
CHILD_DETAIL_OUT=$(run_helper 2>"$TMP_ROOT/child-detail.err")
CHILD_DETAIL_RC=$?
set -e
assert_rc "$CHILD_DETAIL_RC" 0 'child-detail: successful assessment exits 0'
assert_contains 'ASSESSMENT_CHILD_DETAIL=launcher failed <implement-tmpdir> <REDACTED-TOKEN>' "$CHILD_DETAIL_OUT" 'child-detail: forwards sanitized stderr'
assert_not_contains "$TOKEN" "$CHILD_DETAIL_OUT" 'child-detail: secret does not escape'
assert_not_contains "$IMPL_TMP" "$CHILD_DETAIL_OUT" 'child-detail: tmpdir does not escape'
assert_no_raw_stderr "$IMPL_TMP" 'child-detail: raw stderr removed after success'

# --- child stderr capture remains bounded while draining ---
setup_impl child-detail-bounded
printf 'run-child\n' >"$IMPL_TMP/.test-start-mode"
printf 'ARCHITECTURAL_ASSESSMENT_STATUS=ok\nARCHITECTURAL_ASSESSMENT_RESULTS=invariants:clean,guidelines:clean\n' \
  >"$IMPL_TMP/.test-assessment-stdout"
printf '20000\n' >"$IMPL_TMP/.test-assessment-stderr-bytes"
set +e
BOUNDED_DETAIL_OUT=$(run_helper 2>"$TMP_ROOT/child-detail-bounded.err")
BOUNDED_DETAIL_RC=$?
set -e
assert_rc "$BOUNDED_DETAIL_RC" 0 'child-detail-bounded: successful assessment exits 0'
SANITIZER_INPUT_SIZE=$(cat "$IMPL_TMP/.test-sanitizer-input-size")
if [ "$SANITIZER_INPUT_SIZE" -le 8220 ]; then
  pass 'child-detail-bounded: sanitizer receives bounded stderr'
else
  fail "child-detail-bounded: sanitizer received $SANITIZER_INPUT_SIZE bytes"
fi
assert_contains 'ASSESSMENT_CHILD_DETAIL=' "$BOUNDED_DETAIL_OUT" 'child-detail-bounded: retains diagnostic prefix'
assert_no_raw_stderr "$IMPL_TMP" 'child-detail-bounded: raw stderr removed'

# --- malformed output preserves sanitized terminal detail ---
setup_impl malformed-child-detail
printf 'run-child\n' >"$IMPL_TMP/.test-start-mode"
printf 'malformed stdout\n' >"$IMPL_TMP/.test-assessment-stdout"
printf 'parse failed\nsecond line\n' >"$IMPL_TMP/.test-assessment-stderr"
set +e
MALFORMED_DETAIL_OUT=$(run_helper 2>"$TMP_ROOT/malformed-child-detail.err")
MALFORMED_DETAIL_RC=$?
set -e
assert_rc "$MALFORMED_DETAIL_RC" 0 'malformed-child-detail: adapter publishes fail-closed'
assert_contains 'ASSESSMENT_STATUS=fail-closed' "$MALFORMED_DETAIL_OUT" 'malformed-child-detail: fail-closed status'
assert_contains 'ASSESSMENT_CHILD_DETAIL=parse failed second line' "$MALFORMED_DETAIL_OUT" 'malformed-child-detail: diagnostic preserved'
assert_no_raw_stderr "$IMPL_TMP" 'malformed-child-detail: raw stderr removed'

# --- sanitizer failure forwards nothing and still removes raw stderr ---
setup_impl sanitizer-failure
printf 'run-child\n' >"$IMPL_TMP/.test-start-mode"
printf 'yes\n' >"$IMPL_TMP/.test-sanitizer-fail"
printf 'must remain raw only\n' >"$IMPL_TMP/.test-assessment-stderr"
set +e
SANITIZER_FAIL_OUT=$(run_helper 2>"$TMP_ROOT/sanitizer-failure.err")
SANITIZER_FAIL_RC=$?
set -e
assert_rc "$SANITIZER_FAIL_RC" 0 'sanitizer-failure: adapter publishes fail-closed'
assert_not_contains 'must remain raw only' "$SANITIZER_FAIL_OUT" 'sanitizer-failure: raw stderr not forwarded'
assert_no_raw_stderr "$IMPL_TMP" 'sanitizer-failure: raw stderr removed'

# --- merge-result write failure still removes raw stderr ---
setup_impl merge-write-failure
printf 'yes\n' >"$IMPL_TMP/.test-corrupt-merge"
printf 'write failed diagnostic\n' >"$IMPL_TMP/.test-assessment-stderr"
MERGE_PATH="$IMPL_TMP/bgjob/implement-step8-assessment.merge.env"
cat >"$MERGE_PATH" <<ENV
ASSESSMENT_REQUESTED_KINDS=invariants,guidelines
ASSESSMENT_COVERED_FINGERPRINT=$(expected_fingerprint)
ASSESSMENT_ATTEMPT=1
ENV
set +e
run_helper --bgjob-child --merge-result-env "$MERGE_PATH" >"$TMP_ROOT/merge-write-failure.out" 2>"$TMP_ROOT/merge-write-failure.err"
MERGE_FAIL_RC=$?
set -e
assert_rc "$MERGE_FAIL_RC" 2 'merge-write-failure: child fails closed'
assert_no_raw_stderr "$IMPL_TMP" 'merge-write-failure: raw stderr removed'

# --- signal interruption preserves the signal status and removes raw stderr ---
setup_impl child-signal
MERGE_PATH="$IMPL_TMP/bgjob/implement-step8-assessment.merge.env"
cat >"$MERGE_PATH" <<ENV
ASSESSMENT_REQUESTED_KINDS=invariants,guidelines
ASSESSMENT_COVERED_FINGERPRINT=$(expected_fingerprint)
ASSESSMENT_ATTEMPT=1
ENV
printf '0.5\n' >"$IMPL_TMP/.test-assessment-sleep"
PATH="$STUB_BIN:$PATH" \
  IMPLEMENT_TMPDIR="$IMPL_TMP" \
  CLAUDE_PLUGIN_ROOT="$FAKE_PLUGIN" \
  bash "$HELPER_UNDER_TEST" --bgjob-child --merge-result-env "$MERGE_PATH" >"$TMP_ROOT/child-signal.out" 2>"$TMP_ROOT/child-signal.err" &
CHILD_SIGNAL_PID=$!
for _ in $(seq 1 50); do
  if find "$IMPL_TMP" -maxdepth 1 -name 'architectural-assessment-stderr.*' -print -quit | grep -q .; then
    break
  fi
  sleep 0.01
done
set +e
kill -TERM "$CHILD_SIGNAL_PID"
wait "$CHILD_SIGNAL_PID"
CHILD_SIGNAL_RC=$?
set -e
assert_rc "$CHILD_SIGNAL_RC" 143 'child-signal: preserves TERM exit status'
assert_no_raw_stderr "$IMPL_TMP" 'child-signal: raw stderr removed'

# --- fresh re-author terminal ---
setup_impl fresh-reauthor
printf 'run-child\n' >"$IMPL_TMP/.test-start-mode"
printf 'ARCHITECTURAL_ASSESSMENT_STATUS=re-author-required\nARCHITECTURAL_ASSESSMENT_RESULTS=invariants:re-author-required:clean-outcome-prose-mismatch,guidelines:clean\n' \
  >"$IMPL_TMP/.test-assessment-stdout"
printf '1:DONE:0\n' >"$IMPL_TMP/.test-wait-script"
set +e
REAUTHOR_OUT=$(run_helper 2>"$TMP_ROOT/fresh-reauthor.err")
REAUTHOR_RC=$?
set -e
assert_rc "$REAUTHOR_RC" 0 'fresh-reauthor: exits 0'
assert_contains 'ASSESSMENT_STATUS=re-author-required' "$REAUTHOR_OUT" 'fresh-reauthor: terminal status'
assert_contains 'ASSESSMENT_RESULTS=invariants:re-author-required:clean-outcome-prose-mismatch,guidelines:clean' "$REAUTHOR_OUT" 'fresh-reauthor: preserves reason'
START_COUNT=$(cat "$IMPL_TMP/.test-start-count" 2>/dev/null || echo 0)
if [ "$START_COUNT" = "0" ]; then
  pass 'fresh-reauthor: no retry or ship handoff'
else
  fail "fresh-reauthor: expected no retry start got $START_COUNT"
fi
FP_GOT=$(printf '%s\n' "$FRESH_OUT" | sed -n 's/^ASSESSMENT_COVERED_FINGERPRINT=//p' | tail -n 1)
if [ "$FP_GOT" = "$FP_EXPECTED" ]; then
  pass 'fresh: covered fingerprint persisted'
else
  fail "fresh: fingerprint got=$FP_GOT expected=$FP_EXPECTED"
fi
KINDS_GOT=$(printf '%s\n' "$FRESH_OUT" | sed -n 's/^ASSESSMENT_REQUESTED_KINDS=//p' | tail -n 1)
if [ "$KINDS_GOT" = "invariants,guidelines" ]; then
  pass 'fresh: kinds normalized to Piece 2 order'
else
  fail "fresh: kinds got=$KINDS_GOT"
fi

# --- completed rejoin success ---
setup_impl rejoin-ok
FP_EXPECTED=$(expected_fingerprint)
cat >"$IMPL_TMP/bgjob/implement-step8-assessment.result.env" <<ENV
BGJOB_RC=0
STEP=implement-step8-assessment
ASSESSMENT_REQUESTED_KINDS=invariants,guidelines
ASSESSMENT_COVERED_FINGERPRINT=$FP_EXPECTED
ASSESSMENT_STATUS=complete
ASSESSMENT_ATTEMPT=1
ASSESSMENT_RESULTS=invariants:clean,guidelines:deterministic-clean
ENV
printf '1:DONE:0\n' >"$IMPL_TMP/.test-wait-script"
set +e
REJOIN_OUT=$(run_helper 2>"$TMP_ROOT/rejoin-ok.err")
REJOIN_RC=$?
set -e
assert_rc "$REJOIN_RC" 0 'completed-rejoin: exits 0'
assert_contains 'ASSESSMENT_STATUS=complete' "$REJOIN_OUT" 'completed-rejoin: complete status'
if [ -e "$IMPL_TMP/bgjob-start-argv.txt" ]; then
  fail 'completed-rejoin: must not start fresh bgjob'
else
  pass 'completed-rejoin: no fresh start'
fi

# --- completed rejoin fail-closed with timeout ---
setup_impl rejoin-fail
FP_EXPECTED=$(expected_fingerprint)
cat >"$IMPL_TMP/bgjob/implement-step8-assessment.result.env" <<ENV
BGJOB_RC=timeout
STEP=implement-step8-assessment
ASSESSMENT_REQUESTED_KINDS=invariants,guidelines
ASSESSMENT_COVERED_FINGERPRINT=$FP_EXPECTED
ASSESSMENT_STATUS=fail-closed
ASSESSMENT_ATTEMPT=2
ENV
printf '1:DONE:timeout\n' >"$IMPL_TMP/.test-wait-script"
set +e
REJOIN_FAIL_OUT=$(run_helper 2>"$TMP_ROOT/rejoin-fail.err")
REJOIN_FAIL_RC=$?
set -e
assert_rc "$REJOIN_FAIL_RC" 0 'fail-closed-rejoin: exits 0'
assert_contains 'ASSESSMENT_STATUS=fail-closed' "$REJOIN_FAIL_OUT" 'fail-closed-rejoin: status'
assert_contains 'BGJOB_RC=timeout' "$REJOIN_FAIL_OUT" 'fail-closed-rejoin: preserves timeout rc'
if [ -e "$IMPL_TMP/bgjob-start-argv.txt" ]; then
  fail 'fail-closed-rejoin: must not start attempt 3'
else
  pass 'fail-closed-rejoin: no attempt 3'
fi

# --- live rejoin: probe WAIT then DONE success ---
setup_impl live-ok
FP_EXPECTED=$(expected_fingerprint)
printf 'live\n' >"$IMPL_TMP/.test-registry-state"
cat >"$IMPL_TMP/bgjob/implement-step8-assessment.merge.env" <<ENV
ASSESSMENT_REQUESTED_KINDS=invariants,guidelines
ASSESSMENT_COVERED_FINGERPRINT=$FP_EXPECTED
ASSESSMENT_ATTEMPT=1
ENV
cat >"$IMPL_TMP/bgjob/implement-step8-assessment.result.env" <<ENV
BGJOB_RC=0
STEP=implement-step8-assessment
ASSESSMENT_REQUESTED_KINDS=invariants,guidelines
ASSESSMENT_COVERED_FINGERPRINT=$FP_EXPECTED
ASSESSMENT_STATUS=complete
ASSESSMENT_ATTEMPT=1
ASSESSMENT_RESULTS=guidelines:clean,invariants:handled
ENV
# Fix results order for coverage — must match kinds order
cat >"$IMPL_TMP/bgjob/implement-step8-assessment.result.env" <<ENV
BGJOB_RC=0
STEP=implement-step8-assessment
ASSESSMENT_REQUESTED_KINDS=invariants,guidelines
ASSESSMENT_COVERED_FINGERPRINT=$FP_EXPECTED
ASSESSMENT_STATUS=complete
ASSESSMENT_ATTEMPT=1
ASSESSMENT_RESULTS=invariants:handled,guidelines:clean
ENV
printf '1:WAIT\n2:DONE:0\n' >"$IMPL_TMP/.test-wait-script"
set +e
LIVE_OUT=$(run_helper 2>"$TMP_ROOT/live-ok.err")
LIVE_RC=$?
set -e
assert_rc "$LIVE_RC" 0 'live-rejoin: exits 0'
assert_contains 'ASSESSMENT_STATUS=complete' "$LIVE_OUT" 'live-rejoin: complete'
assert_contains $'--max-wait-s\n0' "$(cat "$IMPL_TMP/bgjob-wait-argv.txt")" 'live-rejoin: zero-duration probe'
assert_contains $'--max-wait-s\n270' "$(cat "$IMPL_TMP/bgjob-wait-argv.txt")" 'live-rejoin: blocking wait chunk'
if [ -e "$IMPL_TMP/bgjob-start-argv.txt" ]; then
  fail 'live-rejoin: must not duplicate start before terminal'
else
  pass 'live-rejoin: no duplicate start'
fi

# --- active stale live row ---
setup_impl active-stale
printf 'live\n' >"$IMPL_TMP/.test-registry-state"
cat >"$IMPL_TMP/bgjob/implement-step8-assessment.merge.env" <<ENV
ASSESSMENT_REQUESTED_KINDS=guidelines
ASSESSMENT_COVERED_FINGERPRINT=dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
ASSESSMENT_ATTEMPT=1
ENV
set +e
STALE_OUT=$(run_helper 2>"$TMP_ROOT/active-stale.err")
STALE_RC=$?
set -e
assert_rc "$STALE_RC" 2 'active-stale: exit 2'
assert_contains 'ASSESSMENT_ERROR=active-stale-identity-mismatch' "$STALE_OUT" 'active-stale: error token'
if [ -e "$IMPL_TMP/bgjob-start-argv.txt" ]; then
  fail 'active-stale: must not start fresh'
else
  pass 'active-stale: no fresh start'
fi

# --- stale completed envelope cleared then fresh start ---
setup_impl stale-completed
cat >"$IMPL_TMP/bgjob/implement-step8-assessment.result.env" <<ENV
BGJOB_RC=0
STEP=implement-step8-assessment
ASSESSMENT_REQUESTED_KINDS=guidelines
ASSESSMENT_COVERED_FINGERPRINT=eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee
ASSESSMENT_STATUS=complete
ASSESSMENT_ATTEMPT=1
ASSESSMENT_RESULTS=guidelines:clean
ENV
printf 'run-child\n' >"$IMPL_TMP/.test-start-mode"
printf 'ARCHITECTURAL_ASSESSMENT_STATUS=ok\nARCHITECTURAL_ASSESSMENT_RESULTS=invariants:clean,guidelines:clean\n' \
  >"$IMPL_TMP/.test-assessment-stdout"
printf '1:DONE:0\n' >"$IMPL_TMP/.test-wait-script"
set +e
STALE_DONE_OUT=$(run_helper 2>"$TMP_ROOT/stale-completed.err")
STALE_DONE_RC=$?
set -e
assert_rc "$STALE_DONE_RC" 0 'stale-completed: fresh start after clear'
assert_contains 'ASSESSMENT_STATUS=complete' "$STALE_DONE_OUT" 'stale-completed: new complete'
assert_contains 'BUDGET=5700' "$(cat "$IMPL_TMP/bgjob-start-meta.txt")" 'stale-completed: started fresh'

# --- timeout attempt-1 → attempt-2 fail-closed ---
setup_impl timeout-retry
printf 'run-child\n' >"$IMPL_TMP/.test-start-mode"
# First child "succeeds" writing merge but force BGJOB_RC=timeout and incomplete status
# Simpler: don't run child; synthesize wait failures via wait script + start that writes fail envelopes
printf 'record-only\n' >"$IMPL_TMP/.test-start-mode"
# Custom start handler via wait script after we plant result envs between waits — use a small
# python control: after each start, write attempt-specific result.
# Re-implement start mode as sequenced results:
cat >"$IMPL_TMP/.test-start-mode" <<'MODE'
record-only
MODE
# Override: use wait script that on first DONE returns timeout without complete; adapter retries.
# We need start to plant merge identity then wait returns failure for attempt 1, then start again
# for attempt 2, wait returns timeout fail-closed.
#
# Approach: wrap by pre-writing a sequencer script consumed by extending stub — use
# .test-attempt-results file.
cat >"$FAKE_PLUGIN/python/cli.py" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations
import os, sys
from pathlib import Path

def impl() -> Path:
    return Path(os.environ["IMPLEMENT_TMPDIR"])

def log(name: str, text: str) -> None:
    path = impl() / name
    prev = path.read_text(encoding="utf-8") if path.exists() else ""
    path.write_text(prev + text, encoding="utf-8")

def read_merge(merge: str) -> dict[str, str]:
    rows = {}
    p = Path(merge)
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                rows[k] = v
    return rows

def write_result(rows: dict[str, str], rc: str) -> None:
    body = [f"BGJOB_RC={rc}", "STEP=implement-step8-assessment"]
    for key in (
        "ASSESSMENT_REQUESTED_KINDS",
        "ASSESSMENT_COVERED_FINGERPRINT",
        "ASSESSMENT_STATUS",
        "ASSESSMENT_ATTEMPT",
        "ASSESSMENT_RESULTS",
    ):
        if key in rows:
            body.append(f"{key}={rows[key]}")
    (impl() / "bgjob" / "implement-step8-assessment.result.env").write_text("\n".join(body) + "\n", encoding="utf-8")

def bgjob_start(argv: list[str]) -> int:
    log("bgjob-start-argv.txt", "\n".join(argv) + "\n---\n")
    if "architectural-assessment" in argv:
        (impl() / "bad-direct-assessment-start.txt").write_text("yes\n", encoding="utf-8")
    merge = argv[argv.index("--merge-result-env") + 1] if "--merge-result-env" in argv else ""
    budget = argv[argv.index("--budget-s") + 1] if "--budget-s" in argv else ""
    (impl() / "bgjob-start-meta.txt").write_text(f"BUDGET={budget}\nMERGE={merge}\n", encoding="utf-8")
    starts = impl() / ".test-start-count"
    n = int(starts.read_text(encoding="utf-8")) if starts.is_file() else 0
    n += 1
    starts.write_text(str(n), encoding="utf-8")
    rows = read_merge(merge)
    seq = (impl() / ".test-start-seq").read_text(encoding="utf-8").splitlines() if (impl() / ".test-start-seq").is_file() else []
    # lines: N:rc:status[:results]
    for line in seq:
        parts = line.split(":", 3)
        if int(parts[0]) != n:
            continue
        rc, status = parts[1], parts[2]
        if status == "complete":
            rows["ASSESSMENT_STATUS"] = "complete"
            rows["ASSESSMENT_RESULTS"] = parts[3] if len(parts) > 3 else "invariants:clean,guidelines:clean"
        else:
            rows["ASSESSMENT_STATUS"] = status
            rows.pop("ASSESSMENT_RESULTS", None)
        write_result(rows, rc)
        break
    (impl() / ".test-registry-state").write_text("absent\n", encoding="utf-8")
    # reset wait counter per start so wait scripts are per-attempt
    if (impl() / ".test-wait-reset-on-start").is_file():
        (impl() / ".test-wait-count").write_text("0\n", encoding="utf-8")
    print("BGJOB_STATUS=STARTED STEP=implement-step8-assessment PGID=4242")
    return 0

def bgjob_wait(argv: list[str]) -> int:
    log("bgjob-wait-argv.txt", "\n".join(argv) + "\n---\n")
    counter = impl() / ".test-wait-count"
    count = int(counter.read_text(encoding="utf-8")) if counter.is_file() else 0
    count += 1
    counter.write_text(str(count), encoding="utf-8")
    script = (impl() / ".test-wait-script").read_text(encoding="utf-8").splitlines() if (impl() / ".test-wait-script").is_file() else []
    for line in script:
        if not line or line.startswith("#"):
            continue
        parts = line.split(":", 2)
        if int(parts[0]) != count:
            continue
        status = parts[1]
        rc = parts[2] if len(parts) > 2 else "0"
        if status == "WAIT":
            print("BGJOB_STATUS=WAIT"); print("ELAPSED_S=0"); return 0
        if status == "DEAD":
            print("BGJOB_STATUS=DEAD"); return 0
        result = impl() / "bgjob" / "implement-step8-assessment.result.env"
        print("BGJOB_STATUS=DONE")
        print(f"BGJOB_RC={rc}")
        print("STEP=implement-step8-assessment")
        if result.is_file():
            for row in result.read_text(encoding="utf-8").splitlines():
                if row.startswith("ASSESSMENT_"):
                    print(row)
        return 0
    result = impl() / "bgjob" / "implement-step8-assessment.result.env"
    rc = "0"
    if result.is_file():
        for row in result.read_text(encoding="utf-8").splitlines():
            if row.startswith("BGJOB_RC="):
                rc = row.split("=", 1)[1]
    print("BGJOB_STATUS=DONE")
    print(f"BGJOB_RC={rc}")
    print("STEP=implement-step8-assessment")
    if result.is_file():
        for row in result.read_text(encoding="utf-8").splitlines():
            if row.startswith("ASSESSMENT_"):
                print(row)
    return 0

def assessment_run(argv: list[str]) -> int:
    log("assessment-run-argv.txt", "\n".join(argv) + "\n---\n")
    (impl() / "assessment-run-called.txt").write_text("yes\n", encoding="utf-8")
    canned = impl() / ".test-assessment-stdout"
    if canned.is_file():
        sys.stdout.write(canned.read_text(encoding="utf-8"))
        return 0
    print("ARCHITECTURAL_ASSESSMENT_STATUS=ok")
    print("ARCHITECTURAL_ASSESSMENT_RESULTS=invariants:clean,guidelines:deterministic-clean")
    return 0

def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "bgjob" and argv[1] == "start":
        return bgjob_start(argv)
    if len(argv) >= 2 and argv[0] == "bgjob" and argv[1] == "wait":
        return bgjob_wait(argv)
    if len(argv) >= 2 and argv[0] == "architectural-assessment" and argv[1] == "run":
        return assessment_run(argv)
    print(f"unhandled {argv}", file=sys.stderr)
    return 2

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
PY

setup_impl timeout-retry
printf '1:timeout:fail-closed\n2:timeout:fail-closed\n' >"$IMPL_TMP/.test-start-seq"
# Actually attempt1 should be retryable failure (timeout + not complete). start-seq line 1:
printf '1:timeout:incomplete\n2:timeout:fail-closed\n' >"$IMPL_TMP/.test-start-seq"
# For incomplete, our stub sets ASSESSMENT_STATUS=incomplete which fails validation → retry
# Wait once per attempt
printf '1:DONE:timeout\n2:DONE:timeout\n' >"$IMPL_TMP/.test-wait-script"
printf 'yes\n' >"$IMPL_TMP/.test-wait-reset-on-start"
set +e
TO_OUT=$(run_helper 2>"$TMP_ROOT/timeout.err")
TO_RC=$?
set -e
assert_rc "$TO_RC" 0 'timeout-retry: exits 0 with terminal fail-closed'
assert_contains 'ASSESSMENT_STATUS=fail-closed' "$TO_OUT" 'timeout-retry: fail-closed'
assert_contains 'BGJOB_RC=timeout' "$TO_OUT" 'timeout-retry: preserves timeout'
START_COUNT=$(cat "$IMPL_TMP/.test-start-count" 2>/dev/null || echo 0)
if [ "$START_COUNT" = "2" ]; then
  pass 'timeout-retry: exactly two bgjob starts'
else
  fail "timeout-retry: expected 2 starts got $START_COUNT"
fi
# Ensure foreground did not call assessment inline
if [ -f "$IMPL_TMP/assessment-run-called.txt" ]; then
  fail 'timeout-retry: must not call Piece 2 inline from foreground'
else
  pass 'timeout-retry: no foreground Piece 2 call'
fi

# --- invalid-output retry then fail-closed ---
setup_impl invalid-retry
printf '1:0:incomplete\n2:0:incomplete\n' >"$IMPL_TMP/.test-start-seq"
printf '1:DONE:0\n2:DONE:0\n' >"$IMPL_TMP/.test-wait-script"
printf 'yes\n' >"$IMPL_TMP/.test-wait-reset-on-start"
set +e
INV_OUT=$(run_helper 2>"$TMP_ROOT/invalid.err")
INV_RC=$?
set -e
assert_rc "$INV_RC" 0 'invalid-retry: exits 0'
assert_contains 'ASSESSMENT_STATUS=fail-closed' "$INV_OUT" 'invalid-retry: fail-closed after second invalid'
assert_contains 'BGJOB_RC=1' "$INV_OUT" 'invalid-retry: fail-closed normalizes zero rc'
assert_not_contains 'BGJOB_RC=0' "$INV_OUT" 'invalid-retry: fail-closed never reports zero rc'
START_COUNT=$(cat "$IMPL_TMP/.test-start-count" 2>/dev/null || echo 0)
if [ "$START_COUNT" = "2" ]; then
  pass 'invalid-retry: two starts'
else
  fail "invalid-retry: expected 2 starts got $START_COUNT"
fi

# --- authored success states ---
setup_impl authored
printf '1:0:complete:invariants:violation,guidelines:deviation\n' >"$IMPL_TMP/.test-start-seq"
printf '1:DONE:0\n' >"$IMPL_TMP/.test-wait-script"
set +e
AUTH_OUT=$(run_helper 2>"$TMP_ROOT/authored.err")
AUTH_RC=$?
set -e
assert_rc "$AUTH_RC" 0 'authored: exits 0'
assert_contains 'ASSESSMENT_RESULTS=invariants:violation,guidelines:deviation' "$AUTH_OUT" 'authored: preserves states'

# --- path safety: symlinked detail file ---
setup_impl symlink-detail
ln -s "$IMPL_TMP/.ship-route-exit-handoff.env" "$IMPL_TMP/detail-link"
printf 'NEXT_ACTION=assessments\nDETAIL=\nDETAIL_FILE=%s\n' "$IMPL_TMP/detail-link" >"$IMPL_TMP/.ship-route-exit-handoff.env"
set +e
SYM_OUT=$(run_helper 2>"$TMP_ROOT/symlink-detail.err")
SYM_RC=$?
set -e
assert_rc "$SYM_RC" 2 'path-safety: symlinked DETAIL_FILE rejected'

# --- path safety: symlinked bgjob dir ---
setup_impl symlink-bgjob
rm -rf "$IMPL_TMP/bgjob"
ln -s "$TMP_ROOT" "$IMPL_TMP/bgjob"
set +e
SYMB_OUT=$(run_helper 2>"$TMP_ROOT/symlink-bgjob.err")
SYMB_RC=$?
set -e
assert_rc "$SYMB_RC" 2 'path-safety: symlinked bgjob dir rejected'

# --- duplicate kind rejection ---
setup_impl dup-kinds
printf 'NEXT_ACTION=assessments\nDETAIL=guidelines,guidelines\n' >"$IMPL_TMP/.ship-route-exit-handoff.env"
set +e
DUP_OUT=$(run_helper 2>"$TMP_ROOT/dup.err")
DUP_RC=$?
set -e
assert_rc "$DUP_RC" 2 'handoff: duplicate kinds rejected'

# --- daemon-reserved keys refused in child write path (static + unit via helper text) ---
assert_contains 'BGJOB_PID|BGJOB_OWNER_PID' "$helper_text" 'required-kvs: refuses daemon-reserved merge keys'

# --- live rejoin attempt-1 timeout → attempt-2 ---
setup_impl live-timeout-retry
FP_EXPECTED=$(expected_fingerprint)
printf 'live\n' >"$IMPL_TMP/.test-registry-state"
cat >"$IMPL_TMP/bgjob/implement-step8-assessment.merge.env" <<ENV
ASSESSMENT_REQUESTED_KINDS=invariants,guidelines
ASSESSMENT_COVERED_FINGERPRINT=$FP_EXPECTED
ASSESSMENT_ATTEMPT=1
ENV
# First waits: probe WAIT, then DONE timeout with incomplete; then attempt2 start+wait
cat >"$IMPL_TMP/bgjob/implement-step8-assessment.result.env" <<ENV
BGJOB_RC=timeout
STEP=implement-step8-assessment
ASSESSMENT_REQUESTED_KINDS=invariants,guidelines
ASSESSMENT_COVERED_FINGERPRINT=$FP_EXPECTED
ASSESSMENT_STATUS=incomplete
ASSESSMENT_ATTEMPT=1
ENV
printf '1:WAIT\n2:DONE:timeout\n1:DONE:timeout\n' >"$IMPL_TMP/.test-wait-script"
# After retry clear, start-seq for the single attempt-2 start:
printf '1:timeout:fail-closed\n' >"$IMPL_TMP/.test-start-seq"
printf 'yes\n' >"$IMPL_TMP/.test-wait-reset-on-start"
set +e
LTR_OUT=$(run_helper 2>"$TMP_ROOT/live-timeout.err")
LTR_RC=$?
set -e
assert_rc "$LTR_RC" 0 'live-timeout-retry: exits 0'
assert_contains 'ASSESSMENT_STATUS=fail-closed' "$LTR_OUT" 'live-timeout-retry: fail-closed'
START_COUNT=$(cat "$IMPL_TMP/.test-start-count" 2>/dev/null || echo 0)
if [ "$START_COUNT" = "1" ]; then
  pass 'live-timeout-retry: one attempt-2 start after rejoin failure'
else
  fail "live-timeout-retry: expected 1 start got $START_COUNT"
fi

# --- live DEAD without an envelope retries seeded attempt 1 ---
setup_impl dead-no-envelope
FP_EXPECTED=$(expected_fingerprint)
printf 'live\n' >"$IMPL_TMP/.test-registry-state"
cat >"$IMPL_TMP/bgjob/implement-step8-assessment.merge.env" <<ENV
ASSESSMENT_REQUESTED_KINDS=invariants,guidelines
ASSESSMENT_COVERED_FINGERPRINT=$FP_EXPECTED
ASSESSMENT_ATTEMPT=1
ENV
printf '1:DEAD\n' >"$IMPL_TMP/.test-wait-script"
printf '1:timeout:fail-closed\n' >"$IMPL_TMP/.test-start-seq"
printf 'yes\n' >"$IMPL_TMP/.test-wait-reset-on-start"
set +e
DEAD_OUT=$(run_helper 2>"$TMP_ROOT/dead-no-envelope.err")
DEAD_RC=$?
set -e
assert_rc "$DEAD_RC" 0 'dead-no-envelope: exits 0'
assert_contains 'ASSESSMENT_STATUS=fail-closed' "$DEAD_OUT" 'dead-no-envelope: publishes terminal failure'
assert_contains 'ASSESSMENT_ATTEMPT=2' "$DEAD_OUT" 'dead-no-envelope: retries as attempt 2'
START_COUNT=$(cat "$IMPL_TMP/.test-start-count" 2>/dev/null || echo 0)
if [ "$START_COUNT" = "1" ]; then
  pass 'dead-no-envelope: starts exactly one retry'
else
  fail "dead-no-envelope: expected 1 retry start got $START_COUNT"
fi

# --- completed malformed terminal envelope retries before acceptance ---
setup_impl malformed-completed
FP_EXPECTED=$(expected_fingerprint)
cat >"$IMPL_TMP/bgjob/implement-step8-assessment.result.env" <<ENV
BGJOB_RC=0
STEP=implement-step8-assessment
ASSESSMENT_REQUESTED_KINDS=invariants,guidelines
ASSESSMENT_COVERED_FINGERPRINT=$FP_EXPECTED
ASSESSMENT_STATUS=complete
ASSESSMENT_ATTEMPT=1
ENV
printf '1:0:complete\n' >"$IMPL_TMP/.test-start-seq"
set +e
MALFORMED_OUT=$(run_helper 2>"$TMP_ROOT/malformed-completed.err")
MALFORMED_RC=$?
set -e
assert_rc "$MALFORMED_RC" 0 'malformed-completed: exits 0'
assert_contains 'ASSESSMENT_STATUS=complete' "$MALFORMED_OUT" 'malformed-completed: replacement succeeds'
START_COUNT=$(cat "$IMPL_TMP/.test-start-count" 2>/dev/null || echo 0)
if [ "$START_COUNT" = "1" ]; then
  pass 'malformed-completed: starts attempt 2 after invalid cache'
else
  fail "malformed-completed: expected 1 retry start got $START_COUNT"
fi


# --- stale completed identities restart at attempt 1 for every input field ---
for identity_field in HEAD_SHA BASE_REF DIFF_FINGERPRINT; do
  setup_impl "identity-drift-$identity_field"
  FP_EXPECTED=$(expected_fingerprint)
  cat >"$IMPL_TMP/bgjob/implement-step8-assessment.result.env" <<ENV
BGJOB_RC=0
STEP=implement-step8-assessment
ASSESSMENT_REQUESTED_KINDS=invariants,guidelines
ASSESSMENT_COVERED_FINGERPRINT=$FP_EXPECTED
ASSESSMENT_STATUS=complete
ASSESSMENT_ATTEMPT=1
ASSESSMENT_RESULTS=invariants:clean,guidelines:clean
ENV
  case "$identity_field" in
    HEAD_SHA) sed -i '' 's/HEAD_SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/HEAD_SHA=dddddddddddddddddddddddddddddddddddddddd/' "$IMPL_TMP/architectural-guideline-materialize.env" ;;
    BASE_REF) sed -i '' 's/BASE_REF=origin\/main/BASE_REF=origin\/release/' "$IMPL_TMP/architectural-guideline-materialize.env" ;;
    DIFF_FINGERPRINT) sed -i '' 's/DIFF_FINGERPRINT=cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc/DIFF_FINGERPRINT=eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee/' "$IMPL_TMP/architectural-guideline-materialize.env" ;;
  esac
  printf '1:0:complete\n' >"$IMPL_TMP/.test-start-seq"
  set +e
  DRIFT_OUT=$(run_helper 2>"$TMP_ROOT/identity-drift-$identity_field.err")
  DRIFT_RC=$?
  set -e
  assert_rc "$DRIFT_RC" 0 "identity-drift-$identity_field: exits 0"
  assert_contains 'ASSESSMENT_ATTEMPT=1' "$DRIFT_OUT" "identity-drift-$identity_field: restarts at attempt 1"
  START_COUNT=$(cat "$IMPL_TMP/.test-start-count" 2>/dev/null || echo 0)
  if [ "$START_COUNT" = "1" ]; then
    pass "identity-drift-$identity_field: clears stale result before fresh start"
  else
    fail "identity-drift-$identity_field: expected 1 fresh start got $START_COUNT"
  fi
done

printf '\nPassed: %s Failed: %s\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
