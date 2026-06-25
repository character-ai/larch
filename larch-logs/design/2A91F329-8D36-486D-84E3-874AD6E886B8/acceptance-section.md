## Acceptance

- `make lint`, `make py-lint`, and `make py-test` all pass.
- These focused checks pass: `make test-implement-fence-shape`, `scripts/test-implement-structure.sh`, `scripts/test-implement-anti-polling-rule.sh`, `scripts/test-implement-anti-halt.sh`, `scripts/test-design-structure.sh`, `scripts/test-render-cost-line-callsites.sh`, `scripts/test-quick-mode-docs-sync.sh`, and `python3 python/cli.py lint readability-preamble`.
- `skills/implement/SKILL.md` and `skills/design/SKILL.md` both have a strictly lower line count than before the change.
- `skills/implement/references/step18-cleanup.md` and `skills/design/references/finalize-step5.md` exist, each with `Consumer`, `Contract`, and `When to load` headers.
- New on-entry `MANDATORY — READ ENTIRE FILE` reads appear only at `/implement` Step 8+ (`ship-pr-exit-matrix.md`), `/implement` Step 18 (`step18-cleanup.md`), and `/design` Step 5 (`finalize-step5.md`). No new `/implement` Step 5 entry read is added.
- Move-not-copy holds: each relocated block is deleted from its `SKILL.md`, with no duplicate normative authority, enforced by `forbid` / `not_contains` guards in the structure harnesses.
- KEEP-safe inline content is unchanged: step markers, step transitions, anti-halt boundaries, all orchestrator Bash fences, immediate-background timeout text, S030-pinned paths, and `LARCH_FINAL_SUMMARY_*` / `---LARCH-SUMMARY-FINAL-*` bindings stay in `SKILL.md`.
- No step behavior, ordering, or wrapper-call changes in `/design` or `/implement`.
- Files under `python/` are unchanged.
