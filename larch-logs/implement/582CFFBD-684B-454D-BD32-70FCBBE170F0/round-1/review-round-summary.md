# Review Round 1

- Mode: `diff`
- Accepted findings: 9
- Rejected findings: 0
- Exonerated findings: 0
- Neutral findings: 1

## Accepted Findings

### FINDING_1: Cross-skill coupling for OOS helpers in audit-scan-run
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: `audit-scan-run.sh` sources implement-private out-of-scope helpers via relative paths, so refactors under `skills/implement/scripts/` can break audit scans and blur ownership boundaries.
- **Suggested revision**: Extract a single shared contract (for example under `scripts/`) and have both audit and implement callers source that one module.


### FINDING_10: Pre-lock main-sync probe may fail-open on stale or flaky origin
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Pre-lock main sync uses a non-fetched `origin` ref and can treat probe errors as fail-open, allowing locking when local `main` is unsafe relative to upstream under stale or flaky git conditions.
- **Suggested revision**: Document fetch requirements for operators and/or tighten fail-open so it applies only when `SYNC_STATUS` is explicitly ok or not-main.


### FINDING_11: Anti-recursion / noise regex may miss legacy audit titles
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: The anti-recursion pattern no longer matches legacy audit titles, so remaining old titles may not be classified as noise for issue search and C.1 bucketing.
- **Suggested revision**: Union old and new patterns until migration is verified complete; keep tests in `test-audit-runs.sh` aligned.


### FINDING_12: Plan omits first-class description of new pre-lock main-sync failures
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: The plan emphasized removing `has_run_logs_audit_report_title` but did not surface new pre-lock `check-main-sync` exit-`2` modes, so operators comparing behavior to the short plan can miss new lock failures.
- **Suggested revision**: Document the main-sync gate as a first-class requirement next to the audit-title work, or land it as a separately tracked change with its own plan item.

---

**Note:** I did not call `CreatePlan` because your hard constraint forbids any tool that creates or overwrites workspace files; that would trip the dirty-tree sidecar. If you need this body written to a file by a follow-up agent run, say where it should land.

**Counts:** 17 raw inputs collapsed to **12** normalized findings (merged: 2+15+16; 3+10+11; 4+13).

### FINDING_3: Legacy audit titles without `audit-report` may become `/fix-issue`-eligible
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Removing the dedicated `has_run_logs_audit_report_title` path while relying on `has_report_prefix` risks treating legacy or new-shaped run-logs audit titles as lockable when the `audit-report` label is missing—re-opening chain-of-history locking that the old guard blocked.
- **Suggested revision**: Add a legacy-prefix guard, enforce a label-only invariant (with monitoring), and extend `test-find-lock-issue` so a new-shaped title without the label still exits `2` with the report-prefix error (fixture 24 alone is insufficient).


### FINDING_4: Git-log fallback for inline-triage / oos-silent-drop uses wrong repo context
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: When transcripts are missing, counters fall back to `git` history using the caller’s working tree instead of the repo associated with `RUN_DIR`, producing wrong pass/fail for `oos-silent-drop` when cwd does not match the audited run log or metadata is absent.
- **Suggested revision**: Tie the revision range to the repo rooted at `RUN_DIR`, or emit a partial/git-skip result; document the required cwd contract; consider disabling the fallback unless `RUN_DIR` is under the resolved repo and record the evidence mode in scan output.


### FINDING_5: Operator scan table omits new `oos-silent-drop` scan
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `scans.tsv` registers `oos-silent-drop` but the operator-facing baseline table in `audit-runs` `SKILL.md` does not, so severity and location are easy to miss during operations or edits.
- **Suggested revision**: Add a coordinated baseline row in `SKILL.md` aligned with `scans.tsv`.


### FINDING_6: `oos-disposition-gate` not enforced on ship-pr path before clearing `OOS_PENDING`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: The gate is documented in `SKILL.md` but not invoked from `ship-pr.sh` before `OOS_PENDING` is cleared, so a buggy orchestrator or resume path can advance state without running the mandatory shell boundary.
- **Suggested revision**: Invoke `oos-disposition-gate.sh` from `ship-pr.sh` (or an equivalent mandatory boundary) before `state_set OOS_PENDING false`; fail the phase on non-zero exit.


### FINDING_7: Filed-issue URL acceptance is not GitHub-host-specific
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `filed_url` matching treats any `https://…/issues/<digits>` as valid, so crafted or mistaken NDJSON could satisfy thresholds without a real GitHub filing.
- **Suggested revision**: Restrict to known GitHub hosts or URLs validated via `gh`; add a regression test rejecting off-host URLs.


