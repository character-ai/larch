# scripts/test-lint-foreground-markers.sh — contract

Black-box regression harness for `scripts/lint-foreground-markers.sh`. It builds isolated fixture trees under `mktemp -d` (no `.git` so the linter exercises the non–git-worktree `find` enumeration path), writes synthetic `skills/*/SKILL.md` and `skills/shared/*.md` files, and asserts exit codes plus stderr needles for:

1. **Clean path** — banner immediately above a bash-tagged fenced block, canonical `# Foreground required…` comment on the line before `${CLAUDE_PLUGIN_ROOT}/scripts/collect-agent-results.sh`.
2. **Missing banner** — comment present, banner absent → `missing banner`.
3. **Missing comment** — banner present, comment absent → `missing comment`.
4. **Blockquoted banner** — same as (1) but the banner line is prefixed with a Markdown blockquote marker (greater-than as the first non-whitespace character, followed by a single ASCII space before the banner text).
5. **Banner outside pre-fence window** — more than 20 Markdown lines between banner and opening fence → `missing banner`.
6. **Comment too far above anchor** — comment separated from the invocation by more than five in-fence lines → `missing comment`.
7. **Non–Family-B script** — `wait-for-reviewers.sh` in a fence without markers → passes (not denylisted).
8. **Non-shell fence** — `collect-agent-results.sh` inside a YAML-tagged fenced block → ignored.
9. **`ship-pr.sh`** — markers required and satisfied → passes.
10. **Indented opening fence** — leading spaces on the bash fence opener line → still scanned.
11. **`skills/shared/` path** — contract exercised under `skills/shared/*.md` glob.
12. **`if`/`while` shaped invocation** — `if ! …/run-step5-review.sh` with markers → passes.
13. **Assignment-shaped invocation** — `CMD=${CLAUDE_PLUGIN_ROOT}/scripts/review-and-fix.sh` with markers → passes.
14. **Substring guard** — `test-collect-agent-results.sh` token in a fence without Family-B markers → must **not** trip the collector anchor (no violation).
15. **`dispatch-plan-voters.sh`** — markers satisfied → passes.
16. **Family A baseline** — pinned `grep -cF 'run_in_background: true'` counts on the four orchestrator `skills/{design,implement,research,review}/SKILL.md` files (guards accidental proliferation of background Bash tool calls in the primary skill entrypoints).

Wiring: Makefile targets `test-lint-foreground-markers` and `lint-foreground-markers`, one `test-harnesses-16` shard entry, pre-commit hook `lint-foreground-markers`, and `agent-lint.toml` exclusions mirroring the `lint-bash32` Makefile-only pattern. Primary normative contract: `scripts/lint-foreground-markers.md`.
