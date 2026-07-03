### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:prefetch
- **Concern**: The corpus-fetch fix still omits --state all for gh issue list. Scenario: gh issue list defaults to open issues, so the planned pagination can select only open [BUG] rows and miss the closed fixes the audit is supposed to verify.
- **Proposed resolution**: Add --state all to every gh issue list call used for the bug corpus, including optional-field fallback calls.

### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:153-190
- **Concern**: Deep model selection still relies on a fixed Sonnet verifier agent plus a Task model parameter. Scenario: Running `/analyze-bugs --deep-model fable` can validate and echo fable, then still launch `.claude/agents/bug-fix-verifier.md` with `model: sonnet` because repo agent contracts put the model in frontmatter, not in the skill workflow. The accepted prior finding about `--deep-model` remains incomplete if the dispatch mechanism cannot actually select the requested model.
- **Proposed resolution**: Specify a supported dispatch shape: map `sonnet|opus|fable` to concrete verifier agent definitions or another repo-supported model-selection mechanism, and use the same alias-to-model-id map for cost pricing.

### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/skills/analyze-bugs/SKILL.md
- **Concern**: Pin stable ledger path and stdout KV handoff between prefetch, ledger, and report. Scenario: The issue scope anchors ledger at `~/.cache/larch/analyze-bugs/<repo>/ledger.jsonl`, but the plan only names per-run bundle dirs under `runs/<timestamp-or-id>/` and never fixes `ledger.jsonl` location. Prefetch says it will emit paths, yet the skill workflow never requires parsing or forwarding `RUN_DIR`, `MANIFEST_PATH`, `LEDGER_PATH`, or batch queue paths the way `audit-runs` parses `PREFLIGHT_OK` / `PR_LIST`. A restarted run can rebuild a new run dir while later stages still point at stale artifacts, breaking resume and incremental reuse.
- **Proposed resolution**: Document repo-slug `ledger.jsonl` beside `runs/`. Have prefetch/ledger/report emit and require whole-line KVs (`RUN_DIR=`, `MANIFEST_PATH=`, `LEDGER_PATH=`, triage/deep batch paths). Update the skill to capture prefetch stdout and pass `--run-dir` / `--ledger-path` into later verbs.

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py
- **Concern**: Report merge must key cached verdicts to the manifest cache triple, not issue number alone. Scenario: Ledger skip logic is keyed by `(issue_number, fix_sha, later_history_hash)`, but the report verb only says to merge mechanical, triage, deep, skipped, and cached verdicts. If report joins on issue number, a reopened bug, new fix commit, or changed later-history hash can surface an old deep verdict against a new manifest row.
- **Proposed resolution**: Join manifest rows to ledger/report state on the full cache key (or equivalent triple). Ignore cached stage verdicts when the key differs. Prefer current-run stage output over ledger, and ledger over mechanical defaults only when keys match.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py
- **Concern**: Define `--deep-model` mapping to Task model slugs and `rate_row` model ids. Scenario: Round 1 accepted wiring `--deep-model`, but the plan still only allows `sonnet|opus|fable` and says to map into Task without a table. `rate_row` expects ids like `claude-sonnet-4-6` and `claude-fable-5`, not those aliases. A partial map can launch the wrong verifier model and price the run with the wrong rate row.
- **Proposed resolution**: Add one explicit map: CLI alias -> Task `model` -> `rate_row` model id (reuse `config.CLAUDE_*_MODEL`). Echo both `DEEP_MODEL=` and `DEEP_RATE_MODEL=` on stdout. Test unsupported values and each allowed alias.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py
- **Concern**: Specify the `--sample K` candidate pool for calibration. Scenario: The feature requires sampling random triage passes through deep verify to measure false-pass rate. The plan only says `--sample K` fills remaining deep budget after required candidates, not which triage verdicts are eligible. Sampling `SUSPECT`/`NEEDS_DEEP` or mechanical rows would distort calibration metrics.
- **Proposed resolution**: Restrict `--sample` to triage `FIXED_CLEAR` and `FIXED_LIKELY` rows not already deep-queued. Record `sampled: true` provenance. Compute false-pass rate only from that pool in `report`.

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py
- **Concern**: `git log --grep "Fixes #N"` needs an exact issue-reference match. Scenario: The planned grep is a substring regex, so issue #123 can match a commit that only says `Fixes #1234`; newest-wins can attach the wrong fix commit and verify an unrelated diff as the bug fix.
- **Proposed resolution**: Post-filter matched commit messages or use a boundary-aware pattern for exact issue references, and add one fake-runner regression case for prefix issue numbers.

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py; python/larch/report/report_tokens_cost.py:110-121
- **Concern**: Map `--deep-model` shorthands before pricing. Scenario: `rate_row("claude", model="sonnet")` misses the table key and falls back to the Claude default Opus row, so the required cost summary overprices the default Sonnet run and makes the cost validation misleading.
- **Proposed resolution**: Define one mapping from `sonnet|opus|fable` to the existing full config model constants and use it for both Task dispatch and the `rate_row` call.

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: architecture
- **Location**: .claude/skills/analyze-bugs/SKILL.md
- **Concern**: Prefetch-to-ledger-to-report handoff is still implicit. Scenario: FINDING_4 was only partly fixed: prefetch says it will emit paths, but the skill never requires parsing those KV lines or forwarding a stable run dir, and ledger/report lack documented flags for manifest, batch manifests, ingest files, and ledger path. A resumed or multi-step run can ingest the wrong JSONL or report against a stale partial run directory.
- **Proposed resolution**: Mirror rejected_analysis: prefetch emits RUN_DIR, MANIFEST_PATH, LEDGER_PATH, and per-batch TRIAGE_BATCH_* / DEEP_QUEUE_* KVs; document required ledger/report argv (--run-dir, --manifest, --ingest-triage, --ingest-deep); SKILL steps 3-9 must parse stdout and pass those paths on every invocation.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py
- **Concern**: --deep-model dispatch mapping is still unspecified. Scenario: FINDING_5 fix is incomplete: Python validates sonnet|opus|fable and the skill says to map the flag to Task model, but no table ties CLI tokens to Task model slugs or to rate_row model IDs for ANALYZE_BUGS_COST_ESTIMATE. Implementers can validate fable yet still launch Sonnet or price the wrong tier.
- **Proposed resolution**: Document and test one map: sonnet->claude-sonnet-4-6, opus->claude-opus-4-8, fable->claude-fable-5; SKILL passes the mapped Task model; report uses the same map with rate_row for the cost line.

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/agents/bug-fix-triage.md
- **Concern**: Triage JSONL schema omits binding spec fields. Scenario: The issue requires strict JSONL with issue, verdict, missing_items, reason, and needs_deep. The planned agent only lists verdict enums, and ledger ingest tests malformed rows but not required keys. Ingest will reject or mis-parse agent output on every triage batch.
- **Proposed resolution**: Add the exact one-object-per-line schema to bug-fix-triage.md and ledger ingest validation; tests must assert rejection when any required field is missing.

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: .claude/agents/bug-fix-verifier.md
- **Concern**: Deep verifier JSONL ingest shape is undefined. Scenario: Stage 2 ingest upserts by cache_key and stage, but the verifier prompt only lists verdict literals. Without a required issue (and reason) field contract, deep JSONL cannot be joined to manifest rows deterministically.
- **Proposed resolution**: Specify deep JSONL as one line per bug with at least issue, verdict, and reason; ledger ingest rejects rows missing issue or an allowed verdict; add a focused ingest test.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py
- **Concern**: --sample K eligible pool is not defined. Scenario: The spec sends K random triage FIXED verdicts through deep verify to measure false-pass rate. The plan only says sample fills remaining deep budget after escalations, not that the pool is triage FIXED_CLEAR and FIXED_LIKELY only, excluding bugs already queued for required deep review.
- **Proposed resolution**: Sample only from manifest rows whose triage verdict is FIXED_CLEAR or FIXED_LIKELY and who are not already required-deep; tag sampled rows; false-pass math must use sampled deep outcomes only.

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:36-38
- **Concern**: Prefetch does not require `gh issue list --state all`. Scenario: `gh issue list` defaults to open issues, so an implementation can paginate only open `[BUG]` issues and miss the closed fixes this feature is meant to audit.
- **Proposed resolution**: Require `--state all` or an equivalent all-state corpus before title-prefix filtering, and keep the closed issue cases in the planned offline tests.

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:63-70
- **Concern**: `--deep-model` aliases are not mapped before pricing. Scenario: The public flag uses `sonnet|opus|fable`, but the shared rate table is keyed by full Claude model IDs. Passing `sonnet` to `rate_row` falls back to Opus pricing, so the required cost summary is wrong for the default model.
- **Proposed resolution**: Add one alias map from flag values to the existing Claude model constants, and use it for both Task dispatch and cost estimates.

### FINDING_16:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:60-61
- **Concern**: `--sample K` is not specified as random over fixed triage passes. Scenario: The feature requires random FIXED samples to estimate triage false-pass rate. The plan only says samples fill remaining deep budget, so an implementation can sample the first K rows and print a biased calibration metric.
- **Proposed resolution**: Specify random or deterministic pseudo-random sampling over `FIXED_CLEAR` and `FIXED_LIKELY` rows after required deep candidates, preserving the planned sampled provenance and false-pass metrics.

### FINDING_17:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:144-151,162-167
- **Concern**: Agent output contracts omit the required ingestable JSONL fields. Scenario: Stage 1 requires JSONL with `issue`, `verdict`, `missing_items`, `reason`, and `needs_deep`; the plan only says strict JSONL. The deep prompt lists verdicts but not a JSONL-only schema, while the ledger expects strict deep JSONL.
- **Proposed resolution**: Spell out exact triage and deep JSONL schemas in the agent prompts and ingestion tests, including the triage `needs_deep` field and the fields the report consumes.
