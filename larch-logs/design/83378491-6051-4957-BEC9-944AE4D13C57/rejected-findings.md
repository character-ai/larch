### [Plan Review] FINDING_11

### FINDING_11: Clean-run transcript call-count acceptance not wired into automated validation
**Reviewers**: Codex-Requirements (1)
**Severity**: important / risk-integration
**Concern**: Acceptance bullet #8 requires an `/implement <issue>` clean-run transcript showing ~6 fewer mid-run Bash calls vs. baseline. The plan only wires unit/structural harnesses + `make lint`; the call-count reduction can land unproven. The structural test pivots check call-site counts but not transcript-level Bash invocations.
**Proposed resolution**: Add an explicit validation step in the plan: either (a) a fixture-based transcript test that asserts the expected `Bash(` call-count delta, OR (b) document that the verification is operator-driven (manual `/implement` run against a small fixture issue, with a recorded baseline). If (b), explicitly capture the baseline measurement in the PR description.


### [Plan Review] FINDING_13

### FINDING_13: PHANTOM_APPEND_WARN_ERROR newline sanitization missing
**Reviewers**: Cursor-Requirements (1)
**Severity**: latent / security
**Concern**: Plan binds `PHANTOM_APPEND_WARN_ERROR` to captured stderr (or stdout under FINDING_1's correction). Multi-line or crafted error output could embed literal newlines into the `emit_kv` line and break token-aware KV parsing or log consumers downstream. `rebase-push.sh` already newline-folds `REBASE_OUTPUT` before emit for the same reason.
**Proposed resolution**: Single-line sanitize the captured `append-execution-issue.sh` error text (fold/strip newlines, e.g., `tr '\n' ' '`) before `emit_kv PHANTOM_APPEND_WARN_ERROR …` in `lib-phantom-probe.sh`. Document the sanitization in the sibling `.md`.


### [Plan Review] FINDING_14

### FINDING_14: Nested subprocess emit_kv lines may interleave with wrapper terminal KVs
**Reviewers**: Cursor-Innovation (1)
**Severity**: latent / architecture
**Concern**: The wrapper invokes `check-phantom-dirty.sh` and `append-execution-issue.sh` as subprocesses (or library function calls that themselves spawn subprocesses). These children inherit FD3 (the quiet contract stream); their `emit_kv` lines (e.g., `APPENDED=true`, `LOG=…`, `FAILED=true`) can interleave before the wrapper's own terminal KV block. The orchestrator's token-aware scan already tolerates this for known keys, but new unknown keys would surface in `/implement`'s parsing.
**Proposed resolution**: Either (a) extend the plan or SKILL pointer to require token-aware scan and ignore unknown keys (existing behavior), OR (b) document the allowed set of interleaved keys (`APPENDED`, `LOG`, `FAILED`, `ERROR`) so future helper additions don't silently expand the KV surface. Acceptance test: harness case asserting that wrapper's own terminal KVs survive a stub child that emits extra interleaved keys.


### [Plan Review] FINDING_15

### FINDING_15: New Makefile recipes don't use harness-timer.sh wrapper (consistency nit)
**Reviewers**: Cursor-Arch (1)
**Severity**: nit / code-quality
**Concern**: Peer `test-implement-rebase-macro` target uses `bash scripts/harness-timer.sh $@ bash scripts/test-implement-rebase-macro.sh`. The plan's new recipes use bare `bash scripts/test-*.sh`. Inconsistent timing harness and slightly weaker local dev parity.
**Proposed resolution**: Wrap the new test targets with `bash scripts/harness-timer.sh $@ bash scripts/...` like the existing peer targets do.


### [Plan Review] FINDING_17

### FINDING_17: Combined harness should include explicit STATUS=tracked-only case
**Reviewers**: Cursor-Requirements (1)
**Severity**: nit / code-quality
**Concern**: `test-rebase-checkpoint-probe.sh` enumerates phantom STATUS variants `clean`, `phantom`, `unknown`, but not `tracked-only`. The standalone harness has it explicitly. `check-phantom-dirty.sh` emits `STATUS=tracked-only` as a real production branch (when there are dirty files but none are new since the baseline). The combined wrapper also hits this branch in production.
**Proposed resolution**: Add an explicit `STATUS=tracked-only` case to `test-rebase-checkpoint-probe.sh` (between cases 10 and 11), OR document the omission with a sentence explaining that the combined harness defers tracked-only coverage to the standalone harness.


### [Plan Review] FINDING_18

### FINDING_18: DENYLIST insertion order — "phantom" comes before "rebase" alphabetically
**Reviewers**: Cursor-Innovation (1)
**Severity**: nit / code-quality
**Concern**: The plan describes the new DENYLIST entries as "in alphabetical-ish order following existing precedent" and lists `rebase-checkpoint-probe.sh` before `phantom-probe-with-warn.sh`. Alphabetically, `p` < `r` — `phantom-probe-with-warn.sh` should come first.
**Proposed resolution**: Either insert `phantom-probe-with-warn.sh` before `rebase-checkpoint-probe.sh` in the DENYLIST heredoc, or drop the "alphabetical-ish" claim from the plan prose.


### [Plan Review] FINDING_19

### FINDING_19: Plan's Region 1 SKILL.md example has nested bash fence (markdown corruption risk)
**Reviewers**: Cursor-Pragmatic (1)
**Severity**: nit / code-quality
**Concern**: The plan's Region 1 SKILL.md sample shows a fenced code block (markdown ```) inside another fenced markdown block. If an implementer copies the plan literally into SKILL.md, the nested fence terminator closes the outer fence prematurely and corrupts the markdown structure of `skills/implement/SKILL.md`. This is a plan-artifact concern, not runtime code, but it would surface as a bad PR diff.
**Proposed resolution**: Reformat the Region 1 example to use a single clean fence (banner line + per-anchor comment line + one `\`\`\`bash` open + invocation + one `\`\`\`` close) without nesting. Provide each of the 4 call-site fences as separate non-nested examples in the plan.


