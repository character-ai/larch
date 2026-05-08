# check-review-changes.sh contract

## Purpose

Tells `/implement` Step 6 whether the code review step (Step 5: `/review` skill in normal mode, or the inline reviewer loop in quick mode) modified the working tree. The result gates Step 6's `/relevant-checks` second pass and Step 7's "Address code review feedback" commit. False positives here produce phantom commits that may absorb stray operator files; false negatives mean review-induced changes are skipped.

## Contract

**Stdout** — THREE `key=value` lines, ALWAYS emitted on every invocation, in stable order:

```
FILES_CHANGED=true|false
UNTRACKED_BASELINE=present|missing
GIT_PROBE_FAILED=true|false
```

Consumers MUST parse with key-based extraction (e.g., `grep -E '^FILES_CHANGED='` or `awk -F= '$1=="FILES_CHANGED"{print $2}'`). Do NOT `eval` or `source` the script's stdout — output may include arbitrary file paths from the working tree.

**Stdin**: none.

**Exit codes**: always `0`, including on bad CLI input (unknown flag, `--baseline` with no path). On parse errors the script emits an informational `ERROR=…` line on stderr and degrades to the missing-baseline path on stdout (`FILES_CHANGED=false UNTRACKED_BASELINE=missing GIT_PROBE_FAILED=false` if no other detection source fires). Parse errors are NOT probe failures, so `GIT_PROBE_FAILED` stays `false` on the parse-error path. Callers MUST parse stdout, not stderr or exit code.

**Health-probe key — `GIT_PROBE_FAILED`**: each git probe (`git diff --name-only` for unstaged, `git diff --name-only --cached` for staged, and `git ls-files --others --exclude-standard | sort` for untracked) captures its exit status explicitly. Any non-zero probe sets `GIT_PROBE_FAILED=true`; otherwise `false`. The signal is independent of `FILES_CHANGED` — a probe failure produces empty output for that source, which is observationally indistinguishable from "no changes" in `FILES_CHANGED` alone, and `GIT_PROBE_FAILED` is the only way for callers to distinguish the two states.

**Best-effort git probing (default, no `--strict`)**: probe failures degrade to "no changes detected on that source" for the purpose of computing `FILES_CHANGED`. This is the historical graceful-degradation behavior: a degraded run reports a conservative `FILES_CHANGED=false` rather than blocking Step 6, and the operator's tracked-changes flow (commit / push) surfaces any genuine git breakage downstream. The new `GIT_PROBE_FAILED` key now exposes the unknown-state signal so callers can decide independently.

**Strict mode (`--strict`)**: when set AND any probe failed (`GIT_PROBE_FAILED=true`), the script forces `FILES_CHANGED=true` — fail-closed: treat unknown working-tree state as may-have-changed, so Step 6 enters the changes-found branch rather than silently skipping the post-/review checks pass. Without `--strict`, `FILES_CHANGED` reflects only the observed signal (preserving the historical default). `--strict` does NOT change behavior when all probes succeed (`GIT_PROBE_FAILED=false`); it is purely a fail-closed gate on probe-failure paths.

## Detection sources

`FILES_CHANGED=true` if and only if any of:

- `git diff --name-only` (unstaged) is non-empty
- `git diff --name-only --cached` (staged) is non-empty
- `UNTRACKED_BASELINE=present` AND the untracked delta is non-empty

The untracked delta is `comm -23 <(current-sorted) <(baseline-sorted)` — paths in the current untracked set that were NOT in the pre-/review snapshot.

## Required pre-snapshot

The `--baseline <path>` flag points to a sorted list of untracked paths captured BEFORE `/review` ran. `/implement` Step 5 owns this snapshot. The snapshot is an artifact of the `/implement` orchestration contract, not of this script.

## Baseline-state classification

| Baseline state | Detected as | Untracked dimension |
|----------------|-------------|---------------------|
| `--baseline` not passed | `missing` | ignored (delta = ∅) |
| Path passed but file does not exist | `missing` | ignored (delta = ∅) |
| Path passed but file is unreadable | `missing` | ignored (delta = ∅) |
| Path passed, file readable and zero-byte | `present` | delta = current (no untracked at snapshot time) |
| Path passed, file readable and non-empty | `present` | delta = comm -23 |

A zero-byte readable file is `present` (not `missing`) because it legitimately represents "the working tree had no untracked files at snapshot time"; every current untracked path is therefore review-created.

## Caller

The single in-tree caller is `skills/implement/SKILL.md` Step 6. Step 5 of the same SKILL.md owns writing the `--baseline` file before either the quick-mode reviewer loop or the normal-mode `/review` invocation. Edit-in-sync rule: any change to this contract MUST update both Step 5 (snapshot) and Step 6 (call site) in the same PR.

## Standalone / debugging invocation

Manual operators running the script directly (no `--baseline`) get `UNTRACKED_BASELINE=missing` and the untracked dimension is silently skipped — i.e., a working tree containing only untracked files reports `FILES_CHANGED=false`. This is a deliberate behavior change from the pre-fix script (which reported `FILES_CHANGED=true` for any untracked file). To exercise the full contract manually:

```bash
# Simulate Step 5's snapshot
git ls-files --others --exclude-standard | LC_ALL=C sort > /tmp/baseline.txt
# … perform review-equivalent edits …
skills/implement/scripts/check-review-changes.sh --baseline /tmp/baseline.txt
```

## Snapshot resume hazard

The snapshot path `$IMPLEMENT_TMPDIR/pre-review-untracked.txt` is stable across Step 5 re-entries (resume / retry). On a re-entry, Step 5 attempts a fresh snapshot; on success the file is overwritten via atomic temp+rename; on failure Step 5 unconditionally `rm -f`s the prior baseline so this script's `=missing` path activates rather than diffing against stale data. Operators should not edit `$IMPLEMENT_TMPDIR` between Step 5 and Step 6.

## Test harness

`skills/implement/scripts/test-check-review-changes.sh` (offline harness, wired via `make lint`'s `test-harnesses` target). Cases pin the regression behavior (issue #651), the empty-vs-missing distinction, the `printf '%s\n'` → `comm` → `sed` safety net, the issue #695 dash-prefixed-filename fix, and the issue #1485 `GIT_PROBE_FAILED` / `--strict` fail-closed mode. See `skills/implement/scripts/test-check-review-changes.md` for case-by-case detail and the deliberate-behavior-change callout for case (f).

## Edit-in-sync

Behavior changes (new detection source, stdout key rename, exit-code semantics) must be mirrored in:
- this file
- the script docstring header in `check-review-changes.sh`
- `skills/implement/SKILL.md` Step 5 (snapshot block) AND Step 6 (call site, key parsing)
- `skills/implement/scripts/test-check-review-changes.sh` (regression cases)
- `skills/implement/scripts/test-check-review-changes.md` (case documentation)

All in the same PR. The CI workflow does not currently grep this file or the script for content invariants.
