### [rejected] FINDING_1

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_1: Debug scripts committed and listed in SKILL.md wrapper inventory
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: Four ad-hoc `_dbg*` / `_debug-step5c.sh` development scripts are committed under the shipped `skills/design/scripts/` tree and referenced from `skills/design/SKILL.md` wrapper inventory. They are not plan deliverables, not CI-tested, and pollute the runtime surface; agents and agent-lint may treat them as supported contract wrappers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Delete the _dbg* / _debug* files and remove all SKILL.md references.
  - From cursor-specialist-edge-cases-output.txt: Remove _dbg* and _debug-* scripts from skills/design/scripts/ or fold any needed coverage into official test harnesses only.
  - From cursor-specialist-edge-cases-output.txt: Remove debug script entries from the wrapper inventory and SKILL.md references after deleting the files.
  - From cursor-specialist-testing-output.txt: Remove before merge or relocate outside the shipped plugin tree; delete SKILL.md inventory entries.
  - From codex-generic-output.txt: Remove the debug scripts and their SKILL.md inventory references before merging.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (0 YES)

### FINDING_16: Bounded root-cause summary not re-sanitized at compose time
- **Reviewer(s)**: dyn-tierb-safety-output.txt
- **Severity**: important
- **Concern**: `safe_root_summary_from_state` in `design-failure-report.sh` reads `SITE`, `TRIGGER`, and `FAILURE_OUTCOME` from `design-failure-terminal-state.env` and writes them into the bounded root-cause summary feeding Tier B GitHub bodies without re-running `validate-token` / `safe_*` sanitizers at compose time. Staging validates once; a later tmpdir edit or partial write could put path-like or URL-like text into a public upstream issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tierb-safety-output.txt: Re-sanitize each field through `stall-recovery-report.sh validate-token` (or the existing `safe_site_value` / `safe_trigger_value` / `safe_outcome_value` helpers) before writing `ROOT_FILE` / `BOUNDED_ROOT_FILE`, and fail closed to fallback print when any value is `redacted` or invalid.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (0 YES)

### FINDING_17: Tier B create bodies expose Run ID as public correlation handle
- **Reviewer(s)**: dyn-tierb-safety-output.txt
- **Severity**: important
- **Concern**: Tier B **create** bodies in `stall-recovery-report.sh` still emit `Run ID` in the public metadata table. `/design` now files those bodies cross-repo from consumer clones, so run IDs become public correlation handles for local `larch-logs/design/<RUN_ID>/` trees (plans, issue bodies, `source-env.sh`, etc.). Dedup comments are bounded, but the initial issue body is not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tierb-safety-output.txt: For `--profile generic` / `design-failure-*` Tier B surfaces, omit `Run ID` from `compose_tier_b_projection`, or replace it with a one-way hash that is not reversible to the log path; keep full run ID only in Tier A dev-clone filing.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (0 YES)

### FINDING_18: Sensitive-corpus exact-token checks can be evaded by paraphrase
- **Reviewer(s)**: dyn-tierb-safety-output.txt
- **Severity**: important
- **Concern**: Sensitive-corpus extraction in `stall-recovery-report.sh` only indexes lines 12–240 characters from design artifacts, and `sensitive_token_rejects_file` checks exact `grep -Fq` token hits. Paraphrased or shortened excerpts of issue/plan text in bounded root-cause prose can evade detection if they never appear as a full corpus line/token. Harness tests only inject full marker lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tierb-safety-output.txt: Add substring checks for high-risk design sources (normalized sliding windows or minimum-length n-grams on `issue-body.txt` / `plan.txt` / `feature-description.txt`), or restrict bounded root-cause `summary`/`prose` to token-only templates with no free-form sentences.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_7: Operator-action sentinel checked after failed-outcome terminal filing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: `design-failure-operator-action.env` is checked only after the failed-outcome terminal-report branch in `design-failure-report.sh`. A run with an operator-action sentinel and a later `failed-clarify` or other `failed-*` outcome can validate terminal state and file a terminal report instead of honoring the operator-action skip policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: After terminal/escalation sentinel checks, if operator-action env exists repair audit and skip before failed-* compose.
  - From codex-generic-output.txt: Move the operator-action sentinel branch before cancelled and failed outcome handling, after only the terminal-report and escalation-success duplicate sentinels.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: record-escalation silently no-ops when helper not executable
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `record-escalation` in `review-design-step3-loop.sh` silently no-ops when the shared helper is not executable. Approved runs lose escalation evidence with no durable audit; teardown skips escalation-success filing. Only an ephemeral WARN KV is emitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Log helper absence or record-escalation failure to execution-issues.md not only via ephemeral WARN KV.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

