## Goal
Implement issue #3651: [IMPLEMENTING] [OOS] Implement hardening: stall-recovery enum/docs/lint + timing A1 pins\n\n## Combined implement-side hardening (from #3620 + #3621).

## Implementation Plan
## Combined implement-side hardening (from #3620 + #3621)

> **Blocked by #3647** (review voting → YES/NO, in flight): land this after #3647 merges so new harness pins, fixtures, and doc wording are authored against the post-#3647 review surface. No functional dependency on #3648 or #3649; file overlap with the rest of that group is nil for Part II and limited to different sections of `SECURITY.md` / `skills/implement/SKILL.md` for Part I.

Combines #3620 (itself a combine of #3579 + #3580 + #3576) and #3621 (itself a combine of #3588 + #3589): two `skills/implement`-side hardening families with **zero file overlap between the two Parts** — one `/design` + `/implement` cycle covers both. Part boundaries are preserved from the source issues; both carried design-notes blocks are included for the `/design` redo. Vote-tally lines are normalized to YES/NO counts.

---

# Part I — Stall-recovery hardening (from #3620)

Three `/implement`-review out-of-scope follow-ups in the `skills/implement` stall-recovery family. #3579 and #3580 both modify `stall-recovery-report.sh` and overlap on the Step-2/12d `STALL_TRACKING=true` bailed-row routing; #3576 adds a missing harness pin for the adjacent `stall-recovery-issue.env` batch-key mapping.

**Implementer note on overlap:** #3579 (Part I-A) and #3580 item (c) (Part I-B) both touch the decision of whether `recovery-out-of-scope` / the `STATUS=bailed` row must unconditionally set `STALL_TRACKING=true`. Reconcile these into a single consistent answer when implementing (see the design notes below — already resolved in code; document it).

## Part I-A — Complete the `safe_bail_reason_value` enum (from #3579)

**Surfaced by**: Code review panel (Cursor + Codex + Claude dynamic) · **Phase**: implement · **Vote tally**: Accepted (Rule A combine: same logical concern — enum completeness)

`skills/implement/scripts/stall-recovery-report.sh` `safe_bail_reason_value()` is missing classifier-evidence tokens that exist in production bail flows:

- `recovery-out-of-scope` (mirrored into `IMPLEMENT_BAIL_REASON` without consistent `STALL_TRACKING=true` routing, and absent from the enum);
- `ci-fix-exhausted` (used as classifier evidence in ship-pr but absent from the report enum).

Each absence causes a mismatch where `FAILURE_CLASS` names the token while `Bail reason` renders `redacted`.

