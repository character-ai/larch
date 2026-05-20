# test-prompt-template-invariants.sh

Cross-cutting regression harness that asserts structural invariants in rendered subagent prompts. Prevents future refactors from silently stripping anti-narrative directives, structured-output demands, and acceptable-output examples that were added by the prompt-audit work in issue #2421.

## What it guards

| Script | Required markers |
|---|---|
| `skills/review/scripts/dispatch-panel.sh` | `### In-Scope Findings` literal; "Begin your response with the literal line" directive; acceptable-output example block; focus-directive framing; absence of removed checklist items 2 and 3 |
| `scripts/dispatch-plan-voters.sh` | `Verify silently`; `Output ONLY vote lines`; `PLAN_VOTER_PARSE_RATE_RETRY_PREFIX`; `make_plan_voter_retry_prompt_file` |
| `skills/review-and-fix/scripts/review-and-fix.sh` | `Output ONLY result lines`; acceptable-output example; `emit_submodule_prohibition` call |
| `scripts/lint-fix-loop.sh` | `FIXED:` / `UNFIXABLE:` result-shape spec; acceptable final-line shapes example; `emit_submodule_prohibition` call |
| `skills/design/scripts/render-plan-review-prompt.sh` | TSV header literal; filled-in TSV example; anti-preamble directive; no-issues sentinel instruction |
| `scripts/scout-dynamic-archetypes.sh` | `prompt_body` constraints block; closing-sentence requirement; closing-sentence repair code |
| `scripts/collect-agent-results.sh` | format-agnostic NS_STRONG_HEADER; absence of old `### FINDING_N` format reference |

## Makefile Wiring

Wired into `make lint` under `test-prompt-template-invariants`.

## Edit In Sync

When changing any of the guarded scripts, update this harness in the same PR.
