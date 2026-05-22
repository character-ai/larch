Here is the normalized aggregator output. Reviewer prose is treated as evidence only; IDs follow first-seen cluster order (lowest input finding number in each merged group).

---

## Structured finding list

### FINDING_1: Stall JSON can embed raw captures when redactor is missing or unusable
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Concern**: When `redact-secrets.sh` is missing or not executable, stall sidecar JSON can still include unredacted or partially unredacted material (including `git_state` via a path that may `cat` stdin unchanged, and `ps` / `lsof` / transcript material combined into JSON). That conflicts with omission / fail-closed expectations in `SECURITY.md` and risks tokens, paths, and git porcelain or patch text in committed stall artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_2: Doc implies JSON sidecars without `jq`; implementation requires `jq`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: [scripts/lib-cursor-launcher-common.md](scripts/lib-cursor-launcher-common.md) (notably line 3) is read as allowing sidecars when `jq` is unavailable, but the code path does not emit those JSON sidecars without `jq`. Operators may mis-diagnose missing sidecars or environment issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Synchronous stall forensics after SIGTERM extend the window before SIGKILL
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Heavy, synchronous capture work scheduled after SIGTERM but before SIGKILL stacks timeouts, redaction, git, and `jq` work. That can lengthen the TERM phase, keep resources busy longer than intended, and delay escalation to SIGKILL for stalled or misbehaving agents.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Duplicate `SCRIPT_DIR` resolution in emit vs redact helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: [nit] `SCRIPT_DIR` (or equivalent script root) is resolved more than once between emit and `redact_stdin`, which invites maintenance drift if layout changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Empty precomputed diff / alternate diff source for review
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-audit-scan-wiring-output.txt
- **Concern**: [nit] The launcher-supplied or cached `diff.txt` was empty (and/or merge-base `main..HEAD` empty locally), so reviewers fell back to `git diff` / `origin/main`-style ranges or general repo state instead of the capped precomputed hunks. That limits line-level branch fidelity and harness expectations for this review mode; mitigations are procedural (non-empty diff export, session cache, documentation of fallback), not necessarily in-repo code for this change set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: N/A N/A
  - From cursor-specialist-testing-output.txt: None needed in code
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-audit-scan-wiring-output.txt: Address the concern above.

### FINDING_6: `git_state` redaction lacks wall-clock bounding used elsewhere; can block stall teardown
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `git_*` fields use `cursor_launcher_redact_stdin` (or equivalent) without the same `timeout` / `gtimeout` envelope applied to other stall captures. A wedged or slow `redact-secrets` on git output can stall the stall monitor after SIGTERM and delay the SIGKILL phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: `scans.tsv` registry row mixes NDJSON outcome vocabulary into severity / expected columns
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-audit-scan-wiring-output.txt
- **Concern**: The new row at [.claude/skills/audit-runs/scans.tsv:7](.claude/skills/audit-runs/scans.tsv:7) places prose in `expected_outcome` and uses `informational` in the severity column, unlike sibling rows that keep triage-style severities and treat `informational` as an NDJSON `result`, not a registry severity token. Downstream filters or human sorting by severity may mis-handle the row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-audit-scan-wiring-output.txt: Set the fifth column to a normal severity level (typically `low`, matching other informational-capable scans) and keep the fact that successful runs emit `result:"informational"` only in `audit-scan-run.sh` NDJSON and in `audit-scan-run.md`, not as the TSV `severity` token.

### FINDING_8: `SECURITY.md` stall snapshot wording overstates uniform bounded redaction vs implementation
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Concern**: Documentation implies redaction and timeboxing behavior (including for git-related fields) that the implementation does not uniformly provide (e.g. git path without timeout-wrapped redaction; raw capture paths when the redactor is missing). Auditors or operators may trust committed stall JSON or the doc more than the code warrants.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: Same-UID `ps` argv snapshot can pull unrelated Cursor-related command lines
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: [latent] Same-UID `ps` filtering for lines containing `cursor` can include argv from unrelated concurrent Cursor sessions or repos, inflating or mis-attributing stall forensics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: `test-launch-cursor-ci.sh` fixtures hard-fail when `jq` is absent
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] New stall JSON fixtures (e.g. 7–8) fail the whole harness if `jq` is missing, even though production may skip JSON sidecars without `jq`. Minimal CI or contributor images without `jq` could see avoidable harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: `lsof` assertion is best-effort; regression might not fail CI
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Assertions around `lsof` can always pass via a best-effort “ok” branch, so a regression that always leaves the `lsof` field empty might not fail the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] `ship-pr.sh` phase-2 stall-aware retry not in this diff
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Phase 2 stall policy in `scripts/ship-pr.sh` is called out as out of scope for this branch or plan gating; no breakage asserted for this review conclusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: N/A N/A
  - From cursor-specialist-edge-cases-output.txt: None