**Suggested fix:** add each token to `safe_bail_reason_value`, the documented BAIL_REASON enum in `stall-recovery-report.md` and `SECURITY.md`, and a regression fixture that pins the rendered row. For `recovery-out-of-scope`, document the (already-implemented) unconditional `STALL_TRACKING=true` + mirror behavior. Sources: OOS_3 (recovery-out-of-scope), OOS_5 (ci-fix-exhausted). (OOS_2's `main-branch-post-dispatch` is already done — see design notes.)

## Part I-B — Latent stall-report improvements (from #3580)

**Surfaced by**: Code review panel (Cursor + Codex + Claude dynamic) · **Phase**: implement · **Vote tally**: Accepted (Rule B combine: SIMPLE latent improvements)

Three latent improvements in the stall-recovery-report surface, each individually small (~20-30 LOC) but genuinely out-of-scope for the originating PR:

(a) `skills/implement/scripts/stall-recovery-report.sh` `compose_body_content` loads `EXIT_CODE` and bail reason from persisted state, but Step-2 manifest bail strings pass through `materialize-manifest-oos.sh` rather than a dispatch-time sanitizer; adding an earlier redaction pass before persistence would reduce reliance on `safe_bail_reason_value` as the sole gate. **(Open question — see design notes; may resolve to doc-note, fixture re-pin, or drop.)**

(b) `skills/implement/scripts/stall-recovery-report.sh` `cmd_lint` validates only `surface` and `field_key` columns; extending it to compare the `transform` and `source` columns across TSV, code heredoc, and docs would catch drift such as `integer-or-unknown` reverting silently.

(c) `skills/implement/SKILL.md` Step-2 legal-actions matrix does not yet reflect that `IMPLEMENT_BAIL_REASON` mirroring and unconditional `STALL_TRACKING=true` are required on the `STATUS=bailed` row; add a short Step 12d hard-bail routing subsection naming the concrete steps (skip 3-15, continue 16-17, run 18a with coalesced `--bail-reason`).

Sources: OOS_1 (sanitization timing), OOS_4 (lint completeness), OOS_6 (SKILL.md matrix).

## Part I-C — Harness pin for `stall-recovery-issue.env` batch-key normalization (from #3576)

**Already implemented** — verification-only during the redo (see design notes: pinned by `case20n` / `case20n2` / `case20n3`; the originally cited `references/stall-recovery.md:59-71` location no longer exists).

## Part I — Design notes from prior /design Q&A (2026-06-06)

Carried context for re-running `/design`. Scope/decision notes from a Q&A session — **not** a plan, and not reviewer-panel findings.

**Scope — large parts are already implemented; verify before re-planning:**
- `main-branch-post-dispatch` is already in `safe_bail_reason_value()`, the `stall-recovery-report.md` enum, the `SECURITY.md` enum, and fixture `case7l`. The original "missing" claim for it is stale.
- Part I-C (`normalize-issue-env` batch-key dedup) is already harness-pinned by `case20n` / `case20n2` / `case20n3`.
- So Part I-A's genuinely-missing enum tokens are only `ci-fix-exhausted` and `recovery-out-of-scope`.

**Decisions:**
- **`recovery-out-of-scope` / `STATUS=bailed` `STALL_TRACKING` reconciliation (the #3579/#3580 overlap):** already resolved in code. Its sole wiring site — the Step 2.4 recovery sub-branch in `skills/implement/SKILL.md` — already sets `IMPLEMENT_BAIL_REASON=recovery-out-of-scope` and `STALL_TRACKING=true`. Keep unconditional `STALL_TRACKING=true` + mirror; just document it. No reclassification: it stays `unrecoverable`. The enum change is render-only so the `Bail reason` row shows the real token instead of `redacted`.
- **Allowlist TSV scope:** `stall-recovery-report-allowlists.tsv` is a `surface × field_key` table and does **not** carry bail-reason tokens. The BAIL_REASON enum lives only in `safe_bail_reason_value()` + `stall-recovery-report.md` + `SECURITY.md`. The original "add each token to the allowlist TSV" instruction is imprecise.
- **Part I-B(b):** extend `cmd_lint` to compare full 4-column rows (`surface` + `field_key` + `source` + `transform`), not just `surface`/`field_key`, and update the lint documentation to match.
- **Part I-B(c):** add a "Step 12d hard-bail routing" doc subsection to `skills/implement/SKILL.md` documenting existing behavior (`STATUS=bailed` mirrors `IMPLEMENT_BAIL_REASON`/`FINAL_BAIL_REASON`, sets `STALL_TRACKING=true`, skips Steps 3–15, continues 16–17, runs 18a with the coalesced `--bail-reason`).
- **Run mode:** SIMPLE tier.

**Open question (decide during the redo — not yet settled):**
- **Part I-B(a) — "earlier redaction pass before persistence":** the literal form (redact the bail reason before it is persisted) would break `classify_from_evidence`, which needs the raw bail token as evidence; the public report surface is already allowlist-gated (`safe_bail_reason_value`) plus a `redact-secrets.sh` body backstop; and the free-form/secret bail-value → `redacted` invariant is already pinned by existing `case13b` / `case13c`. Candidate resolutions: (1) doc note only, (2) a regression fixture that re-pins the invariant, or (3) drop I-B(a) entirely.

---

# Part II — Timing-attribution A1-scanner coverage (from #3621)

Two `/implement`-review out-of-scope follow-ups with the same root cause: the A2 timing pins only covered implement-specific launchers, so `LARCH_TIMING_SKILL` skill-misattribution can still slip past the 15-file A1 scanner in `scripts/test-implement-structure.sh` under a polluted shell. Same A1-scanner / timing-ledger surface; fix both gaps as one unit.

## Part II-A — Timing-harness gaps in `record-implement-review-round-timing.sh` (from #3588)

**Surfaced by**: cursor-specialist-edge-cases + cursor-specialist-testing · **Phase**: implement · **Vote tally**: Accepted — YES=3, NO=0 (round 1 review)

`skills/review-and-fix/scripts/record-implement-review-round-timing.sh`:

1. The A1 scanner in `scripts/test-implement-structure.sh` enumerates 15 production scripts but omits `record-implement-review-round-timing.sh`, which calls `timing-ledger.sh record-round`. A dropped `export LARCH_TIMING_SKILL=implement` before that call would not fail the harness, leaving Step 5 deferred round timing vulnerable to skill misattribution under a polluted shell.
2. The round-only idempotency short-circuit exits 0 without updating start/end timestamps when a partial row already exists; aligning it with full-tuple fingerprinting (as in the design-helper variant) would prevent silent stale-row reuse.

**Suggested fix:** add `record-implement-review-round-timing.sh` to the A1 scanner set and extend the awk pattern to cover the `record-round` subcommand (export-or-same-line pin rule); and align the pre-check with full-tuple fingerprinting.

## Part II-B — Implement lint-fix path reaches unpinned record-vendor-task via `launch-codex-exec.sh` (from #3589)

**Surfaced by**: dyn-telemetry-attribution · **Phase**: implement · **Vote tally**: Accepted — YES=2, NO=0 (round 1 review)

`scripts/lint-fix-loop.sh` → `scripts/launch-codex-exec.sh`: The `/implement` lint-fix path dispatches through `launch-codex-exec.sh`, a shared launcher that serves design/review/research. Under a polluted `LARCH_TIMING_SKILL=design` shell, Codex lint-fix vendor rows can still be tagged `design` while the 15-file A1 scanner passes. The originating plan intentionally excluded `launch-codex-exec.sh` (it is generic); fixing it requires an implement-session guard at the lint-fix dispatch site in `lint-fix-loop.sh` rather than a blanket `=implement` pin on the shared launcher. Not a regression introduced by that PR — the A2 pins only covered the implement-specific launchers.

## Part II — Design decisions (carried over from prior /design Q&A)

Agreed during a prior /design session; that session's plan was reverted for a redesign. Carry these into the next design.

- **Scope: full Part II scope.** Implement all three sub-changes — (1) A1-scanner coverage for `record-implement-review-round-timing.sh` plus its `record-round` subcommand, (2) full-tuple idempotency fingerprinting in that helper, and (3) the lint-fix `LARCH_TIMING_SKILL=implement` dispatch guard. The behavioral idempotency change (Part II-A #2) is **in scope**, not deferred.
- **Implement-only.** Do not mirror to the design side: `scripts/test-design-structure.sh` has no analogous A1 scanner to extend, so mirroring would be net-new infrastructure beyond this issue.
- **No blanket pin on the shared launcher.** Apply the `LARCH_TIMING_SKILL=implement` guard at the lint-fix dispatch site in `scripts/lint-fix-loop.sh`, not on the generic `scripts/launch-codex-exec.sh` (which also serves design/review/research). The `run_cursor` path needs no change — its launcher (`run-external-agent.sh --tool cursor`) records no skill-derived timing row.
- **Preserve strict same-line enforcement.** The export-or-same-line relaxation in the A1 scanner applies only to the `record-round` subcommand; `mark` / `record-vendor-task` / `timing-report.sh` keep the strict same-line pin requirement.

---
*Combined from #3620 + #3621 (sources closed as superseded); those were themselves combines of #3579 + #3580 + #3576 and #3588 + #3589 via `/combine-issues`. Vote tallies normalized to YES/NO counts per the post-#3647 voting surface. No live blocker edges carried from the sources (their only edge, #3628, is closed).*

## Test plan
(no test plan section in plan-file)
