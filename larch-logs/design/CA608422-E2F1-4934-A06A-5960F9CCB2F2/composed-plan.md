## Plan

Two independent changes batched in one issue.
- **Part 1 (docs only):** document `apiKeyHelper` removal + dual-auth Claude aliases.
- **Part 2 (behavior):** flip the default external tool to Codex-first for the coder, CI fixer, and merge-resolve fixer roles, in Bash and the Python port, with order-asserting tests and affected prose docs synced.

New order everywhere is `codex → cursor → claude` (Claude stays the terminal fallback). Explicit `--coder cursor` / `--coder codex` behavior is unchanged.

### Files to modify/create

#### UPDATED: `docs/installation-and-setup.md`
Part 1, docs only. Extend the `### Claude` subsection (the block ending right before `### Codex`) with three additions:
- A note to remove any file-level `apiKeyHelper` from `~/.claude/settings.json`, and why: larch's Claude subprocesses run `claude --print`, read `~/.claude/settings.json` directly, and do not inherit a top-level `--settings` override. In subscription/OAuth mode (no `ANTHROPIC_API_KEY` in env) the helper returns empty → `apiKeyHelper failed` → `401 Invalid bearer token`; a non-zero helper exit does not fall back to OAuth.
- The four example aliases verbatim from the issue, in one `bash` fence: `claude_api`, `opus_api`, `claude_login`, `opus_login`.
- The mechanism: subprocesses inherit the top-level session env, so billing tracks the top-level account; `*_api` → API token, `*_login` → subscription OAuth. State the credential precedence `ANTHROPIC_API_KEY` (env) > `apiKeyHelper` > stored OAuth, that a configured `apiKeyHelper` never falls back to OAuth, and that the aliases are illustrative (personal git wrappers out of scope).

No runtime/script/behavior change in this file.

