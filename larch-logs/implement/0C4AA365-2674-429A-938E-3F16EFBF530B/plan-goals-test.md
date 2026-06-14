## Goal
Implement issue #4070: [IMPLEMENTING] /design Step 3: two-phase MainAgent vote/re-tally wrapper.

## Implementation Plan
## Plan

## Approach

- Add `design-step3-mav.sh` with two phases:
  - `--phase pre`: source the design env, run the canonical pause gate before MAV work, read Step 3 result state through the standardized safe result-env reader, preserve and render the redacted scope anchor when present, and emit trusted wrapper KVs in a machine-only section.
  - `--phase post`: source the design env, run the canonical pause gate before MAV work, snapshot loop mode, artifact round, resume round, and anchor before re-tally or persistence, run the canonical MainAgent re-tally, persist result envs, append the 0-judge warning for both `ok` and handled `tally-error`, record deferred timing for successful `ok`, route the round phase only on successful re-tally in loop mode, and emit normalized KVs.
- Use the same pause contract as existing design wrappers.
- Use a standardized Step 3 result-env read contract via `scripts/read-result-env.sh`.
- Keep the judgment step in prose: LLM reads pre-phase evidence and ballot as untrusted data, writes `voter-main-agent.txt`.
- Keep Step 3 resume semantics unchanged.
- Do not change `persist-retally-step3-env.sh`, `tally-plan-review.sh`, `record-plan-review-round-timing.sh`, or `design-pause-save.sh`.

## Files to modify/create

### NEW: skills/design/scripts/design-step3-mav.sh

Launcher-owned wrapper with `--phase pre|post`. Accepts standard wrapper args (`--session-env-path`, `--claude-pid`, `--plugin-root`, `--phase pre|post`). Sources session env; requires `DESIGN_TMPDIR`; implements canonical pause gate; uses `read-result-env.sh` for safe Step 3 result-env reading with primary `.step3-review-result.env` and secondary `.step3-plan-review-result.env`. Pre phase renders scope anchor via `render-main-agent-scope-anchor.sh`, prefixes evidence lines, emits trusted KVs in `DESIGN_STEP3_MAV_KV` sentinels. Post phase snapshots loop mode, resume round, artifact round, and anchor before tally; runs `tally-plan-review.sh --voter MainAgent:voter-main-agent.txt`; calls `persist-retally-step3-env.sh`; appends idempotent 0-judge warning; records deferred timing; routes phase file in loop mode only.

### NEW: skills/design/scripts/design-step3-mav.md

Sibling contract documenting the two-phase interface, pause gate, safe result-env reading, trusted KV sentinels, pre-failure abort contract, post tally-error routing, loop-mode detection, and output KVs.

### NEW: skills/design/scripts/test-design-step3-mav.sh

Offline harness covering: canonical pause gate (including exec verification and missing ISSUE_NUMBER), standardized result-env reading (primary precedence, secondary absent-key fill, session-env fallback, symlink rejection), pre-phase (BALLOT_PATH in trusted section, file-first anchor, evidence line prefixing, renderer failure propagation), post-phase success with one accepted finding, zero-accepted loop routing (awaiting-continuation), tally-error routing (byte-compatible env and phase content), readable-malformed voter preservation, legacy single-mode preservation (absent STEP3_REVIEW_LOOP_STATUS), round precedence, and prose regression checks (SKILL.md and plan-review.md no longer contain inline MAV mechanics).

### NEW: skills/design/scripts/test-design-step3-mav.md

Harness contract documenting all test cases.

### UPDATED: skills/design/SKILL.md

Add `design-step3-mav.sh`, `design-step3-mav.md`, and test harness paths to wrapper contract inventory. Replace the long `main-agent-vote-required` mechanical paragraph with: (1) preserve the `TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required` branch; (2) call `design-step3-mav.sh --phase pre`; (3) abort MAV branch on pre failure; (4) parse trusted KVs only from `DESIGN_STEP3_MAV_KV` section; (5) abort if `BALLOT_PATH` missing; (6) LLM reads ballot, applies voting and OOS rubrics, writes `voter-main-agent.txt`; (7) call `design-step3-mav.sh --phase post`; (8) abort on post exit 2; (9) parse `TALLY_PLAN_REVIEW_STATUS`, `ACCEPTED_COUNT`, `PHASE`, `STEP3_RESUME_ROUND`; (10) on `tally-error`, run `design-step3-gate-b-bypass.sh` and route to Step 3b; (11) in loop mode after successful post, resume via Step 3 resume fence; (12) in legacy single mode, continue to Gate B. Update `STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required` post-loop branch matrix to delegate env refresh and phase routing to post phase. Update global tally-error short-circuit to cover MAV post `TALLY_PLAN_REVIEW_STATUS=tally-error` with `LOOP_STATUS=complete`.

