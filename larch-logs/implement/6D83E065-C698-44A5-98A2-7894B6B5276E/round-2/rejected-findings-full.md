### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Design OOS path resolution triplicated across bash and Python
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Design OOS path resolution is triplicated across a bash function, checkpoint inline logic, and Python with no shared module. A future fix to resolver order or existence checks can land in one site and be missed in others, breaking Python vs bash parity on design-export-only OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a single bash helper plus `python/oos_paths.py` and import from `ship.py`; source the bash helper from `ship-pr.sh` and `oos-disposition-checkpoint.sh`.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Step 9a.1 combine/issue/sentinel procedure lacks end-to-end offline harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Step 9a.1 combine/issue/sentinel/larch-log procedure is documentation plus fixed-string pins only; no end-to-end offline harness. Helper or `/issue` wiring regressions in steps 4–6 could pass structure tests while orchestrator mis-orders steps in production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional follow-up harness with fixture tmpdir and stubbed `/issue` stdout, or accept doc-only scope explicitly.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Python writes `phase=pr-create` before OOS gates complete
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `phase=pr-create` is written before OOS gates finish, so state shows pr-create while the run still needs Step 9a.1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Keep pr-prep or write `oos-filing` phase until disposition passes.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: Resolver ordering lacks dedicated unit tests for bash/Python parity
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Resolver is inline without focused unit tests for `DESIGN_TMPDIR` vs design-export vs flat ordering; refactors can break bash/Python parity without failing tests until integration paths run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add focused tests for `resolve_oos_accepted_design_path` ordering in `python/test_oos.py` or `test_ship.py`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Manifest `oos_observations` jq count and materialize policy duplicated in three callers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Manifest `oos_observations` jq count and fail-closed vs fail-open materialize policy is duplicated in three callers. One caller could treat empty-array materialize failure as blocking while another continues silently if only one copy is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Centralize count and policy in `materialize-manifest-oos.sh` stdout contract or a shared lib wrapper invoked by all three sites.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: `has_title` dedup compares redacted incoming title to non-redacted on-disk headings
- **Reviewer(s)**: dyn-bash-runtime-output.txt
- **Severity**: important
- **Concern**: Title dedup is asymmetric: `has_title` normalizes the incoming title with `normalize_title` (redaction + whitespace collapse) but compares to on-disk headings that only get whitespace/case normalization in awk, not the same `sanitize_public_text` pass. PII/URL redaction can change the string vs an existing heading, dedup misses, and a second `### OOS_N:` block is appended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-runtime-output.txt: Apply the same `sanitize_public_text` + whitespace normalization to extracted heading text in `has_title`, or compare a pre-redaction dedup key while still writing the redacted public title.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: `sanitize_public_text` omits link-local/metadata and some internal host patterns
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: latent
- **Concern**: Mechanical redaction covers a fixed internal-host/PII regex set but omits common non-public endpoints (e.g. `169.254.169.254`) and internal hostnames outside the hard-coded TLD suffix list. Manifest descriptions flow to `oos-accepted-main-agent.md` and `/issue` batch mode verbatim.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Reuse or extract the shared outbound scrubber used elsewhere (or expand the regex set to include link-local/metadata ranges) and add regression tests for metadata-style URLs and non-suffix internal hosts.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: `write_description` pipeline subshell drops Description lines from manifest OOS blocks
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `write_description` uses `sanitize|while` inside a redirected compound command; pipeline subshell drops Description output. Manifest `oos_observations` with non-empty description yield `### OOS_N` blocks missing `- **Description**:` lines; `/issue` files title-only issues and loses reproduction detail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore heredoc-fed `while` (pre-round-1 pattern) or avoid pipe subshell; add test asserting Description text in `oos-accepted-main-agent.md`.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: No behavioral harness for ship-pr materialize failure / `OOS_PENDING` pr-create guard
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: New pr-prep materialize failure handling and pr-create `OOS_PENDING` guard have no behavioral harness—only static awk order pins. With `LARCH_SHIP_PR_IMPL=bash` (default), a regression could skip setting `OOS_PENDING` on materialize failure with manifest OOS, or create a PR while `OOS_PENDING=true`, without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a small ship-pr harness stubbing `materialize-manifest-oos.sh` to assert `OOS_PENDING`/conservative exit and pr-create refusal paths.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

