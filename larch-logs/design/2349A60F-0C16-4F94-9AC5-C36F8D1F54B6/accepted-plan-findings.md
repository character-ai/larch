### FINDING_1: Anti-halt continuation chain + Step Name Registry missing `2b.5`
- **Reviewers**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements (5 reviewers)
- **Concern**: `skills/design/SKILL.md` line ~28 lists the canonical step-boundary continuation chain (e.g., `2b→3`) and similar continuation prose throughout the file. With Step 2b.5 inserted, those chains become stale and operators following the muscle-memory chain may skip the new sub-step. Additionally, `skills/design/scripts/step-name-registry.tsv` needs a `2b.5` row so breadcrumb short names are normative. Also: the plan text uses `discussion-rounds.md` without the `references/` prefix in places, which can mislead implementers.
- **Proposed resolution**: Update the anti-halt continuation chain to include `2b.5` (`2b→2b.5→3`) and sweep `skills/design/SKILL.md` for other `2b→3`-only continuation prose. Add a `2b.5  plan size` row to `skills/design/scripts/step-name-registry.tsv`. Use repo-relative paths `skills/design/references/discussion-rounds.md` throughout the plan and SKILL insertion text.


### FINDING_10: Step 5d hardcoded `gh issue comment 2672` ships unsafe runtime behavior to consumer repos
- **Reviewers**: Codex-Edge (security), Codex-Innovation (security), Codex-Pragmatic, Codex-Requirements (4 reviewers)
- **Concern**: The plan adds a Step 5d that runs `gh issue comment 2672` unconditionally at the end of every successful `/design` finalize. When `/design` runs in a consumer repository (the typical case for a Claude Code plugin), `gh issue comment 2672` resolves against the hub-default repo — which may not be `character-ai/larch`. This would post deferred-velocity-scope notes to an unrelated public issue #2672 in the consumer's repo, causing spam at best and leaking workflow metadata at worst. The "best-effort" framing does not mitigate the wrong-repo issue.
- **Proposed resolution**: Do NOT add Step 5d to the shipped SKILL.md. Handle the #2672 dependency note as a one-time project-management action OUTSIDE the runtime skill — e.g., post the comment manually during this design's implementation PR, or augment #2672's body via a separate `gh` invocation outside `/design`. If the auto-post is truly required, gate it with: (a) explicit `--repo character-ai/larch`, (b) a once-only sentinel in `~/.cache/larch/`, and (c) a guard that only runs from this specific issue (#2670) — but the preferred resolution is to remove Step 5d entirely.


### FINDING_11: `check-plan-size.sh` KV output must use `emit_kv` to reach FD 3 under `lib-quiet.sh`
- **Reviewers**: Cursor-dyn-script-contract, Cursor-Innovation, Cursor-Requirements (3 reviewers)
- **Concern**: The plan says `check-plan-size.sh` sources `lib-quiet.sh` and `larch_quiet_init`, then "emits KV lines on stdout". Under the quiet-by-default contract, ordinary `printf`/`echo` to stdout is redirected to the quiet log; only `emit`/`emit_kv` reach FD 3 (the contract stream). Naive stdout printing would make the orchestrator's KV capture empty, silently mis-firing branches.
- **Proposed resolution**: Mirror `scripts/emit-plan.sh` exactly: `source "$SCRIPT_DIR/../../../scripts/lib-quiet.sh"`, `larch_quiet_init`, and `emit_kv KEY value` for every machine-readable KV line (`PLAN_LINES`, `DIFF_LINES`, `FILES_COUNT`, `SOFT_TRIGGER_FIRED`, `HARD_TRIGGER_FIRED`, `TRIGGER_REASONS`, plus `PLAN_SIZE_STATUS` on exit-2). Document this contract in `check-plan-size.md` and update the plan's helper spec accordingly. The orchestrator captures the contract stream (FD 3) the same way other helpers do.


