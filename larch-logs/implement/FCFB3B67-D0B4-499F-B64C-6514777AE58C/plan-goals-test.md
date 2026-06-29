## Goal
Implement issue #5837: [IMPLEMENTING] [BUG] Code-review voters lack a uniform runtime waterfall (voter-1 + Claude ballot).

## Implementation Plan
## Summary

The code-review voter panel (`/implement` Step 5, `/review` Step 2) does not have a working three-tier waterfall for **all** voters. The waterfall keys on a **static pre-launch availability probe** (binary present + auth), not on **actual runtime success**, and the three voter slots are not treated uniformly:

- **Voter-1** is launched once, *outside* the real waterfall, and is **never re-dispatched** when its tool fails at runtime. Under the current Cursor unpaid-invoice (`ActionRequiredError`) outage — which passes the probe but hard-fails on the first API call — voter-1 is simply dropped, degrading the panel from 3 judges to 2.
- **Voters 2/3** *do* waterfall (Cursor/Codex → other external → Claude), but the terminal **Claude tier for code voters is not granted read access to the ballot file**, so when both external tools are down and Claude is the only substitute, it can hit a permission prompt (or drift to a non-grammar format), gets discarded as ≥80% `JUDGE_ERROR`, and the panel collapses to **0 judges** ("main-agent-required").

Operator intent: voters should be treated **uniformly** and **all use the waterfall** — if a voter tool is unavailable *for any reason* (including runtime/billing failure), its substitute is spawned, and if that one is unavailable, the third is tried. Cursor → Codex → Claude must hold at runtime, and the Claude tier must actually be able to vote.

## Original report

