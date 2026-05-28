### FINDING_1: plan-review-loop.sh is too monolithic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `plan-review-loop.sh` concentrates orchestration, collector parsing, OOS accumulation, deduplication, embedded Python, and multi-round branching in one large file, increasing maintenance risk and review miss rate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: duplicate collector parsing can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Collector STATUS parsing exists in both `_parse_collect_records` and `_run_plan_review_round`, so future fixes may update only one path and break zero-finding or degradation behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: integration harness misses required multi-round and Gate B scenarios
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-multi-round-integration.sh` omits several plan-required scenarios, including SKILL Step 3 KV parsing, Gate B passive-summary/fallback routing, revision-failed handoff, cross-entry cleanup, plan identity, publish-failure staging checks, convergence/streak behavior, and stronger cap-hit assertions. These gaps allow Step 3 rehydration, Gate B routing, cleanup, revision failure, or cap semantics to regress while integration tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: artifact allowlist tests are static instead of derived from live snapshots
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-lib-design-round-artifacts.sh` validates a static basename list rather than live or golden loop snapshot output, so new snapshot artifacts can pass unit checks and later fail publish/integration behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: accepted finding count regex is inconsistent
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Inner-round and outer-loop `ACCEPTED_COUNT` grep patterns differ, so malformed `FINDING` headers could affect convergence streak or cap-hit decisions inconsistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: obsolete global dedup state is misleading
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_dedup_failed` is still initialized at module scope even though it is reset per round, which suggests global state may carry across rounds when it should not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: loop can report complete without running a round
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The terminal exit after the loop is effectively unreachable for normal runs, but `--round-num` greater than `--round-cap` could skip the loop and exit successfully with `LOOP_STATUS=complete`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: cumulative accepted OOS is truncated across rounds
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Both tally and empty-artifact paths can truncate `oos-accepted-design.md` during later rounds, losing OOS accepted in earlier rounds before Step 5b files them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: OOS accumulation includes rejected or exonerated items
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_accumulate_round_oos` merges all OOS blocks from `oos.md`, so rejected or exonerated OOS items can enter `oos-accepted-design.md` and later be filed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: main-agent-vote-required skips OOS accumulation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The `main-agent-vote-required` branch exits before `_accumulate_round_oos`, so a round with accepted OOS and main-agent vote required can leave the cumulative OOS file empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: symlinked snapshot sources produce partial forensic archives
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_snapshot_round_dir` skips symlinked sources per file instead of failing the snapshot or marking degraded, which can publish incomplete round forensic artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: unit harness misses plan-required loop cases
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/test-plan-review-loop.sh` lacks acceptance-listed cases for OOS accumulation, dedup reset, convergence streaks, degraded streak reset, severity defaults, important-count gating, revise exit failure, and legacy golden fixtures, allowing core loop behavior to regress without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] legacy single-pass mode is not documented as direct-script-only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `SKILL.md` always passes `--round-cap`, making legacy single-pass behavior harness/direct-script-only, but operators may infer it is available through normal SKILL invocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] revise.env allowlist entry appears unused
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `revise.env` is allowlisted although `revise-plan-with-waterfall.sh` does not create it, creating stale or misleading artifact policy surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_15: revise sub-allowlist lacks fail-closed publish coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-design-log-publish` covers happy-path revise artifacts but not disallowed files under `round-N/revise`, so production publish failures from unexpected revise files may escape tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: relevant-checks omits plan-review-loop.md
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Changes to `skills/design/scripts/plan-review-loop.md` do not trigger the same loop or integration tests as `plan-review-loop.sh`, allowing contract drift to merge without relevant checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: integration coverage docs overstate implemented scenarios
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-multi-round-integration.md` suggests broader coverage than the harness actually provides, which can mislead contributors about SKILL Gate B and cross-entry test protection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_18: SECURITY.md underdocuments published plan-review artifacts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` still describes plan-review publish as `findings-classification.tsv` only, while current code publishes a broader allowlist including ballots and vote outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: Step 3 env writer permits newline injection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `write_step3_result_env` does not reject or escape newlines and equals signs before SKILL.md line-parses the env file, so a compromised or buggy writer could forge later keys such as `LOOP_STATUS`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: environment script overrides execute arbitrary paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_PLAN_REVIEW_REVISE_SH` and sibling environment overrides can redirect execution to arbitrary scripts with session tmpdir access, but their test-only status is not documented or enforced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_21: Gate B routing contradicts emit-plan-failed handling
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `approval-gates.md` and `SKILL.md` disagree on `emit-plan-failed`: one path treats it as manual-choice routing while another auto-applies, risking a second apply against an already revised plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: regex dedup can remove intentional duplicate plan lines
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Auto-apply regex dedup may delete repeated requirement lines that are intentionally duplicated, corrupting plan structure before validators or size gates run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: revise artifact filenames differ from plan-listed names
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The revise allowlist uses `prompt.txt` and `*-candidate.patch` while the plan names `revise-prompt.md` and `patch.diff`, so downstream tooling that follows the plan names may miss actual artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
