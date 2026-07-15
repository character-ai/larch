## Goal
Implement issue #7447: [IMPLEMENTING] [FEATURE] /status resolves pinned vendor model ids against live model lists.

## Implementation Plan
[FEATURE] /status resolves pinned vendor model ids against live model lists

## Context

Mechanical backing for the #7237 bug class, deliberately excluded from #7437 (which appends the prose-only G-Ext-5 guideline). The 2026-07-15 /learn-from-bugs run (scan marker PR #7433) named this as the mechanical alternative for the cluster; prose-only prevention tends not to stick (#6746, #6747). Sibling of #7437, no blocking edge in either direction: the guideline append and this probe land independently.

## Root cause recap

#7237: `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY` in `python/larch/core/config.py` pinned `grok-4.5`, an id the Cursor CLI does not expose (valid id: `cursor-grok-4.5-high`), which broke the MODERATE /implement lane. PR #7240 fixed the instance and asserted the corrected constant in `python/tests/core/test_config.py`. That pin protects one constant's current value only; nothing validates any pinned model id against the vendor's live model list, so the next hand-pinned id ships unprobed the same way.

## Proposal

Extend the /status flow (`skills/status/SKILL.md`, which uses the same probe machinery as /implement Step 0: `python3 python/cli.py agent check-reviewers` for binary/runtime probes, then `agent degraded-tools-gate` for ok / binary-missing / probe-failed classification) so that when a vendor probe reports `ok`, the flow also resolves that vendor's pinned model ids from `config.py` against the vendor's live model list, and reports any unknown id as a distinct non-ok state naming the id and the owning constant.

Pinned ids to resolve:
- Cursor: the values of `CURSOR_IMPLEMENT_MODEL_BY_DIFFICULTY` (currently `composer-2.5` and `cursor-grok-4.5-high`).
- Codex: `CODEX_DEFAULT_MODEL`, `CODEX_REVIEW_MODEL_DEFAULT`, `CODEX_VOTE_MODEL_DEFAULT` (currently `gpt-5.6-sol`, `gpt-5.6-luna`, `gpt-5.6-terra`).

## Verified vendor surfaces (probed 2026-07-15)

- Cursor: `cursor-agent models` lists the account's available models, one `id - display name` line each (`--list-models` also exists on the main command). Both current Cursor pins resolve in today's list, so the check is implementable now and would have caught #7237 at /status time.
- Codex: `codex --help` exposes `-m, --model` but no model-list subcommand. Design should probe for an equivalent owning surface; if none exists, adopt a documented per-vendor policy (validate Cursor pins; report Codex ids as unverifiable) rather than silently skipping, per G-Ext-5's failed-confirmation rule.

## Scope notes

- /status is read-only health reporting; an unknown pinned id should degrade soft (report a non-ok line, not abort the skill).
- Whether /implement Step 0's `degraded-tools-gate` should also consume the unknown-model signal (downgrading the affected lane before dispatch, since #7237 bit /implement rather than /status) is a design decision to settle in /design; default expectation is /status-only first.
- Treat the model-list output as untrusted data per G-Ext-1; parse it with a pinned grammar and fail closed on unparseable output.

## Acceptance criteria

- /status output includes per-vendor model-pin resolution when the vendor probe is `ok`.
- A pinned id absent from the vendor's live list yields a non-ok state that names both the id and the owning config constant.
- A vendor with no model-list surface is reported as unverifiable, not silently skipped.
- Tests cover the known-id pass, unknown-id fail, and list-command-failure paths via the injected Runner seam (G-Py-5, G-Py-7), with no live vendor calls in CI.
- CI green.

## Test plan
(no test plan section in plan-file)
