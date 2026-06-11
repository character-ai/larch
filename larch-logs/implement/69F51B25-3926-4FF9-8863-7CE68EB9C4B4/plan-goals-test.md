## Goal
Implement issue #4010: [IMPLEMENTING] /implement: drop vestigial runtime reference loads and dead SKILL.md text\n\n**Problem.** The `/implement` happy path loads reference files it no longer needs and carries dead prose in `skills/implement/SKILL.md`. Each vestigial load costs one tool call plus permanent context in every run..

## Implementation Plan
## Plan

## Plan

## Approach

Use direct codebase inspection. `approach-synthesis.txt` is `NO_SKETCHES_CLASSIFIED_SIMPLE`, so do not claim sketch agreement. `dialectic-resolutions.md` is empty, so synthesis stands. Apply the approved scope and accepted reviewer finding.

Keep behavior stable. Change only prompt load rules, the rebase probe KV contract, related harness coverage, bounded materiality wording, and dead-text cleanup.

## Files to modify/create

### UPDATED: skills/implement/SKILL.md

- Replace the Rebase Checkpoint Macro unconditional load rule:
  - Remove the unconditional MANDATORY read of `skills/implement/references/rebase-checkpoint-routing.md`.
  - Require the routing reference when the probe process rc is non-zero, regardless of `ROUTE`.
  - Require the routing reference when process rc is `0` and `ROUTE` is `conflict` or `bail`.
  - Require the routing reference when `ROUTE` is missing or malformed.
  - Skip it only when process rc is `0` and `ROUTE=continue`.
  - Do not use `REBASE_OUTCOME` as a substitute for the `ROUTE` skip predicate.
  - Preserve the path string so `scripts/test-implement-structure.sh` still passes.
- Update the four checkpoint routing paragraphs for `1.r`, `4.r`, `7.r`, and `7a.r`:
  - Parse `ROUTE=continue|conflict|bail`.
  - On rc `0` with `ROUTE=continue`, continue without reading the routing reference.
  - On rc `0` with `ROUTE=conflict` or `ROUTE=bail`, read the routing reference.
  - On any non-zero rc, read the routing reference regardless of `ROUTE`.
  - If `ROUTE` is missing or malformed, read the routing reference before any fallback handling.
  - Remove stale text that mandates unconditional routing-reference reads.
  - Remove stale text that permits `REBASE_OUTCOME` parsing to skip the routing reference.
- For the Step 7a paragraph:
  - Treat `step-7a.sh` relay stdout as part of the same KV stream.
  - Clarify that any `Parse REBASE_OUTCOME first` wording means scan ordering within the combined stream, not a substitute for the process rc plus `ROUTE=continue` skip predicate.
- Demote the Step 7a `summary-comment-template.md` load:
  - Remove the MANDATORY Step 7a read.
  - State that `step-7a.sh` owns `larch:diagrams` upsert through `python3 python/cli.py diagrams upsert`.
  - Keep the Step 2.5 Q/A load unchanged.
- Replace the phantom probe MANDATORY directive:
  - Keep a non-MANDATORY pointer to `skills/implement/references/phantom-probe.md`.
  - Add: trailing `PHANTOM_*` KVs are advisory telemetry; do not act on them.
- Replace the Step 0 degraded-gate runtime pointer to `skills/shared/external-reviewers.md`:
  - Remove both Step 0 degraded-gate references to the shared file.
  - Do not leave any Step 0 runtime-load directive that names `skills/shared/external-reviewers.md`.
  - Anchor the procedure in inline SKILL.md bullets: gate script invocation, `DEGRADED` / `BOTH_DOWN` branching, sentinel handling, and prompt behavior.
  - Inline the full predicate: interactive runs may prompt only in operator-facing mode; subagents, `claude -p`, cron, eval, autonomous runs, and `<<autonomous-loop>>` runs do not prompt.
  - Preserve current degraded behavior and sentinel handling.
- Add a one-sentence body under `### Cross-Skill Presence Propagation`.
  - Use a no-op presence sentence.
  - Do not paste or move the anti-halt harness phrase into this section.
  - Preserve the existing pinned anti-halt phrase at its current required post-Step-5 site.
- Remove the dangling lines:
  - `After the helper returns clean ... close Step 3 telemetry:`
  - `After the helper returns clean ... close Step 6 telemetry:`
- Handle NEVER #13 without deleting operative guidance:
  - Do not migrate #13 content into NEVER #8.
  - Use the existing Step 8+ long-running driver recovery paragraph around `skills/implement/SKILL.md:782` as the canonical destination.
  - Before stubbing #13, verify that the Step 8+ recovery block still covers foreground-only bash re-invoke guidance, `LARCH_SHIP_PR_IMPL` selector, no `--resume-phase`, and ship-pr-state read requirements.
  - Add only missing unique guidance to that Step 8+ recovery block.
  - After parity is confirmed, compress #13 to the same one-line removed-stub shape as #2 and #10.
