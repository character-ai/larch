### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/implement/test_ship.py (plan.txt:51-55)
- **Concern**: Accepted prior fix is incomplete: the ship-level empty-fingerprint test still makes the live materialization monkeypatch optional.. Scenario: If the implementer skips that monkeypatch, the test can exercise the staged fallback after live diff materialization fails, so it will not verify the required empty-fingerprint guard on the repo_root live-materialization path.
- **Proposed resolution**: Make the monkeypatch mandatory for this test and assert `materialize_implementation_diff` is called once with `repo_root`, `base_remote="origin"`, and `base_ref="main"` while `DIFF_FINGERPRINT=` remains empty.



### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/implement/test_ship.py
- **Concern**: Empty-fingerprint ship test must require a materialize monkeypatch. Scenario: The plan marks the `materialize_implementation_diff` monkeypatch as optional. On a minimal non-git `repo_root`, `_materialize_live_diff` returns `None`, so `_pin_and_load_guidelines_note` still drops the note via the `live_diff is None` fallback without ever hitting the `live_diff is not None` plus empty `DIFF_FINGERPRINT` guard at `architectural_guidelines.py:589`. The test can pass while the targeted fail-closed branch regresses.
- **Proposed resolution**: Require monkeypatching `materialize_implementation_diff` to return a non-empty diff and assert it was called once with `(repo_root, base_remote="origin", base_ref="main")`. Drop the "optionally" wording.



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/core/test_architectural_guidelines.py
- **Concern**: Empty-fingerprint helper test must prove the live-materialization branch ran. Scenario: The helper empty-fingerprint case only asserts `False` and no consumable durable note. That outcome is identical when `live_diff is None` and the helper falls back to `pin_note_from_staged` at `architectural_guidelines.py:582-587`, so the test does not prove the `live_diff is not None` plus empty-fingerprint skip at line 589 was exercised.
- **Proposed resolution**: After monkeypatching a non-empty live diff, add `mock.assert_called_once_with(repo, base_remote="origin", base_ref="main")` (or equivalent call-count assertion) in addition to the return-value checks.



