## Goal
Remove dead test cases, stale Makefile .PHONY tokens, and stale doc references left over from skill/script removals

## Implementation Plan
## Plan

### Affected files (exhaustive)

- `scripts/render-run-summary.sh` (3 line edits: 2, 26, 87)
- `scripts/render-run-summary.md` (2 line edits: 4, 12)
- `scripts/test-render-run-summary.sh` (2 line edits at 120 + 123 — replace `fix-issue` with `implement` in the "stderr envelope pins" test case argv)
- `Makefile` (single line 4 — remove 10 tokens from the omnibus `.PHONY:` declaration)
- `.claude/skills/audit-runs/SKILL.md` (2 prose edits at lines 53 and 107)
- `skills/design/references/sketch-prompts.md` (1 prose edit at line 11)
- `scripts/agent-model-args.sh` (1 comment edit at line 28)
- `scripts/run-external-agent.md` (1 prose edit at line 78)
- `scripts/eval-research.sh` (1 comment edit at line 498)

### Sequenced steps

1. **Class A — `render-run-summary.sh` + sibling `.md`**: drop the `fix-issue` enum value and its usage / header / `case` mentions. Edits at the exact lines listed above. The script's only live caller (`skills/implement/scripts/write-final-report.sh`) is unaffected because it never passes `--skill fix-issue`.

2. **Class A — `test-render-run-summary.sh` argv rewrite**: in the "stderr envelope pins" block (currently lines 116–141), change `--skill fix-issue` → `--skill implement` and `--mode '/fix-issue'` → `--mode '/implement'`. Leave the surrounding `STATUS=ok` / `OUTPUT_FILE=` assertions unchanged. Run `bash scripts/test-render-run-summary.sh` to confirm green.

3. **Class B — `Makefile` `.PHONY` cleanup**: edit line 4. Remove these 10 whitespace-separated tokens (preserving the surrounding tokens and their spacing): `test-issue-lifecycle`, `test-fix-issue-bail-detection`, `test-fix-issue-step-order`, `test-find-lock-issue`, `test-design-manifest`, `test-classify-issue`, `test-post-design-boundary`, `test-implement-post-design-boundary`, `test-fix-issue-write-final-report`, `test-persist-post-plan-keys`. Run `make -n test-harnesses` afterwards to confirm no stale targets are referenced.

4. **Class C — `.claude/skills/audit-runs/SKILL.md` line 53**: rewrite the `**Operator parity with \`/fix-issue\` on \`main\`**` clause as `**Operator parity with run-log audit-title hygiene on \`main\`**` and drop the `\`find-lock-issue.sh\`` script name; keep the substantive content about `scripts/check-main-sync.sh` and `SYNC_STATUS=probe-error` unchanged. Replace the `find-lock-issue.sh` reference with prose like "the same `[Run Logs Audit … Report]` title regex used by the audit-report writer." Preserve all other prose, including the lead `**Adding a scan** requires coordinated updates: …` block.

5. **Class C — `.claude/skills/audit-runs/SKILL.md` line 107**: rewrite `(same shape as \`find-lock-issue.sh\` \`has_report_prefix\` for run-logs audit titles)` as `(same \`^\[Run Logs Audit .* Report\]\` title-prefix shape used elsewhere in the audit-runs workflow)`.

6. **Class C — `skills/design/references/sketch-prompts.md` line 11**: replace `\`launch-cursor-review.sh\` uses Cursor max-mode and its high-risk prompt suffix when \`--risk high\`; \`launch-codex-review.sh\` passes Codex effort args when \`--risk high\`` with `\`scripts/launch-review.sh --tool cursor\` uses Cursor max-mode and its high-risk prompt suffix when \`--risk high\`; \`scripts/launch-review.sh --tool codex\` passes Codex effort args when \`--risk high\``.

7. **Class C — `scripts/agent-model-args.sh` line 28**: change the comment from `# use cursor-wrap-prompt.sh for max-mode, and launch-cursor-review.sh owns its` to `# use cursor-wrap-prompt.sh for max-mode, and launch-review.sh --tool cursor owns its`. The surrounding comment block (lines 26–29) keeps its meaning.

