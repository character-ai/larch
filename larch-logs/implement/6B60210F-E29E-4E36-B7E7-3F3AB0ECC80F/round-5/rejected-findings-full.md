### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: launch_tier invokes .sh without explicit bash
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Launcher scripts are invoked without a `bash` prefix; if scripts lose `+x` in a consumer checkout, `Popen` fails where explicit `bash` would still work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: run_waterfall skips rotation when first_tier absent from tiers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: When `first_tier` is not in `tiers`, rotation is skipped and policy uses the wrong tier vs bash offset semantics. Stale `first_tier` names can short-circuit incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: transient retry substring ordering diverges from bash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Ordered substring checks for EOF/during, git fetch/failed, lookup/no such host differ from `scripts/lib-net.sh`. Reordered transient stderr may not retry in Python but would in bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: failed_jobs silently skips non-dict job rows
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Malformed gh JSON with non-dict job rows is skipped silently, yielding incomplete failed-job lists and wrong CI-fix targeting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: pr_for_branch open-only can miss closed PRs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Open-only branch lookup can miss closed/merged PRs, causing `pr_create` to retry create/conflict instead of returning the existing PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Observability dataclasses mutable vs frozen convention
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `logging_util` observability dataclasses are mutable while other cross-phase records are frozen, which may confuse Phase 2 authors about immutability/hash safety.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: subprocess timeout tests may flake under load
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Timeout tests use a 0.1s margin around `sleep(5)`; heavily loaded `python-tests` CI may flake on timeout assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: mutating gh helpers lack transient no-retry regression tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Beyond `pr_merge`, mutating gh helpers lack stub-runner single-call tests; future retry wrappers could regress without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: quiet breadcrumb tests cover suppression only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `quiet=False` and `LARCH_QUIET_DISABLE` paths are untested and could regress silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_22: make lint / pre-commit omit Python gates
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Local `make lint` and pre-commit can pass while `python-lint` CI fails; Python gates are not documented or hooked locally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: stdlib-only test misses dynamic non-literal imports
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: AST policy does not catch `importlib.import_module(variable)`; a future runtime module could add non-stdlib deps while the test stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: redact() trailing newline on gh body files
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Bash vs Python PR bodies may differ by one trailing newline on edge payloads for body-file writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: CI workflow plan drift (make vs inline python commands)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: CI jobs call `make py-lint`/`py-test` instead of plan-specified `working-directory: python` with inline linter commands; functionally similar today but future divergence may go unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: run_waterfall omits planned classify_fn parameter
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `run_waterfall` uses built-in `effective_failure_class` only; callers cannot inject alternate classification as the plan specified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: test_config immutability coverage incomplete
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Immutability tests cover only `TRANSIENT_RETRY_BACKOFF_SEC`, not other documented frozen tables such as `FIXER_TIER_ORDER`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: JsonlJournal / BreadcrumbWriter emit unredacted text
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: After Phase 7 wires gh/git stderr into journal or breadcrumbs, PATs in tool output could be persisted to tmpdir JSONL or stderr without redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: TransientNetworkError carries raw CommandResult
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `TransientNetworkError` exposes raw `CommandResult` with no `redact_gh_error` port; future callers logging `exc.result.stderr` could leak tokens from gh auth failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: git reset/rebase/push flag injection via arbitrary ref strings
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: git helpers accept arbitrary mode/ref strings; user-controlled refs starting with `-` could enable git CLI flag injection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: relevant-checks always runs full py-lint/py-test on any python/*.py change
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Any change under `python/*.py` triggers full-tree `py-lint` and `py-test`; editing a single test file still lints the entire python tree locally, which may slow iteration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

