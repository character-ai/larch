### OOS_1: materialize_manifest_oos can recreate security-oos-observations.md after private disposition clears the sidecar
- **Description**: materialize_manifest_oos can recreate security-oos-observations.md after private disposition clears the sidecar. Scenario: ship.py and oos_filer._file call materialize_manifest_oos before the security sidecar gate; a resumed ship after oos-pipeline cleared the sidecar can rewrite security findings from manifest observations. This is outside the 10 scoped items but is a concrete private-data durability gap.
- **Reviewer**: Cursor-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: python/larch/issue/file_oos.py:340-377
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] `materialize_manifest_oos` can recreate a cleared security sidecar on ship resume
- **Description**: [OUT_OF_SCOPE] `materialize_manifest_oos` can recreate a cleared security sidecar on ship resume. Scenario: `ship.py` calls `materialize_manifest_oos` on every pre-PR resume before checking the sidecar. After `oos-pipeline` clears `security-oos-observations.md`, a manifest with security observations can rewrite the sidecar and re-trigger `needs_user_reason=oos-filing`, looping the operator.
- **Reviewer**: Cursor-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: python/larch/implement/ship.py:601-620
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