- Tighten Preflight item 6:
  - Replace the materiality inspection instruction with one bounded probe: a single batched Bash probe block.
  - The probe should cover plan-cited paths and existence checks such as `test -f` and targeted `rg`.
  - Drop any open-ended codebase, `CLAUDE.md`, or `AGENTS.md` read preamble before the probe.
  - Preserve the stale-notice exit-2 path unchanged.
  - Add: if the probe does not show clear staleness, continue to Step 0 without further codebase or doc reads.

### UPDATED: scripts/rebase-checkpoint-probe.sh

- Emit `ROUTE=continue` on rc `0` after `REBASE_OUTCOME=ok|skipped`.
- Emit `ROUTE=conflict` on rc `1` with `REBASE_OUTCOME=conflict`.
- Emit `ROUTE=bail` on rc `3` and on unexpected non-zero rc paths.
- Preserve all existing exit codes, `REBASE_OUTCOME`, `CONFLICT_FILES`, `REBASE_ERROR`, skip-precedence behavior, and phantom probe behavior.
- Keep phantom probing on rc `0` only.
- Do not use `ROUTE` to change script behavior. It is a prompt-routing convenience KV.

### UPDATED: scripts/rebase-checkpoint-probe.md

- Add `ROUTE=continue|conflict|bail` to the stdout KV grammar.
- Document mapping:
  - `continue`: rebase succeeded or skipped. The orchestrator may skip `rebase-checkpoint-routing.md` only when the probe process rc is `0` and `ROUTE=continue`.
  - `conflict`: rebase conflict. The orchestrator must read `rebase-checkpoint-routing.md`.
  - `bail`: non-conflict failure or unexpected rc. The orchestrator must read `rebase-checkpoint-routing.md`.
- Add explicit routing rules:
  - Any non-zero probe process rc requires reading `rebase-checkpoint-routing.md`, regardless of `ROUTE`.
  - `ROUTE=continue` is actionable only with process rc `0`.
  - Missing or malformed `ROUTE` requires reading `rebase-checkpoint-routing.md`.
  - Only rc `0` plus `ROUTE=continue` skips the read.
  - `REBASE_OUTCOME` must not bypass the process rc plus `ROUTE=continue` skip predicate.
- State that exit codes remain unchanged and authoritative.

### UPDATED: scripts/test-rebase-checkpoint-probe.sh

- Assert `ROUTE=continue` on rc `0` success paths.
- Assert `ROUTE=continue` on rc `0` skipped paths, including existing skip-precedence coverage.
- Assert `ROUTE=conflict` on rc `1`.
- Assert `ROUTE=bail` on rc `3`.
- Assert `ROUTE=bail` on unexpected non-zero rc paths.
- Preserve existing assertions for exit codes, `REBASE_OUTCOME`, `CONFLICT_FILES`, `REBASE_ERROR`, and phantom probe behavior.

## Edge cases

- `SKIPPED_ALREADY_PUSHED=true` still wins over `SKIPPED_ALREADY_FRESH=true`.
- `ROUTE=continue` must be emitted for both `REBASE_OUTCOME=ok` and `REBASE_OUTCOME=skipped`.
- `ROUTE=continue` is actionable only with process rc `0`.
- Any non-zero probe rc must force the routing-reference read, even if stdout contains `ROUTE=continue`.
- Missing or malformed `ROUTE` must force the routing-reference read before any fallback handling.
- `REBASE_OUTCOME` may inform post-read handling, but must not decide whether to skip the routing reference.
- Conflict fallback from `git diff --name-only --diff-filter=U` still works when `CONFLICT_FILES` is missing.
- Unexpected rc still re-exits with the original rc after emitting `REBASE_OUTCOME=failed`, `REBASE_ERROR=unexpected-rc-<n>`, and `ROUTE=bail`.
- Step 7a relays the probe stdout. The new `ROUTE` KV must pass through without changing `step-7a.sh` flush routing.
- `PHANTOM_*` KVs may still appear after `ROUTE=continue`. They remain telemetry only.
- Degraded-tool prompting must remain disabled for subagents, `claude -p`, cron, eval, autonomous runs, and `<<autonomous-loop>>`.
- Step 0 may still mention external reviewers as a concept, but must not require loading `skills/shared/external-reviewers.md`.
- Preflight item 6 must not allow open-ended reads before or after the bounded materiality probe.
- If the bounded materiality probe does not clearly show staleness, continue to Step 0.
- NEVER #8 must remain focused on ScheduleWakeup and Monitor bans.

