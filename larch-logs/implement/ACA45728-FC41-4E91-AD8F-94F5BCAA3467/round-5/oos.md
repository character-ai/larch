### OOS_1: [OUT_OF_SCOPE] CHANGELOG / plugin.json release alignment
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `CHANGELOG.md`, `.claude-plugin/plugin.json`: #3227 in Unreleased while 47.0.13 documents #3229 cleanup. Release notes may not match the version bump on merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Align version section with the merged feature set when cutting release.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] plan-review collector tee vs production redaction location
- **Reviewer(s)**: dyn-tail-redaction-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/plan-review-loop.sh:758-763` still tees collector raw stderr to FD 2/4; production redaction for panel failures lives in `collect-agent-results.sh` §3.8. Branch regression test documents existing unredacted stub stderr on FD 2 rather than introducing a new emit path.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_11: [OUT_OF_SCOPE] `emit_kv SIDECAR_LOG=` still exposes full unredacted sidecar path
- **Reviewer(s)**: dyn-tail-redaction-output.txt
- **Severity**: latent
- **Concern**: `emit_kv SIDECAR_LOG=…` on implement failure paths (unchanged contract) still exposes a filesystem path to the full, unredacted sidecar; branch adds redacted `.stderr-tail` surfacing but does not narrow that KV surface.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_12: [OUT_OF_SCOPE] Positive note: producer/consumer wiring and redaction harness
- **Reviewer(s)**: dyn-tail-redaction-output.txt
- **Severity**: nit
- **Concern**: Producer/consumer wiring otherwise routes chat emission through `emit_failed_agent_stderr_tail_larch_err` on `${stem}.stderr-tail` artifacts, honors empty-stem guards in `ship-pr` and Step 5, and adds harness checks that synthetic `sk-ant-*` tokens are redacted in codex/cursor implement tails.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_13: [OUT_OF_SCOPE] Optional `_collect_rc` wiring (dyn-cleanup duplicate)
- **Reviewer(s)**: dyn-cleanup-retention-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/plan-review-loop.sh:757-766`: `set +e` / `_collect_rc=$?` allow collector stderr tee on non-zero exit; `_collect_rc` never consulted afterward; behavior still depends on parsed stdout records. Consider wiring into degraded/panel-failed classification if hard collector failure should not be inferred solely from empty parse output. (Overlaps in-scope FINDING_4; listed separately as reviewer-marked OOS.)
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cleanup-retention-output.txt: Consider wiring `_collect_rc` into existing degraded/panel-failed classification if hard collector failure should not be inferred solely from empty parse output.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_14: [OUT_OF_SCOPE] cleanup cache vs `/tmp` enumeration asymmetry (intentional)
- **Reviewer(s)**: dyn-cleanup-retention-output.txt
- **Severity**: nit
- **Concern**: `skills/cleanup/scripts/cleanup.sh:99-110` vs `55-61`: cache pass enumerates all top-level session entries; `/tmp` pass pre-filters with top-level `-mtime +N`. Documented in `cleanup.md` and tested; intentional, not a regression.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_15: [OUT_OF_SCOPE] cleanup nested-scan fail-safe — no additional defects
- **Reviewer(s)**: dyn-cleanup-retention-output.txt
- **Severity**: nit
- **Concern**: `skills/cleanup/scripts/cleanup.sh:26` and `test-cleanup.sh:39-57`: nested-scan fail-safe and `-maxdepth 5` boundary align with docs and tests. No additional cleanup correctness defects found in branch diff for those behaviors.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_16: [OUT_OF_SCOPE] lint-fix-loop cases 10–11 intentional split
- **Reviewer(s)**: dyn-fixture-isolation-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-lint-fix-loop.sh:268-308` case 10 pre-seeds `${output}.stderr-tail` in stub to test “do not clobber”; case 11 covers diag fallback. Matches plan producer/consumer separation; not a defect.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_17: [OUT_OF_SCOPE] plan-review shared stub mutation ordering
- **Reviewer(s)**: dyn-fixture-isolation-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh:2115-2130` mutates shared `$STUB/collect-agent-results.sh` like existing helpers; end-of-file placement limits ordering risk today.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_18: [OUT_OF_SCOPE] Pre-existing harness patterns (global quiet, REPO_ROOT launchers)
- **Reviewer(s)**: dyn-fixture-isolation-output.txt
- **Severity**: nit
- **Concern**: Pre-existing harness patterns (e.g. `test-codex-implementer.sh` invoking production launchers from `REPO_ROOT`; `test-ship-pr.sh:6` global `LARCH_QUIET_DISABLE=1`) were not introduced by this branch’s stderr-tail work.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge summary**: 55 raw slots → **24 in-scope** `FINDING_*` blocks and **18** `OOS_*` blocks. Largest merges: launcher SIDECAR/diag clobber (8 reviewers), `_collect_rc` (5), step2 codex gap (2), lint-fix stem contract (2). Highest-severity in-scope cluster: **important** on launcher tail clobber/preservation (FINDING_1, 15, 16), collector fail-open (FINDING_4), and lint-fix `STDERR_TAIL_PATH` contract (FINDING_15).

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] #3229 cleanup harness on same branch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `skills/cleanup/scripts/test-cleanup.sh`: #3229 cleanup harness changes on same branch. Unrelated retention/find-failure edits increase shard runtime and review noise for #3227-only reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Treat as separate review scope or split PR if policy requires.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_3: [OUT_OF_SCOPE] `LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0` not re-tested on new consumers
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-lib-failed-agent-stderr-tail.sh`: disable knob not re-tested on new consumers. `LARCH_FAILED_AGENT_STDERR_TAIL_LINES=0` might still noop correctly via lib, but lane-specific wiring is unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional: one consumer smoke per lane with `lines=0` asserting no chat fence.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_4: [OUT_OF_SCOPE] cleanup cache enumeration fail-open (#3229)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `skills/cleanup/scripts/cleanup.sh:21-31`: cache enumeration `find` failure is fail-open (#3229). Stale session dirs may retain ephemeral argv/sidecars longer than retention policy implies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Fail closed or warn+abort enumeration pass; separate from #3227.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] Pre-existing `LINT_FIX_STATUS` awk space truncation
- **Reviewer(s)**: dyn-bash-flow-output.txt
- **Severity**: nit
- **Concern**: `scripts/ship-pr.sh:151` still parses `LINT_FIX_STATUS` with awk `print $2`, so values containing spaces would truncate; new `STDERR_TAIL_PATH` / `CODER_LOG_FILE` paths correctly use `substr` after `=`.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] Pre-existing `ship-pr.sh` omits `set -e`
- **Reviewer(s)**: dyn-bash-flow-output.txt
- **Severity**: nit
- **Concern**: `scripts/ship-pr.sh` intentionally omits `set -e`; new `_surface_*` helpers use `|| true` consistently, so they do not change that contract.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] Unrelated commits on branch (#3229, version, larch-logs)
- **Reviewer(s)**: dyn-bash-flow-output.txt
- **Severity**: nit
- **Concern**: Commits on this branch include unrelated cleanup/docs (`#3229`, version bump, larch-logs); stderr-tail findings above are limited to #3227 surfacing changes.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_8: [OUT_OF_SCOPE] Step 5 quiet / FD routing if review-and-fix stderr redirected
- **Reviewer(s)**: dyn-fd-routing-output.txt
- **Severity**: latent
- **Concern**: `skills/review-and-fix/scripts/review-and-fix.sh:7-14`: Step 5 lint stderr surfacing uses `emit_failed_agent_stderr_tail_larch_err` with `LARCH_QUIET_DISABLE=1` in parent loop (real FD 2). Not introduced by #3227 wiring; future wrapper redirecting review-and-fix stderr to a file would swallow Step 5 tails unless surfacing moves to a caller with unredirected FD 4.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_9: [OUT_OF_SCOPE] Auth-retry may leave prior attempt’s tail (forensics vs stale noise)
- **Reviewer(s)**: dyn-fd-routing-output.txt
- **Severity**: nit
- **Concern**: `scripts/launch-cursor-implement.sh:314-318`: auth-retry clears sidecar/diag but may preserve `.stderr-tail`; later attempt failing with empty diag can leave prior attempt’s tail for step2. May be desirable forensics or stale noise; not a new FD-routing defect from this branch.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

