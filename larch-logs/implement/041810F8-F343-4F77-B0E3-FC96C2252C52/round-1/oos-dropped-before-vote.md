### OOS_1: [OUT_OF_SCOPE] Remove orphaned implement step-0-bootstrap command (`b56f27a8c`)
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Commit `b56f27a8c` removes the orphaned `implement step-0-bootstrap` command surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Run-log flush for step-0-bootstrap removal (`f73db7d61`)
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Commit `f73db7d61` (chore(larch-logs): flush run log) documents that the feature commit removes the dead `implement step-0-bootstrap` surface in four files (`python/larch/cli.py` registry row, re-export in `python/larch/implement/implement_dispatch.py`, ~200 lines in `python/larch/implement/dispatch_bootstrap.py`, and matching baseline rows in `python/env-via-config-constant-baseline.json`). The live `/implement` Step 0 path is unchanged (`skills/implement/scripts/step-0-bootstrap.sh` still calls `bootstrap invoke` directly). `step0_degraded_gate_main` remains with correct imports. Removal is consistent across all three registration sites, so there is no partial-delete import failure. Unknown commands fail closed via `cli.py` (`ERROR: unknown subcommand`, exit 2). Repo-wide search finds no runtime callers of `implement step-0-bootstrap` or `step0_bootstrap_main` outside historical larch-logs and plan-fidelity calibration fixtures. Baseline regen also dropped stale `agent_voters._append_voter1_failure` rows; that symbol is already absent on `origin/main`, so the extra churn is mechanical, not a functional regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Stale plural docstring in dispatch_bootstrap.py
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `python/larch/implement/dispatch_bootstrap.py:2` — The module docstring still says "Step 0 bootstrap entrypoints" (plural) but only `step0_degraded_gate_main` remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Rename the docstring to match the single surviving entrypoint when convenient; no runtime impact.

### OOS_4: [OUT_OF_SCOPE] Historical calibration diffs retain removed step-0-bootstrap symbols
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `python/test_fixtures/plan-fidelity-calibration/diffs/` — Historical calibration diffs still embed the removed `("implement", "step-0-bootstrap")` registry row and `step0_bootstrap_main` body.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Leave as-is per plan edge-case guidance; update only if a calibration harness starts failing on the deleted symbol.

### OOS_5: [OUT_OF_SCOPE] Breaking CLI removal for out-of-tree callers
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: Deleting `implement step-0-bootstrap` is an intentional breaking CLI removal for out-of-tree callers. External scripts or operator tooling that still invoke `python/cli.py implement step-0-bootstrap` will get `ERROR: unknown subcommand` and exit 2 after merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Migrate callers to bootstrap invoke or step-0-bootstrap.sh; note in release notes if external consumers are known.

### OOS_6: [OUT_OF_SCOPE] No dedicated unit tests for step0_degraded_gate_main
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `step0_degraded_gate_main` has no dedicated unit tests beyond registry import smoke. Future edits to `dispatch_bootstrap.py` could break degraded-gate forwarding without a behavioral test catching argv or relay regressions. Pre-existing gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: add a focused test only when degraded-gate behavior is next touched.
```

**Merge notes**

- **No merges applied.** Each input finding targets a distinct commit, docstring, fixture set, external-caller risk, or test gap; fixes differ.
- **Slot coverage:** `cursor-specialist-edge-cases` appears in FINDING_1–4 (mixed slot: in-scope + OOS). `cursor-specialist-testing` appears only in FINDING_5–6 (`[OUT_OF_SCOPE]`, out-of-scope-only slot).
- **Severity:** `[latent]` taken from testing concerns for FINDING_5–6; nit for validation/OOS items with no runtime impact or explicit leave-as-is guidance.
- **Revisions:** Generic “Address the concern above.” kept verbatim for FINDING_1–2; substantive fix text quoted from each reviewer’s concern where the structured revision field was generic.