### UPDATED: skills/design/references/plan-review.md

Update `Deferred main-agent adjudication` section to replace normative inline mechanics with wrapper delegation (`design-step3-mav.sh --phase pre/post`). Remove `_RETALLY_SCOPE_ANCHOR_IN` prompt-side binding, direct `render-main-agent-scope-anchor.sh`, direct `tally-plan-review.sh`, direct `persist-retally-step3-env.sh`, prompt-side timing with raw `date +%s`, direct `record-plan-review-round-timing.sh`. Preserve all voting rubric, OOS rubric, scope-anchor evidence framing, and judgment guidance. Document handled `tally-error` routing consistently with `SKILL.md`.

### UPDATED: skills/design/scripts/test-step3-orchestrator-fence.sh

Repoint MAV fence assertions to require `design-step3-mav.sh --phase pre/post` and `DESIGN_STEP3_MAV_KV` sentinel parsing. Assert SKILL.md and plan-review.md no longer contain inline prompt-composed MAV commands.

### UPDATED: Makefile

Add `test-design-step3-mav` to `.PHONY` and `test-harnesses-7`. Add target: `python3 python/cli.py timing harness-mark --label $@ -- bash skills/design/scripts/test-design-step3-mav.sh`.

### UPDATED: scripts/relevant-checks.sh

Map `design-step3-mav.sh`, `.md`, `test-design-step3-mav.sh`, `.md`, `plan-review.md`, and `test-step3-orchestrator-fence.sh` to `test-design-step3-mav`.

## Edge cases

- Pause requested: wrapper execs canonical pause-save before any MAV phase work.
- Pre failure: SKILL.md aborts before ballot read, voter write, post, resume, or Gate B.
- Anchor outside tmpdir or symlinked: renderer rejects it; wrapper surfaces failure.
- Anchor contains KV-looking text: evidence lines are prefixed so `BALLOT_PATH=/tmp/evil` cannot spoof parsing.
- Post-persist env rewrite: post uses pre-persist snapshots for loop mode and resume round.
- Missing or unreadable voter file: handled `tally-error`, persists cleanup, appends idempotent warning, exits 0.
- Tally error: persists `tally-error`, omits stale scope anchor, routes to Step 3b via `design-step3-gate-b-bypass.sh`.
- Zero accepted in loop mode: writes `.step3-round-N.phase` as `awaiting-continuation`.
- Legacy single mode: does not create phase file, emits `PHASE=unchanged`.
- Tally-error retry: warning append is idempotent per artifact round.

## Failure modes

- Wrapper unsafe-sources Step 3 result envs: use `read-result-env.sh` to prevent.
- Post reads loop mode after `persist-retally-step3-env.sh`: pre-persist snapshot prevents.
- SKILL.md keys tally-error only from `LOOP_STATUS=tally-error`: post emits `LOOP_STATUS=complete`; must branch on `TALLY_PLAN_REVIEW_STATUS=tally-error`.
- Phase routing writes wrong round: harness covers `ROUND_NUM` vs `ROUNDS_COMPLETED` precedence.
- Reference docs reintroduce inline MAV mechanics: prose checks in harness protect both SKILL.md and plan-review.md.

## Testing strategy

- `make test-design-step3-mav` (new focused harness)
- `make test-harnesses-7` (aggregate shard including new harness)
- `make test-persist-retally-step3-env`, `make test-tally-plan-review`, `make test-run-step3-review`, `make test-review-design-step3-loop`, `make test-step3-orchestrator-fence`, `make test-design-structure`, `make test-design-pause-resume`
- `bash scripts/relevant-checks.sh`
- `make lint`

## Acceptance

- MainAgent adjudication is two Bash calls (`design-step3-mav.sh --phase pre` and `--phase post`) plus the resume fence; no raw `date +%s` or prompt-composed re-tally argv remains in SKILL.md or plan-review.md prose.
- `test-design-step3-mav.sh` covers `tally-error` and zero-accepted phase routing; byte-compatible env and phase file assertions pass.
- `test-step3-orchestrator-fence.sh` asserts neither SKILL.md nor plan-review.md contains inline prompt-composed MAV commands.

diff_lines: 980

## Test plan
(no test plan section in plan-file)
