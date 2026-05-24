Here is the normalized aggregator output. In-scope items are merged by behavioral risk; out-of-scope inputs are merged into a single `### OOS_1` block. Slots that only said “Address the concern above.” are omitted under the no–fix-direction rule.

---

### FINDING_1: docs/linting.md harness table dropped `test-get-issue-context` row
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The harness markdown table no longer documents `make test-get-issue-context` while the Makefile still exposes the target (and shard routing), so operators lose discoverability and docs drift from CI/Makefile.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restore the removed row next to the new bootstrap row
  - From cursor-specialist-edge-cases-output.txt: Restore the `test-get-issue-context` table row from `main` alongside the new row.

---

### FINDING_2: Bootstrap breadcrumbs can interleave non-KV prose on stdout (quiet-disable / missing breadcrumb FD)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: With `LARCH_QUIET_BREADCRUMBS=1` and/or `LARCH_QUIET_DISABLE=1`, breadcrumb emission can land on stdout when `LARCH_QUIET_BREADCRUMB_FD` is unset, violating strict stdout-as-KV expectations and breaking consumers that parse stdout as `KEY=value` only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Require numeric BREADCRUMB_FD before emitting, document the pairing, or otherwise guarantee breadcrumbs never use stdout in this entrypoint.
  - From cursor-specialist-testing-output.txt: Wire a default breadcrumb FD like review-core ensure_breadcrumb_fd or document+require FD; update implement-bootstrap.md breadcrumbs section accordingly
  - From cursor-specialist-edge-cases-output.txt: Send breadcrumbs to stderr under quiet-disable, require a numeric breadcrumb FD when breadcrumbs are enabled, or filter non-KV lines in `SKILL.md`; update the contract doc accordingly.

---

### FINDING_3: Redundant guard before reading caller dynamic archetypes max
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: An always-true empty check on `dynamic_archetypes_value` adds branches on every run without changing behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Remove the always-true -z guard on dynamic_archetypes_value.

---

### FINDING_4: Step 0 implement-bootstrap prose length vs surrounding imperative style
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Long Step 0 prose in `skills/implement/SKILL.md` increases merge/conflict burden and reader fatigue for limited gain over the script contract doc.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Condense prose and defer detail to implement-bootstrap.md

---

### FINDING_5: Umbrella / cross-doc wording vs shipped stderr (`larch_err`) advisory contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Umbrella or spec language still points at `emit`/FD-3 for warnings while the implementation documents stderr advisories, risking future “fixes” that move warnings back to FD-3/stdout and break KV purity or quiet-stream consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Align issue/umbrella wording with the delivered stderr contract on merge.
  - From cursor-specialist-edge-cases-output.txt: Align implementation with the umbrella contract or revise the umbrella / `implement-bootstrap.md` to bless stderr advisories.
  - From cursor-specialist-plan-fidelity-output.txt: Update umbrella issue text to match implement-bootstrap.md or explicitly dual-path emit under quiet sessions.

---

### FINDING_6: `write-session-env.sh` non-zero exit ignored after successful `session-setup`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: If `write-session-env.sh` returns non-zero, bootstrap can still exit 0 and later steps may use an incomplete `session-env`, masking failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Capture rc; on failure emit STEP_FAILED=write-session-env and exit 2 before ledgers

---

### FINDING_7: `session-setup` success path drops non-KV stderr/emit lines (stale-plugin advisory visibility)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Only stdout is KV-ingested and stderr is discarded on success, so known non-KV advisory lines (e.g. stale-plugin working-tree-ahead) may no longer reach the operator transcript compared to direct `session-setup` invocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Forward known non-KV emit lines to larch_err or tee setup_out while parsing

---

### FINDING_8: Exit code 2 conflation between argv/usage (`die_usage`) and infrastructure `STEP_FAILED` failures
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Documentation and operator mental models can misread malformed argv (usage) as the same class of Step 0 infrastructure failure that carries `STEP_FAILED` on stdout, because both use exit status 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document argv failures as exit 2 or remove the "(other)" row
  - From cursor-specialist-edge-cases-output.txt: Use a distinct exit status for usage errors or emit an explicit `STEP_FAILED` usage token before exit.