## Failure modes

- If `ROUTE` is missing or malformed and the orchestrator skips the routing reference, green-path loads may be skipped incorrectly.
- If probe documentation describes skipping on rc `0` alone, it can drift from SKILL.md and allow bad green-path skips.
- If probe documentation omits the non-zero rc rule, future orchestrators may trust stale stdout over authoritative process status.
- If an orchestrator honors `ROUTE=continue` despite non-zero rc, green-path loads may be skipped incorrectly.
- If stale `REBASE_OUTCOME` routing text remains, it may bypass the required process rc plus `ROUTE=continue` predicate.
- If Step 7a treats `Parse REBASE_OUTCOME first` as a routing-reference skip rule, it may skip required conflict or bail guidance.
- If the reference path strings are removed from `SKILL.md`, structure tests fail.
- If the Cross-Skill Presence Propagation body embeds the anti-halt harness phrase, it may move or duplicate text pinned elsewhere by the harness.
- If Step 2.5 loses its `summary-comment-template.md` load, Q/A public summary text may lose its template authority.
- If either Step 0 degraded-gate sentence still points to `skills/shared/external-reviewers.md`, the happy path may still load the shared file.
- If NEVER #13 is stubbed before Step 8+ recovery parity is verified, foreground ship re-invoke behavior may regress.
- If #13 content is migrated into NEVER #8, it can corrupt the unrelated ScheduleWakeup and Monitor invariant.
- If Preflight item 6 retains open-ended inspection wording, materiality checking can exceed the intended one-tool-call budget.
- If Preflight item 6 lacks the uncertain-materiality continue path, bounded inspection may stall even when it does not clearly show staleness.

## Testing strategy

- Run targeted harnesses:
  - `make test-rebase-checkpoint-probe`
  - `make test-implement-rebase-macro`
  - `make test-implement-structure`
  - `make test-implement-anti-halt`
  - `make test-step-7a`
- Run halt-rate or anti-halt coverage:
  - `make test-anti-halt`
  - `make test-implement-relevant-checks-anti-halt`
- Run repository checks:
  - `bash scripts/relevant-checks.sh`
  - `make lint`
- Add or run targeted grep checks:
  - Confirm SKILL.md has no unconditional MANDATORY read of `skills/implement/references/rebase-checkpoint-routing.md`.
  - Confirm all four checkpoint paragraphs gate the skip on process rc `0` and `ROUTE=continue`.
  - Confirm Step 7a says `Parse REBASE_OUTCOME first` is stream scan ordering, not a routing-reference skip predicate.
  - Confirm `rebase-checkpoint-probe.md` states both skip requirements: process rc `0` and `ROUTE=continue`.
  - Confirm `rebase-checkpoint-probe.md` states any non-zero probe rc requires reading `rebase-checkpoint-routing.md`.
  - Confirm SKILL.md and probe docs state missing or malformed `ROUTE` requires reading `rebase-checkpoint-routing.md`.
  - Confirm Preflight item 6 uses a single batched Bash probe block and does not mention open-ended codebase, `CLAUDE.md`, or `AGENTS.md` reads.
  - Confirm Preflight item 6 explicitly continues to Step 0 when the probe does not show clear staleness.
  - Confirm the Step 8+ recovery block covers `LARCH_SHIP_PR_IMPL`, no `--resume-phase`, ship-pr-state read, and foreground-only bash re-invoke guidance before NEVER #13 is stubbed.
  - Confirm NEVER #8 body is not used as the ship recovery migration destination.
  - Confirm the Cross-Skill Presence Propagation body does not contain the pinned anti-halt harness phrase.
  - Confirm the existing pinned anti-halt phrase remains unchanged at its current required post-Step-5 site.

diff_added: 44
diff_deleted: 20
mechanical_churn: low
diff_lines: 64

## Acceptance

- A green-path `/implement` run mandates none of: `phantom-probe.md`, `summary-comment-template.md` (outside Step 2.5 Q/A), `rebase-checkpoint-routing.md`.
- `make lint`, the implement structure harnesses, and the halt-rate harness tokens stay green.
- `ROUTE=continue` is emitted by `rebase-checkpoint-probe.sh` on rc 0 success/skipped paths; `ROUTE=conflict` on rc 1; `ROUTE=bail` on rc 3 and unexpected rc.
- `make test-rebase-checkpoint-probe`, `make test-implement-structure`, and `make test-implement-anti-halt` pass.
- No behavior change to any gate, probe, or external reviewer invocation.

diff_lines: 64

## Test plan
(no test plan section in plan-file)
