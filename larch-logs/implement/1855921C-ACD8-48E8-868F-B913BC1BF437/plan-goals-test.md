## Goal
Implement issue #4219: [IMPLEMENTING] [BUG] /design Step 5c: anti-poll violation skips final-summary.md generation.

## Implementation Plan
## Plan

Add a narrow Step 6 guard for the known race:

- If `.design-step5c-status.env` is missing.
- And `$DESIGN_TMPDIR/.bg-wait-active` exists.
- Then emit a hard Step 6 in-flight error to stderr and exit 1.
- Do this before the existing missing-sidecar preserved/skipped branches.

Keep the marker name as `.bg-wait-active`. Do not add or rename Step 5c marker logic.

## Files to modify/create

### UPDATED: skills/design/scripts/design-step6-prelude.sh

Add the guard immediately after `design_source_env_optional` and before:

```bash
if [[ ! -f "$DESIGN_TMPDIR/.design-step5c-status.env" ]]; then
```

Use a safe empty-tmpdir check:

```bash
if [[ ! -f "$DESIGN_TMPDIR/.design-step5c-status.env" && -n "${DESIGN_TMPDIR:-}" && -f "$DESIGN_TMPDIR/.bg-wait-active" ]]; then
  printf '%s\n' "**⚠ Step 6 prelude: design-step5c.sh appears still in-flight (.bg-wait-active present); do not proceed until <task-notification> fires.**" >&2
  exit 1
fi
```

Keep the existing missing-sidecar skip branch unchanged for the non-in-flight case.

### UPDATED: skills/design/scripts/design-step6-cleanup.sh

Add the same guard after the pause-save early exec and before the existing missing-sidecar preservation branch.

Use Step 6 cleanup wording:

```bash
if [[ ! -f "$DESIGN_TMPDIR/.design-step5c-status.env" && -n "${DESIGN_TMPDIR:-}" && -f "$DESIGN_TMPDIR/.bg-wait-active" ]]; then
  printf '%s\n' "**⚠ Step 6: design-step5c.sh appears still in-flight (.bg-wait-active present); do not proceed until <task-notification> fires.**" >&2
  exit 1
fi
```

Keep the existing preservation branch unchanged for missing sidecar without an active background marker.

### UPDATED: scripts/test-design-structure.sh

Extend `assert_step6_cleanup_wrappers` with structural pins:

- `design-step6-prelude.sh` contains `.bg-wait-active`.
- `design-step6-cleanup.sh` contains `.bg-wait-active`.
- Both contain `appears still in-flight`.

This catches regressions where the functional test exists but wrappers lose the guard.

### NEW: skills/design/scripts/test-design-step6.sh

Add a small offline harness.

Test cases:

1. **Prelude in-flight hard error**
   - Create a temp design tmpdir.
   - Create `$DESIGN_TMPDIR/.bg-wait-active`.
   - Do not create `.design-step5c-status.env`.
   - Run `design-step6-prelude.sh` with `DESIGN_TMPDIR`.
   - Assert exit code 1.
   - Assert stderr contains `appears still in-flight`.
   - Assert stdout does not contain `STEP6_PRELUDE_STATUS=skipped`.

2. **Cleanup in-flight hard error**
   - Same setup.
   - Run `design-step6-cleanup.sh`.
   - Assert exit code 1.
   - Assert stderr contains `appears still in-flight`.
   - Assert stdout does not contain `CLEANUP_STATUS=preserved`.

3. **Existing missing-sidecar behavior remains**
   - Use a fresh tmpdir with no `.bg-wait-active`.
   - Run prelude.
   - Assert exit 0 and stdout contains `STEP6_PRELUDE_STATUS=skipped`.
   - Assert stderr does not contain `appears still in-flight`.
   - Run cleanup.
   - Assert exit 0 and stdout contains `CLEANUP_STATUS=preserved`.
   - Assert stderr does not contain `appears still in-flight`.

4. **Status sidecar overrides stale marker**
   - Use a fresh tmpdir.
   - Create both `.design-step5c-status.env` and `.bg-wait-active`.
   - Use a minimal sidecar body that follows the normal skip/preserve path:

```bash
PLAN_WRITE_OK=false
```

   - Run prelude.
   - Assert exit 0.
   - Assert stdout contains `STEP6_PRELUDE_STATUS=skipped`.
   - Assert stderr does not contain `appears still in-flight`.
   - Run cleanup.
   - Assert exit 0.
   - Assert stdout contains `CLEANUP_STATUS=preserved`.
   - Assert stderr does not contain `appears still in-flight`.

Implementation notes:

- Use `mktemp -d` and `trap 'rm -rf "$TMP"' EXIT`.
- Capture stdout and stderr separately into files under the temp root.
- Assert in-flight diagnostics on stderr.
- Assert KV status lines and KV negatives on stdout.
- Set `DESIGN_TMPDIR` through the environment.
- Set `CLAUDE_PLUGIN_ROOT="$ROOT"` for consistency.
- Make the file executable.

### UPDATED: skills/design/SKILL.md

Add `test-design-step6.sh` to the wrapper contract inventory list, immediately after `test-design-step5c.sh` (around line 189):

```
- `${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/test-design-step6.sh`
```

This prevents agent-lint S030 from flagging the new harness as an unreferenced skill file.

### UPDATED: Makefile

Add `test-design-step6` to `.PHONY`.

Add the target near the existing design script harnesses:

```make
test-design-step6:
	python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-step6.sh
```

Add `test-design-step6` to `test-harnesses-6`, next to `test-design-step5c`, because the new harness covers adjacent Step 5c/Step 6 publish handoff behavior.

## Edge cases

- If `DESIGN_TMPDIR` is empty, the guard must not probe `/.bg-wait-active`.
- If `.design-step5c-status.env` exists, Step 6 must ignore `.bg-wait-active` and follow the status sidecar.
- If both files are absent, preserve the current skipped/preserved behavior.
- If the cleanup script is called directly, it must still fail hard for in-flight Step 5c.
- If a stale marker remains after the sidecar exists, Step 6 must not block solely on the stale marker.

## Failure modes

- A stale `.bg-wait-active` without a status sidecar will now block Step 6. That is acceptable because it is safer than deleting or preserving based on incomplete publish state.
- If Step 5c exits without removing `.bg-wait-active` and without writing the status sidecar, Step 6 will surface the inconsistency as a hard error.
- If the guard accidentally checks only `.bg-wait-active`, the sidecar-plus-marker test must fail.

## Acceptance

Verified behavior:

- `design-step6-prelude.sh`: when `.design-step5c-status.env` absent and `.bg-wait-active` present, exits 1 with `**⚠ Step 6 prelude: design-step5c.sh appears still in-flight...`
- `design-step6-cleanup.sh`: same guard exits 1 with `**⚠ Step 6: design-step5c.sh appears still in-flight...`
- Both scripts: when `.bg-wait-active` absent (no sidecar), existing skip/preserve behavior unchanged.
- Both scripts: when sidecar present (even if marker also present), guard does not fire.
- `test-design-structure.sh` `assert_step6_cleanup_wrappers`: pins `.bg-wait-active` and `appears still in-flight` in both wrappers.
- `test-design-step6.sh`: four test cases pass covering all four guard-path combinations.
- `make test-design-step6` and `bash scripts/relevant-checks.sh` pass.

diff_lines: 155

## Test plan
(no test plan section in plan-file)
