### FINDING_1: Manifest security focus-area predicate diverges from gate
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `materialize-manifest-oos.sh` uses a custom security focus-area matcher that can disagree with `oos-non-security-block-count.awk`, causing security OOS to be materialized or excluded inconsistently with the disposition gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Python tool-failure logging bypasses canonical helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-shell-flow-output.txt
- **Severity**: important
- **Concern**: Python `_append_execution_tool_failure` hand-writes `execution-issues.md` instead of using `append-tool-failure.sh`, weakening parity with bash logging, stderr capture, and redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-shell-flow-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Duplicated design OOS path resolvers can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Bash and Python duplicate accepted-design OOS path resolution, increasing the chance that future design-export path changes are applied to one path but not another.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Python materialize hook uses hardcoded repo-relative script path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `python/ship.py` resolves `materialize-manifest-oos.sh` using a hardcoded repo-relative path rather than `CLAUDE_PLUGIN_ROOT` with fallback, which can break non-standard plugin layouts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Title idempotency is inconsistent and fragile
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-shell-flow-output.txt
- **Severity**: latent
- **Concern**: `has_title` deduplicates titles case-sensitively and passes user-controlled titles into awk, so reruns with case, whitespace, quote, backslash, or newline differences can create duplicate or inconsistent OOS blocks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-shell-flow-output.txt: Address the concern above.

### FINDING_6: Step 2 parses manifest observation count twice
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `step2-implement.sh` computes `oos_observations` length separately from the materialization helper, duplicating JSON parsing on the complete path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Structure test over-pins documentation wording
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-implement-structure.sh` contains a large brittle substring block duplicating `oos-pipeline.md`, so harmless documentation wording edits can break CI without behavior changing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_10: All-already-filed design wording can hide other OOS sources
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `oos-pipeline.md` wording for all-already-filed design batches can be read as skipping combine/file steps even when review or main-agent OOS remains unfiled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

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

### FINDING_13: [OUT_OF_SCOPE] Stale DESIGN_TMPDIR can hide design-export OOS
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-evidence-logging-output.txt
- **Severity**: latent
- **Concern**: When `DESIGN_TMPDIR` is set but stale or missing the accepted-design file, resolvers can prefer it over `design-export/oos-accepted-design.md`, making design-export OOS invisible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-evidence-logging-output.txt: Address the concern above.

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

### FINDING_17: Load-directive checks are too global
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Structure tests only check a global load-directive count, not bounded adjacency to each required entry point, so all directives could cluster in one section while another entry loses its mandatory pointer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_18: Materialize helper contract header is not covered
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `materialize-manifest-oos.md` is not covered by the existing reference-header triplet scan, allowing header drift without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_19: Redaction structure pin omits PII token
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Structure tests pin redaction behavior without asserting the planned `<REDACTED-PII>` token or equivalent PII sanitization language.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] NEVER #5 awk extraction is fragile
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The structure harness’s NEVER #5 awk block extraction can silently become empty after list renumbering, weakening run-statistics negative checks.
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

### FINDING_23: [OUT_OF_SCOPE] Security-marked OOS lacks explicit private routing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The disposition gate excludes security-marked blocks from filing counts, but pre-existing flows may not ensure those blocks are routed through `SECURITY.md` or private disclosure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_24: Manifest titles are used as printf format strings
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: User-controlled manifest titles can contain `%` format conversions that corrupt headings or abort materialization under `set -e`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

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

### FINDING_27: [OUT_OF_SCOPE] New materialize harness lacks agent-lint exclusions
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: New `test-materialize-manifest-oos` harness files may need `agent-lint.toml` exclusions consistent with sibling implement harnesses.
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

### FINDING_30: [OUT_OF_SCOPE] Known degraded OOS paths remain
- **Reviewer(s)**: dyn-oos-flow-output.txt
- **Severity**: latent
- **Concern**: Known in-plan degraded paths remain, including file-conflict TSV loss on `/issue` Step-5-skip paths and LLM-judged combine pass Rule A.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-flow-output.txt: Address the concern above.

### FINDING_31: Untitled manifest observations can be dropped as duplicates
- **Reviewer(s)**: dyn-manifest-bridge-output.txt
- **Severity**: important
- **Concern**: Empty or missing manifest titles normalize to the same default heading, so title-only idempotency can skip later untitled observations with no error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-manifest-bridge-output.txt: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] Title-only idempotency leaves stale text on changed descriptions
- **Reviewer(s)**: dyn-manifest-bridge-output.txt
- **Severity**: nit
- **Concern**: Re-materializing an observation with the same title but changed description intentionally leaves stale accepted markdown due to the documented title-idempotency contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-manifest-bridge-output.txt: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] Materialize harness omits edge cases
- **Reviewer(s)**: dyn-manifest-bridge-output.txt
- **Severity**: latent
- **Concern**: The materialize harness does not cover multiple empty-title observations, shell-metacharacter descriptions, or Python’s empty-array failed-materialize branch.
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

### FINDING_36: [OUT_OF_SCOPE] Bash pre-OOS_PENDING gate also omits strict filed-URL file
- **Reviewer(s)**: dyn-python-parity-output.txt
- **Severity**: latent
- **Concern**: A pre-existing bash helper path omits `--filed-urls-strict-file`, matching Python’s looser inlined gate rather than the stricter checkpoint helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-parity-output.txt: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] Disposition URL count is not per-block
- **Reviewer(s)**: dyn-python-parity-output.txt
- **Severity**: latent
- **Concern**: `disposition_ok` uses `filed > 0` instead of requiring per-block coverage, which can amplify skip-Step-9a.1 risks when a lone sentinel URL exists.
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

### FINDING_40: Run-statistics accepted count is not scoped to newly filed issues
- **Reviewer(s)**: dyn-evidence-logging-output.txt
- **Severity**: latent
- **Concern**: `SKILL.md` defines the accepted OOS statistic without excluding sentinel-recovered or already-filed items, risking inflated `run-statistics.md` counts on reruns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-evidence-logging-output.txt: Address the concern above.

### FINDING_41: OOS pipeline does not explicitly collect rejected review OOS into NDJSON
- **Reviewer(s)**: dyn-evidence-logging-output.txt
- **Severity**: important
- **Concern**: Step 6 says rejected/non-accepted entries remain under a rejected sub-block, but lacks an executable collection step to append those markers to checkpoint-visible NDJSON, which can make the disposition gate fail after accepted URL rows are written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-evidence-logging-output.txt: Address the concern above.
