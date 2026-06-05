## Decision 1: Fix breadth / scope
- **Question**: How broad should the fix be — minimal /implement call-site change, also harden the gate script, also audit other skills?
- **Resolution**: Broadest scope. (a) /implement call-site rehydration of the four presence keys from the durable session-env file; (b) harden `degraded-tools-gate.sh` to detect empty/unset presence (distinct from explicit `false`) and emit a loud diagnostic; (c) audit `/design`, `/research`, `/review` degraded-gate call sites for the same ambient-shell-state reliance and fix any that share the pattern.
- **Source**: user

## Decision 2: Regression guard location
- **Question**: Where should the regression assertion (that the /implement degraded-gate block reads presence keys from session-env.sh, not ambient scope) live?
- **Resolution**: `skills/implement/scripts/test-implement-structure.sh` — this is a structural SKILL.md grep assertion and that harness already owns /implement SKILL.md structural/content pins. (Not `test-implement-bootstrap.sh`, which tests bootstrap script behavior.)
- **Source**: user

## Decision 3: Cross-skill audit result (which skills actually share the bug)
- **Question**: Of /implement, /design, /research, /review, which degraded-gate call sites actually rely on ambient shell state across a fresh Bash tool call?
- **Resolution**: `/implement` — CONFIRMED: gate runs in a separate Bash block from the Step 0 bootstrap; bootstrap stdout (`_inv_out`) is gone in the gate block, so `--codex-present` etc. resolve empty. `/design` — BORDERLINE: gate is a separate procedure from the Step 0a session-setup parse, so a fresh-block run would also lose ambient `$CODEX_PRESENT`; mitigated because `write-design-current-env.sh` persists the keys to `source-env.sh` and the prelude sources them, but the SKILL.md prose ("from the session-setup parse above") is inconsistent with the canonical "re-parse in current block" guidance and should be hardened to read from the durable sourced env explicitly. `/research` and `/review` — SAFE: both invoke the gate "in this Step 0 block" (same Bash block as session-setup), so re-parsing session-setup stdout in-block works.
- **Source**: codebase (skills/implement/SKILL.md:332, skills/design/SKILL.md:313, skills/research/SKILL.md:139, skills/review/SKILL.md:29, scripts/write-design-current-env.sh:214-219, skills/shared/external-reviewers.md §Degraded-tools gate)

## Decision 4: Durable rehydration source and helper
- **Question**: What is the canonical durable source for the four presence keys and how is it read?
- **Resolution**: `/implement` reads from `$IMPLEMENT_TMPDIR/session-env.sh` (written by `write-session-env.sh:198-207`) via `scripts/read-session-env-key.sh` with `--default false` — the same pattern `implement-bootstrap.sh` itself already uses (lines 572, 713) and the same pattern the resume block uses for LARCH_* keys (SKILL.md:346-349). `/design` reads from the prelude-sourced `source-env.sh` / `current-design-env-$PPID.sh` (written by `write-design-current-env.sh`).
- **Source**: codebase

## Decision 5: Hard constraints — what must NOT break
- **Question**: What existing behavior must be preserved?
- **Resolution**: (1) `degraded-tools-gate.sh` stays a PURE DETECTOR — it never prompts/blocks; exit 0 on valid argv, exit 2 on argv error only. (2) DEGRADED / BOTH_DOWN / CODEX_STATE / CURSOR_STATE outputs for VALID (non-empty) inputs are byte-for-byte unchanged — the hardening only adds a loud diagnostic + (optionally) a new KV for the empty-input case; it must NOT alter classification for legitimate `present=false`. (3) Fail-safe polarity is preserved: empty/unset presence still resolves toward "down" so the gate errs toward prompting, never toward a silent auto-proceed. (4) Callers that already pass explicit valid flags (`/research`, `/review`) keep working unchanged. (5) The `*_SET` omitted-flag WARNING behavior (lines 59-70) is preserved.
- **Source**: codebase + scripts/degraded-tools-gate.md contract

## Decision 6: Gate-hardening behavior
- **Question**: What exactly does "harden the gate on empty/unset presence" do?
- **Resolution**: When a `--codex-present` / `--cursor-present` value resolves empty (passed empty OR unset with empty env) — distinct from the existing omitted-flag warning — emit a loud `larch_err` diagnostic naming the empty input(s), so operators can distinguish "tool genuinely down" from "caller passed empty inputs (rehydration bug)". Surface an additional machine-readable KV (e.g. `PRESENCE_INPUT_EMPTY=true`) so a structural/behavioral test can assert it. DEGRADED computation unchanged (empty still resolves to a down-state via fail-safe). Exact KV name/shape to be finalized in the plan and refined by review.
- **Source**: codebase + reasoned (binding architecture deferred to plan review)
