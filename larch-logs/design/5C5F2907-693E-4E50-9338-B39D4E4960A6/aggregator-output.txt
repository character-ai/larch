### FINDING_1: Closed-issue corpus must include all states
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: The bug corpus can still be built from open issues only, so closed [BUG] fixes may never enter the audit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add --state all to every gh issue list call used for the bug corpus, including optional-field fallback calls.
  - From Codex-Requirements: Require `--state all` or an equivalent all-state corpus before title-prefix filtering, and keep the closed issue cases in the planned offline tests.

### FINDING_2: Deep-model alias mapping must drive dispatch and pricing
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The `--deep-model` alias path still needs one concrete mapping that governs verifier dispatch and pricing, or the run can validate one tier while charging another.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Specify a supported dispatch shape: map `sonnet|opus|fable` to concrete verifier agent definitions or another repo-supported model-selection mechanism, and use the same alias-to-model-id map for cost pricing.
  - From Cursor-Pragmatic: Add one explicit map: CLI alias -> Task `model` -> `rate_row` model id (reuse `config.CLAUDE_*` MODEL). Echo both `DEEP_MODEL=` and `DEEP_RATE_MODEL=` on stdout. Test unsupported values and each allowed alias.
  - From Codex-Pragmatic: Define one mapping from `sonnet|opus|fable` to the existing full config model constants and use it for both Task dispatch and the `rate_row` call.
  - From Cursor-Requirements: Document and test one map: sonnet->claude-sonnet-4-6, opus->claude-opus-4-8, fable->claude-fable-5; SKILL passes the mapped Task model; report uses the same map with rate_row for the cost line.
  - From Codex-Pragmatic: Define one mapping from `sonnet|opus|fable` to the existing full config model constants and use it for both Task dispatch and the `rate_row` call.
  - From Codex-Requirements: Add one alias map from flag values to the existing Claude model constants, and use it for both Task dispatch and cost estimates.

### FINDING_3: Prefetch must hand off stable run and ledger paths
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: The skill still lacks an explicit stdout/argv handoff for durable run and ledger paths, so resumed stages can read stale artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Document repo-slug `ledger.jsonl` beside `runs/`. Have prefetch/ledger/report emit and require whole-line KVs (`RUN_DIR=`, `MANIFEST_PATH=`, `LEDGER_PATH=`, triage/deep batch paths). Update the skill to capture prefetch stdout and pass `--run-dir` / `--ledger-path` into later verbs.
  - From Cursor-Requirements: Mirror rejected_analysis: prefetch emits RUN_DIR, MANIFEST_PATH, LEDGER_PATH, and per-batch TRIAGE_BATCH_* / DEEP_QUEUE_* KVs; document required ledger/report argv (--run-dir, --manifest, --ingest-triage, --ingest-deep); SKILL steps 3-9 must parse stdout and pass those paths on every invocation.

### FINDING_4: Cached verdicts must join on the full cache key
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Reporting by issue number alone can resurrect stale cached verdicts for reopened bugs or changed fix surfaces; the merge must respect the full cache key triple.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Join manifest rows to ledger/report state on the full cache key (or equivalent triple). Ignore cached stage verdicts when the key differs. Prefer current-run stage output over ledger, and ledger over mechanical defaults only when keys match.

### FINDING_5: Sampled deep-verify pool must be restricted and tracked
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: `--sample K` needs to draw only from fixed triage verdicts eligible for false-pass measurement, not arbitrary or already-deep-queued rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Restrict `--sample` to triage `FIXED_CLEAR` and `FIXED_LIKELY` rows not already deep-queued. Record `sampled: true` provenance. Compute false-pass rate only from that pool in `report`.
  - From Cursor-Requirements: Sample only from manifest rows whose triage verdict is FIXED_CLEAR or FIXED_LIKELY and who are not already required-deep; tag sampled rows; false-pass math must use sampled deep outcomes only.
  - From Codex-Requirements: Specify random or deterministic pseudo-random sampling over `FIXED_CLEAR` and `FIXED_LIKELY` rows after required deep candidates, preserving the planned sampled provenance and false-pass metrics.

### FINDING_6: Fix commit lookup must avoid prefix collisions
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: A substring `git log --grep` match can bind the wrong fix commit to a bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Post-filter matched commit messages or use a boundary-aware pattern for exact issue references, and add one fake-runner regression case for prefix issue numbers.

### FINDING_7: Triage and deep JSONL contracts must require ingest fields
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The triage and deep agents still do not pin the ingestable JSONL fields, so the ledger cannot reliably validate or join their output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add the exact one-object-per-line schema to bug-fix-triage.md and ledger ingest validation; tests must assert rejection when any required field is missing.
  - From Cursor-Requirements: Specify deep JSONL as one line per bug with at least issue, verdict, and reason; ledger ingest rejects rows missing issue or an allowed verdict; add a focused ingest test.
  - From Codex-Requirements: Spell out exact triage and deep JSONL schemas in the agent prompts and ingestion tests, including the triage `needs_deep` field and the fields the report consumes.
