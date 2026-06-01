Aggregating reviewer findings: verifying overlap by reading the cited locations so merged concerns stay accurate.
Structured aggregator output (3 findings after merging the duplicate empty-`SESSION_ID` validation reports from Cursor-Innovation and Cursor-Pragmatic):

### FINDING_1: Anti-halt gates verbatim emit on helper exit 0
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The global anti-halt reminder at `skills/design/SKILL.md:29` still requires helper exit 0 before the verbatim `final-summary.md` emit. After Step 5c extraction via `design-publish.sh`, the driver can exit 1 (including plan-block-write failure) while `final-summary.md` is non-empty. Agents that treat line 29 as normative may skip the mandatory verbatim emit even though the post-driver non-empty file gate in Step 5c should still apply.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the SKILL.md update, align the line 29 anti-halt clause with the post-driver non-empty FINAL_SUMMARY_PATH gate; add or repoint a grep in scripts/test-render-cost-line-callsites.sh if dropping the old helper-exit-0 pin at line 64

### FINDING_2: `SESSION_ENV_PATH` unset / resolve order in `design-publish.sh`
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: In the planned `skills/design/scripts/design-publish.sh`, `SESSION_ENV_PATH` is referenced before assignment, and plugin-root resolution is ordered before `DESIGN_TMPDIR` canonicalization. Under `set -u`, the driver can abort on the first `phase_driver_resolve_plugin_root` call (unbound variable), or resolve plugin root before `cd … && pwd -P`, so the orchestrator may see exit ≠ 2 and abort before result-env parse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add `DESIGN_TMPDIR="$(cd "$DESIGN_TMPDIR_ARG" && pwd -P)"` then `SESSION_ENV_PATH="$DESIGN_TMPDIR/session-env.sh"` then `PLUGIN_ROOT="$(phase_driver_resolve_plugin_root …)"` matching `design-init-runparams.sh:134-139`

### FINDING_3: Empty `--session-id` blocked if init validators are copied verbatim
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: Planned `design-publish.sh` argv text says to copy validation helpers from `design-init-runparams.sh`, but the plan also requires `--session-id` to be present yet empty for publish-skip, `WARN=`, and rename-skip branches. `design-init-runparams.sh` uses `validate_plain_scalar` (rejects empty) and `[[ -n "$SESSION_ID" ]]` (see ~29–34, 113–114, 131). Copying those helpers into `design-publish.sh` would make empty `SESSION_ID` exit 2 and break the planned skip paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add validate_session_id that only rejects newline/CR (empty allowed); do not reuse validate_plain_scalar or the init non-empty SESSION_ID gate; pin empty SESSION_ID in test-design-publish.sh
  - From Cursor-Pragmatic: Add a session-id validator that only rejects embedded newline/CR; do not require non-empty; document in design-publish.md; cover with test-design-publish.sh SESSION_ID empty case

---

**Merge notes (for voters, not part of machine output):**
- Original inputs 3 and 4 were merged into `FINDING_3` (same behavioral risk: empty `SESSION_ID` vs init-runparams validation).
- Inputs 1 and 2 remain separate (SKILL.md emit gate vs driver bootstrap ordering).
- No `[OUT_OF_SCOPE]` tags in the supplied inputs; no `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).
