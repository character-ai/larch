## Architectural Guideline Assessment for issue #6881

**G-Fix-1 (Fix the class, not the instance)**: Followed. The fix applies the identity contract to both `run-step-checks.sh` and `step-6-entry.sh` — the two production launchers that share the same stale-rejoin bug — rather than patching only the step3 case.

**G-Py-1 (Frozen dataclasses for composite data)**: The new `checks_result_identity.py` uses a frozen identity type for cross-boundary data, following this guideline.

**G-Py-2 / G-Py-9 (Annotate types)**: The new Python module will annotate all signatures and locals per the guideline.

**G-Py-3 (Domain types over stringly-typed primitives)**: The identity type represents the envelope classification (matching, stale, incomplete, unsafe) as a domain type rather than raw strings.

**G-Py-4 (Fail loudly and fail closed)**: The plan explicitly fails closed on identity computation failure and on active identity mismatch with a live bgjob — no silent swallowing.

**G-Py-5 (Injectable seams)**: The identity helper computes identity through an injected runner, keeping it testable offline.

**G-Py-7 (Typed wrappers for external CLIs)**: Git commands in the identity helper are wrapped through the injected runner with typed results.

**G-Py-8 (Re-verify after integrity mutations)**: Child mode recomputes identity before terminal publication to verify the postcondition.

**No guideline deviations**: All guidelines are aligned with or aspirationally addressed by the plan.
