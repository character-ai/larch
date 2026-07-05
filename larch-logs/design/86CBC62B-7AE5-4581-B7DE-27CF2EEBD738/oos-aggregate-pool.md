### OOS_1: [OUT_OF_SCOPE] materialize_manifest_oos can recreate security-oos-observations.md after oos-pipeline clears it
- **Description**: [OUT_OF_SCOPE] materialize_manifest_oos can recreate security-oos-observations.md after oos-pipeline clears it. Scenario: After private disposition deletes the sidecar, ship.py still calls materialize_manifest_oos before the pre-PR sidecar gate; manifest security observations can repopulate the file and re-trigger oos-filing, so mixed manifest+review security runs may loop even after item 8 ships
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/larch/issue/file_oos.py:340-377
- **Phase**: design

Vote tally: YES=2 NO=0 JUDGE_ERROR=1 Result=accepted

