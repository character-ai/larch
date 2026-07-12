### [Plan Review] FINDING_1

### FINDING_1: Resume-close must migrate dependencies before closure
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Resume-close still retries `close-original` directly after filing, even when dependency migration has not completed. This can leave original-issue dependency edges stale and provides no documented annotate → migrate-deps → close sequence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rewrite §0 resume-close: when `.decompose-issues-filed` exists and `.decompose-deps-migrated` is absent, run `decompose migrate-deps` (with live-graph verification) before any `close-original` attempt; only then allow resume-close to call `close-original`.
  - From Cursor-Innovation: Update section 0 so resume-close runs migrate-deps when the filing sentinel exists and the migration sentinel is absent, then close-original only after migration postconditions verify.
  - From Cursor-Pragmatic: Rewrite §0 so resume-close runs python/cli.py decompose migrate-deps when filing is complete and .decompose-deps-migrated is absent, then close-original only after migration success; add a resume fixture in test_decompose.py.
  - From Cursor-Requirements: Add an explicit §0 resume branch: when `.decompose-issues-filed` is present and `.decompose-deps-migrated` is absent or stale, run the canonical `decompose migrate-deps` fence (with live-graph revalidation) before any `close-original` retry; only skip migration when the sentinel and postcondition already verify.


### [Plan Review] FINDING_2

### FINDING_2: Define an executable migrate-deps invocation contract
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The normative Split-path documentation does not specify how to invoke `migrate-deps`, bind it to the repository and design temporary directory, parse its output, or order it relative to annotation and closure. Prompt-side wiring could therefore skip or misconfigure migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a § migrate-deps fence to the rewritten decompose-panel.md: `python3 ... decompose migrate-deps --design-tmpdir "$DESIGN_TMPDIR" --original-issue "$ISSUE_NUMBER" --repo "$GITHUB_REPOSITORY"` (plus any annotation path flags the Python verb needs), required `DECOMPOSE_DEPS_*` rows, exit-code branching, and explicit ordering after annotate and before close-original.


### [Plan Review] FINDING_3

### FINDING_3: Replace stale panel-failure branches with an inline terminal contract
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: Removing panel dispatch leaves `panel-failed`, `failed-judge-panel`, and related structure-harness assertions in place, while inline partition-validation exhaustion has no defined summary outcome, staging behavior, or terminal token. This can retain dead panel prompts or misreport inline failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Remove Split-path panel-failed Retry/Cancel and `failed-judge-panel` orchestration from SKILL.md; define one terminal outcome for inline partition validation exhaustion (stage + Final summary + preserve tmpdir); add `### UPDATED: scripts/test-design-structure.sh` (and finalize-step5-failures.md if it still ties `failed-judge-panel` to decompose-panel retry).
  - From Cursor-Pragmatic: Name a dedicated terminal outcome (for example failed-partition-proposal), list it in SKILL.md Final summary exports, update finalize-step5-failures.md and python/larch/design/design_terminal.py, and replace the judge-panel harness assertions in scripts/test-design-structure.sh.
  - From Cursor-Requirements: Name a single terminal outcome for inline partition validation exhaustion (reuse or replace `failed-judge-panel`), document the `stage-terminal-state` / Final-summary path in `decompose-panel.md` and `finalize-step5-failures.md`, remove Split-path `PANEL_STATUS=panel-failed` and Retry panel prose from `SKILL.md`, and add a `### UPDATED:` entry for `scripts/test-design-structure.sh` (plus the focused decompose test named in the plan) so the new failure route is asserted.


### [Plan Review] FINDING_4

### FINDING_4: Persist the inline partition proposal at a canonical path
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The inline partition proposal has no durable canonical file before `decompose prepare`. A proposal existing only in chat cannot reliably support prepare repair loops, pause/resume, or consistent reruns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require writing the validated inline proposal to a single normative path (for example `$DESIGN_TMPDIR/decompose/inline-partition.md`), use it for every prepare rerun, persist it through operator acceptance, and document resume behavior when that file already exists.
  - From Cursor-Requirements: Require the inline procedure to write the validated proposal to a canonical durable file under `$DESIGN_TMPDIR/decompose/` (for example `inline-partition-proposal.md`) before every `decompose prepare` call, and mandate that all prepare/repair/resume steps read that same path rather than recomputing from memory.


### [Plan Review] FINDING_5

### FINDING_5: Preserve proposal-authoritative intra-batch dependency flags
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The rewritten filing path may omit `--no-dep-llm` and `--intra-batch-deps-file`, allowing `/larch:issue` to invent dependency edges or drop proposal-declared edges. This can violate the partition’s declared independence and dependency graph.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: State explicitly in the new §7b: when `partition-deps.tsv` is non-empty, invoke `/larch:issue` with `--intra-batch-deps-file "$DESIGN_TMPDIR/decompose/partition-deps.tsv"` and `--no-dep-llm`; omit `--intra-batch-deps-file` only when the TSV is empty (independent pieces).
  - From Cursor-Pragmatic: Add an explicit §7b contract: always pass --no-dep-llm for partition batches; pass --intra-batch-deps-file only when partition-deps.tsv has rows; pin the empty-TSV all-independent case in test_decompose.py.
  - From Cursor-Requirements: In the rewritten Split-path §7b, make the `/larch:issue` batch invocation normative: `--input-file` on `partition-input.txt`, `--intra-batch-deps-file` on `partition-deps.tsv`, `--no-dep-llm`, `--context-file "$DESIGN_TMPDIR/source-env.sh"`, dedup enabled, and stdout capture to `issue-run.stdout`, matching today's panel path semantics without the removed serial edges.


### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md
- **Concern**: [SCOPE-REDUCTION] Stale panel-failed Split-path contract survives the inline rewrite. Scenario: The plan removes panel dispatch from Split-path but does not list updates to SKILL.md panel-failed handling, finalize-step5-failures.md Split-path ownership prose, or scripts/test-design-structure.sh lines 613-614. Inline prepare failure also has no named SUMMARY_OUTCOME, leaving failed-judge-panel tied to a removed panel-retry flow.
- **Proposed resolution**: Remove Split-path panel-failed and Retry panel branches; name a single terminal outcome for inline prepare failure; update finalize-step5-failures.md and test-design-structure.sh accordingly; keep failed-judge-panel only for Step 3 panel-init-failed.


