### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: `PR_URL` validation permits `http://`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `_PR_URL_RE` accepts plaintext `http://` PR URLs, which could propagate insecure URLs to downstream consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restrict the regex to `^https://` only; GitHub.com always uses HTTPS and GitHub Enterprise deployments should redirect.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Repo slug validation allows a repo segment starting with `-`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `_valid_repo_slug` rejects slugs starting with `-` but allows the repo-name segment after `/` to start with `-`; reviewers note this is likely not argument injection in the current subprocess shape but remains an incomplete guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Either add an assertion that neither segment starts with `-`, or note this as an accepted gap given the subprocess call is `--repo <value>`.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Terminal ship-state phase now discards the descriptive `step`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-postmerge-idem-output.txt
- **Severity**: nit
- **Concern**: `_write_terminal_state` writes `PHASE=stalled` for all non-OK terminal states instead of preserving the descriptive step in ship state, which may be intentional but is undocumented and loses diagnostic granularity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Either document this normalization in the plan/changelog, or clarify that the plan authorized it during review rounds.
  - From dyn-postmerge-idem-output.txt: Either explicitly document that `PHASE=stalled` is now canonical for all non-OK terminal states (remove the `step` parameter from the signature to avoid confusion), or restore `phase = "done" if result is Outcome.OK else step or "stalled"` to maintain diagnostic parity with the bash driver.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Duplicate boolean parsing helpers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_state_bool_text(value)` duplicates the behavior of `run_logs._state_bool_or_default(value, default=False)`, creating two private implementations of the same parsing rule.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Either make `_state_bool_or_default` a public helper in `run_logs` (rename to `parse_state_bool`) and reuse it, or add a thin public wrapper — eliminating the duplication.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

