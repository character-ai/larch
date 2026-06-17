### FINDING_1: SKILL.md Step 18 / NEVER #17 contracts contradict consolidated wrapper
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan moves Step 18 to a consolidated `step-18.sh` with marker-only body emission and wrapper-owned breadcrumbs, but `skills/implement/SKILL.md` still carries live orchestrator instructions that conflict: NEVER #17 (line 63) keeps a Step 18 Read-fallback carve-out; Step 18a (line 860) still mandates a prompt-side no-stall skip breadcrumb; Step 18b (lines 880–892) still requires Read-based `summary-final.md` emission and a separate `.step17-emitted` write. The plan’s `### UPDATED: skills/implement/SKILL.md` section does not explicitly require removing or replacing these blocks. An implementer can leave both contracts in place and the orchestrator may duplicate breadcrumbs, follow the stale Read path after teardown when the tmpdir is gone, or drop the no-stall skip breadcrumb inside collapsed tool output if orchestrator relay is not pinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the ### UPDATED: skills/implement/SKILL.md section, explicitly replace NEVER list item 17 (~line 63) to match the new Step 18 marker-extraction contract and remove the Read-fallback carve-out for Step 18
  - From Cursor-Innovation: Add an explicit deletions checklist under ### UPDATED: skills/implement/SKILL.md: drop 860 skip print, replace 880-892 Step 18b emit contract with marker-only finalize stdout parsing, and align NEVER #17 Step 18 bullets with wrapper-owned .step17-emitted
  - From Cursor-Pragmatic: Keep prompt-side skip print in `SKILL.md` when `STALL_RECOVERY_REQUIRED=false`, or add the skip line to the gate stdout relay list alongside `RENAME_*` / `ISSUE_URL`

### FINDING_2: Finalize marker printing can abort before teardown under `set -e`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan folds marker printing with closing token/timing marks and `implement-finalize teardown` under the same `set -euo pipefail` script as retirees. A failed `cat` of `summary-final.md` (mirroring `step-16-17.sh` `print_summary_markers`) can exit before token/timing marks and teardown, leaving `$IMPLEMENT_TMPDIR` and session pointers uncleared (#3425 violation).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Wrap marker printing in `set +e` (or `cat ... || true`) and always run closing marks, `_restore_finalize`, and teardown afterward, matching `step-16-17.sh` non-aborting marker behavior.

### FINDING_3: In-memory stall-layer resolution ambiguous vs `_stall_layer_active`
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan applies `_stall_layer_active` to decide `STALL_RECOVERY_REQUIRED` but says memory comes from `step-18a-gate.sh` sources. The retiree only accepts `true|false` in `--stall-tracking-memory` (`step-18a-gate.sh:65-68`); other non-empty values silently stay `false` in the emitted KV while disk/finalize/session use broader activation. A non-canonical in-memory `STALL_TRACKING` value can be dropped and skip recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Pin memory resolution as: use the `--stall-tracking-memory` arg when non-empty, else `${STALL_TRACKING:-false}`, with no `true|false`-only case filter; run `_stall_layer_active` on the emitted `STALL_TRACKING_MEMORY` value.

### FINDING_4: No-stall path may violate one-Bash-call acceptance criterion
- **Reviewer(s)**: Codex-Generic
- **Severity**: blocking
- **Concern**: The binding issue acceptance requires one `step-18.sh` Bash call on the no-stall path, but the proposed SKILL flow still requires prompt-side orchestration between `--phase gate` and `--phase finalize`, changing the contract from one Bash call to two Bash calls plus orchestrator work between them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Restore the one-call no-stall wrapper contract, or return for explicit rescoping before implementing this plan if Step 18a.5 must remain prompt-side