#### UPDATED: `scripts/implement-bootstrap.sh`
Part 2, coder role. In `_phase_coder_implicit`, flip the implicit waterfall from cursor-first to codex-first:
- Probe `codex_available` first (`coder=codex`), then `cursor_available` (`coder=cursor`), then `claude` terminal (`coder_fallback=true`).
- Update the leading comment (currently cites #2738 / `Cursor -> Codex -> Claude`) to cite #3337 / `Codex -> Cursor -> Claude`. Keep the "Review/fix dispatchers remain Codex-first" sentence.
- Update the two `larch_err` warnings and their `_phase_coder_append_warning` strings to the new order: "Codex unavailable — falling back to Cursor implementer" and "Cursor unavailable — falling back to Claude implementer".

Do NOT touch `_phase_coder_explicit` or `_phase_coder_explicit_waterfall`: explicit `--coder` resolution is independent of the implicit default and must keep working (`--coder cursor` → cursor→codex→claude; `--coder codex` → codex→cursor→claude).

#### UPDATED: `scripts/implement-bootstrap.md`
Part 2, doc sync (also test-pinned). In the `--coder` table row, change the omitted-default clause "`phase_coder_select` runs the Cursor → Codex → Claude waterfall" to `Codex → Cursor → Claude`. Leave the explicit-coder clauses (`--coder codex` → Cursor → Claude; `--coder cursor` → Codex → Claude) unchanged — those describe explicit overrides, which do not change.

#### UPDATED: `scripts/ship-pr.sh`
Part 2, CI fixer + merge-resolve roles.
- `run_ci_fix_vendor`: change the base tuple `local tiers=(cursor codex claude) ...` to `local tiers=(codex cursor claude) ...`. Leave the `offset=$(( start_attempt % 3 ))` rotation and the `first-fixer-non-health` bail unchanged; both correctly follow the new base order (attempt 0 now starts at Codex).
- `run_recovery_waterfall`: change `for tier in cursor codex claude; do` to `for tier in codex cursor claude; do`. The per-tier `command -v` guards are unchanged.

#### UPDATED: `scripts/ship-pr.md`
Part 2, doc sync. Update the order prose to codex-first: the three-tier recovery description ("`launch-cursor-ci.sh`, then `launch-codex-ci.sh`, then `launch-claude-ci.sh`"), the "3-tier inner waterfall (Cursor → Codex → Claude, one launch per tier)" line, and the "rotates the cursor→codex→claude waterfall start tier" line. Also sync the **first-fixer / Exit 3** prose that still names Cursor as the CI-fix tier (the `first-fixer-non-health` bail description and the `run_ci_fix_vendor` special-case "first tier (`cursor`)"): reword to **rotated first tier** (Codex on `start_attempt=0` after the base-order flip; health failures still fall through to remaining tiers), aligning with the invariant "keys off the first tier of the rotated list, not the literal `cursor` tier". Grep `ship-pr.md` for `cursor`/`codex` ordering prose to catch any other references.

#### UPDATED: `skills/implement/SKILL.md`
Part 2, doc sync. Two targets:
- **`phase_coder_select` paragraph:** states the implicit order as "Cursor → Codex → Claude", which becomes wrong after the flip. Reword to reflect codex-first **without** introducing the literal arrow substring `Codex → Cursor → Claude` (use commas, e.g. "the implicit implementer waterfall — Codex, then Cursor, then Claude — arrives at Claude"). Reason: `scripts/test-implement-step2-routing.sh` asserts SKILL.md does NOT contain `Codex → Cursor → Claude` (the waterfall order stays script-side, not duplicated as prompt-side prose).
- **Exit 3 / `first-fixer-non-health` paragraph:** replace Cursor-only wording ("Cursor CI-fix launcher reported `LAUNCHER_FAILURE_CLASS=other`") with **rotated-first-tier** language — the bail fires when the first tier of the rotated CI-fix list (Codex on `start_attempt=0`) reports `LAUNCHER_FAILURE_CLASS=other`. Keep autonomous sub-procedure caps and `BAIL_NEEDS_USER_INPUT` semantics unchanged.

#### UPDATED: `SECURITY.md`
Part 2, security-doc sync (AGENTS.md convention). Two targeted edits in the External-tool-delegation / omitted-`--coder` surface:
- The `/implement` Step 0 paragraph: replace the Cursor-first narrative with Codex-first (#3337) — the omitted-`--coder` default is now Codex → Cursor → Claude by external availability; cite #3337 (supersedes the #2738 Cursor-first reversal). Keep the narrow-scope framing ("applies only when the operator omits `--coder`"), the explicit-pin guidance, review/fix lanes remain Codex-first, and all sandbox/delegation posture unchanged.
- The standalone omitted-`--coder` routing note: sync to "follows Codex → Cursor → Claude by external availability"; drop or rewrite the stale Phase 4 (#2738) paragraph that tells operators to re-pin `--coder=codex` (that guidance is inverted after this flip). Retain the informational `diff_lines` / `coder_fallback=true` sentences.

No runtime change in this file.

#### UPDATED: `docs/external-reviewers.md`
Part 2, doc sync. In the routing table, update the **CI / checks recovery** row: change `(Cursor→Codex→Claude)` to `(Codex→Cursor→Claude)` so the canonical routing table matches codex-first `ship-pr.sh` behavior. Leave other rows unchanged (review-and-fix already Codex-first; implementer row stays generic "Selection waterfall keyed on `--coder`").

#### UPDATED: `docs/linting.md`
Part 2, doc sync. In the `make test-implement-step2-routing` harness table row, change omitted-`--coder` wording from `Cursor → Codex → Claude waterfall` to `Codex → Cursor → Claude waterfall`. No Makefile change.

#### UPDATED: `python/config.py`
Part 2, Python parity. Change `FIXER_TIER_ORDER: Final[tuple[str, ...]] = ("cursor", "codex", "claude")` to `("codex", "cursor", "claude")`. No other Python code change: `ci_monitor._available_tiers()` and `rebase.py` derive their order from this tuple. Update the adjacent `# parity with ship-pr run_ci_fix_vendor` comment if it names the old order.

#### UPDATED: `python/test_config.py`
Part 2, test. Update the equality assertion to `assert config.FIXER_TIER_ORDER == ("codex", "cursor", "claude")`.

#### UPDATED: `python/test_ci_monitor.py`
Part 2, test (Python parity). `FIXER_TIER_ORDER` drives `run_ci_fix` / `evaluate_failure` / `monitor`; retarget cursor-first assertions, commit-script mock keys, `TierAttempt(tier=...)` stubs, and rotation comments to codex-first:
- `test_run_ci_fix_pushed_after_winning_tier`: `launch_calls == ["codex"]`; commit-msg mock `Apply CI fixes (codex)`.
- `test_run_ci_fix_first_fixer_non_health_after_stage` (and any tier-tagged stubs): first-tier `tier="codex"` + matching commit mock.
- `test_evaluate_failure_verify_failed_then_pushed`: rotation comment — attempt 0 → codex (`start_attempt=0`), attempt 1 → cursor (`start_attempt=1`); swap commit mock keys to match.
- `test_run_ci_fix_short_circuit_first_fixer_non_health`: assert first launch is `codex`.
- Grep the file for remaining `Apply CI fixes (cursor)` / `tier="cursor"` order assumptions after editing.

#### UPDATED: `scripts/test-implement-step2-routing.sh`
Part 2, test. Three string updates:
- The `BOOTSTRAP_MD` assertion `'Cursor → Codex → Claude'` → `'Codex → Cursor → Claude'`.
- The two `BOOTSTRAP_SH` fallback-warning assertions → "Codex unavailable — falling back to Cursor implementer" and "Cursor unavailable — falling back to Claude implementer" (update the trailing labels to match).
- Leave the `assert_not_contains "$IMPLEMENT_SKILL" 'Codex → Cursor → Claude'` line intact — it guards SKILL.md cleanliness. Its label may be clarified but the assertion must stay.

#### UPDATED: `scripts/test-ship-pr.sh`
Part 2, test. Re-point the order-sensitive cases so the first tier is Codex:
- `ci_fix_vendor_tier_order_cursor_first` → rename to `..._codex_first`: make the Codex stub the one that succeeds; assert a single Codex launch; update repo name + messages.
- `ci_fix_vendor_tier_order_falls_through_to_codex` → rename to `..._falls_through_to_cursor`: Codex stub returns `LAUNCHER_EXIT=1`, Cursor stub succeeds; assert Codex then Cursor (no Claude); update messages.
- `ci_fix_vendor_tier_order_falls_through_to_claude`: outcome unchanged (both externals fail → Claude); grep assertions are order-agnostic. Update the leading comment to codex-first.
- The four `#3227` stderr-tail / first-fixer cases that assume cursor-is-first: swap the Cursor and Codex stub bodies so the FIRST tier (Codex) is the failing/probe-emitting one ("surfaces pre-seeded tier stderr-tail", "wrapper_rc=2 surfaces ... before codex tier" → reword to "cursor tier", the recovery-waterfall "tier_rc-only failure advances", and "first-fixer-non-health surfaces tier stderr-tail" with `LAUNCHER_FAILURE_CLASS=other` on the Codex/first tier). Keep each assertion's intent; update messages.

#### UPDATED: `scripts/test-ship-pr-fix-loop-2632.inc.sh`
Part 2, test. Invert the four order-sensitive cases so Codex is the first tier:
- `t4` (first-fixer `class=other` → exit 3, single launch): move the `LAUNCHER_FAILURE_CLASS=other` first-tier stub to Codex; rename the case/repo and messages.
- `t4b` (health failure → waterfall to next): Codex (first) health-fails, Cursor (second) succeeds; assert both invoked; rename.
- `t4c` (`wrapper_rc=2` → next): Codex (first) `exit 2`, Cursor (second) succeeds; assert both invoked; rename.
- `t4d` (non-first `class=other` does NOT bail → all three run): Codex (first) health-fails, Cursor (second) emits `class=other`, Claude succeeds; assert all three; rename and reword "policy cursor-only" → "policy first-tier-only".
- `t5`–`t21` are order-agnostic (launch counts / all-fail / plan-file / failure-log / rc3-defer / missing-claude); leave unchanged.

### Approach
Single base-order flip per role, plus parity in Python and synced tests/docs.
- Coder: flip the probe order in `_phase_coder_implicit` (two `if` branches + warnings).
- CI fixer: flip only the base `tiers=(...)` tuple; the per-attempt rotation and first-fixer bail follow it.
- Merge-resolve: flip the literal `for tier in ...` list.
- Python: one tuple in `config.py`; all consumers derive from it, so no consumer edits — but `test_config.py` and `test_ci_monitor.py` tier-order mocks/assertions need updating.
- Tests assert observed launcher order or warning strings; update stubs/assertions to codex-first. Most ship-pr cases are order-agnostic and stay.
- Docs: sync prose that states the old order (`ship-pr.md`, `implement-bootstrap.md`, `skills/implement/SKILL.md`, `SECURITY.md`, `docs/external-reviewers.md`, `docs/linting.md`), respecting the SKILL.md arrow-substring guard.

### Edge cases
- **Explicit `--coder` unchanged:** the implicit flip must not alter `_phase_coder_explicit*`; covered by existing `#3207` explicit-waterfall assertions (kept green).
- **Start-tier rotation:** `run_ci_fix_vendor` rotates start tier per outer attempt; attempt 0 now starts at Codex. The `first-fixer-non-health` bail keys on `first_tier`, so it now bails when Codex (first) fails non-health — the intended new behavior, asserted by the rewritten `t4` / first-fixer tests.
- **Both externals unavailable:** all three roles still fall through to Claude (terminal tier preserved).
- **SKILL.md guard:** synced wording must avoid the literal arrow `Codex → Cursor → Claude` (commas instead) or `test-implement-step2-routing.sh` fails.
- **Python is parity-only:** `python/` is not wired into the live path until Phase 7; the flip is parity, no live runtime effect yet.

### Failure modes
- **Missed order assertion** in a test file → CI red. Mitigation: grep each touched test for `cursor`/`codex` ordering and run the named harnesses locally.
- **Stale prose left behind** → drift. Mitigation: grep `scripts/ship-pr.md`, `scripts/implement-bootstrap.md`, `skills/implement/SKILL.md`, `SECURITY.md`, `docs/external-reviewers.md`, and `docs/linting.md` for the old order after editing.
- **Accidentally flipping an out-of-scope cursor-first surface** (plan-review / brainstorm) → scope creep against the report below. Mitigation: those surfaces are explicitly NOT edited.

### Testing strategy
- `bash scripts/relevant-checks.sh` (repo-wide pre-commit hooks).
- `bash scripts/test-implement-step2-routing.sh`
- `bash scripts/test-ship-pr.sh`
- `make py-test` (full suite; do not narrow to `test_config.py`) — confirms `FIXER_TIER_ORDER`, `python/test_ci_monitor.py` codex-first mocks/assertions, and order-independent Python tests.
- `make lint-bash32` after shell edits.

### Surfaced cursor-first defaults — reported, NOT flipped (per design Round 1 decision)
Cursor-first defaults OUTSIDE the three named roles. NOT changed in this issue; recorded for a separate decision:
- **R1 — `/design` plan-review per-archetype Cursor-slot fallback** (`Cursor → Codex → Claude`): `docs/review-agents.md`, `docs/collaborative-sketches.md`. Codex-archetype slots already fall back Codex-first; only the Cursor-archetype slots are cursor-first.
- **R2 — `/design` brainstorm framing lane** (`Cursor → Codex → Claude`): `skills/design/references/brainstorm.md`.
- **Excluded (not a preference):** `/design` sketch + plan-review static spawn order launches Cursor slots first — that is parallel spawn ordering (slowest-first), not a fallback preference. The `/review` voter panel already has both a Codex-first and a Cursor-first slot (balanced).

## Acceptance

Part 1 — Documentation:
- [ ] The Claude section of `docs/installation-and-setup.md` explains removing `apiKeyHelper` from `~/.claude/settings.json` and why (subprocess `claude --print` auth → 401 in subscription mode).
- [ ] The four example aliases (`claude_api`, `claude_login`, `opus_api`, `opus_login`) are documented with the API-key-vs-subscription mechanism.
- [ ] Docs-only: no runtime/script/behavior change in this part.

Part 2 — Codex-first defaults:
- [ ] Default coder (no `--coder`) prefers Codex over Cursor (`Codex → Cursor → Claude`).
- [ ] CI fixer waterfall (`run_ci_fix_vendor`) prefers Codex over Cursor.
- [ ] Merge-resolve / conflict fixer waterfall (`run_recovery_waterfall`) prefers Codex over Cursor.
- [ ] Both Bash (`scripts/`) and Python (`python/`) paths updated for parity; `FIXER_TIER_ORDER` and its tests (`test_config.py`, `test_ci_monitor.py`) updated.
- [ ] Claude remains the terminal fallback tier in all three roles.
- [ ] Explicit `--coder cursor` still works; only the omitted default changes.
- [ ] Order-asserting tests pass (`test-implement-step2-routing.sh`, `test-ship-pr.sh`, `test-ship-pr-fix-loop-2632.inc.sh`, `make py-test`).
- [ ] Affected prose docs synced to the new order (`ship-pr.md`, `implement-bootstrap.md`, `skills/implement/SKILL.md`, `SECURITY.md`, `docs/external-reviewers.md`, `docs/linting.md`).

diff_lines: 313