### FINDING_13: Transcript / diag tails captured after stall teardown, not at stall trip as plan described
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] `last_transcript_lines` (and related tails) are read after SIGTERM to the monitored wrapper rather than at the instant the stall threshold trips before kill sequencing. Post-stall tails may omit pre-stall progress, include stall noise, or reflect teardown, misleading stall JSON readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_14: `ps` capture scope vs plan (full-tree visibility vs UID-scoped capped snapshot)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan language implied broader process visibility (e.g. full-tree style); implementation uses UID-scoped `ps` plus `grep cursor` capped to a line budget. Other-UID or non-matching-argv Cursor-related processes may be absent from stall JSON, limiting some diagnostic hypotheses the plan called out.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_15: Git snapshot in sidecar is porcelain-oriented vs plan wording for `git status`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan text referenced `git status`; sidecar records `git status --porcelain` (plus rebase patch excerpt when applicable). Minor literal mismatch vs strict plan wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_16: Plan-to-file traceability: stall behavior concentrated in library vs listed launcher script
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan file list highlights `scripts/launch-cursor-ci.sh` while functional stall sidecar work lives in `scripts/lib-cursor-launcher-common.sh` without a visible hunk in the launcher file, weakening grep-only traceability for reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] `launch-cursor-ci.sh` still invokes stall monitor though not the main diff hunk
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: [nit] `scripts/launch-cursor-ci.sh` unchanged in the reviewed diff but still invokes the stall monitor; architectural / plan-scope note only for this review conclusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: No code change required for review conclusion

### FINDING_18: `audit-scan-run.sh` histogram path rolls all files into UNKNOWN on `jq` failure
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] On histogram failure, the implementation may attribute the entire file count to UNKNOWN, so a transient `jq` failure misreports channel distribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] `audit-scan-run.sh` only uses first column of `scans.tsv`; other columns are documentation
- **Reviewer(s)**: dyn-audit-scan-wiring-output.txt
- **Concern**: Wiring reads only the first column from `scans.tsv` and hardcodes scan paths; `type` / `pattern` columns remain documentation-only for all scans, not a regression unique to this scan row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-scan-wiring-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] `audit-compute-counters.sh` does not aggregate stall-cause scan
- **Reviewer(s)**: dyn-audit-scan-wiring-output.txt
- **Concern**: Matches the skill rule to wire counters only when a scan feeds cumulative YAML totals; batch-level stall trending would need NDJSON consumption or future counter keys if operators want that without manual NDJSON inspection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-scan-wiring-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Static diff cannot certify executed checks / acceptance rows
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Acceptance criteria that require executed `/relevant-checks` and passing harness runs are not verifiable from a static diff in read-only review mode; certification would need logs from an implementing session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Notes on merges (for voters, not instructions):** FINDING_1 subsumed input 1, 6, and 19 (same leak surface when redactor is absent). FINDING_2 subsumed 2, 9, 14, and 24 (identical doc/`jq` concern). FINDING_3 subsumed 3 and 22 (SIGTERM–SIGKILL blocking forensics). FINDING_5 subsumed 5, 11, 17, 33, and 36 (empty diff / alternate review basis). FINDING_6 subsumed 7, 12, and 25 (unbounded git redaction in teardown). FINDING_7 subsumed 8 and 35 (`scans.tsv` column conventions). FINDING_8 subsumed 13 and 20 (`SECURITY.md` vs code). FINDING_10 subsumed 15 and 32 (`jq` and harness fixtures). FINDING_12 subsumed 10 and 27 (`ship-pr` out of scope). Input 18 was kept separate from 16 (31) because 18 is explicitly `[OUT_OF_SCOPE]` while 31 is an in-scope traceability nit. FINDING_9 (security breadth of `ps`) and FINDING_14 (plan fidelity / narrow capture) stay separate: different failure modes and different suggested directions (narrow to target tree vs broaden or re-scope the plan).
