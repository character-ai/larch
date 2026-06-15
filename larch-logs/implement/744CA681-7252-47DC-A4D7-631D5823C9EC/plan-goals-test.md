## Goal
Implement issue #4442: [IMPLEMENTING] --emergency flag in /implement should skip plan validation step entirely, instead of performing it but ignoring flags it raises.

## Implementation Plan
## Plan

## Approach

Make the smallest contract change:

- Treat `--emergency` as a skip for Preflight item 4.
- Place the item 4 emergency skip before any mandatory read of `preflight-plan-audit.md`.
- Do not run `preflight-plan-audit.md` under emergency.
- Do not write `audit.txt` under emergency.
- Do not append an `audit-refuse` emergency bypass log entry.
- Continue from the item 4 skip to item 6 semantic materiality.
- Add an Anti-halt continuation rule for the emergency skip breadcrumb.
- Preserve the existing Anti-halt audit-pass continuation pin verbatim.
- Keep item 6 active under emergency.
- Keep zero-review provenance refusal in `scripts/implement-preflight.sh` unchanged.
- Keep canonical emergency bypass tokens limited to `missing-plan`, `malformed-plan`, and `missing-designed-prefix`.

## Files to modify/create

### UPDATED: `skills/implement/SKILL.md`

- Update the Protocol Execution Directive:
  - State that item 4 runs only when `emergency_requested=false`.
  - State that when `emergency_requested=true`, item 4 is skipped and execution proceeds directly to item 6.
  - Replace "item 6 remains the semantic materiality judgment after audit pass or emergency-bypassed audit refuse" with wording that covers `AUDIT=pass` or emergency audit skip.
- Update the Anti-halt critical boundary:
  - Keep the existing literal audit-pass continuation pin verbatim: `do NOT end the turn on the audit-pass envelope`
  - Add the emergency audit-skip breadcrumb as a separate Preflight continuation signal beside the existing audit-pass rule.
  - State that after the emergency skip breadcrumb, the orchestrator must immediately continue through Preflight items 6 and 7, then Step 0.
  - State that the orchestrator must not halt waiting for an `AUDIT=pass` envelope on the emergency skip path.
- Update the flag table row for `--emergency`:
  - Say it skips the item 4 plan-adequacy audit.
  - Say it does not downgrade `AUDIT=refuse`, because no audit result exists on that path.
  - Remove clarify-state pending/refuse from the bypass list.
  - Keep the existing plan-block fallback and `missing-designed-prefix` bypass behavior.
  - Keep `coder=claude`.
  - List only the three real emergency bypass surfaces: missing plan, malformed plan, and missing designed prefix.
- Update the Emergency mode paragraph:
  - Change any "exactly four gates" wording to "exactly three gates".
  - Enumerate only `missing-plan`, `malformed-plan`, and `missing-designed-prefix`.
  - Remove `AUDIT=refuse` as a downgraded gate.
  - Remove the clarify-state pending/refuse path as an emergency bypass.
  - State that item 4 is skipped when `emergency_requested=true`.
  - State no bypass-log entry is written for the item 4 skip.
  - Keep canonical bypass tokens limited to `missing-plan`, `malformed-plan`, and `missing-designed-prefix`.
- Rewrite Preflight item 4 so the emergency branch is the first control-flow instruction:
  - Put the `emergency_requested=true` branch before any `MANDATORY — READ ENTIRE FILE` line.
  - Put it before any directive to read `skills/implement/references/preflight-plan-audit.md`.
  - Print one skip breadcrumb, for example: `⏭️ /implement --emergency: skipping plan-adequacy audit for issue #<N>; continuing to semantic materiality.`
  - Explicitly forbid reading `skills/implement/references/preflight-plan-audit.md` on this branch.
  - Explicitly forbid creating or overwriting `$PREFLIGHT_TMPDIR/audit.txt` on this branch.
  - Explicitly forbid appending to `$PREFLIGHT_TMPDIR/emergency-bypass.log` on this branch.
  - Jump directly to item 6.
  - Keep the mandatory read and existing audit body only on the non-emergency path.
- Update item 5:
  - Remove the `emergency_requested=true` branch.
  - Make `AUDIT=refuse` always exit 3 after the existing clarify-state/comment/label flow.
- Update item 6 heading:
  - Replace `AUDIT=pass` or emergency-bypassed `AUDIT=refuse` with `AUDIT=pass` or emergency audit skip.
  - Keep stale-plan behavior unchanged.
- Update the exit-code table:
  - Remove the emergency carve-out for `AUDIT=refuse`.
  - State that emergency skips the audit before any `AUDIT=refuse` result exists.
- Grep the file for stale active-surface references and remove or rewrite only the in-scope ones: `audit-refuse`, `emergency-bypassed AUDIT=refuse`, `bypassing clarify-state`, `plan-adequacy refusal`, `clarify-state pending`.

### UPDATED: `python/bootstrap.py`

- Remove `"audit-refuse"` from the `_append_emergency_bypass()` canonical token set.
- Do not otherwise change emergency log parsing, issue validation, invalid-format redaction, sentinel consumption, or run-log append behavior.

### UPDATED: `scripts/test-plan-adequacy-audit.sh`

- Replace assertions that require the emergency `audit-refuse` warning, explicit `BYPASS kind=audit-refuse`, and `audit-refuse` canonical token text.
- Add assertions for the new skip contract in `SKILL.md`:
  - Item 4 puts the `emergency_requested=true` branch before any mandatory read of `preflight-plan-audit.md`.
  - Item 4 contains the emergency skip breadcrumb or equivalent skip wording.
  - Item 4 says not to read `preflight-plan-audit.md` under emergency.
  - Item 4 says not to create or overwrite `audit.txt` under emergency.
  - Item 4 says not to append an emergency bypass log for the skip.
  - Item 6 is reachable from `AUDIT=pass` or emergency audit skip.
