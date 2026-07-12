## Proposed Design Outline

### Goals
- Replace per-script start-or-wait boilerplate in `design-step5c.sh`, `design-step3-review.sh`, `design-step3b-tail.sh` with a single `bgjob adapt` call.
- Inherit the unified liveness policy from `bgjob adapt`, removing duplicated rehydrate, registry-check, stale-clear, merge-env recreate, and self-reexec logic.
- Preserve behavioral equivalence: `/design` steps 3, 3b, and 5c work identically after conversion.

### Non-goals
- `/implement` adapters (`step-8-assessment.sh`) and step-8 grammar forks.
- Python logic changes beyond what the merge-env path shift strictly requires.
- Changes to the SKILL.md `read-result-env` call paths (backward compat handled by `_preferred_bgjob_result_input`).

### Approach sketch
- For each script: delete the `*_bgjob_registry_state()` heredoc, `*_recreate_merge_env()` call, `mkdir/rm -f` stale-clear block, and `exec bgjob start ... bash "$0" --run-xxx-child` self-reexec.
- Replace with `exec python3 "$PLUGIN_ROOT/python/cli.py" bgjob adapt --step <STEP> --tmpdir "$DESIGN_TMPDIR" --budget-s <N> -- bash "$0" --bgjob-child "$@"`.
- In each script, rename `--run-xxx-child` to `--bgjob-child`; accept and ignore `--merge-result-env` in the child-mode arg parser.
- For `design-step3b-tail.sh` child: pass `--merge-result-env` to `design_step4_tail_write_merge_env()` so KVs reach the `bgjob adapt`-owned merge env.
- Update Python `design_step5c.py` (`_step5c_write_status`) and `design_step6.py` (`_read_step5c_status_sidecar`) to use the `bgjob adapt`-owned merge env path.
- Update the three `.md` doc files to reflect the new invariants.

### Surfaces in scope
- `skills/design/scripts/design-step5c.sh`
- `skills/design/scripts/design-step3-review.sh`
- `skills/design/scripts/design-step3b-tail.sh`
- `skills/design/scripts/design-step5c.md`
- `skills/design/scripts/design-step3-review.md`
- `skills/design/scripts/design-step3b-tail.md`
- `python/larch/design/design_step5c.py` (merge env path)
- `python/larch/design/design_step6.py` (sidecar reader)

### Open questions
- None.