8. **Class C — `scripts/run-external-agent.md` line 78**: remove the substring `\`scripts/launch-gemini-implement.sh\`, ` from the comma-separated list of production entry points. Leave the remaining tokens (`launch-review.sh`, `launch-cursor-implement.sh`, `launch-codex-implement.sh`, `launch-cursor-ci.sh`, `launch-codex-ci.sh`, `dispatch-plan-voters.sh`, `review-and-fix.sh`) and their order unchanged.

9. **Class C — `scripts/eval-research.sh` line 498**: rewrite the comment `# scripts/parse-skill-judge-grade.sh: any malformed input yields a single` as `# the fail-closed parser discipline below: any malformed input yields a single` (drop the dangling reference to the deleted script; the next two comment lines describing the `JUDGE_STATUS=parse_failed` envelope already carry the substantive content).

10. **Validation pass**: run `bash scripts/relevant-checks.sh` (covers shellcheck, markdownlint, agent-lint, and the relevant test harnesses) plus `make test-render-run-summary` and `make test-harness-shards-coverage`. No new test scripts are added; no test is removed.

### Breaking changes / migration

- `scripts/render-run-summary.sh` no longer accepts `--skill fix-issue`. Anyone passing it would already be a no-op caller (the only live caller passes `--skill implement`), but any future external script that wanted that value will now get the canonical `Usage: ... --skill implement ...` error and exit `2`. This is the intended behavior; the value was already dead post `/fix-issue` removal in `e44e0568`.
- No other breaking surface: the 10 `.PHONY` deletions remove stale tokens that had no rule body (so any `make <stale-name>` already failed with `No rule to make target`); the 5 prose edits are documentation-only.

### Decisions closed

- `render-run-summary.sh` `fix-issue` branch handling: **delete entirely** (not preserved behind a flag, not aliased to `implement`). Rationale: the value is unreachable from live callers and was always a thin synonym; an alias would be added complexity for no consumer.
- `audit-runs/SKILL.md` rewrites: **keep the operator-facing audit-title hygiene content; drop only the `/fix-issue` / `find-lock-issue.sh` framing**. Rationale: the substantive contract (audit-title regex shape, `check-main-sync.sh` pre-lock probe) is still live and useful.
- Renamed launcher references in sketch-prompts.md and agent-model-args.sh: **use `launch-review.sh --tool <name>`** (the current `a3175126`-consolidated form) rather than just `launch-review.sh`. Rationale: the comments are about specific tool-specific behavior, so retaining the `--tool` qualifier preserves the diagnostic precision.
- No new test files. The single test case rewrite in `test-render-run-summary.sh` keeps the same assertions and coverage; no behavior is left untested.

## Acceptance

- `make test-render-run-summary` passes (in particular, the "stderr envelope pins" test case is exercised with `--skill implement` and still asserts `STATUS=ok` + `OUTPUT_FILE=`).
- `grep -nE 'fix-issue' scripts/render-run-summary.sh scripts/render-run-summary.md scripts/test-render-run-summary.sh` returns **zero hits** after the change.
- For each of the 10 stale tokens, `grep -E "^\\.PHONY:" Makefile | grep -wF "<token>"` returns no match.
- `python3 -c '...'` set-difference (declared `.PHONY` minus actual rule names) returns the empty set (the audit script from this issue's investigation reproduces this; embedded inline in the PR description if needed).
- `grep -nE 'launch-cursor-review|launch-codex-review|launch-gemini-implement|parse-skill-judge-grade|find-lock-issue\.sh' skills/design/references/sketch-prompts.md scripts/agent-model-args.sh scripts/run-external-agent.md scripts/eval-research.sh .claude/skills/audit-runs/SKILL.md` returns **zero hits** after the change.
- `bash scripts/relevant-checks.sh` exits `0` (covers shellcheck, markdownlint, agent-lint, applicable harnesses).
- `make test-harness-shards-coverage` still passes (the test-harnesses shard balance is not perturbed because none of the affected `.PHONY` tokens point at rules listed in any `test-harnesses-N` shard).
- No new files created. Touched files: exactly the 9 listed under "Affected files" above.
- `git grep -F '/fix-issue' -- ':!CHANGELOG.md' ':!larch-logs/'` returns hits only inside negative-pin regression assertions (e.g., `scripts/test-implement-structure.sh` line 331 / `scripts/test-review-structure.sh` line 391 / `.claude/skills/audit-runs/scripts/test-audit-runs.sh`'s `--no-fix-issues` negative-pin block) — these are legitimate "must not return" guards and remain intact.

## Test plan
(no test plan section in plan-file)
