### OOS_1: [OUT_OF_SCOPE] Duplicate `### Warnings` headers (same as in-scope materialize helper fix)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `append_security_audit` always prints new `### Warnings` header; multiple security-routed manifest OOS duplicate Warnings headers in `execution-issues.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Append bullets under existing Warnings section when present.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_10: [OUT_OF_SCOPE] Prompt-side sanitize at Step 9a.1 combine/file time (pre-existing)
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: latent
- **Concern**: Steps 3.4, 4, and 6 rely on prompt-side “Sanitize before compose” rather than mechanical scrubber at combine/file time for design/review accepted-OOS sources that never pass through `materialize-manifest-oos.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_11: [OUT_OF_SCOPE] Full `manifest.json` descriptions in run-log artifacts (pre-existing)
- **Reviewer(s)**: dyn-public-redaction-output.txt
- **Severity**: latent
- **Concern**: Security-routed manifest observations can remain in `$IMPLEMENT_TMPDIR/manifest.json` with full descriptions; unchanged by new security-routing helper; can leak if manifest is copied into committed run logs without redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-public-redaction-output.txt: Address the concern above.

---

**Merge notes (brief):** Input findings 4/13/28, 5/24/35/36/38, 6/8, 9/25, 10→OOS_1, 18/48, 19/51, 23/35/27, 31/42, 32/45, 33/37/40→OOS_6, 34→OOS_5, 41/47→OOS_8 were merged. Generic “Address the concern above” bullets were omitted where the concern field already carried the substantive fix text from dyn reviewers; slots with only that placeholder and no inline fix in the concern were omitted per aggregator rules.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] `#308` triplet scan excludes `materialize-manifest-oos.md`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `#308` triplet scan excludes `skills/implement/scripts/materialize-manifest-oos.md`. Contract header drift in helper `.md` under scripts/ is not caught by references-headers job (pre-existing glob scope).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend references-headers scope or add implement-structure pin for helper contract triplet if desired.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] Schema trusts implementer to exclude security from `oos_observations[]` prose
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Security content without focus-area field can still be filed publicly after partial redaction; operational policy; out of branch scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_4: [OUT_OF_SCOPE] Materialize fail-open when jq reports zero observations for malformed manifest shape
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Manifest OOS in non-array shape may be silently dropped without `OOS_PENDING` when jq reports zero observations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Tighten jq validation or fail closed on materialize error when manifest object present.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_5: [OUT_OF_SCOPE] Security-only manifest OOS leaves private disclosure as manual operator step
- **Reviewer(s)**: dyn-oos-state-output.txt
- **Severity**: latent
- **Concern**: Manifest entries with dedicated security `focus-area` are excluded from `oos-accepted-main-agent.md` and only logged to `security-oos-observations.md`; with manifest-only security OOS, `ship-pr.sh` may never set `OOS_PENDING` because no accepted file grows. Matches security routing intent but not introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-state-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_6: [OUT_OF_SCOPE] Stale `DESIGN_TMPDIR` without fallback to `design-export/` (pre-existing)
- **Reviewer(s)**: dyn-oos-state-output.txt, dyn-manifest-bridge-output.txt, dyn-bash-runtime-output.txt
- **Severity**: latent
- **Concern**: When `DESIGN_TMPDIR` is set but `$DESIGN_TMPDIR/oos-accepted-design.md` is missing, resolvers do not fall back to `$IMPLEMENT_TMPDIR/design-export/oos-accepted-design.md`. Branch adds Python parity with existing bash behavior rather than introducing the miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-state-output.txt: Address the concern above.
  - From dyn-manifest-bridge-output.txt: Address the concern above.
  - From dyn-bash-runtime-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_7: [OUT_OF_SCOPE] Stale `oos-issue-cap.md` references nonexistent assertion `9g`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Edit-in-sync references nonexistent assertion 9g in `test-implement-structure.sh`; contributors may search for 9g and get false leads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Update the reference to the actual OOS structure-test block or remove the stale label.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_8: [OUT_OF_SCOPE] `run_oos_disposition_gate_if_required` omits `--filed-urls-strict-file` for design path (pre-existing)
- **Reviewer(s)**: dyn-bash-runtime-output.txt, dyn-python-parity-output.txt
- **Severity**: latent
- **Concern**: `run_oos_disposition_gate_if_required_before_oos_pending_false` in pr-prep does not pass `--filed-urls-strict-file` for the design path while the Step 8+ checkpoint does. Not introduced by materialization hooks in this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-runtime-output.txt: Address the concern above.
  - From dyn-python-parity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_9: [OUT_OF_SCOPE] Python driver has no `--resume-phase pr-create` equivalent (pre-existing)
- **Reviewer(s)**: dyn-python-parity-output.txt
- **Severity**: latent
- **Concern**: Python driver reruns checks, postbump, and pr-prep on every invoke; predates branch but amplifies size-guard regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-parity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

