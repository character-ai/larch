# Review Round 1

- Mode: `diff`
- 21 accepted, 9 rejected (8 exonerated)

## Accepted Findings

### FINDING_1: Manifest security focus-area predicate diverges from gate
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `materialize-manifest-oos.sh` uses a custom security focus-area matcher that can disagree with `oos-non-security-block-count.awk`, causing security OOS to be materialized or excluded inconsistently with the disposition gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt: Address the concern above.


### FINDING_11: Missing ISSUES_FAILED adjacency guard
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Structure tests do not enforce the planned negative adjacency check preventing `ISSUES_FAILED>0` guidance from appearing near accepted-URL append instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_12: Missing manifest-success Python regression test
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_ship.py` does not test the successful manifest-materialization path where manifest-only OOS populates `oos-accepted-main-agent.md` and blocks PR creation until disposition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: Step 2 lacks fail-closed materialization-failure harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There is no harness asserting that Step 2 bails when the manifest has non-empty `oos_observations[]` and materialization fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: Manifest OOS can be lost after materialization failure before checkpoint
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-oos-flow-output.txt
- **Severity**: important
- **Concern**: If manifest materialization fails or is skipped, later OOS checkpoint paths are markdown-only and can clear with zero accepted blocks while manifest JSON still contains unfiled OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-oos-flow-output.txt: Address the concern above.


### FINDING_16: DESIGN_TMPDIR branch lacks Python coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Python tests do not cover the `DESIGN_TMPDIR` accepted-design path branch, so Python resolver order can diverge from bash unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Redaction structure pin omits PII token
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Structure tests pin redaction behavior without asserting the planned `<REDACTED-PII>` token or equivalent PII sanitization language.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_21: Manifest titles can inject extra OOS headings
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Newlines or control characters in manifest titles can create column-0 `### OOS_N:` headings in accepted-OOS markdown, causing spurious public issue filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_22: Manifest OOS text lacks mechanical internal URL/PII redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `materialize-manifest-oos.sh` writes manifest OOS content to accepted markdown without mechanically redacting internal URLs or PII before later public issue flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_25: Description heredoc handling can execute or corrupt manifest text
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-manifest-bridge-output.txt
- **Severity**: important
- **Concern**: `write_description` uses unsafe heredoc handling for manifest descriptions, allowing shell expansion/command substitution and delimiter collisions that can execute code or truncate stored descriptions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-manifest-bridge-output.txt: Address the concern above.


### FINDING_26: Python dispatch-order pin is missing
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Structure tests check only for string presence in `ship.py`, not that manifest materialization runs before `_oos_gate`, so refactors could skip manifest-only OOS while tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_28: Python OOS gate lacks bash NDJSON precondition
- **Reviewer(s)**: dyn-oos-flow-output.txt, dyn-python-parity-output.txt
- **Severity**: important
- **Concern**: Python `_oos_gate` calls `oos.disposition_ok` without the bash checkpoint’s mandatory `oos-issues.ndjson` discovery/precheck when non-security OOS exists, allowing PR creation without the evidence surface bash requires.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-flow-output.txt, dyn-python-parity-output.txt: Address the concern above.


### FINDING_29: PR-create can run while OOS_PENDING remains true
- **Reviewer(s)**: dyn-oos-flow-output.txt
- **Severity**: important
- **Concern**: `run_pr_create_phase` and the Python PR-create entry do not hard-stop when `OOS_PENDING=true`, so a mistimed resume can create a PR before the OOS checkpoint clears.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-flow-output.txt: Address the concern above.


### FINDING_31: Untitled manifest observations can be dropped as duplicates
- **Reviewer(s)**: dyn-manifest-bridge-output.txt
- **Severity**: important
- **Concern**: Empty or missing manifest titles normalize to the same default heading, so title-only idempotency can skip later untitled observations with no error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-manifest-bridge-output.txt: Address the concern above.


### FINDING_34: Python gate omits strict filed-URL design files
- **Reviewer(s)**: dyn-python-parity-output.txt, dyn-evidence-logging-output.txt
- **Severity**: important
- **Concern**: Python `_oos_gate` does not pass `filed_urls_strict_files` for the resolved design accepted-OOS path, breaking parity with the bash checkpoint for design blocks that already contain `- **Filed URL**:` lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-parity-output.txt, dyn-evidence-logging-output.txt: Address the concern above.


### FINDING_35: Python can skip Step 9a.1 when accepted-OOS files are non-empty
- **Reviewer(s)**: dyn-python-parity-output.txt
- **Severity**: important
- **Concern**: Bash pr-prep hands off whenever accepted-OOS markdown is non-empty, but Python runs `disposition_ok` first and may proceed directly to PR creation, skipping the full Step 9a.1 workflow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-parity-output.txt: Address the concern above.


### FINDING_38: Step 2 logs materialize failures with hardcoded exit code
- **Reviewer(s)**: dyn-shell-flow-output.txt
- **Severity**: nit
- **Concern**: `step2-implement.sh` records materialization failures with `--exit-code "1"` regardless of the helper’s actual exit status, reducing triage fidelity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-flow-output.txt: Address the concern above.


### FINDING_39: Step 2 treats jq count failures as zero observations
- **Reviewer(s)**: dyn-shell-flow-output.txt
- **Severity**: important
- **Concern**: `MAT_OOS_COUNT` suppresses jq errors to `0`, allowing Step 2 to emit `STATUS=complete` while manifest OOS may remain unmaterialized after a parse or infrastructure failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-flow-output.txt: Address the concern above.


### FINDING_5: Title idempotency is inconsistent and fragile
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-shell-flow-output.txt
- **Severity**: latent
- **Concern**: `has_title` deduplicates titles case-sensitively and passes user-controlled titles into awk, so reruns with case, whitespace, quote, backslash, or newline differences can create duplicate or inconsistent OOS blocks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-shell-flow-output.txt: Address the concern above.


### FINDING_8: Materialize failure policy diverges on empty manifests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-oos-flow-output.txt, dyn-manifest-bridge-output.txt, dyn-shell-flow-output.txt
- **Severity**: important
- **Concern**: Python and shell ship paths can fail closed on any `materialize-manifest-oos.sh` error, even when `oos_observations[]` is empty or absent, diverging from Step 2’s intended fail-open behavior for provably empty manifests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-oos-flow-output.txt, dyn-manifest-bridge-output.txt, dyn-shell-flow-output.txt: Address the concern above.


### FINDING_9: Security-only manifest OOS can be silently dropped
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Security-tagged manifest observations are skipped by materialization without durable audit trail, `OOS_PENDING`, or `SECURITY.md` handoff, allowing manifest-only security OOS to disappear from the filing/routing workflow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


