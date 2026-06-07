## Goal
Implement issue #3618: [IMPLEMENTING] /design voter & external-agent reliability: ballot-pointer/grammar regression test + Codex health-probe, Claude read-tools, lenient vendor retries\n\n> **Blocked by #3647 and #3649** (review-voting overhaul): Part A pins the voter-prompt output grammar and extends `scripts/test-render-voter-prompt.sh`, and both of those surfaces are being reshaped — #3647 collapses the vote grammar to two tokens (YES/NO) and #3648 removes the assessor lane; #3649 rewrites the voter criteria around the necessity rubric and adds its own sync assertions to the same harness. Author Part A against the **post-#3649 renderer**. Part B only weakly overlaps the trio (`test-launch-review.sh`, `dispatch-plan-voters.sh` fixtures with #3647) — the blocks above already serialize past that. Can run in parallel with #3648 and #3651 (no meaningful overlap)..

## Implementation Plan
> **Blocked by #3647 and #3649** (review-voting overhaul): Part A pins the voter-prompt output grammar and extends `scripts/test-render-voter-prompt.sh`, and both of those surfaces are being reshaped — #3647 collapses the vote grammar to two tokens (YES/NO) and #3648 removes the assessor lane; #3649 rewrites the voter criteria around the necessity rubric and adds its own sync assertions to the same harness. Author Part A against the **post-#3649 renderer**. Part B only weakly overlaps the trio (`test-launch-review.sh`, `dispatch-plan-voters.sh` fixtures with #3647) — the blocks above already serialize past that. Can run in parallel with #3648 and #3651 (no meaningful overlap).

Combines #3597 and #3598 — both are follow-ups from the same `/design` voter-failure investigation (silent voter-prompt truncation, root-caused and fixed in #3596). #3597 hardens the external-agent voter path; #3598 adds the regression test that locks the fix in. Shipping the hardening together with its regression coverage as one `/design` + `/implement` unit.

---

## Part A — Regression test: voter prompts always carry the ballot pointer + vote grammar (from #3598)

### Context

The voter failure was a silent voter-prompt truncation that no test caught. Add coverage so it cannot silently regress again. Locks in the file-by-reference contract (the prompt must always point reviewers at the ballot file).

### Scope

Extend `skills/shared/scripts/test-render-voter-prompt.sh` (and/or a `dispatch-plan-voters.sh` harness) to assert:

1. Rendering the voter prompt with a `--scope-anchor-file` at a real `DESIGN_TMPDIR` / `~/.cache/larch/sessions/<run>/` path exits 0 and the output **contains** the `Read the ballot from this path` line **and** the two-token `FINDING_N:` (and `OOS_N:`) vote-output grammar as it exists post-#3647/#3649 — pin the grammar lines the shipped renderer actually emits, not a hardcoded historical token list.
2. `dispatch-plan-voters.sh` `make_prompt_file` fails loudly (non-zero) when `render-voter-prompt.sh` errors, instead of emitting a truncated prompt.

### Acceptance

- New assertions fail against the pre-fix code and pass after the bug fix; wired into `make lint`.

---

## Part B — External-agent voter reliability hardening (from #3597)

### Context