- Add assertions for the Anti-halt continuation contract:
  - The emergency skip breadcrumb is treated as a continuation signal.
  - The orchestrator must continue through Preflight items 6 and 7, then Step 0.
  - The orchestrator must not wait for `AUDIT=pass` on the emergency skip path.
  - The existing audit-pass continuation pin remains present for non-emergency runs.
- Add assertions that active prose no longer documents clarify-state pending/refuse or plan-adequacy refusal as emergency bypasses.
- Keep existing assertions for: `missing-plan`, `malformed-plan`, `missing-designed-prefix`, `BYPASS kind=<lowercase-token> issue=<number>`, helper-side bypass behavior in `scripts/implement-preflight.sh`.

### UPDATED: `docs/issue-anchored-plan.md`

- Update the intro summary bullets near the top:
  - State that non-emergency `/implement` runs the in-prompt plan-adequacy audit.
  - State that `/implement --emergency` skips the in-prompt plan-adequacy audit.
  - Remove plan-adequacy refusal as an emergency downgrade.
  - Remove clarify-state pending/refuse as an emergency downgrade.
  - Preserve the statement that semantic materiality still runs.
- Update the Plan adequacy emergency-mode paragraph:
  - Say `/implement --emergency` skips the Preflight plan-adequacy audit.
  - Remove `AUDIT=refuse` from the downgraded gates.
  - Remove clarify-state pending/refuse as an emergency bypass.
  - State no `audit-refuse` bypass log is written for the skip.
  - Preserve the statement that semantic materiality stale-plan notice is not bypassed.
- Update the canonical emergency bypass-token list to: `missing-plan`, `malformed-plan`, `missing-designed-prefix`.

### UPDATED: `SECURITY.md`

- Update the `/implement` Preflight admission emergency-mode text:
  - Say `--emergency` skips the item 4 plan-adequacy audit.
  - Say no `AUDIT=refuse` exists on the emergency skip path.
  - Say no `audit-refuse` bypass token or bypass-log entry is written for the skip.
  - Remove clarify-state pending/refuse as an emergency bypass.
  - List only the remaining canonical bypass tokens: `missing-plan`, `malformed-plan`, `missing-designed-prefix`.
  - Preserve any zero-review provenance refusal language.
- Qualify the standalone adequacy enforcement sentence in the same section:
  - State that non-emergency runs enforce adequacy with `plan-block read` plus the in-prompt audit.
  - State that emergency runs still use helper-side plan-block fallback behavior but skip the in-prompt plan-adequacy audit.

## Edge cases

- Emergency runs with a missing or malformed plan still use `scripts/implement-preflight.sh` fallback behavior and still write the existing bypass tokens.
- Emergency runs with zero-review provenance still fail in `implement-preflight.sh`; do not weaken that guard.
- Emergency runs skip item 4 before any audit read and before any `AUDIT=refuse` exists, so item 5 must not run.
- Emergency runs must continue from the skip breadcrumb to item 6, item 7, and Step 0 without waiting for an audit envelope.
- Non-emergency runs keep the full audit and clarify-state refusal flow unchanged.
- Non-emergency audit-pass runs keep the existing Anti-halt continuation guard unchanged.
- Stale-plan semantic materiality still runs after the emergency skip and may still exit 2.

## Failure modes

- If the item 4 emergency branch appears after the mandatory audit read, emergency can still load and run the audit.
- If the Anti-halt boundary is not updated, an orchestrator may stop after the skip breadcrumb instead of continuing to item 6.
- If the literal `do NOT end the turn on the audit-pass envelope` pin is removed, anti-halt lint can fail and the non-emergency continuation guard can regress.
- A stale `audit-refuse` token left in docs or `SKILL.md` can make operators expect a bypass log that no longer exists.
- A stale `audit-refuse` token left in `python/bootstrap.py` can keep accepting obsolete emergency logs.
- Stale clarify-state pending/refuse wording can incorrectly document a removed emergency bypass.
- If item 6 wording is not updated, the path from emergency skip to semantic materiality may be ambiguous.
- If `SECURITY.md` keeps unqualified adequacy-audit wording, it can overstate the emergency trust boundary.

## Testing strategy

- Run `bash scripts/test-plan-adequacy-audit.sh`.
- Run `bash scripts/test-implement-anti-halt.sh`.
- Run `make py-lint`.
- Run `make py-test`.
- Run `make lint`.
- Also grep for stale active-surface references: `grep -RIn "audit-refuse\|emergency-bypassed AUDIT=refuse\|bypassing clarify-state\|plan-adequacy refusal\|clarify-state pending" skills/implement/SKILL.md python/bootstrap.py scripts/test-plan-adequacy-audit.sh docs/issue-anchored-plan.md SECURITY.md`

## Acceptance

- `bash scripts/test-plan-adequacy-audit.sh` passes with updated assertions for emergency skip.
- `bash scripts/test-implement-anti-halt.sh` passes with the emergency skip breadcrumb as a continuation signal.
- `make py-test` passes (bootstrap.py canonical set no longer includes `audit-refuse`).
- `make lint` passes.
- `grep -RIn "audit-refuse" skills/implement/SKILL.md python/bootstrap.py docs/issue-anchored-plan.md SECURITY.md` returns zero hits on active-prose surfaces.

review_status: complete
rounds_completed: 4
diff_lines: 78

## Test plan
(no test plan section in plan-file)
