## Goal
Implement issue #6809: [IMPLEMENTING] [BUG] /design Step 5c oversize-override recovery broken after review revises the plan.

## Implementation Plan
## Plan

## Approach

Fix two coupled defects that prevent `/design` Step 5c from recovering after a plan-size Override when Step 3 review revises the plan.

**Work item 1 — authority token not re-synced after dedup.**
`revise_waterfall` calls `_sync_oversize_override_authority` after writing the revised plan (plan_quality.py:1330), but `_run_dedup` immediately calls `gate-b-dedup --dedup` afterward. `gate_b_dedup_plan` writes `plan.txt` via `_write_atomic` (plan_review_loop.py:397) without re-syncing the authority token. Any duplicate line removed by dedup changes the plan text, breaking the sha256 fingerprint match. `plan check-size` then sees `OVERSIZE_OVERRIDE=` (empty), and Step 5c refuses publish.

Fix: add a public `sync_oversize_override_authority` wrapper in `plan_quality.py`; import and call it in `gate_b_dedup_plan` immediately after `_write_atomic`. This also covers the `design-step35-settle.sh` path that calls `gate-b-dedup --dedup` directly.

**Work item 2 — stale result-env rejoin defeats documented recovery.**
`design-step5c.sh` checks for a result env at line 81 before checking bgjob registry liveness at line 87. When the bgjob terminated with failure, the result env exists (stale) and the registry is "missing". The result-env check fires first and `exec bgjob wait --max-wait-s 0` returns the stale refusal immediately. Every documented recovery path (`re-run design-step5c.sh`) loops on the same stale failure.

Fix: move the registry liveness check before the result-env check. Only rejoin when the registry is live. When the registry is missing or cleared (not live), remove any stale result env and do a fresh bgjob start.

## Files to modify/create

### UPDATED: skills/design/scripts/design-step5c.sh

Restructure the launcher gate (lines 72–99):

- Keep symlink and non-regular result-env shape checks (lines 73–80); these must remain as guards.
- Run `step5c_bgjob_registry_state` next (currently at lines 87–89; move up).
- If registry state is `live`, `exec bgjob wait --max-wait-s 0`.
- Remove the result-env rejoin block (current lines 81–86).
- For all non-live registry states (`missing` or `cleared`), fall through to `rm -f "$_result_env"` then `bgjob start`.

After the fix, `rm -f "$_result_env"` at line 99 already clears any stale terminal result env before the fresh start.

### UPDATED: python/larch/design/plan_quality.py

Add a public function after `_sync_oversize_override_authority`:

```python
def sync_oversize_override_authority(*, design_tmpdir: Path, plan: Path) -> None:
    """Re-sync the override authority token after any write that preserves the trailer."""
    _sync_oversize_override_authority(design_tmpdir=design_tmpdir, plan=plan)
```

No other changes in this file.

### UPDATED: python/larch/review/plan_review_loop.py

Add import at top with other larch.design imports:

```python
from larch.design.plan_quality import sync_oversize_override_authority
```

In `gate_b_dedup_plan`, immediately after `_write_atomic(path=plan, ...)` (current line 397), add:

```python
sync_oversize_override_authority(design_tmpdir=tmpdir, plan=plan)
```

The `tmpdir` variable is the plan parent (design_tmpdir); `plan` is `tmpdir / "plan.txt"`. Both are already in scope.

### UPDATED: skills/design/scripts/test-design-step5c.sh

Replace the "existing bgjob result env routes to wait" assertion (lines 118–124) with a stale-result-env re-launch assertion:

- Write a stale `$D/bgjob/design-step5c.result.env` with a fake terminal failure marker.
- Re-run `design-step5c.sh` with no live registry entry.
- Assert stdout matches `BGJOB_STATUS=STARTED STEP=design-step5c PGID=*` (fresh start), not `BGJOB_STATUS=DONE`.
- Assert the new result env differs from the stale one (was overwritten by fresh run).
- Keep the existing launch and merge-env assertions.

