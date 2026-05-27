# scripts/generate-cursor-implementer.sh — contract

`scripts/generate-cursor-implementer.sh` regenerates `agents/cursor-implementer.md` from the shared implementer body in `agents/_implementer-base.md` plus Cursor-specific frontmatter, intro prose, sandbox note, and token substitutions. Default mode rewrites the agent file in place; `--check` exits non-zero if the committed file would drift from generator output.

Determinism is load-bearing: `LC_ALL=C`, no timestamps, no git state, and hard-coded substitutions for `TOOL_MODIFIED_HISTORY` and `TOOL_COMMIT_STDERR`. Enforcement comes from `scripts/check-generators.sh`, which dispatches every row in `scripts/generators.tsv` in `--check` mode. Edit `agents/_implementer-base.md` for shared prompt changes and rerun this generator in the same PR.

- Strips Hard guard #9 from the Cursor artifact via `sed -e '/^9\. \*\*NEVER spawn or maintain persistent interactive subprocess sessions\.\*\*/,/^$/d'` so the Cursor implementer does not inherit Codex-specific subprocess-tool prohibitions (issue #2991). `agents/cursor-implementer.md` ends with rule #8; pin is asserted in `skills/implement/scripts/test-cursor-implementer.sh`.