### FINDING_12: Helper rc handling specification — exit-2 vs other non-zero
- **Reviewers**: Cursor-dyn-flag-lifecycle, Cursor-dyn-script-contract (×2), Cursor-Requirements, Codex-dyn-script-contract (×2) (6 reviewers)
- **Concern**: The plan's Failure mode 1 says "exits 2 and Step 2b.5 surfaces the error as a warning" but doesn't distinguish exit 2 (validated input-error path with `PLAN_SIZE_STATUS`) from other non-zero exits (internal shell errors, argv parse errors before `PLAN_SIZE_STATUS` can be emitted). Also: the plan's Split-path "$DESIGN_TMPDIR preserved" justification relies on `PLAN_WRITE_OK` gating Step 6 cleanup, but `PLAN_WRITE_OK` is only set in Step 5c — the actual mechanism for early-exit preservation is that execution doesn't reach Step 5 or Step 6 at all.
- **Proposed resolution**: Specify rc handling explicitly in the SKILL.md Step 2b.5 sub-step: `rc 0` → parse KVs and branch; `rc 2` → parse `PLAN_SIZE_STATUS` (single value), print a `**⚠ 2b.5: check-plan-size — <status>**` warning, append captured output to `execution-issues.md` Warnings, continue to Step 3 (no trigger fired); any other rc → treat as internal error, append captured stdout+stderr to `execution-issues.md`, ignore any partial trigger KVs, continue to Step 3. Rewrite the Split-path preservation paragraph to state explicitly that the Split branch exits before reaching Step 5/Step 6, and that `PLAN_WRITE_OK` remains unset (which is correct but not the load-bearing mechanism).


### FINDING_13: Files-count `grep -cE` aborts under `set -e` with zero matches
- **Reviewers**: Codex-Innovation, Codex-Pragmatic, Codex-Requirements (3 reviewers)
- **Concern**: The plan promises `FILES_COUNT=0` for legacy plans with no `### NEW:`/`### UPDATED:`/`### REWRITTEN:` headings. But `grep -cE '...' "$PLAN_FILE"` exits 1 when there are zero matches, and under `set -euo pipefail` (which the plan specifies) the helper would abort instead of emitting `FILES_COUNT=0`. Step 2b.5 would warn and skip the threshold check.
- **Proposed resolution**: Specify a no-match-safe implementation: `FILES_COUNT=$(grep -cE '^### (NEW|UPDATED|REWRITTEN):' "$PLAN_FILE" || true)` per BASH_AUTHORING §1. Alternatively use `awk '/^### (NEW|UPDATED|REWRITTEN):/ {n++} END {print n+0}'`. Add an explicit zero-heading harness case to `test-check-plan-size.sh`.


### FINDING_14: Mutual-exclusion validation must run before Step 0a session-setup, not after
- **Reviewers**: Cursor-dyn-flag-lifecycle, Codex-dyn-flag-lifecycle (2 reviewers)
- **Concern**: The plan says argv parsing and mutual-exclusion rejection happen "in Step 0b", but Step 0b runs AFTER Step 0a session-setup. An invalid invocation like `/design --trivial --partition 2670` would create `DESIGN_TMPDIR`, run `session-setup.sh`, then reject — leaving an orphan tmpdir. The Files-to-modify line says "abort before Step 0", which conflicts with the in-Step-0b placement.
- **Proposed resolution**: Specify a pre-Step-0 flag validation pass (an early argv parse for tier flags + `--partition`) BEFORE `session-setup.sh` runs. The validation pass produces only a hard-error-and-abort decision; it does not initialize state. The actual full Step 0b parsing (which writes `feature-description.txt`, `run-params.json`, etc.) still happens after Step 0a. Document the exact error message (naming both `--trivial` and `--partition`) and add a structural test pin (`test-design-structure.sh`) for the validation order.


