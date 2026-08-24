# test-prompt-template-invariants.sh

Cross-cutting regression harness that asserts structural invariants in rendered subagent prompts. Prevents future refactors from silently stripping anti-narrative directives, structured-output demands, and acceptable-output examples that were added by the prompt-audit work in issue #2421.

## What it guards

| Script | Required markers |
|---|---|
| `crates/larch-cli/src/review_dispatch_panel_prompt.md` | `### In-Scope Findings` literal; "Begin your response with the literal line" directive; acceptable-output example block; focus-directive framing; absence of removed checklist items 2 and 3 |
| `python/cli.py render voter` | `Verify silently`; `Output ONLY vote lines`; no `*plan-voter-prompt-retry.txt` artifact; no Codex parse-retry stub branch |
| `scripts/larch.sh review-and-fix apply-findings` | `Output ONLY result lines`; acceptable-output example; submodule-prohibition section |
| `crates/larch-core/src/implement/checks_lint_fix.rs` (`compose_prompt` / `codex_lint_fix_prompt_appendix`) | Codex-combined prompt includes `FIXED:` / `UNFIXABLE:` result-shape spec, acceptable final-line shapes example, submodule prohibition, machine `site`, orchestrator-verification, edit-only, and no-`exec_command` markers; the shared prompt alone must not include Codex-only exec prohibitions. Pinned by the module's in-crate tests, not this Bash harness. |
| `scripts/larch.sh render plan-review` | TSV header literal; filled-in TSV example; anti-preamble directive; no-issues sentinel instruction |
| `scripts/larch.sh scout dynamic-archetypes` | `prompt_body` constraints block; closing-sentence requirement; closing-sentence repair code |
| `crates/larch-core/src/vendor/review.rs` | format-agnostic NS_STRONG_HEADER; absence of old `### FINDING_N` format reference |

## Makefile Wiring

Wired into `make lint` under `test-prompt-template-invariants`.

## Edit In Sync

When changing any of the guarded scripts, update this harness in the same PR.
