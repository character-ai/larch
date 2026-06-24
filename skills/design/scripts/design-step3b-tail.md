# design-step3b-tail.sh

## Purpose

Combined `/design` wrapper for Step 4 rejected-findings output and Gate C preview setup after the Step 3b finalize boundary completes.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Accepts launcher-owned `--session-env-path` and `--claude-pid` arguments.
- Does not derive the root Claude PID from `$PPID` internally.
- Emits rejected findings between `---LARCH-REJECTED-BEGIN---` and `---LARCH-REJECTED-END---` markers.
- Filters the rejected-findings body through `python3 cli.py plan-review emit-rejected --report-framing` so operator output is presented as considered-not-adopted suggestions, not unimplemented gaps.
- Falls back to identity-key-filtered `emit-rejected` without `--report-framing` on any non-zero exit from the framed path, with the same considered-not-adopted heading and annotation.
- Leaves the on-disk `rejected-findings.md` unchanged for run-log audit fidelity.
- Owns the Step 4 compatibility FINALIZE guard for paused sessions missing `.completed/finalize`.
- Reads `skip_approve_requested` before Gate C preview.
- Runs `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design dialectic-gatec --design-tmpdir "$DESIGN_TMPDIR"` as a foreground Python subprocess before preview; the call is no-op when no candidate file exists, fingerprints mismatch, or `--skip-approve` suppresses new auto debate.
- Writes `.completed/dialectic-gatec-terminal` after `dialectic-gatec` completes.
- Owns digest-before-preview ordering and uses `design-step3b-tail.sh` as the retired `design-step4b-preview.sh` replacement.
- The orchestrator, not this wrapper, backgrounds the whole tail fence when debate may run.
- Exits early after the Gate C preview when `.pause-save-complete` exists.
- Does not depend on architecture diagram artifacts.
- Must not mutate repository files; dialectic artifacts live under `$DESIGN_TMPDIR`.

## Harness

Covered by `scripts/test-design-structure.sh`.