### UPDATED: skills/design/scripts/design-step5c.md

Update the invariants section (line 16):

Change "reuses a live identity-valid `design-step5c` registry row or regular `$DESIGN_TMPDIR/bgjob/design-step5c.result.env`" to "reuses only a live identity-valid `design-step5c` registry row; stale or terminal result envs are cleared before fresh start".

### UPDATED: python/tests/review/test_plan_review.py

Add one test after the existing `test_gate_b_dedup_preserves_trailers_and_rejects_new_keys`:

`test_gate_b_dedup_resyncs_oversize_override_authority`:
1. Write `plan.txt` with a duplicate body line and `oversize_override: operator` trailer.
2. Call `run_cli("plan", "set-oversize-override", "--design-tmpdir", str(tmp_path))` to seed the authority file.
3. Verify `run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))` reports `OVERSIZE_OVERRIDE=operator`.
4. Call `run_cli("plan-review", "gate-b-dedup", "--design-tmpdir", str(tmp_path), "--snapshot-trailers")`.
5. Call `run_cli("plan-review", "gate-b-dedup", "--design-tmpdir", str(tmp_path), "--dedup")`.
6. Assert dedup removed at least 1 duplicate line (confirms plan text changed).
7. Call `run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))` again.
8. Assert `OVERSIZE_OVERRIDE=operator` (authority was re-synced by the dedup step).

### MAY_UPDATE: skills/design/SKILL.md

The existing recovery prose ("Override: plan set-oversize-override, delete composed-plan.md, re-run design-step5c.sh") becomes accurate after the code fixes. Update only if there are references to manually clearing `bgjob/design-step5c.result.env` or other now-unnecessary steps.

### MAY_UPDATE: skills/design/references/finalize-step5.md

Mirror: if the existing doc says to manually clear the result env as part of Fix-and-retry or Return-to-Gate-C recovery, remove that instruction. Otherwise no change.

## Edge cases

- A live Step 5c bgjob with no result env still rejoins through `bgjob wait` (only live path uses exec bgjob wait).
- A dead registry entry with a stale terminal result env triggers fresh start (result env cleared, bgjob restarted).
- A symlink result env still fails closed (guard retained).
- A non-regular result env still fails closed (guard retained).
- Dedup with zero duplicates removed: `_write_atomic` still writes plan.txt; `sync_oversize_override_authority` re-syncs (idempotent if content unchanged).
- Dedup called from `design-step35-settle.sh` directly (not through `_run_dedup`): same fix applies since it goes through `gate_b_dedup_plan`.

## Failure modes

- If registry lookup fails: emit `BGJOB_ERROR=registry-check-failed` and exit non-zero (unchanged from current code).
- If result-env removal fails before fresh start: the existing `rm -f ... || true` at line 99 is already permissive; failure is non-fatal.
- If `sync_oversize_override_authority` encounters an OSError reading plan.txt: silently returns (inherits `_sync_oversize_override_authority`'s error handling).

## Testing strategy

Run after changes:

- `bash skills/design/scripts/test-design-step5c.sh`
- `shellcheck skills/design/scripts/design-step5c.sh skills/design/scripts/test-design-step5c.sh`
- `python3 -m pytest python/tests/review/test_plan_review.py -k 'gate_b_dedup'`
- `python3 -m pytest python/tests/design/test_plan_quality.py -k 'oversize_override or revise_waterfall'`

## Acceptance

Run after changes:

- `bash skills/design/scripts/test-design-step5c.sh`
- `shellcheck skills/design/scripts/design-step5c.sh skills/design/scripts/test-design-step5c.sh`
- `python3 -m pytest python/tests/review/test_plan_review.py -k 'gate_b_dedup'`
- `python3 -m pytest python/tests/design/test_plan_quality.py -k 'oversize_override or revise_waterfall'`

diff_lines: 130

## Test plan
(no test plan section in plan-file)
