# Review Round 2

- Mode: `diff`
- Accepted findings: 10
- Rejected findings: 0
- Exonerated findings: 6
- Neutral findings: 0

## Accepted Findings

### FINDING_1: Production never writes `steps_ran` for skipped Step 9a.1
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: `/implement` lifecycle does not set `steps_ran.<step>` at real skip/flush boundaries; committed manifests keep empty `steps_ran`, so audit required-file-presence logic that keys off explicit `false` never arms for genuine skipped Step 9a.1 runs despite the new schema.
- **Suggested revision**: Wire `larch-log.sh manifest --field steps_ran.<condition>=false|true` from the actual skip/complete boundaries; add integration or fixture tests proving manifest shape after those paths.


### FINDING_10: `audit-map-runs.sh` — PR-to-run mapping depends on `Closes` in PR body; v2 omits `pr_number`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Primary mapping expects `Closes` in the PR body; bodies with only `Fixes`/`Resolves` (or no closing keyword) can yield empty `run_id` in audit TSV even when a run log exists; older manifest-primary behavior could map when `pr_number` was written.
- **Suggested revision**: Document the contract; extend closing-keyword parsing; and/or add v2 manifest fields so mapping does not depend on `Closes` alone.


### FINDING_11: `audit-map-runs.sh` — `pick_newest_manifest_among_pr` matches only numeric `pr_number`
- **Reviewer(s)**: dyn-schema-compat-output.txt
- **Concern**: Predicate requires `pr_number` type `number`; string (or other) typed values never match numeric `$pn` even when numerically equal, breaking fallback for legacy string manifests.
- **Suggested revision**: Use a jq predicate that accepts number or string (e.g. guarded `tonumber?` comparison).


### FINDING_15: Missing round-trip test for dotted `steps_ran.*` manifest updates
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `test-larch-logs-manifest.sh` lacks assertions that multiple `steps_ran.*` updates compose correctly in `larch-log.sh` (nested value + `updated_at` behavior).
- **Suggested revision**: Add `jq` assertions after `manifest --field steps_ran.step9a1=false` (and similar) to catch filter composition regressions.


### FINDING_16: No harness for plain “bailed” outcome vs renderer Outcome bullet
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Future changes to `bailed*|stalled` handling or `OUTCOME` assignment could drop the only user-visible signal for early bails without failing tests.
- **Suggested revision**: Add a minimal bailed fixture in `test-write-final-report.sh` and assert `**Outcome**: bailed` (or equivalent) in rendered output.


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


### FINDING_6: Post-merge `ship-pr.sh` still writes `status=done` and `pr_number`
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-schema-compat-output.txt
- **Concern**: `run_postmerge_phase` still calls `larch-log.sh manifest` with `status=done` and `pr_number` after merge while finalize teardown stopped writing those keys on normal paths; scope for issue #2513(B) (“absent from every committed manifest”) is ambiguous and docs read in isolation can contradict.
- **Suggested revision**: Confirm issue scope; either remove postmerge writes if global absence is required, or document `ship-pr` as the intentional merge-time writer and align `scripts/ship-pr.md` / tests with the split contract.


### FINDING_7: `larch-log.sh` manifest `--field` allows malformed `steps_ran*` keys (e.g. `steps_ranx`, `steps_ranstep9a1`)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Typos can match a generic arm and write a top-level field instead of validated `steps_ran.<step>`, causing schema drift and audits reading the wrong structure.
- **Suggested revision**: Add a reject arm or prefix guard so only `steps_ran.<step>` is accepted; fail fast on other `steps_ran`-prefixed keys.


