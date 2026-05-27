## Decision 1: Visibility target
- **Question**: Should the fix make the entire `larch:final-summary` / `larch:run-summary` block visible at top chat, or only the `- **Cost**:` line?
- **Resolution**: Full structured block at top chat (without requiring manual Bash-output expansion). Requires relaxing the current anti-halt rule or adding a verbatim-only sentinel mechanism.
- **Source**: user (Step 1c)

## Decision 2: Parent linkage to #2837
- **Question**: How should this issue relate to the closed parent #2837 (whose PR #2836 merged earlier today and listed ROOT CAUSE G — the chat-collapse path — but did not fully resolve it)?
- **Resolution**: Follow-up issue building on #2837. The renderer infrastructure from #2837 stays unchanged; the new fix is the channel-of-emission change.
- **Source**: user (Step 1c)

## Decision 3: Skill coverage (in-scope)
- **Question**: Which skills require the fix?
- **Resolution**: Both `/design` and `/implement` are in-scope (per issue title and body). Other skills that use the `LARCH_QUIET_PID = $$` pattern for non-summary purposes (e.g., `/research validate-citations.sh`, `/report-tokens run-analysis.sh`, `/upgrade-larch`, `/alias`) are out-of-scope — they do not produce end-of-run summary blocks that operators read at top chat.
- **Source**: codebase (grep of `LARCH_QUIET_PID` users; only `render-final-summary.sh`, `write-final-report.sh`, and the shared `render-run-summary.sh` produce user-perceived end-of-run summaries)

## Decision 4: Out-of-scope (binding)
- **Question**: What is explicitly NOT in scope per the issue body?
- **Resolution**: (1) Do NOT change the rigid template body — per-agent cost breakdown and bullet shape stay. (2) Do NOT change the GitHub issue comment upsert path — already works. (3) Do NOT change the committed `larch-logs/.../final-summary.md` file path — already works. The fix scope is strictly the "surface the block at top chat level" gap.
- **Source**: issue body

## Decision 5: Hard constraints (must preserve)
- **Question**: What existing behavior must NOT break?
- **Resolution**: (1) The per-agent cost breakdown invariant from #2837 must be preserved (`Claude $X, Codex $X, Cursor $X` in `- **Cost**:` line; no TOTAL-only paraphrase). (2) Sinks 2-4 (disk file, committed log, GitHub comment) must still receive the full block exactly as today. (3) The Bash-tool result UI element must still contain the full block (sink 1) — the fix only adds a top-chat surfacing channel, it does not redirect away from stdout.
- **Source**: codebase (`#2837` plan), issue body

## Decision 6: Affected SKILL.md prose locations
- **Question**: Which SKILL.md anti-halt rules need updating?
- **Resolution**: Both anti-halt rules: `skills/design/SKILL.md` Step 5c item 9 / continuation reminder, and `skills/implement/SKILL.md` Step 17 / NEVER #20. Both currently forbid free-form re-emission of the block; the fix must permit a verbatim-only emission mechanism (the exact mechanism is decided in the sketch phase).
- **Source**: codebase (grep of "free-form natural-language recap summary" in both SKILL.md files)
