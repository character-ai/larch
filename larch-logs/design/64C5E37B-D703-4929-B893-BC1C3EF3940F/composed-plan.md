## Plan

Add one Python pre-driver verb and replace the three Step 8 pre-driver fences with one fence.

The verb should:

1. Rehydrate `IMPLEMENT_TMPDIR` and plugin root like the existing Step 8 helpers.
2. Run the existing Python 3.11 guard first.
3. If the guard fails, replay all guard output to stderr only, emit exactly one `NEXT_ACTION=stall` line on stdout, and return exit code 4.
4. If `$IMPLEMENT_TMPDIR/ship-pr-state.sh` has no shell KV entries, run the existing initial seeder.
5. If the seeder fails, replay captured child output to stderr, emit `NEXT_ACTION=halt-seed`, and return the seeder exit code.
6. Always run `python/cli.py oos file --implement-tmpdir "$IMPLEMENT_TMPDIR"` after the guard and conditional seed.
7. If OOS filing fails, replay captured child output to stderr only, emit `NEXT_ACTION=halt-oos`, and return the OOS exit code.
8. On success, emit `NEXT_ACTION=ship` and return 0.

Keep stdout machine-readable. Emit exactly one `NEXT_ACTION=...` line from the new verb on every path. Forward captured child stdout and stderr to stderr so guard STALLED JSON and `oos file` JSON do not pollute the new stdout contract.

Guard stdout isolation, OOS stdout isolation, distinct halt tokens (`halt-seed` vs `halt-oos`), quiet-mode stdout contract, pre-version-gate fast path, Step 8+ intro paragraph split, pre-driver OOS disposition contract relocation, and SKILL routing are all covered in the full plan body on the issue.

**Files:** `python/cli.py`, `python/implement_dispatch.py`, `skills/implement/SKILL.md`, `scripts/test-implement-fence-shape.sh`, `scripts/test-implement-structure.sh`, `python/test_implement_dispatch.py`, `python/test_cli.py`.

## Acceptance

- One verb + one fence replace the three pre-driver fences.
- Idempotent re-entry behavior is preserved (seed only when state absent/empty; distinct exit-code stops honored).
- Stdout contract: exactly one `NEXT_ACTION=stall|halt-seed|halt-oos|ship` line; all child stdout (guard JSON, OOS JSON) goes to stderr only.
- The fence-shape harness (`scripts/test-implement-fence-shape.sh`) expectations are updated (`EXPECTED_NEW=34`).
- `scripts/test-implement-structure.sh` updated with new pins.

review_status: complete
rounds_completed: 5
diff_lines: 323
