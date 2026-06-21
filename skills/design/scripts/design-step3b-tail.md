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
- Owns the Gate C preview call and `skip_approve_requested` read.
- Exits early after the Gate C preview when `.pause-save-complete` exists.
- Does not depend on architecture diagram artifacts.

## Harness

Covered by `scripts/test-design-structure.sh`.
