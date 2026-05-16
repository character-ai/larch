## Goal
Purge all Gemini references from larch codebase

## Implementation Plan

### Goal
Purge all Gemini code, scripts, tests, documentation, and configuration from the larch codebase. After the purge, `git grep -in gemini` must return zero hits in tracked files (excluding larch-logs/** and CHANGELOG.md historical entries).

### Files to delete entirely

**Scripts (each .sh + sibling .md):**
- scripts/launch-gemini-implement.sh / .md
- scripts/lib-gemini-launcher-review.sh / .md
- scripts/lib-gemini-model-resolver.sh / .md
- scripts/lib-gemini-tool-drift.sh / .md
- scripts/gemini-reviewer-policy.toml
- scripts/gemini-known-tools.txt / .md
- scripts/generate-gemini-implementer.sh / .md

**Agents:**
- agents/gemini-implementer.md

**Tests:**
- skills/implement/scripts/test-gemini-implementer.sh / .md

### Files to edit (remove Gemini sections/code paths)

**scripts/agent-model-args.sh** — drop the `gemini` arm and LARCH_GEMINI_MODEL / CLAUDE_PLUGIN_OPTION_GEMINI_MODEL precedence chain; update companion .md

**scripts/lib-timing-kinds.sh** — drop `gemini-review`, `gemini-review-generic`, `gemini-implement` from timing-kinds lists

**scripts/launch-review.sh** — drop the `gemini)` case (~line 1013-1018), `--tool gemini` validation paths (lines 26, 36-37, 56, 74-78, 136), and any other gemini handling; update companion .md

**scripts/check-reviewers.sh** — drop `[[ "$tool" == "gemini" ]] && continue` (~line 264) and the no-op `--artifact-dir` flag (~line 29); update companion .md

**scripts/session-setup.sh** — drop `GEMINI_HEALTHY=false` / `GEMINI_AVAILABLE=false` emissions (lines 389-390, 439-440, 470), `--gemini-healthy false` from WSE_ARGS (~line 486), any other gemini references; update companion .md

**scripts/write-session-env.sh** — drop `--gemini-healthy` flag (lines 7, 13, 52); update companion .md

**scripts/lib-external-launcher-common.sh** — drop `gemini` from tool-case statements (~lines 43, 113); update companion .md

**scripts/collect-agent-results.sh** — drop `gemini:launch-review.sh` (~line 411) and `launch-gemini-implement.sh|gemini` (~line 413); update companion .md

**scripts/run-external-agent.sh** — drop the gemini example from the docstring; update companion .md

**scripts/token-report.sh** — drop the gemini vendor formatting branch (~line 241); update companion .md

**scripts/append-token-record.sh** — drop `gemini` from the accepted-TOOL case (~line 38); update companion .md (if exists)

**scripts/timing-report.sh** — drop gemini sort/aggregation branches (~lines 129, 185, 202); update companion .md

**scripts/timing-ledger.sh** — drop gemini timing kind references; update companion .md

**scripts/launch-cursor-implement.md** and **scripts/launch-codex-implement.md** — drop any gemini cross-references in Edit-in-sync lists

**scripts/external-tool-registry.sh / .md** — drop gemini entries

**scripts/generators.tsv** — drop gemini entries

**skills/implement/scripts/step2-implement.sh** — drop `gemini)` coder case (~lines 265-270), `--gemini-healthy` flag handling (~lines 89, 102, 176-179, 220, 224), `gemini-runtime-failure` / `gemini-bailed-no-reason` tokens; update companion .md

**skills/implement/SKILL.md** — drop every `--coder=gemini` mention, `GEMINI_HEALTHY` reference, Gemini-specific paragraphs, and references to `launch-gemini-implement.sh`

**skills/fix-issue/SKILL.md** — drop `--gemini-healthy true` from write-session-env.sh call (~line 134) and from the later write-session-env.sh call in Step 1

**skills/shared/external-reviewers.md** — drop the gemini section (GEMINI_HEALTHY=false and GEMINI_AVAILABLE=false always-unconditional paragraphs) and any other gemini paragraphs

**skills/shared/subskill-invocation.md** — drop gemini references if any

**skills/shared/voting-protocol.md** — drop gemini references if any

**skills/review/references/voting.md** — drop gemini references if any

**agents/_implementer-base.md** and **agents/cursor-implementer.md** — drop any gemini cross-references

**Docs:**
- docs/external-reviewers.md — drop gemini sections
- docs/configuration-and-permissions.md — drop gemini env vars and permissions
- docs/review-agents.md — drop gemini
- docs/skills.md — drop gemini if present
- docs/workflow-lifecycle.md — drop gemini if present
- docs/linting.md — drop gemini if present
- docs/installation-and-setup.md — drop gemini if present
- README.md — drop gemini from feature matrix, skill catalog, and prose
- SECURITY.md — drop gemini if mentioned
- AGENTS.md — drop gemini if mentioned (verify; may be meta-reference only that's fine since it's being updated in this PR)

**Rules:**
- .claude/rules/external-tool-launcher-parity.md — rewrite for two-tool parity (Codex + Cursor only), drop gemini mentions and 'dormant Gemini reviewer' language
- .claude/rules/launcher-argv-test-coverage.md — drop gemini harness path bullets
- .claude/rules/timing-task-kind-allowlist.md — drop gemini timing kind entries
- .claude/rules/verify-external-tool-invocations.md (if exists) — drop gemini if listed

**Config:**
- .claude-plugin/plugin.json — drop gemini options (CLAUDE_PLUGIN_OPTION_GEMINI_MODEL if present)
- agent-lint.toml — drop gemini exclusions or references
- .github/workflows/*.yaml — drop gemini steps or env vars

**skill topology:**
- skills/shared/topology.tsv — drop gemini rows

**Tests to edit:**
- scripts/test-launch-review.sh — delete 'Running launch-review gemini suite' block (~lines 1890-2475) and other gemini cases
- scripts/test-timing-ledger.sh — drop `--vendor gemini` test case (lines 51-54)
- scripts/test-collect-agent-retry.sh — drop LARCH_GEMINI_MODEL=test-gemini-model GEMINI_REVIEW=1 test case (~line 633) and other gemini cases
- scripts/test-collect-agent-retry.md — drop case (P3b)
- scripts/test-review-structure.sh — drop gemini 'negative pin' assertions (~lines 379-382)
- scripts/test-review-structure.md — drop 'Assertion 19' about gemini negative pins
- scripts/test-run-external-agent.sh and .md — drop gemini cases and references
- skills/implement/scripts/test-step2-dispatch.sh — drop gemini coder cases; update companion .md
- scripts/test-agent-model-args.sh and .md — drop gemini cases
- scripts/test-check-reviewers.sh and .md — drop gemini references
- scripts/test-session-setup-health-defaults.sh and .md — drop gemini references
- scripts/test-external-tool-registry.sh and .md — drop gemini entries
- scripts/test-timing-report.sh — drop gemini references
- scripts/test-cache-key-discipline.sh and .md — drop gemini if present
- scripts/test-check-generators.sh — drop gemini if present
- Makefile — drop test-gemini-implementer from test-harnesses-2 shard (~line 28), drop standalone test-gemini-implementer target

**Other skills to scan and edit:**
- skills/implement/references/codex-manifest-schema.md and .digest.md — drop gemini bail reason tokens
- skills/implement/scripts/post-design-boundary.sh and .md — drop gemini references
- skills/implement/scripts/test-post-design-boundary.sh — drop gemini if present
- skills/implement/scripts/test-step2-dispatch.md — drop gemini references
- skills/cleanup/scripts/cleanup.sh — drop gemini references
- skills/report-tokens/scripts/run-analysis.sh and .md — drop gemini vendor references
- skills/report-tokens/scripts/test-rate-assertions.sh and .md — drop gemini references
- scripts/render-specialist-prompt.sh — drop gemini if present
- scripts/read-session-env-key.md — drop gemini if mentioned
- scripts/check-step-token-budget.md — drop gemini if mentioned
- scripts/lib-dirty-tree-sidecar.md — drop gemini if present
- scripts/lib-cursor-auth.md — drop gemini if present
- scripts/lib-validate-meta-path.md — drop gemini if present
- scripts/launch-codex-ci.md — drop gemini if present
- scripts/session-setup.md — drop gemini references
- scripts/timing-ledger.md — drop gemini timing kinds
- scripts/timing-report.md — drop gemini branches
- scripts/token-report.md — drop gemini vendor branch
- scripts/external-tool-registry.md — drop gemini entries
- scripts/collect-agent-results.md — drop gemini paths
- scripts/agent-model-args.md — drop gemini arm
- scripts/write-session-env.md — drop --gemini-healthy flag

**Env vars to remove from all code paths:**
- LARCH_GEMINI_MODEL
- CLAUDE_PLUGIN_OPTION_GEMINI_MODEL
- GEMINI_REVIEW
- GEMINI_HEALTHY / GEMINI_AVAILABLE

### Testing strategy
After all edits, run:
1. git grep -in 'gemini' (excluding larch-logs/** and CHANGELOG.md) — must return zero hits
2. make lint — pre-commit, agent-lint, all test-harnesses-N shards
3. Verify no gemini-* entries in timing report output

## Test plan
(no test plan section in plan-file)