### FINDING_15: Step 1c/1d sprawl AskUserQuestion must be Split/Cancel only (no Continue)
- **Reviewers**: Codex-Requirements (1 reviewer)
- **Concern**: The feature description (issue #2670) is explicit: at Step 1c/1d, "the standard Split / Cancel options (no override at this stage since there is no plan yet — the user can refine the feature description)". The plan's Step 1c/1d prose lists options as "Let my panel of agents split this feature for you" / "Continue with current scope" — i.e., Continue (the soft-override option) is offered. This contradicts the feature contract.
- **Proposed resolution**: At Step 1c/1d, the sprawl AskUserQuestion offers exactly two options: "Let my panel of agents split this feature for you" / "Cancel". On Cancel, run the Terminal cost line block, print a cancellation message (`**ℹ /design cancelled by operator (Step 1c/1d sprawl heuristic).**`), exit 0, preserve `$DESIGN_TMPDIR`. On Split, hard-fail per the Split-path procedure (same as Step 2b.5 Split). No Continue option at this stage.


### FINDING_16: Makefile placement guidance line range is stale
- **Reviewers**: Cursor-Pragmatic (1 reviewer)
- **Concern**: The plan says "Place it adjacent to other `test-*` targets that share a harness shard (the existing `test-*` block in the Makefile around line 80-150)." The actual test-harnesses-N shard block lives around lines 168-378 of the current Makefile. An implementer searching the wrong region misses the real shard wiring.
- **Proposed resolution**: Update the plan's Makefile bullet to reference the actual shard block (e.g., "near `test-emit-plan` and other design-script tests in the `test-harnesses-N` shard block, currently around lines 168-378"). Even simpler: name an adjacent target (`test-emit-plan`) and require the new target to be placed alongside it.


### FINDING_17: Test harness needs additional fixtures (zero-heading, multiple-trailer, --partition persistence, --partition+--trivial mutual exclusion)
- **Reviewers**: Cursor-dyn-test-fixture-gap, Codex-dyn-test-fixture-gap (2 reviewers)
- **Concern**: The 11-case harness covers threshold crossings, missing plan, missing trailer, and partial boundary cases. It does NOT cover: zero-heading legacy plan (FILES_COUNT=0 path; tied to FINDING_13), multiple `diff_lines:` lines in body (last-wins or final-non-empty rule; tied to FINDING_4), `--partition` persistence across re-runs (orchestrator-level, not helper-level), `--partition` + `--trivial` mutual exclusion (argv-parse level, not helper-level). The orchestrator-level cases may need a separate harness rather than expanding `test-check-plan-size.sh`.
- **Proposed resolution**: Extend `test-check-plan-size.sh` with cases 12-15 covering helper-owned scenarios (zero-heading, multi-trailer). Add structural pins to `scripts/test-design-structure.sh` or `skills/design/scripts/test-design-driver.sh` for orchestrator-owned scenarios (`--partition` argv parse, mutual exclusion error, persistence read from `run-params.json`).


### FINDING_18: Reviewer-prompt renderer test assertion may not detect the one-line edit
- **Reviewers**: Cursor-dyn-test-fixture-gap, Cursor-Edge (2 reviewers)
- **Concern**: The plan updates `render-plan-review-prompt.sh` line 94 ("Files cited in Files-to-modify subsections..." → "Files cited in `### NEW:`/`### UPDATED:`/`### REWRITTEN:` subsections..."). The existing `assert_contains` in `test-plan-review-prompt.sh` pins "The plan describes the codebase AFTER this PR lands" — that needle survives the edit unchanged, so the renderer change isn't actually covered by the named test.
- **Proposed resolution**: Add a dedicated `assert_contains` for the new heading-named wording (e.g., a literal needle containing "`### NEW:`/`### UPDATED:`/`### REWRITTEN:` subsections"). Or, if the existing needles already provide enough coverage of the renderer logic, drop the renderer change as unnecessary churn. The plan should pick one path and align prose with the test.


### FINDING_2: New `-p`/`--partition` flag missing from public argv surfaces (argument-hint, README, docs/skills.md, plugin.json)
- **Reviewers**: Cursor-Arch, Cursor-Innovation, Codex-Arch, Codex-Pragmatic, Codex-Requirements (5 reviewers)
- **Concern**: The plan adds a row to the compact flag table in `skills/design/SKILL.md` but does not update the `argument-hint:` frontmatter on line ~4, the "Public argv allows only" allowlist sentence, the `README.md` `/design` argv row (around lines 58-61), the `docs/skills.md` argument row, or the `.claude-plugin/plugin.json` description (which mentions /design arguments). Operators read these surfaces for discovery; flag drift across them is the standard repo convention to avoid.
- **Proposed resolution**: Add `-p`/`--partition` to the SKILL.md `argument-hint:` frontmatter, the "Public argv allows only" allowlist sentence in the SKILL.md flag section, the README.md `/design` argv row, the docs/skills.md Arguments line, and the .claude-plugin/plugin.json `/design` description (whichever surfaces reference the public argv). Document the `--trivial` mutual-exclusion rule alongside the other tier rules in each surface that lists arguments.


### FINDING_20: FILES_COUNT regex stricter than scout's heading regex
- **Reviewers**: Cursor-Edge (1 reviewer)
- **Concern**: Scout's wrapper uses `^###\s*(NEW|UPDATED|REWRITTEN)\s*:\s*(.+)$` (tolerant of extra whitespace between `###`, the keyword, and `:`). The plan's helper grep is `^### (NEW|UPDATED|REWRITTEN):` (strict single-space form). Plans using non-canonical whitespace would feed the scout but not the helper, causing FILES_COUNT to undercount.
- **Proposed resolution**: Align the helper regex with the scout regex (`^###[[:space:]]*(NEW|UPDATED|REWRITTEN)[[:space:]]*:` for portable bash 3.2), OR document in `check-plan-size.md` + Step 2b plan-format prose that the strict single-space form (`### NEW: <path>`) is the canonical and required format. Add a harness case verifying the chosen behavior.


### FINDING_21: Add structural test pins for argv mirror + helper-call wiring
- **Reviewers**: Codex-Requirements (1 reviewer)
- **Concern**: `scripts/test-design-structure.sh` covers the SKILL.md structural contract today, but the new flag's docs/script integration isn't covered by structural pins. Regressions in argv documentation, --trivial mutual-exclusion prose, `check-plan-size.sh` call after `ACTION=EMIT_PLAN`, or the no-Continue hard/partition wording could land without any local harness failing.
- **Proposed resolution**: Add grep-style structural pins in `scripts/test-design-structure.sh` (or `skills/design/scripts/test-design-driver.sh` if more appropriate) for: (a) the `-p`/`--partition` row in the compact flag table, (b) the mutual-exclusion prose with `--trivial`, (c) the Step 2b.5 invocation of `check-plan-size.sh` after `ACTION=EMIT_PLAN`, (d) the hard-trigger no-Continue wording. One assertion per pin; matches the existing structural-test style.

End of ballot. 21 findings; 0 distinct OOS observations (all OOS items overlap with FINDING_2 and are subsumed by in-scope precedence).

### FINDING_3: HARD trigger override-by-`--partition` defeats the no-override contract
- **Reviewers**: Cursor-Arch, Codex-Edge, Codex-Requirements (3 reviewers)
- **Concern**: The plan's Step 2b.5 control flow has `--partition` forcing the soft branch unconditionally. When `HARD_TRIGGER_FIRED=true` AND `--partition` is set, the operator could see "Continue with current scope" as an option — which bypasses the no-override contract from the feature description ("Hard trigger ... AskUserQuestion: Split / Cancel, no override"). A >800-line or >1500-diff-line plan invoked with `--partition` would still allow Continue.
- **Proposed resolution**: Evaluate hard triggers BEFORE the `--partition` override. The branch order must be: (a) if `HARD_TRIGGER_FIRED=true`, always show Split/Cancel (no Continue) regardless of `--partition`; (b) only when no hard threshold fired, treat `--partition` as a soft trigger (Split/Continue). Update the plan's Step 2b.5 sub-step bullets to reflect this ordering.


### FINDING_4: PLAN_LINES vs DIFF_LINES divergence with multiple `diff_lines:` lines; align with `emit-plan.sh` final-non-empty-line contract
- **Reviewers**: Cursor-Arch, Cursor-dyn-script-contract (×2), Cursor-Pragmatic, Codex-Arch, Codex-dyn-script-contract, Codex-dyn-test-fixture-gap, Codex-Innovation (8 reviewers)
- **Concern**: The plan defines `PLAN_LINES` as `wc -l` after removing "the trailing `diff_lines:` line" (singular) while `DIFF_LINES` is parsed from "the last line matching `^diff_lines: [0-9]+$`" (anywhere in the file). These two rules disagree when a plan has prose containing `diff_lines: N` and a separate trailer: `PLAN_LINES` would include the prose line (inflating the count) while `DIFF_LINES` would still grab the last match. Also, `scripts/emit-plan.sh:51-58` requires the trailer to be the final non-empty line — a stricter contract than "last matching anywhere". A helper that accepts plans `emit-plan.sh` rejects creates two validators with different valid-plan grammars.
- **Proposed resolution**: Align `check-plan-size.sh` with `emit-plan.sh`: require the trailer to be the final non-empty line and parse `diff_lines:` from that line only. Define `PLAN_LINES` as `wc -l` after removing that single trailer line. Document this rule in `check-plan-size.md` and `references/flags.md`. Add a harness case where prose contains `diff_lines: 100` but a separate trailer holds the canonical value, asserting both `PLAN_LINES` (correctly counted) and `DIFF_LINES` (=trailer value).


### FINDING_5: `TRIGGER_REASONS` ordering claim is internally inconsistent
- **Reviewers**: Cursor-dyn-script-contract, Cursor-dyn-test-fixture-gap, Cursor-Innovation, Cursor-Requirements, Codex-dyn-script-contract, Codex-dyn-test-fixture-gap (6 reviewers)
- **Concern**: Plan cases 5 and 8 expect `TRIGGER_REASONS=plan-body-lines,diff-lines,files-count` and label it "lexicographic". The actual lexicographic ascending order of those tokens is `diff-lines,files-count,plan-body-lines`. Tests would fail until the expected string or the implementation is changed.
- **Proposed resolution**: Pick one of two options and propagate it across the plan, helper spec, `check-plan-size.md`, and harness fixtures: (a) emit and assert true lexicographic order `diff-lines,files-count,plan-body-lines` (with `LC_ALL=C sort` to make this portable), OR (b) define a fixed priority order (e.g., the order thresholds are checked: plan-body-lines, diff-lines, files-count) and drop the "lexicographic" claim. Document the chosen rule explicitly so implementation and tests stay aligned.


### FINDING_6: Test case 11 boundary coverage incomplete — only diff_lines 600/601 enumerated
- **Reviewers**: Cursor-Arch, Cursor-dyn-test-fixture-gap, Cursor-Requirements, Codex-dyn-test-fixture-gap (4 reviewers)
- **Concern**: Case 11 in the harness lists "Boundary `==` cases" but only spells out `diff_lines: 600` (no trigger) vs `diff_lines: 601` (triggers). The Edge cases section promises strict `>` semantics for ALL three soft thresholds plus both hard thresholds (250/251 plan-body-lines, 600/601 diff-lines, 8/9 files-count, 800/801 plan-body-lines hard, 1500/1501 diff-lines hard). Without explicit fixtures, several boundaries could ship untested.
- **Proposed resolution**: Expand case 11 (or add cases 12-15) with explicit equality and plus-one fixtures for each of the five numeric thresholds (250/251, 600/601, 8/9, 800/801, 1500/1501), asserting strict-`>` behavior and that hard-tier precedence is correctly applied when both soft and hard thresholds cross.


### FINDING_7: `--partition` flag has no durable session storage — re-fire after Gate B / discussion can lose the flag
- **Reviewers**: Cursor-dyn-flag-lifecycle, Cursor-Edge, Codex-dyn-flag-lifecycle (3 reviewers)
- **Concern**: After Step 0b argv parse, the only durable router artifact is `run-params.json` (written by `write-run-params.sh`), whose schema currently has no `partition` field. Subsequent Bash blocks restore `source-env.sh` keys but not raw argv. When Step 2b.5 re-fires after Gate B's Apply or post-plan discussion's plan revision, the orchestrator's "is `--partition` set?" check has no persisted source — it relies on prompt-side mental state, which is fragile across turns and subagents.
- **Proposed resolution**: Add a persisted key — either extend `write-run-params.sh` schema with `partition_requested: <bool>` (and update `scripts/write-run-params.md` + `scripts/test-write-run-params.sh`), or write an exported `DESIGN_PARTITION_REQUESTED=true` line via `scripts/write-design-current-env.sh` (and update its sibling `.md` + harness). Update the plan to require Step 2b.5 to read that key, not raw argv. The persisted-key approach is preferred because `run-params.json` is the canonical router artifact.


### FINDING_8: Step 1c/1d semantic sprawl hook must be placed in `references/discussion-rounds.md`
- **Reviewers**: Codex-Arch, Codex-dyn-flag-lifecycle (×2 — Finding 3 and Finding 4), Codex-Innovation, Codex-Pragmatic (5 reviewers)
- **Concern**: The plan adds the Step 1c/1d sprawl heuristic prose only to `skills/design/SKILL.md`, but SKILL.md delegates both step bodies to `skills/design/references/discussion-rounds.md` via the MANDATORY directives ("Execute the Step 1c body in that file" / "Execute the Step 1d body in `discussion-rounds.md`"). An orchestrator following the normative reference will never see the sprawl hook and will proceed straight to Step 2a without ever firing the partition offer.
- **Proposed resolution**: Add `skills/design/references/discussion-rounds.md` to the plan's Files-to-modify section. Place the semantic sprawl AskUserQuestion + Split-path handoff directly in the Step 1c body (after the recommended-question paragraph) and the Step 1d body (after each user answer, before re-prompting). The SKILL.md should only point to the canonical reference, not contain a duplicate hook.


### FINDING_9: Gate B and post-plan discussion plan-revision paths must call Step 2b.5 after `ACTION=EMIT_PLAN`
- **Reviewers**: Cursor-Pragmatic, Codex-Arch, Codex-dyn-flag-lifecycle, Codex-Edge, Codex-Innovation, Codex-Pragmatic (6 reviewers)
- **Concern**: `references/approval-gates.md` Gate B (Apply all / Go through each) and `references/discussion-rounds.md` post-plan discussion sub-round both currently say "re-emit `ACTION=EMIT_PLAN`" and proceed (to Step 3b or to the caller). They do NOT mention the new Step 2b.5 threshold check. Plans that grow past thresholds after Gate B Apply or after a discussion-driven revision would bypass the new partition gate entirely.
- **Proposed resolution**: Add `skills/design/references/approval-gates.md` and `skills/design/references/discussion-rounds.md` to Files-to-modify. Update Gate B Apply all / per-finding Apply paths in `approval-gates.md` to require running Step 2b.5 (the named procedure) immediately after the post-revision `ACTION=EMIT_PLAN`, before advancing to Step 3b. Likewise update the post-plan discussion revision authority in `discussion-rounds.md` to call Step 2b.5 after each plan-revision `ACTION=EMIT_PLAN`. Reference Step 2b.5 as a named procedure callable from each plan-revision boundary.


