## Plan

## Approach

Compress only the two inline anti-halt banners.

Keep these verbatim or semantically intact:
- `**Anti-halt continuation reminder.**`
- the skill-specific step chains
- all Critical boundary callouts
- all non-sequential control-flow carve-outs
- the `/implement` pointer: `→ shared/subskill-invocation.md#anti-halt`

Do not edit `skills/shared/subskill-invocation.md`.
Do not edit `scripts/test-anti-halt-banners.sh`.

## Files to modify/create

### UPDATED: `skills/implement/SKILL.md`

Replace the current long banner line near the top with a shorter line that keeps:
- the contract token
- child `Skill` calls and numbered-step `Bash` helper coverage
- Immediate-background notification semantics
- Preflight through Step 18 scope
- all existing Critical and Terminal boundary sentences
- the shared anchor pointer

Cut duplicated shared-anchor rationale:
- verbose cleanup-output/status-message examples
- "strictly subordinate" detail beyond the concise carve-out
- normal sequential continuation explanation
- generic relevant-checks rationale beyond one concise clause

### UPDATED: `skills/design/SKILL.md`

- numbered-step `Bash` helper and visible-output coverage
- **Immediate-background notification semantics**, including the in-flight yield-after-launch-ack clause: `That yielding is NOT a halt` (mirror `skills/implement/SKILL.md` line ~14 and current `skills/design/SKILL.md` line ~29)
- the full sub-step chain: `1c→1d→1d.5→1d.7→2a→2b→2b.5→3→3.5→3b→4→4b→5→5b→5b.5→5c.1→5c.5→5c.7→5c.8→6`
- Step 1d.5 and Step 1d.7 discussion-loop exception
- approval-gate re-entry carve-outs
- Gate C Approve continuation
- Step 2b intermediate-deliverable warning
- Step 5b.5 architecture timing
- Step 2b.5 before Step 3 boundary
- concise explicit non-sequential carve-out
- **compressed Step 5c / Final-summary terminal boundary** with dual-profile wording:
  - after Step 5c `python/cli.py design step5c` returns (`_publish_rc` 0, 1, or 3) or after any cancellation Final summary block writes a non-empty summary file, emit only via `skills/shared/final-summary-emit.md`; never free-form recap ("Design complete.", artifact bullets, cost paraphrase); **not** gated on `python/cli.py design render-final-summary` exit 0
  - **preserve verbatim** inside the banner (compression may shorten surrounding prose only): `marker-first profile for completed Step 5c task output when _publish_rc is 0, 1, or 3`
  - cancellation outcomes follow the site-specific profile in `final-summary-emit.md` (file-only at Step 0b cancel routes vs marker-first after completed background fences)

Cut duplicated or locally restated guidance:
- `Step 1e Gate A is reachable only via re-entry...`, because Step 1e owns that detail
- verbose examples inside the Step 5c terminal cluster (e.g. `~$10.46`, long profile enumeration); keep the compressed dual-profile terminal-boundary sentences above, not the full elaboration
- shared-anchor duplicate clauses about normal sequential continuation
- generic halt-rationale examples already covered by the shared anchor

## Edge cases

- Preserve the exact contract token so `scripts/test-anti-halt-banners.sh` still passes.
- Preserve the exact lint-pinned substring `marker-first profile for completed Step 5c task output when _publish_rc is 0, 1, or 3` in the always-loaded banner so `scripts/test-render-cost-line-callsites.sh` (via `make lint`) still passes.
- Preserve `That yielding is NOT a halt` in the `/design` banner; pre-Step-3 paths have no other copy of this Immediate-background rule.
- Do not collapse Step 5c terminal emit into a single profile; completed Step 5c handoff uses marker-first; cancellation outcomes use the site-specific profile per `final-summary-emit.md`.
- Do not remove any `/design` non-sequential re-entry path.
- Do not weaken Immediate-background behavior.
- Do not make `/design` depend on reading the shared anchor at runtime.
- Do not remove the Step 5c terminal-handoff rule from the always-loaded banner; Step 5 body repeats it but may fall out of context after long Step 3 review loops.

## Failure modes

- Over-compression can remove a real skill-specific boundary (especially Step 5c dual-profile terminal emit rules, `That yielding is NOT a halt`, or Critical boundaries).
- Rewording the contract token can break `test-anti-halt-banners.sh`.
- Paraphrasing the lint-pinned `marker-first profile for completed Step 5c task output when _publish_rc is 0, 1, or 3` substring can pass `test-anti-halt-banners.sh` yet fail `make lint`.
- Collapsing cancellation and completed Step 5c emit into one profile can push operators to marker-first on file-only cancel exits.
- Moving the rule to the shared file only would fail the turn-1 inline requirement.
- Trimming without measuring can miss the roughly-halve context-cost goal while still passing lint.

## Testing strategy

Run:
- `bash scripts/test-anti-halt-banners.sh`
- `make lint`

**Manual acceptance check (no new script):** before editing, capture word or byte counts for each anti-halt banner paragraph (`skills/implement/SKILL.md` line ~14, `skills/design/SKILL.md` line ~29). After compression, re-measure and confirm each banner is roughly half the baseline (~377→~190 words for `/implement`, ~573→~285 words for `/design`) while preserving every item in the keep lists above, including `That yielding is NOT a halt`, the dual-profile Step 5c terminal boundary, and the verbatim lint-pinned marker-first substring. Record before/after counts in the PR description or commit message.

No Python tests are required unless implementation changes Python, which this plan does not require.

## Acceptance

All three plan-review slots (Cursor-Pragmatic, Cursor-Requirements, Codex-Generic) returned zero in-scope findings. Plan is accepted as written.

review_status: ok
rounds_completed: 3
diff_lines: 4
