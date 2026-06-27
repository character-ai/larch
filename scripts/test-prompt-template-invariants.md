# test-prompt-template-invariants.sh

Cross-cutting regression harness that asserts structural invariants in rendered subagent prompts. Prevents future refactors from silently stripping anti-narrative directives, structured-output demands, and acceptable-output examples that were added by the prompt-audit work in issue #2421.

## What it guards

| Script | Required markers |
|---|---|
| `python/review_pipeline.py` | `### In-Scope Findings` literal; "Begin your response with the literal line" directive; acceptable-output example block; focus-directive framing; absence of removed checklist items 2 and 3 |
| `python/cli.py plan-review voter-dispatch` | `Verify silently`; `Output ONLY vote lines`; no `*plan-voter-prompt-retry.txt` artifact; no Codex parse-retry stub branch |
| `python/cli.py review-and-fix apply-findings` | `Output ONLY result lines`; acceptable-output example; `emit_submodule_prohibition` call |
| `scripts/python/cli.py checks lint-fix` | Codex-combined prompt includes `FIXED:` / `UNFIXABLE:` result-shape spec, acceptable final-line shapes example, `emit_submodule_prohibition` call, machine `site`, orchestrator-verification, edit-only, and no-`exec_command` markers; shared `_compose_prompt` alone must not include Codex-only exec prohibitions |
| `python/cli.py render plan-review` | TSV header literal; filled-in TSV example; anti-preamble directive; no-issues sentinel instruction |
| `python/cli.py scout dynamic-archetypes` | `prompt_body` constraints block; closing-sentence requirement; closing-sentence repair code |
| `python/larch/agents/agents.py` | format-agnostic NS_STRONG_HEADER; absence of old `### FINDING_N` format reference |

## Makefile Wiring

Wired into `make lint` under `test-prompt-template-invariants`.

## Edit In Sync

When changing any of the guarded scripts, update this harness in the same PR.