---

### FINDING_9: Optional `--skip-codex-probe` / `--skip-cursor-probe` no longer forwarded to `session-setup`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Callers that relied on forwarding these argv flags through the old fenced Step 0 path cannot express the same skip-probe behavior via bootstrap without an alternative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Re-add argv forwarding or document caller-env-only replacement

---

### FINDING_10: NEVER #14 harness grep is intentionally narrow (two literals)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Static greps for only two forbidden spellings can miss alternative direct-write forms to `session-env.sh` while still violating NEVER #14 intent, weakening CI regression detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Expand grep patterns or narrow documented harness guarantee to the literals checked
  - From cursor-specialist-edge-cases-output.txt: Expand forbidden patterns or document the intentional narrow grep as non-exhaustive.

---

### FINDING_11: Incomplete handling/docs for `STEP_FAILED` beyond gate/setup (incl. create-branch)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Exit-code docs and Step 0 operator messaging focus on `session-entry-gate` / `session-setup`, leaving create-branch and other `STEP_FAILED` tokens under-documented or without the same normalized failure UX, so failures can look like silent `exit 2`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Update exit-code table to include create-branch path and fields emitted on stdout
  - From cursor-specialist-testing-output.txt: Add a failure branch or explicitly document the raw-only handling for create-branch failures
  - From cursor-specialist-edge-cases-output.txt: Add a generic failure branch or explicitly document supported `STEP_FAILED` tokens.

---

### FINDING_12: Missing harness for failing `token-claude-source` / `CLAUDE_SOURCE_OK=false`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Without a stubbed failure case, regressions in token capture or append-tool-failure wiring may not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a stubbed failing token-claude-source case asserting CLAUDE_SOURCE_OK=false and tail expectations

---

### FINDING_13: Misleading `_gh_out` name for gate stderr scrape
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The variable name suggests `gh` output rather than gate error scraping, which can mislead debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Rename to a gate-specific identifier

---

### FINDING_14: Unquoted here-doc re-expands ingest/bootstrap stdout blobs as shell syntax (command substitution risk)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Parsing KV blocks via unquoted here-doc can re-expand lines containing `$(...)`, executing unintended command substitution from crafted or accidental helper output during ingest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Replace heredoc with a read path that does not expand payload (e.g. process substitution + printf into while loop in current shell)
  - From cursor-specialist-security-output.txt: Use read loop fed from printf/process substitution without unquoted here-doc expansion of the full blob

---

### FINDING_15: Protocol “Execution Directive” still lists discrete infra scripts vs collapsed `implement-bootstrap`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The protocol line still enumerates discrete create-branch / session-entry-gate / session-setup as Step 0 first external actions, conflicting with the collapsed `implement-bootstrap.sh` narrative and risking wrong tool/script ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Rewrite clause (3) to mandate implement-bootstrap.sh --up-to-phase infra as the Step 0 infra entrypoint.

---

### FINDING_16: Anti-halt “critical boundary” still routes through standalone `session-setup.sh`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Recovery prose still implies running `session-setup.sh` after preflight audit as a standalone Step 0 hop, which misaligns with bootstrap-first Step 0 ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Rephrase to implement-bootstrap.sh then tracking or plan materialization blocks per the numbered Step 0 section.

---

### FINDING_17: Misspelled `SANBOX_TMP` identifier in bootstrap harness
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Consistent misspelling increases maintainer confusion and typo risk when fixing or extending the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Rename consistently to `SANDBOX_TMP` (or similar).

---

### OOS_1: [OUT_OF_SCOPE] PR/branch noise (logs, unrelated commits, review lens hygiene)
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Large or unrelated run-log, version/changelog, and doc commits bundled with bootstrap work widen the diff and distract review without indicating a functional defect in bootstrap itself.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Use filtered diff views; no code change required for this review lens
  - From cursor-specialist-edge-cases-output.txt: Handle via normal PR splitting / scope hygiene outside this review
  - From cursor-specialist-plan-fidelity-output.txt: Reviewers isolate commit 7b6b837d (or equivalent) for #2735 traceability.

---

This output contains `### FINDING_` blocks, so **`LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` must not appear** anywhere in the file.
