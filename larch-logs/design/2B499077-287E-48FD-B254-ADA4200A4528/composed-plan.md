## Plan

## Implementation Plan

### Approach

Create a thin bash wrapper `step-5-review.sh` that folds the entry telemetry, cap computation, and banner print from the current two-fence pattern into one script. The script then calls `review-and-fix step5 --mode loop` via `exec`. SKILL.md drops the `step-5-entry.sh` fence and the banner-variable plumbing, replacing both with a single immediate-background call to `step-5-review.sh`. Retire `step-5-entry.sh` and update the harnesses.

The banner text stays byte-identical. The only behavioral change is that the banner now appears in the wrapper's stdout (captured in the background task output) rather than being assembled by the orchestrator.

### Files to modify/create

### NEW: skills/implement/scripts/step-5-review.sh

Copy `step-5-entry.sh` as the base: retain `rehydrate_plugin_root` and `read_session_key` helpers, the telemetry mark, and the cap-computation logic (unchanged from entry). Omit the unused `rehydrate_larch_triplet` helper from `step-5-entry.sh` (it is defined but never called). Add a `printf` that emits the Step 5 banner line with resolved `$round_cap` and `$dynamic_archetypes_cap`. End with:

```bash
exec python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" review-and-fix step5 \
  --implement-tmpdir "$IMPLEMENT_TMPDIR" --mode loop --starting-round 1
```

`exec` replaces the wrapper's process so the review loop output flows through directly. The file must be executable.

Banner text (byte-compatible with current SKILL.md template):

```
> **🔶 /implement 5: code review — review-and-fix step5 --mode loop, up to <round_cap> rounds; 3-judge panel on every round (Claude+Codex+Cursor); review panel: specialists per vendor (mechanically pruned in rounds 3-4 when prior yield is zero); dynamic-archetypes cap=<dynamic_archetypes_cap>**
```

### NEW: skills/implement/scripts/step-5-review.md

Sibling doc following the same structure as `step-5-entry.md`. Describe purpose, callers (SKILL.md scripted review loop), KV grammar (none; all output is from the review-and-fix CLI), invariants (Bash 3.2 portable; self-rehydrates `CLAUDE_PLUGIN_ROOT`; telemetry is best-effort), and edit-in-sync rules.

### UPDATED: skills/implement/SKILL.md

Changes in `## Step 5 — Code Review`:

1. Remove the top-level `step-5-entry.sh` Bash fence (3 lines at current lines 543-545). This fence ran unconditionally for both scripted and self-review paths.

2. In `### Self-review mode`: add a minimal foreground telemetry-mark fence immediately before the self-review banner print, to replace the telemetry coverage lost when the top-level entry fence is removed:

```bash
bash "$IMPLEMENT_TMPDIR/larch-run.sh" python/cli.py timing telemetry-mark --implement-tmpdir "$IMPLEMENT_TMPDIR" --label "Step 5 — code review" || true
```

3. In `### Scripted review loop`:
   - Remove the banner-variable plumbing paragraph ("Use the `DYNAMIC_ARCHETYPES_CAP` and `ROUND_CAP` lines..." through "Treat a non-zero fence exit...").
   - Remove the "Print once before the `review-and-fix step5` invocation:" instruction and banner template line.
   - Rewrite the scripted-loop description paragraph (currently at line 582): change "Step 5 invokes `python3 ... review-and-fix step5`... **one** `review-and-fix step5` Bash tool call" to describe one `step-5-review.sh` launcher call that internally marks telemetry, resolves `dynamic_archetypes_cap` (session-env `LARCH_DYNAMIC_ARCHETYPES_MAX`, then process env, then implement-mode default `3`), prints the Step 5 banner, and execs `review-and-fix step5 --mode loop`.
   - Replace the review-loop Bash fence calling `python/cli.py review-and-fix step5 --implement-tmpdir "$IMPLEMENT_TMPDIR" --mode loop --starting-round 1` with `skills/implement/scripts/step-5-review.sh`.
   - Add one sentence for non-zero exit handling: if the wrapper exits non-zero and stdout has no `STEP5_REVIEW_STATUS`, treat it as a Step 5 preflight failure, log to `Warnings`, and do not parse the loop status branches.
   - Keep `run_in_background: true`, `timeout: 21600000`, and the `<task-notification>` wait instruction on the merged fence.

