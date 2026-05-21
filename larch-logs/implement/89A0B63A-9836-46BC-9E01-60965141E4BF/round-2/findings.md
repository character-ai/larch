Aggregating duplicate reviewer themes, assigning stable `FINDING_N` IDs in merged order, and preserving `[OUT_OF_SCOPE]` on merged headings where applicable.

```text
### FINDING_1: Production never writes `steps_ran` for skipped Step 9a.1
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: `/implement` lifecycle does not set `steps_ran.<step>` at real skip/flush boundaries; committed manifests keep empty `steps_ran`, so audit required-file-presence logic that keys off explicit `false` never arms for genuine skipped Step 9a.1 runs despite the new schema.
- **Suggested revision**: Wire `larch-log.sh manifest --field steps_ran.<condition>=false|true` from the actual skip/complete boundaries; add integration or fixture tests proving manifest shape after those paths.

### FINDING_2: `verify-run-log-completeness.sh` diverges from `audit-scan-run.sh` on Step 9a.1 reachability
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-schema-compat-output.txt
- **Concern**: `step9a1` reachability still depends on artifact presence, non-empty `pr_number`, or `status=done`, while v2/flushed manifests often omit `pr_number` and normal teardown may omit `status`; a run can reach step 8 (`final-summary.md`) yet `step9a1` stays false, skipping conditional rows and yielding a false `OK`, out of sync with audit’s `steps_ran`-based skip semantics.
- **Suggested revision**: Align `condition_reached` with `audit-scan-run.sh` (same `steps_ran` rules and/or v2 + `final-summary.md` heuristics unless `steps_ran.step9a1` is explicitly false); add a regression fixture.

### FINDING_3: Stale `implement-finalize.sh` comments about manifest `status` / flush finalization
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, dyn-schema-compat-output.txt
- **Concern**: Comments still describe finalizing manifest `status` on normal teardown though that path no longer persists `status`/`pr_number`, misleading maintainers about recovery vs `stalled_at_step` and where merge-time writes live.
- **Suggested revision**: Reword to stall-only `stalled_at_step`, recovery-only `status=partial`, and pointers to `ship-pr` / other sanctioned writers for any remaining `status`/`pr_number` behavior.

### FINDING_4: `audit-scan-run.md` misstates the `jq` probe (`-n` vs `-ne`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-shell-compat-output.txt
- **Concern**: Doc says `jq -n` for the `steps_ran` gate; implementation uses `jq -ne` so exit status reflects the boolean; readers may copy wrong flags or miss exit-code-driven semantics.
- **Suggested revision**: Align the sentence with `audit-scan-run.sh` (name `jq -ne` or `jq -n -e` and note `-e` maps boolean to process exit code).

### FINDING_5: `write-final-report.md` outcome bullets vs renderer contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Doc implies all nine outcomes appear as Outcome bullets; renderer only surfaces some cases (e.g. bailed/stalled), confusing readers.
- **Suggested revision**: Clarify title vs bullet contract for which outcomes render visibly.

### FINDING_6: Post-merge `ship-pr.sh` still writes `status=done` and `pr_number`
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-schema-compat-output.txt
- **Concern**: `run_postmerge_phase` still calls `larch-log.sh manifest` with `status=done` and `pr_number` after merge while finalize teardown stopped writing those keys on normal paths; scope for issue #2513(B) (“absent from every committed manifest”) is ambiguous and docs read in isolation can contradict.
- **Suggested revision**: Confirm issue scope; either remove postmerge writes if global absence is required, or document `ship-pr` as the intentional merge-time writer and align `scripts/ship-pr.md` / tests with the split contract.

### FINDING_7: `larch-log.sh` manifest `--field` allows malformed `steps_ran*` keys (e.g. `steps_ranx`, `steps_ranstep9a1`)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Typos can match a generic arm and write a top-level field instead of validated `steps_ran.<step>`, causing schema drift and audits reading the wrong structure.
- **Suggested revision**: Add a reject arm or prefix guard so only `steps_ran.<step>` is accepted; fail fast on other `steps_ran`-prefixed keys.

### FINDING_8: `audit-scan-run.sh` trusts manifest `steps_ran` for required-file-presence skips
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Skipped checks rely on committed JSON; a mistaken or malicious manifest could hide missing required audit artifacts while still reporting pass for gated rows (integrity bounded by git trust).
- **Suggested revision**: Document explicit trust assumptions or add independent corroboration if stronger integrity is required.

### FINDING_9: `audit-map-runs.sh` — `gh` failure blocks manifest `pr_number` fallback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: When `gh` is offline or broken, mapping can be empty despite local manifest data that could otherwise fall back.
- **Suggested revision**: Document the tradeoff or add an opt-in local manifest fallback when `gh` fails.

### FINDING_10: `audit-map-runs.sh` — PR-to-run mapping depends on `Closes` in PR body; v2 omits `pr_number`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Primary mapping expects `Closes` in the PR body; bodies with only `Fixes`/`Resolves` (or no closing keyword) can yield empty `run_id` in audit TSV even when a run log exists; older manifest-primary behavior could map when `pr_number` was written.
- **Suggested revision**: Document the contract; extend closing-keyword parsing; and/or add v2 manifest fields so mapping does not depend on `Closes` alone.

### FINDING_11: `audit-map-runs.sh` — `pick_newest_manifest_among_pr` matches only numeric `pr_number`
- **Reviewer(s)**: dyn-schema-compat-output.txt
- **Concern**: Predicate requires `pr_number` type `number`; string (or other) typed values never match numeric `$pn` even when numerically equal, breaking fallback for legacy string manifests.
- **Suggested revision**: Use a jq predicate that accepts number or string (e.g. guarded `tonumber?` comparison).

### FINDING_12: `audit-scan-run.sh` — `is_v2` requires numeric `schema_version`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: String `schema_version` (e.g. `"2"`) can fall through to legacy `pr_number` null rules and mis-classify v2 manifests in cross-cutting NDJSON.
- **Suggested revision**: Coerce or accept string `schema_version` before the legacy vs v2 split.

### FINDING_13: `audit-scan-run.sh` — `steps_ran` skip uses strict JSON boolean `false` only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: String `"false"` in `steps_ran` does not skip; required-file-presence can fail for legitimately skipped steps if values are not normalized.
- **Suggested revision**: Accept string false or normalize `steps_ran` on load.

### FINDING_14: `larch-log.sh` — `steps_ran` step id character set may be too narrow
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Step keys limited to alnum and underscore; hyphenated future step ids cannot be recorded via manifest updates.
- **Suggested revision**: Document allowed charset or widen the pattern to match real step ids.

### FINDING_15: Missing round-trip test for dotted `steps_ran.*` manifest updates
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `test-larch-logs-manifest.sh` lacks assertions that multiple `steps_ran.*` updates compose correctly in `larch-log.sh` (nested value + `updated_at` behavior).
- **Suggested revision**: Add `jq` assertions after `manifest --field steps_ran.step9a1=false` (and similar) to catch filter composition regressions.

### FINDING_16: No harness for plain “bailed” outcome vs renderer Outcome bullet
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Future changes to `bailed*|stalled` handling or `OUTCOME` assignment could drop the only user-visible signal for early bails without failing tests.
- **Suggested revision**: Add a minimal bailed fixture in `test-write-final-report.sh` and assert `**Outcome**: bailed` (or equivalent) in rendered output.

### FINDING_17: [OUT_OF_SCOPE] Verbose `plan-goals-test.md` in committed run log tree
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-shell-compat-output.txt
- **Concern**: Large low-signal markdown under `larch-logs/implement/.../` is policy/process noise for reviewers rather than a script defect.
- **Suggested revision**: Optional editorial trim of flushed plan content if desired.

### FINDING_18: [OUT_OF_SCOPE] `write-final-report.sh` MERGE/PR/MERGE_RESULT fallthrough to unchanged “bailed”
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Pre-existing structure behavior; not introduced by this branch’s outcome/render changes; no change required for this review scope.
- **Suggested revision**: None for this scope.

### FINDING_19: [OUT_OF_SCOPE] `[[ ... ]]` in new `gh` stubs in `test-audit-runs.sh`
- **Reviewer(s)**: dyn-shell-compat-output.txt
- **Concern**: Valid on macOS Bash 3.2; not among constructs flagged by `scripts/lint-bash32.sh` (which scans `*.sh` only).
- **Suggested revision**: None.

### FINDING_20: [OUT_OF_SCOPE] `.claude/skills/audit-runs/SKILL.md` still centers manifest `pr_number` skew
- **Reviewer(s)**: dyn-schema-compat-output.txt
- **Concern**: Skill-level guidance was not updated on this branch and can understate v2 “absent `pr_number` is normal” relative to `audit-scan-run.sh` `is_v2` behavior.
- **Suggested revision**: Follow-up doc/skill alignment if desired.

### FINDING_21: [OUT_OF_SCOPE] `scripts/ship-pr.md` vs `scripts/implement-finalize.md` potential inconsistency
- **Reviewer(s)**: dyn-schema-compat-output.txt
- **Concern**: `ship-pr.md` still documents postmerge `status`/`pr_number` writes (consistent with `ship-pr.sh`) but may read as conflicting with finalize teardown doc after this branch.
- **Suggested revision**: Clarify split contract in a follow-up if policy is finalized elsewhere.

### FINDING_22: [OUT_OF_SCOPE] `larch-log.sh` manifest does not forbid `pr_number`/`status` on `schema_version: 2`
- **Reviewer(s)**: dyn-schema-compat-output.txt
- **Concern**: Permissive-by-design for recovery/tests; schema cleanup remains a caller convention, not an enforced invariant.
- **Suggested revision**: Accept as policy or enforce in a separate change if product requires hard invariants.

### FINDING_23: [OUT_OF_SCOPE] `scripts/larch-log.md` slightly overstates that `status` is never a post-init manifest concern
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Recovery paths can still write `status=partial`; minor contract imprecision.
- **Suggested revision**: Clarify recovery exception in a follow-up doc edit.
```
