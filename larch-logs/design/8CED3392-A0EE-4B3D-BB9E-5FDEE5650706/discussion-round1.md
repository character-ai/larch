## Decision 1: Scope of issue #3008
- **Question**: Issue #3008 lists three sub-asks (align surfaces, add stale-prose lint, extend test harness). Codebase scan shows surfaces are already aligned on "default to auto-apply with warning" (approval-gates.md:101); SECURITY.md and docs/issue-anchored-plan.md have no Gate B prose; no stale phrases exist today. Which sub-asks are in scope for this SIMPLE-tier design?
- **Resolution**: Sub-asks (2) lint and (3) test only. Skip sub-ask (1) alignment doc-edit since surfaces already match — the real OOS risk is silent doc drift (mitigated by the lint) and the test gap (mitigated by the harness extension). Sub-ask (1) is closed as "verified, no change needed."
- **Source**: user

## Decision 2: Stale-prose lint home
- **Question**: Where should the stale-Gate-B-prose lint live? Existing harness, new standalone, or CI YAML grep step?
- **Resolution**: Extend `scripts/test-design-structure.sh`. The harness already has `contains`/`absent` fixed-string check helpers (`grep -Fq`) covering SKILL.md and approval-gates.md, so adding new `absent` checks for stale Gate B prose patterns reuses the existing fail-fast model without a second CI surface.
- **Source**: user

## Decision 3: Recovery-test home
- **Question**: Where should the jq-merge recovery test coverage live? The four-arm recovery in SKILL.md Step 0b runs jq on `run-params.json` after `write-run-params.sh` succeeds — the helper itself never sees that merge.
- **Resolution**: Two test scripts. (a) Extend `scripts/test-write-run-params.sh` with helper failure-path cases (bad/missing args, enum violations on `--manual-gate-b`). (b) Add a new `scripts/test-step0b-router-flag-recovery.sh` that simulates the SKILL.md Step 0b shell snippet (write-run-params.sh + jq-merge for partition/brainstorm/manual) — covers the actual recovery logic that FINDING_8 and FINDING_9 from #3008 specifically flagged as untested.
- **Source**: user

## Hard constraints (from codebase inspection)
- approval-gates.md line 101 is the canonical Gate B degraded-mode rule: "defaulting to auto-apply unless a true-only manual override is already present." Lint MUST be consistent with this rule — banned phrases must contradict it.
- SKILL.md Step 0b jq-merge: `partition_requested` / `brainstorm_requested` are true-only OR-merges; `manual_gate_b` is **overwritten** from current-run value (so omitting `--manual` clears stale persisted manual mode). The new harness MUST exercise this overwrite-not-merge asymmetry.
- Bash 3.2 portability still applies (BASH_AUTHORING.md §3) — new harness must avoid `declare -A`, `mapfile`, etc.