Reported after a "waterfall backup for voters/judges" was merged (follow-up to issue #5817) and observed to be buggy under a live Cursor billing outage.

Self-investigation of a completed run (operator-supplied):

> The waterfall fired correctly but selected Cursor — because the billing block only triggers on actual API calls, not the availability probe. So `cursor_present=True` at dispatch time, voter-1 launched against Cursor, Cursor hard-blocked with the unpaid invoice error, and there was no post-launch retry to Codex. What worked: the waterfall logic in `_launch_voter1` ran. voter-2 and voter-3 both went to Codex and succeeded. The run degraded to a 2-judge panel. What didn't work: the waterfall covers static unavailability (not installed, not authenticated). It has no runtime-failure fallback path — once voter-1 is dispatched to Cursor and Cursor exits 1, the slot is dropped, not re-dispatched to Codex.

Two additional operator observations:

1. In some cases Claude was spawned as the substitute (the waterfall is supposed to be Cursor → Codex 5.4-mini → Claude), Claude produced corrupted/unparseable results, and was discarded as a voter, resulting in an **empty voter panel**. Root cause why Claude failed in the voter job.
2. Desired end state: in **all** cases where an agent is spawned in `/design` or `/implement` to vote on review suggestions, there must be a functioning waterfall backup model — if the agent is unavailable for any reason, its substitute is spawned, and if that one is unavailable, the third is tried.
3. Direction for the fix: **voters should be treated uniformly, and should all use the waterfall.**

## Reproduction scenario

Environment trigger (currently live): Cursor CLI authenticates and is on `PATH` (so the probe reports `cursor_present=true`), but the Cursor account has an unpaid invoice, so every Cursor agent call exits 1 with 0 bytes and `ActionRequiredError: You have an unpaid invoice`.

- **Mode A (degrade to 2 judges):** Run `/implement` (or `/review --diff`) on any change with Codex available. Voter-1's primary tool is Cursor; it launches against Cursor, Cursor exits 1, and the slot is dropped with no re-dispatch. Voters 2/3 run on Codex and succeed → 2-judge "unanimous-2" panel.
- **Mode B (degrade to 0 judges):** Same trigger but with Codex *also* unavailable for the run. The voter waterfall falls through to Claude; the code-voter Claude is not granted ballot read access (and/or drifts to a table format); its output is ≥80% `JUDGE_ERROR` and is removed from quorum → "0 judges available. Panel tier: main-agent-required."

No code change was needed to reproduce; both modes are already present in committed run logs (see Evidence). A faithful unit reproduction: force a runtime nonzero exit for the voter-1 tool and assert the slot is dropped rather than re-dispatched; and launch a code-voter Claude tier and assert it cannot read the ballot path without a permission prompt.

## Expected behavior

- All three voter slots are treated **uniformly** and **all flow through the same waterfall** (`dispatch_waterfall`): primary → other external → Claude.
- A **runtime** failure (nonzero exit, empty output, or billing-class `ActionRequiredError`) on any voter tier triggers re-dispatch to the next tier, exactly like a static-unavailable tier does today.
- The terminal **Claude** tier can actually perform the vote: it is granted read access to the ballot file (as the design plan-voter path and the Codex/Cursor `--add-dir` path already are), so it does not hit a permission prompt.
- Net result: a transient single-vendor outage (Cursor billing) degrades the panel by at most the diversity of that vendor, never to 0 usable judges.

## Observed behavior

- **Voter-1**: dispatched once to Cursor, Cursor exits 1 (billing), slot dropped, **no re-dispatch** → panel degrades 3 → 2 judges.
- **Voters 2/3**: waterfall works for static unavailability and for runtime collector failures, but when it reaches the Claude tier for code voters, Claude is launched without `--read-tools-add-dir`/`--add-dir`, so the ballot Read can hit a permission prompt → Claude emits "I cannot read the ballot…" (or a Markdown table instead of the vote grammar) → ≥80% `JUDGE_ERROR` → voter removed → panel degrades to **0 judges**.

## Root cause analysis

Unifying cause: the voter waterfall is gated on a **static pre-launch probe** (binary present + auth) rather than **runtime success**, and voter-1 is not routed through the shared waterfall at all.

**Mode A — voter-1 has no runtime fallback.** `_launch_voter1` (`python/larch/agents/agent_voters.py:321-366`) selects the first *probe-available* tool via `_first_launch_base_tool_for_slot` (`agent_voters.py:222`) / `_launchable_base_tools_for_slot` (`agent_voters.py:199`) and fires a single subprocess (`_launch_voter1_external`, `agent_voters.py:408`). The result is collected at `voter1_process.wait()` (`agent_voters.py:725`) and, on failure, only logged by `_append_voter1_failure` (`agent_voters.py:463`) — the slot is dropped, **never re-dispatched**. Voters 2/3 instead flow through `agent_waterfall.py` `dispatch_waterfall` (phase1→phase2→phase3, lines `1004-1190`), where `_collect_phase` (`agent_waterfall.py:784`) + `_apply_collector_block` (`agent_waterfall.py:723`) cascade a runtime collector failure to the next tier. Cursor's billing block is a *runtime* failure (exit 1, 0 bytes) that the probe cannot see, so only the slots that go through `dispatch_waterfall` recover — and voter-1 doesn't.

**Mode B — the Claude tier for code voters can't read the ballot.** The ballot is referenced **by path**, not inlined ("Read the ballot from this path: {ballot_file}", `python/larch/rendering/rendering.py:1205`), so every voter must Read the ballot file from disk. Codex/Cursor are granted access via `--add-dir <round-dir>` (`python/larch/agents/_review_launcher.py:798`). But the code-voter Claude path passes **neither** `--read-tools-add-dir` **nor** `--context-files`:

- `_launch_claude_voter` (`agent_voters.py:369`) — bare `launch-claude-review`, no read grant.
- phase-3 Claude branch in `agent_waterfall.py:471-480` — same, no read grant.

So `launch_claude_subprocess_main` skips the `--add-dir <dir> --allowedTools Read --permission-mode plan` grant (`python/larch/agents/_claude_runner.py:366-375`, gated by `if args.read_tools`, which is only set when `--read-tools-add-dir` is forwarded at `_claude_runner.py:540-541`). The **design** plan-voter/review path **does** pass `--read-tools-add-dir` (`python/larch/review/plan_review_panel.py:673` and `:924`; also `plan_scout.py:495`), which is why design Claude voters mostly succeed and code Claude voters can hard-block. A voter whose output is ≥80% `JUDGE_ERROR` is removed from quorum (`python/larch/review/voting.py:1988`, `_DEFAULT_JUDGE_ERROR_PARSE_THRESHOLD = 0.8`; classification `voting.py:1356`/`1383`; `check_voter_parse_rate` `voting.py:2004`). Two discard causes observed: (1) permission-prompt block reading the ballot, and (2) format drift — Claude emitting a Markdown table instead of `FINDING_n: YES CORRECTNESS=… SEVERITY=… QUALITY=… UNCERTAIN=…`, despite an explicit "do NOT format votes as a markdown table" instruction (`rendering.py:1219`).

**Honesty caveat (scoping the permission angle).** Across 883 implement Claude-voter outputs in committed logs, 828 parsed fine — the permission block is the *rare tail*, not universal. The ballot Read usually succeeds; the hard block is permission-state/environment dependent. So Mode B's permission angle is a latent gap that bites under the current both-vendors-down condition, not a constant. It must still be closed so Claude is a reliable terminal tier. Format drift (cause 2) is a model-adherence issue the prompt already warns against; it is secondary to the read-access gap.

## Evidence

- **Cursor billing failure (probe-invisible, runtime-fatal):** `larch-logs/implement/B3DAAA1E-FB13-4358-A0DB-1FE62879AB42/vendor-failure-diagnostics.txt`, `693B7D00-2FD0-4F5A-9B88-80181EC33935`, `6748376C-9390-4B5D-B847-1CDB8C6EBF2F` — `ActionRequiredError: You have an unpaid invoice … exit code 1, output 0 bytes`, recorded at both `review Step 2 cursor-review` and `implement Step 5 cursor-review`.
- **Mode A (voter-1 dropped, no fallback):** `B3DAAA1E-FB13-4358-A0DB-1FE62879AB42/round-1/voter1-diag.txt` = `voter1_rc=1`, `output_bytes=0`, unpaid-invoice diag. `…/round-1/voting-tally.md` shows `cursor-validity | Eligible 0 | … | Missing 3` and a degraded 2-judge panel (`unanimous-2`). The voter-2/3 manifest `…/round-1/code-voter-slots.ndjson` contains only `voter-2` and `voter-3` (both `codex`) — voter-1 is not in the waterfall manifest.
- **Mode B (permission block):** `larch-logs/implement/A6172AC2-1871-4B6D-A47B-AF77F3D427D0/round-1/claude-vote-output.txt` = "I cannot read the ballot — every attempt to access `findings.md` triggers a permission prompt that hasn't been approved yet … add `~/.cache/larch/sessions/**` to the read-allowed paths"; `claude-vote-output-parse-rate-diag.txt` = `judge_error_count=48` / `total_findings=48` (100% `JUDGE_ERROR`).
- **Mode B (format drift):** `larch-logs/design/86E48928-1889-457B-92BC-8F3A50E145DC/claude-vote-output.txt` = Markdown table (`| Item | **YES** | …`); `claude-vote-output-parse-rate-diag.txt` = `judge_error_count=8` / `total_findings=8`.
- **Empty-panel end state:** `larch-logs/implement/1C5D52C6-D024-4D58-8289-0A0240A8CB2A`, `7376649D-3F29-447F-80D2-7B02F5D0AA0E`, `AF4CCD2A-1BA1-4723-BCDB-165C8F29B2C8` round-1 `voting-tally.md` — "1 voter slot(s) emitted narrative-only output (parse-rate ≥80% JUDGE_ERROR) and were removed from the effective quorum." → "0 judges available. Panel tier: main-agent-required. Manual adjudication needed."
- **Asymmetry confirmed by code:** `python/larch/agents/agent_voters.py` and `agent_waterfall.py` never pass `--read-tools-add-dir`; only `plan_review_panel.py:673,924`, `plan_scout.py:495` do. The `#5817` voter-1 comment (`agent_voters.py:329`) confirms voter-1's bespoke probe-time selection.

## Affected files

- `python/larch/agents/agent_voters.py` — the code-voter dispatcher; hosts the bespoke one-shot `_launch_voter1` (no runtime fallback) and `_launch_claude_voter` (no ballot read grant). Primary file to change.
- `python/larch/agents/agent_waterfall.py` — the shared 3-phase waterfall used by voters 2/3; the phase-3 Claude branch (`_launch_slot`, `:471-480`) also omits the ballot read grant. Candidate home for unified voter-1 dispatch.
- `python/larch/agents/_claude_runner.py` — `launch_claude_review_main` / `launch_claude_subprocess_main`; `--read-tools-add-dir` gates the `--add-dir/--allowedTools Read/--permission-mode plan` grant (`:366-375`, `:540-541`).
- `python/larch/agents/_review_launcher.py` — Codex/Cursor `--add-dir <round-dir>` precedent (`:798`).
- `python/larch/review/plan_review_panel.py` (`:673`, `:924`), `python/larch/design/plan_scout.py` (`:495`) — design path that already grants Claude ballot read access; reference implementation and a place to check for the same voter-1 uniformity gap.
- `python/larch/review/voting.py` — `JUDGE_ERROR` parse-rate gate (`:1988`, `:2004`); explains the discard-to-empty-panel mechanism.
- `python/larch/rendering/rendering.py` — ballot referenced by path (`:1205`) and the anti-table format instruction (`:1219`).
- Tests: `python/tests/agents/test_agent_voters.py`, `python/tests/agents/test_agent_waterfall.py` — where regression coverage should land.

## Suggested fix(es)

Per operator direction — **treat all voters uniformly; all voters use the waterfall.** Informational for `/design`/implementers; the coder decides specifics.

1. **Unify all three voter slots under `dispatch_waterfall`.** Remove the special-cased one-shot `_launch_voter1` path and add voter-1 to the same slots manifest (`code-voter-slots.ndjson`) that voters 2/3 use, so every voter gets phase1 (primary) → phase2 (other external) → phase3 (Claude) with **runtime** collector-failure cascade. This single change closes Mode A and makes runtime failure (including Cursor billing exit 1) re-dispatch to the next tier. Preserve the parallelism intent of #5448 (voter-1 ran concurrently with the 2/3 waterfall) by launching all slots together rather than serially.
2. **Grant the Claude voter tier ballot read access in the unified waterfall.** In the Claude launch path used by voters (the phase-3 branch in `agent_waterfall.py:471-480`, and any remaining `_launch_claude_voter`), pass `--read-tools-add-dir <round-dir>` (and/or forward the ballot as a `--context-files` entry), mirroring `plan_review_panel.py`. This removes the permission-prompt block so Claude is a reliable terminal tier.
3. **(Hardening)** Classify billing-class / `ActionRequiredError` as a runtime-unavailable signal (similar to `is_quota_failure`) so the collector treats it like quota and skips Cursor faster instead of burning a launch each slot.
4. **Regression tests:** (a) a runtime Cursor failure on every voter slot re-dispatches Cursor → Codex → Claude; (b) a code-voter Claude tier can read the ballot without a permission prompt and emits parseable grammar; (c) a both-external-down run yields a Claude-only panel that is *non-empty* (votes parse), not "0 judges".

## Open questions

- Should voter-1 be folded into the existing `code-voter-slots.ndjson` manifest + `dispatch_waterfall` call, or should a thin shared helper dispatch all three slots? The former is the smallest change toward "all voters use the waterfall"; confirm it preserves the #5448 concurrency property (voter-1 in parallel with 2/3).
- For the Claude tier, is `--read-tools-add-dir <round-dir>` sufficient, or should the ballot also be forwarded as `--context-files` (defense in depth against permission-state variance)? The design path uses `--read-tools-add-dir`; matching it is the conservative choice.
- Does the `/design` plan-voter path (`plan_review_panel.py`) have the same voter-1 *runtime-fallback* gap even though it already grants ballot read access? It should be checked as part of "uniform" voter handling.
- Should format drift (Claude Markdown table) be hardened beyond the existing prompt instruction (e.g., a one-shot reformat retry on ≥80% JUDGE_ERROR before discard), or is that out of scope for this fix?

## Test plan
(no test plan section in plan-file)
