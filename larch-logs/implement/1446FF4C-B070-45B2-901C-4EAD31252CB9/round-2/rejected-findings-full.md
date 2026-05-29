### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: CI validates `--read-tools` argv only, not runtime Read under `--print`
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Harness checks `.meta` argv, not that Read actually runs; hosts ignoring flags could yield silent zero archetypes in production while lint passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional guarded integration test or explicit SECURITY.md contract that CI is argv-only.
  - From cursor-specialist-plan-fidelity-output.txt: Add Read execution probe or document manual verify-external-tool-invocations in PR.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Read-tools scout relies on plan permission mode and argv allowlist without runtime denial tests
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Harness only checks argv; misconfigured or evolving Claude CLI might allow Write/Bash under `--add-dir`, enabling edits in session tmpdir despite prompt preamble.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add verify-external-tool-invocations smoke test that Write/Bash fail; document residual risk or use stricter permission mode.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: `SCOUT_DYNAMIC_ARCHETYPES_SH` / `LAUNCH_*` env overrides can replace binaries
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Compromised operator env can run arbitrary code with Codex auth and review-tmpdir read access during scout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Document trusted-operator-only overrides in SECURITY.md; keep overrides out of production shells.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: `allowedTools` is Read-only; plan mentioned Read/Grep/Glob
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Scout cannot Grep/Glob staged trees if needed; minor mismatch vs plan wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Update plan text or expand allowlist if required.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Default 180s scout timeout may be insufficient for large read-tools diffs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Default 180s timeout is unchanged for `--read-tools` Claude tier on large staged diffs (~900 KB after trim). Read loops can time out; scout emits timeout/claude-failed and zero dynamic reviewers like an intentional empty manifest.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Raise default timeout for read-tools scout launches or scale timeout from staged byte size; consider a distinct status for read-timeout


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: Duplicate scout-JSON probe logic between waterfall and post-winner validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `tier_raw_is_scout_json` duplicates fence/JSON probe logic used again after a waterfall winner; divergent edits can cause inconsistent tier vs post-winner behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Factor a single probe helper shared by waterfall selection and post-winner validation


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Triplicated terminal fail-open KV blocks in multi-tier exhaustion paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `write_empty_manifest` + `emit_kv` blocks are repeated in multi-tier exhaustion paths, making `SCOUT_STATUS` terminal contract harder to keep consistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a small helper that emits the shared fail-open KV envelope


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: `CURSOR_PRESENT` parsed but unused; Cursor tier not in waterfall
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `CURSOR_PRESENT` is parsed but not used in tier selection; issue acceptance still describes Codex→Cursor→Claude while scout implements Codex→Claude only—readers expect a Cursor tier without code path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document API-only flag inline or rename to signal intentional non-use
  - From cursor-specialist-correctness-output.txt: Update issue acceptance or add Cursor tier when launch-review supports staged reads.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Multi-tier terminal `SCOUT_STATUS` vs plan (probe miss + launcher failure → `claude-failed` not `empty`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-state-machine-output.txt
- **Severity**: important
- **Concern**: When Codex probe-misses and Claude launcher fails, terminal block emits `claude-failed` instead of plan/older text expecting `empty` on probe exhaustion. Case (2) is documented/intentional in `scout-dynamic-archetypes.md` and harness `waterfall-probe-claude-fail`, but plan acceptance and operator/diag expectations may disagree—sync docs or change behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Sync issue/plan acceptance with scout-dynamic-archetypes.md or change branch to always emit empty when had_probe_miss.
  - From cursor-specialist-plan-fidelity-output.txt: Emit empty whenever had_probe_miss under --codex-present true; launcher statuses only when every tier failed launch with no probe miss.
  - From dyn-waterfall-state-machine-output.txt: The audited four-way matrix is otherwise implemented as intended and tested where covered: (1) Codex probe-miss + Claude probe-miss → `empty`; (2) Codex probe-miss + Claude launch-fail → `claude-failed` (documented in `scripts/scout-dynamic-archetypes.md:14`, harness `waterfall-probe-claude-fail`); (3) Codex launch-fail + Claude probe-miss → `empty`; (4) both launch-fail → `claude-failed` (last tier). Case (2) intentionally overrides the plan text’s “any probe miss ⇒ `empty`” rule in favor of surfacing the final launcher status.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