4. Update the **Extracted Script Registry** (~line 95): replace `step-5-entry.md` with `step-5-review.md`.

### UPDATED: scripts/test-implement-structure.sh

1. Replace `'skills/implement/scripts/step-5-entry.sh'` with `'skills/implement/scripts/step-5-review.sh'` in the SKILL.md launcher-check list.
2. Remove `'python/cli.py review-and-fix step5 --implement-tmpdir "$IMPLEMENT_TMPDIR" --mode loop --starting-round 1'` from the same list (now inside the wrapper).
3. Replace `'step-5-entry'` with `'step-5-review'` in the wrappers sibling/executable list.
4. Change both `launcher + 'python/cli.py review-and-fix step5'` anchors (timeout pin and task-notification pin) to `launcher + 'skills/implement/scripts/step-5-review.sh'`.
5. Add a new `require` assertion: `require('skills/implement/scripts/step-5-review.sh', 'review-and-fix step5', 'step-5-review calls review-and-fix step5')`.
6. Add `forbid` assertions for retired paths: `forbid(skill, 'skills/implement/scripts/step-5-entry.sh', 'retired step-5-entry.sh call removed from SKILL')` and `forbid(skill, 'step-5-entry.md', 'retired step-5-entry.md ref removed from SKILL')`.

### UPDATED: scripts/test-implement-fence-shape.sh

Decrement `EXPECTED_NEW` by 1 (removing the top-level `step-5-entry.sh` foreground fence reduces the SKILL.md new-shape Bash fence count). The self-review telemetry fence added above restores 1 fence on the self-review path, so net `EXPECTED_NEW` stays unchanged. Verify the exact value by running the harness before committing.

### UPDATED: python/migrated-scripts.tsv

Append:

```
skills/implement/scripts/step-5-entry.sh	#4015
skills/implement/scripts/step-5-entry.md	#4015
```

### DELETED: skills/implement/scripts/step-5-entry.sh

Remove. No shim.

### DELETED: skills/implement/scripts/step-5-entry.md

Remove. No stub.

---

### Edge cases

- If `session-env.sh` is unreadable or absent, cap falls back to process `LARCH_DYNAMIC_ARCHETYPES_MAX`, then `3`. Unchanged behavior from `step-5-entry.sh`.
- If the resolved cap is out of range, the wrapper exits non-zero before `exec`. SKILL.md handles non-zero exit as preflight failure.
- Self-review mode gets the same telemetry-mark as today, from the new foreground fence added before its banner.
- `step-5-resume.sh` is unaffected: it handles round resume, not initial entry.

### Failure modes

- A lingering reference to `step-5-entry.sh` will fail `make lint-retired-scripts`.
- Banner text drift breaks byte-compatibility; the `printf` in `step-5-review.sh` must match the SKILL.md template exactly.
- Forgetting to mark `step-5-review.sh` executable will cause `test-implement-structure.sh` to fail.
- Mismatched `EXPECTED_NEW` in `test-implement-fence-shape.sh` will fail `make test-harnesses-3` / `make lint`.

### Testing strategy

1. `bash scripts/test-implement-structure.sh`
2. `bash scripts/test-implement-fence-shape.sh` (or `make test-implement-fence-shape`)
3. `bash skills/implement/scripts/test-implement-review-token-propagation.sh`
4. `make lint-retired-scripts`
5. `bash scripts/relevant-checks.sh`

Verify no `ci.yaml` change is needed: `skills/implement/SKILL.md` is not in `UNQUOTED_FILES`; the banner contains no focus-area enum.

## Acceptance

Gate C approved.

diff_lines: 188
