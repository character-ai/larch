### OOS_1: [OUT_OF_SCOPE] correctness: skills/implement/SKILL.md:189 — `--emergency` not rejected or redirected
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `--emergency` was removed from the flag table but is not listed among removed argv surfaces and is not rejected with a migration hint. `/implement --emergency <N>` can hit the generic verbal-description rejection or run as normal implement without force bypasses and without a clear error. Operators need an explicit removed-argv entry pointing to `--force` / `-f`, or a deprecated alias mapping to `force_requested` / `--force`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add --emergency to removed-argv with redirect error or accept as deprecated alias to force_requested/--force
  - From cursor-specialist-edge-cases-output.txt: Add `--emergency` to the removed argv list with text pointing operators to `--force` / `-f`.


### OOS_2: [OUT_OF_SCOPE] correctness: skills/implement/scripts/step-0-bootstrap.sh:160-162 — no legacy `EMERGENCY_REQUESTED` resume fallback
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Resume paths read only `FORCE_REQUESTED` from `run-flags.sh`, with no alias for legacy `EMERGENCY_REQUESTED` and no fallback from `emergency-bypass.log` to `force-bypass.log`. An in-flight session started on the old flag can lose force mode after a plugin upgrade mid-run (external coder selection, missing `Force: true` metadata, skipped bypass-log consumption).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Treat EMERGENCY_REQUESTED as FORCE_REQUESTED and accept emergency-bypass.log alias during migration
  - From cursor-specialist-edge-cases-output.txt: During one release cycle, treat `EMERGENCY_REQUESTED=true` as `FORCE_REQUESTED=true` and accept both bypass-log filenames in `_append_force_bypass`.


