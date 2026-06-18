## Decision 1: Three-category script partition
- **Question**: Which of the 20 scripts still have bash bodies vs. are already thin wrappers?
- **Resolution**: Three groups: (A) thin delegation wrappers already calling Python (step-0-bootstrap, step-2-entry, step-5-resume, step-5-review, step-6-entry, step-8-ship, step-8-oos-checkpoint, step-8-seed-initial, run-step-checks); (B) scripts with bash bodies whose Python port already exists in target modules (flush-execution-issues, refresh-execution-issues, materialize-manifest-oos, oos-issue-cap, oos-file-conflict-deps, oos-disposition-checkpoint, oos-disposition-gate, slack-issue-announce, generate-code-flow-diagram); (C) scripts with bash bodies needing new Python verbs (step-2-post-dispatch, step-8-python-guard, post-tracking-issue); plus (D) legacy inactive step-0-degraded-gate.
- **Source**: codebase

## Decision 2: Thin wrappers → direct Python calls in SKILL.md
- **Question**: Do Group A thin wrappers get deleted and SKILL.md updated to call Python directly?
- **Resolution**: Yes. Per migration recipe "Cut ALL consumers to direct cli.py calls." SKILL.md already uses this pattern (line 399: larch-run.sh python/cli.py implement run-dispatch). Each thin wrapper is replaced with a direct python/cli.py call through larch-run.sh; Python handles its own CLAUDE_PLUGIN_ROOT resolution and LARCH_* env rehydration from session-env.sh.
- **Source**: codebase (SKILL.md line 399 pattern, implement_dispatch.py env rehydration logic)

## Decision 3: Group B scripts — thin wrapper or direct cut
- **Question**: For scripts with existing Python ports, should consumers be cut to direct cli.py calls or should the bash scripts become thin one-liner wrappers?
- **Resolution**: Direct cut per the "no shims" rule. Consumers (SKILL.md fences, any other callers) call python3 cli.py directly. Bash scripts deleted with no replacement wrappers.
- **Source**: docs/python-migration.md "No shims"

## Decision 4: post-tracking-issue.sh porting approach
- **Question**: post-tracking-issue.sh builds an initial summary-metadata.md and posts it. execution_issues.py::refresh_execution_issues() does a similar upsert but differs in initial creation (includes agent, coder, version info). Is there already a Python equivalent?
- **Resolution**: No exact Python equivalent for initial post. A new `implement post-tracking-issue` CLI verb is needed in execution_issues.py. The initial summary construction logic (agent, coder, version fields) must be ported, differing from refresh which only updates existing summary. Post-tracking-issue also writes parent-issue.md sentinel on success.
- **Source**: codebase (post-tracking-issue.sh vs execution_issues.py::refresh_execution_issues)

## Decision 5: step-0-degraded-gate.sh disposition
- **Question**: step-0-degraded-gate.sh is marked legacy — "remains shipped for offline harnesses but is not called on the active Step 0 path." Is it in scope?
- **Resolution**: In scope per issue body listing. Delete it, add to migrated-scripts.tsv. The offline harness tests that reference it (if any) may also need deletion.
- **Source**: issue body + SKILL.md line 94

## Decision 6: lib-execution-issues.sh retirement
- **Question**: When can lib-execution-issues.sh be deleted?
- **Resolution**: After flush-execution-issues.sh is converted to a direct Python call (deleting its bash body that sources lib). refresh-execution-issues.sh does not source lib. Retire lib-execution-issues.sh in the same PR once flush-execution-issues.sh is deleted.
- **Source**: flush-execution-issues.sh line 12 (source lib-execution-issues.sh)
