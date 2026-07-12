### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:sweep_main
- **Concern**: Strict ingestion rejects empty inputs without defining the zero-work path. Scenario: A first sweep with no eligible commits, or a sweep whose finders return no findings, cannot complete despite the specified successful zero-finding cases
- **Proposed resolution**: Explicitly bypass result-file parsing for zero selected merges and zero refutation queues; still reject empty files when work was dispatched



### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: .claude/skills/analyze-bugs/SKILL.md:Preflight and Stage 0/S1
- **Concern**: The pinned sweep tip is not tied to the preflight checkout tip. Scenario: Stage 0 fetches origin/main again; if remote advances, S1 can pin a newer tip while agents inspect the older synced main checkout
- **Proposed resolution**: Capture and pass the preflight SHA through the workflow, or verify main and origin/main equal the pinned SHA before dispatch and fail closed 1. **[correctness] Empty sweep handling is contradictory.** The plan rejects empty finder and refuter inputs but also requires successful zero-commit and zero-finding sweeps. Define explicit zero-work fast paths. 2. **[correctness] The pinned tip can diverge from the checkout.** Stage 0 refetches `origin/main` after preflight. Preserve the preflight SHA or verify checkout identity before agent dispatch.



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:sweep_enumeration
- **Concern**: First-parent enumeration lacks an explicit Git invocation. Scenario: The plan names first-parent history and uses MERGE_SHA^1..MERGE_SHA for per-commit diffs, but never pins the list source to git log --first-parent. A plain git log origin/main range can include non-first-parent commits from merged side branches, so the sweep can analyze commits that never landed on main's first-parent line and miss the acceptance fixture intent.
- **Proposed resolution**: Specify enumeration as git log --first-parent <watermark>..<pinned-tip> (or equivalent rev-list), keep the same exclusion filters, and add a fixture that would include a side-branch-only commit without --first-parent.



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: .claude/skills/analyze-bugs/SKILL.md:S0-S3
- **Concern**: Sweep stages lack the executable Python ingest fences the fail-closed contract requires. Scenario: Strict sweep parsers live in Python, but Stage 0-2 triage/deep stages already use explicit analyze-bugs CLI fences and disk paths. Sweep S2 only says hard-validate finder/refuter results, so the orchestrator can prompt-validate JSONL and skip INGEST_ACCEPTED exact-match enforcement, reproducing ledger-style soft partial success.
- **Proposed resolution**: Mirror triage/deep: add bash fences for sweep prepare, ingest-finder, and ingest-refuter; save finder JSONL under fixed RUN_DIR paths; abort the run on any non-zero ingest exit before refuter dispatch or legacy stages.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py:sweep_main ingest-finder; .claude/skills/analyze-bugs/SKILL.md:S2
- **Concern**: Refuter dispatch input contract is unspecified. Scenario: Python ingest-finder creates a bounded refutation queue, but the plan never names the queue artifact path, required stdout KVs, or how each refuter Task receives merge_sha, finding index, and cited fields. Without that handoff, refuter fan-out cannot be validated against the prepared key set and partial coverage can slip through.
- **Proposed resolution**: Have ingest-finder emit REFUTER_QUEUE_PATH plus queue length KVs; document that S2 dispatches one refuter per queue row using only that file; require ingest-refuter to verify the accepted key set exactly matches the queue before writing the validated sweep-result artifact.



