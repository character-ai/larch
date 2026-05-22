# Review Round 3

- Mode: `diff`
- Accepted findings: 9
- Rejected findings: 0
- Exonerated findings: 6
- Neutral findings: 0

## Accepted Findings

### FINDING_1: Stall JSON can embed raw captures when redactor is missing or unusable
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Concern**: When `redact-secrets.sh` is missing or not executable, stall sidecar JSON can still include unredacted or partially unredacted material (including `git_state` via a path that may `cat` stdin unchanged, and `ps` / `lsof` / transcript material combined into JSON). That conflicts with omission / fail-closed expectations in `SECURITY.md` and risks tokens, paths, and git porcelain or patch text in committed stall artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
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


### FINDING_13: Transcript / diag tails captured after stall teardown, not at stall trip as plan described
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] `last_transcript_lines` (and related tails) are read after SIGTERM to the monitored wrapper rather than at the instant the stall threshold trips before kill sequencing. Post-stall tails may omit pre-stall progress, include stall noise, or reflect teardown, misleading stall JSON readers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


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