Follow-up hardening from the voter-failure investigation. Independent of (and was blocked on) the prompt-truncation bug fix (#3596, now merged); these improve observability, determinism, and resilience of external-agent calls — they are not the root cause of that failure.

### Items

1. **Codex voter health-probe diagnostics.** In the failing run the Codex voters fast-failed with `exit 7` = pre-launch health-gate failure (`scripts/run-external-agent.sh` sets `EXIT_CODE=7` when `external_launch_health_gate "codex"` reports unhealthy). The sidecar was **empty**, so there was no captured reason for *why* Codex went unhealthy mid-session (it was healthy at Step 0, ~50 min earlier). Capture the health-probe failure reason into the `.diag`/sidecar, and consider a mid-run Codex health/auth refresh for long (~1 hr) runs so Codex is not silently lost at voting time.

2. **Claude voter explicit read-tools mode.** The Claude voter is launched in default `claude --print` mode (default tools), which reads the by-reference ballot by path (works empirically, verified). Harden to the explicit read-tools mode (`--add-dir "$DESIGN_TMPDIR" --allowedTools Read --permission-mode plan`) for deterministic, scoped, read-only access rather than relying on default-tool permissions — e.g. expose `--read-tools-add-dir` for the voter path in `scripts/launch-claude-review.sh`, or stage the ballot under `staged-context/`.

3. **More lenient retries for vendor-agent (Codex/Cursor) calls.** External agents hit **transient** failures often — health-gate `exit 7`, network blips, empty / `0-byte` output, model-overload `5xx`. Today the transient-retry budget is small and the inter-retry waits are short: `scripts/launch-review.sh` uses `MAX_TRANSIENT_RETRIES=2` with exponential backoff `_backoff=$(( 1 << TRANSIENT_ATTEMPT ))` + 0–1 s jitter (≈2–4 s), with the same shape on the Cursor lane. Make vendor-agent retries more lenient across the external launchers:
   - **More attempts** — raise the transient-retry budget (e.g., `MAX_TRANSIENT_RETRIES` 2 → 3–4) so a single transient blip does not drop an agent from the panel.
   - **Longer inter-retry waits** — use a longer floor between attempts (e.g., **~10 s**), via a higher `LARCH_TRANSIENT_RETRY_DELAY` default or a raised backoff floor, giving the vendor time to recover from rate-limit / overload before the retry.
   - Apply consistently to both the Codex and Cursor transient-retry loops in `scripts/launch-review.sh` and the shared `scripts/run-external-agent.sh`. Keep **auth-retry** and **quota / usage-limit** handling distinct — do not put a hard quota failure on a 10 s transient loop.
   - This is a **general external-agent reliability** improvement — it benefits every external lane (voters, reviewers, sketches, dialectic debaters, implementers), not just voting.

Cursor needs no change for ballot reading — it reads the out-of-workspace ballot via `--trust` (verified).

### Acceptance

- A degraded/unhealthy Codex voter records the probe failure reason (not an empty sidecar).
- The Claude voter reads the ballot through an explicitly scoped read-only tool grant.
- Transient-retry budget and inter-retry wait are widened (more attempts; ~10 s floor) for Codex and Cursor across `launch-review.sh` / `run-external-agent.sh`, with auth/quota paths left intact; pinned by launcher harness assertions (`scripts/test-launch-review.sh`).
- `make lint` green.

---

*Combined from #3597 + #3598 via `/combine-issues`.*

---

## Design Q&A decisions (recorded for redesign)

A prior `/design` run was reset before finalizing. These are the operator decisions from that run's clarification + outline session, preserved so the redo starts from them. (Reviewer-panel findings from the reset run are intentionally **not** carried over.)

1. **Codex health-probe scope** — implement BOTH: (a) capture the health-probe failure reason into the `.diag`/sidecar, AND (b) a best-effort mid-run Codex health/auth refresh for long (~1 hr) runs so Codex is not silently lost at voting time. The refresh must be best-effort — never worse than today's fast-fail.
2. **Claude voter read access** — thread the existing `--read-tools` / `--read-tools-add-dir` support (already implemented in `scripts/launch-claude-subprocess.sh`) through `scripts/launch-claude-review.sh`; `scripts/dispatch-plan-voters.sh` passes `--read-tools-add-dir "$DESIGN_TMPDIR"` (grant Read on the run's own session dir; do NOT stage the ballot under `staged-context/`).
3. **Transient-retry leniency** — raise `MAX_TRANSIENT_RETRIES` 2 → 4 in BOTH the Codex and Cursor lanes of `scripts/launch-review.sh`, with a ~10s inter-retry backoff floor. Keep auth-retry (default 5) and quota/usage-limit handling separate from the transient loop.

**Path note (discovered during grounding, not a reviewer finding):** the dispatcher lives at `scripts/dispatch-plan-voters.sh` and the renderer harness at `scripts/test-render-voter-prompt.sh` — the issue text's `skills/shared/scripts/` paths for those two are wrong. The renderer itself is `skills/shared/scripts/render-voter-prompt.sh`. Cursor needs no ballot-read change (it uses `--trust`).

---
*Body revised 2026-06-07: vote-grammar references normalized to the post-#3647 two-token surface, stale lane-list entry removed (the assessor lane is deleted by #3648), blocked-by edges added (#3647, #3649). Original wording in the edit history.*


## Test plan
(no test plan section in plan-file)
