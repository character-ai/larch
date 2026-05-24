Here is the normalized aggregator output. In-scope items are ordered by the smallest source finding id in each merged group. Out-of-scope items are grouped as `### OOS_1:` after in-scope findings (min source id 8). There is no `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line because this merge is non-empty.

---

### FINDING_1: One branch bundles unrelated behavioral changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Multiple independent behavioral surfaces ship together (e.g. design plan-size work alongside ship-pr / voter / harness changes), which makes regressions harder to attribute, rollback, bisect, and triage in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_2: Duplicated YES↔EXONERATE prose
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The same YES↔EXONERATE wording exists in more than one place, so future edits can drift and undermine voting consistency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: SEMANTIC_SOFT_ESTIMATE is orchestrator-only and untested
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The soft semantic threshold is not covered by CI; genuinely multi-stream plans below the hard threshold may skip the soft-partition UI with no automated signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: run_ok merges stderr into the parsed KV blob
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Test helper `run_ok` combines stderr into output that grep-based assertions treat as structured KV, so stray stderr could break parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Step 5d upstream deferral lacks argv/repo-identity guard vs documented expectations
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 5d is described as gated on argv-level upstream repo pinning, but the flow effectively keys off issue number, a sentinel, and a hardcoded `gh --repo` target. In clones or forks where issue 2670 exists for unrelated work, the skill can still post the fixed upstream tracking comment on `character-ai/larch#2672`, creating misleading upstream noise and a mismatch with SECURITY / acceptance / flags prose. Related doc-only risk: argv wording can steer security review toward the wrong surface unless it explicitly tracks the `gh` invocation and the real Step 5d conditions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: Partition intent can be lost when run-params repair fails (especially without jq)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Partition persistence recovery depends on `jq` and uses silent `|| true`-style fallbacks. If `write-run-params` fails and `jq` is absent, `partition_requested` may never become true, argv `--partition` can be dropped before Step 2b.5, and the forced soft path is skipped without a clear operator-visible failure mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: rc=2 append-tool-failure instructions are ambiguous about log vs capture
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Orchestrators could misread whether to append from a log file versus in-memory capture and append the wrong payload into `execution-issues.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_8: `--plan-file` contract is not exercised in the harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The helper supports optional `--plan-file`, but tests never pass a non-default plan path, so argv or wiring bugs for that mode could ship while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: TRIVIAL_DOC_ONLY jq assertion omits `partition_requested == false`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The trivial preset path does not re-check the default `partition_requested` false-only expectation in the `jq -e` filter.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: `--plan-file` is not constrained under resolved `DESIGN_TMPDIR`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Callers can aim the helper at arbitrary readable paths; symlinks may escape the session root and leak file-derived counts or headings into the FD3 contract stream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: Step 5d `gh` failure logging omits `append-tool-failure --redact`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Verbose `gh` failures risk copying auth- or token-shaped material into `execution-issues.md` and committed design logs, unlike other network-ish captures that pass `--redact`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: Sentinel touch after successful `gh` can break idempotency
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The sentinel is touched only after a successful `gh` post; if `gh` succeeds but creating the HOME cache or touching the sentinel fails, a later run can duplicate the upstream tracking comment without an `append-tool-failure` capture for the touch failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: SEMANTIC_SOFT_ESTIMATE can re-fire without a session latch
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Gate B or discussion-driven plan re-emits can re-invoke Step 2b.5 and re-trigger semantic soft prompts for the same judgment because nothing persists a once-per-session latch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: Empty or whitespace-only plan misclassified as missing-diff-lines
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: An empty plan body surfaces `missing-diff-lines` rather than a clearer empty-or-missing-body status, which misleads debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: `emit_kv` key order in flags.md may not match the script
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Readers or naive line-order parsers may assume a wire contract that does not match `check-plan-size.sh` or the plan’s helper bullet order.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### OOS_1: [OUT_OF_SCOPE] Branch noise, run logs, and non-2670 stack files
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The diff against main includes bulk unrelated commits, committed run-log or keepalive artifacts, non-#2670 ship/dispatch changes, and general log churn. These items add review noise and process friction but are not treated as correctness defects in the plan-size scripts themselves for this scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge map (for traceability)**  
- FINDING_1 input + FINDING_11 input → **FINDING_1**  
- FINDING_2 input → **FINDING_2**  
- FINDING_3 input → **FINDING_3**  
- FINDING_4 input → **FINDING_4**  
- FINDING_5, 14, 16, 22 input → **FINDING_5**  
- FINDING_6, 20 input → **FINDING_6**  
- FINDING_7 input → **FINDING_7**  
- FINDING_9 input → **FINDING_8** (renumbered after in-scope 1–7)  
- FINDING_10 input → **FINDING_9**  
- FINDING_12 input → **FINDING_10**  
- FINDING_13 input → **FINDING_11**  
- FINDING_17 input → **FINDING_12**  
- FINDING_18 input → **FINDING_13**  
- FINDING_19 input → **FINDING_14**  
- FINDING_21 input → **FINDING_15**  
- FINDING_8, 15, 23, 24 input → **OOS_1**

**Note on numbering:** Sequential `### FINDING_1:` … `### FINDING_15:` are used for in-scope items in ascending order of the smallest source id per block; `### OOS_1:` follows (sources 8, 15, 23, 24). If your downstream validator requires `FINDING_8` through `FINDING_15` labels to match the original ids exactly, say so and the list can be re-titled without changing merged content.

**Why FINDING_22 merged into FINDING_5:** Same behavioral surface (documented argv / SECURITY wording vs actual Step 5d and `gh` behavior); severity **important** dominates **nit**. **Why FINDING_3 and FINDING_13 stay separate:** One is testability and best-effort semantics of the estimate; the other is repeated soft prompting without a latch—different failure modes and fixes.
