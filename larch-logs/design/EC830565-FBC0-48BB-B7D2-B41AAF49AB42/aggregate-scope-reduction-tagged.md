### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/engine.py:964-976
- **Concern**: [SCOPE-REDUCTION] Write-mode discovery is wider than legacy python/-only scope. Scenario: G-Enf-2 / acceptance require byte-identical regen of python/markdown-heading-fence-state-baseline.json. Legacy _collect_all only walks root/python via iter_source_files. run_rule forbids paths on --write, so paths=None makes _discover_tracked_paths enumerate every tracked file (skills/*.py, scripts/*.py, etc.). Syntax policy raise and detect then run on out-of-scope .py files; regen can exit 2 or emit rows legacy never saw.
- **Proposed resolution**: Add rule-owned discovery pathspecs (default python) applied inside _scan_findings even when write_baseline=true and paths is None; pin the thin main adapter to that contract and add a test that tracked scripts/*.py or skills/*.py does not affect check/write.
