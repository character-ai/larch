## Proposed Design Outline

### Goals
- Delegate Step 2b plan drafting to a strong-model subprocess (default `claude-fable-5`) via a new write-capable launcher, keeping orchestrator context free of codebase research reads.
- Route always-on Claude voter model through `LARCH_VOTER_MODEL` (default `claude-fable-5`) in `launch-claude-review.sh`, covering both `/design` and `/review`.
- Fix two stale `--model claude-opus-4-7` fallback-reviewer pins and update `voting-protocol.md` prose to match.

### Non-goals
- No changes to external reviewer panels (Cursor/Codex remain primary reviewers).
- No upgrade of fallback reviewer slots beyond the required `claude-sonnet-4-6` fix.
- No changes to `/implement` orchestration, code-review flow, or skill dispatch logic beyond voter model default.

### Approach sketch
- Create `scripts/launch-claude-drafter.sh` (new): write-capable subprocess launcher using `--allowedTools "Read,Write,Edit"` and `--add-dir` for session dir and repo root; handles `.done` sentinel, token accounting, timing, same patterns as `launch-claude-subprocess.sh`.
- Update `skills/design/SKILL.md` Step 2b: add pre-draft block that generates prompt, launches drafter, waits for `.done`, checks `plan.txt`, presents summary/full via existing threshold logic; falls back to inline drafting on failure.
- Update `scripts/launch-claude-review.sh`: after arg parsing, when `ROLE=voter` and `MODEL=""`, set `MODEL="${LARCH_VOTER_MODEL:-claude-fable-5}"`.
- Update `skills/design/scripts/dispatch-plan-review-panel.sh` and `decompose-panel-dispatch.sh`: one-line model change each (`claude-opus-4-7` → `claude-sonnet-4-6`).
- Update `skills/shared/voting-protocol.md` Voter 1 code-review line to reflect Fable via `LARCH_VOTER_MODEL`.
- Add `LARCH_DESIGN_PLAN_MODEL` and `LARCH_VOTER_MODEL` docs to `docs/configuration-and-permissions.md`.

### Surfaces in scope
- `scripts/launch-claude-drafter.sh` (new)
- `skills/design/SKILL.md` (Step 2b block)
- `scripts/launch-claude-review.sh`
- `skills/design/scripts/dispatch-plan-review-panel.sh`
- `skills/design/scripts/decompose-panel-dispatch.sh`
- `skills/shared/voting-protocol.md`
- `docs/configuration-and-permissions.md`

### Open questions
- None.
