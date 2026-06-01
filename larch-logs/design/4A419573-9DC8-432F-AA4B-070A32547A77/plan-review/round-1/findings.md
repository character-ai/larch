### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_rebase.py:552-557,822-827
- **Concern**: Plan adds base_remote/base_ref to the rebase_and_rebump apply_bump call but does not update two monkeypatched _apply stubs. Scenario: After rebase.py passes base_remote/base_ref, test_rebase_result_uses_apply_result_new_version and test_version_regression_guard_recomputes_target raise TypeError; conflicts with the plan claim that existing test_rebase.py cases pass unchanged
- **Proposed resolution**: Extend the UPDATED python/test_rebase.py section to widen both _apply stubs (defaults or **kwargs) or document the signature change explicitly

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_rebase.py:552-557, python/test_rebase.py:822-827
- **Concern**: Plan changes rebase_and_rebump to pass base_remote and base_ref into version_bump.apply_bump but omits updating existing monkeypatched apply_bump stubs. Scenario: Existing tests that monkeypatch version_bump.apply_bump will raise TypeError for unexpected keyword argument base_remote before the new behavior can be validated
- **Proposed resolution**: Update both existing stubs to accept base_remote and base_ref or **kwargs, and assert defaults where useful

### FINDING_3:
- **Reviewer(s)**: Codex-Edge, Codex-Pragmatic
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/rebase.py:598; python/test_rebase.py:552-557,822-827
- **Concern**: Planned rebase call adds base_remote/base_ref kwargs to apply_bump, but existing monkeypatched apply_bump stubs accept only cwd. Scenario: make py-test will fail with TypeError unexpected keyword argument base_remote in existing rebase tests
- **Proposed resolution**: Update those stubs to accept base_remote/base_ref or **kwargs; optionally assert default origin/main where useful

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_rebase.py:552-557,822-827
- **Concern**: Plan omits updating existing apply_bump monkeypatch doubles. Scenario: After rebase_and_rebump starts calling version_bump.apply_bump(..., base_remote=base_remote, base_ref=base_ref, cwd=cwd), these existing tests raise TypeError before the new assertions run
- **Proposed resolution**: Extend the two local _apply doubles to accept base_remote and base_ref keywords, or add **_unused, as part of the planned python/test_rebase.py update

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:51-54
- **Concern**: test_apply_bump_receives_base omits classify_bump isolation. Scenario: Implementer runs the test with real classify_bump; classify always git.fetch origin main (python/version_bump.py:251), so assertions that guard fetch/show use upstream and not origin/main fail even when apply_bump wiring is correct
- **Proposed resolution**: Specify monkeypatch classify_bump (return PATCH + target_version like other test_rebase rebump cases) before asserting git traffic; or assert only apply_bump kwargs via a spy and keep fetch/show checks in test_apply_bump_threads_base

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_rebase.py:552-558,822-827; plan.txt:25-26,96-99
- **Concern**: Plan says existing tests stay untouched, but existing apply_bump monkeypatch stubs do not accept the new base_remote/base_ref kwargs. Scenario: After rebase_and_rebump starts calling apply_bump(..., base_remote=..., base_ref=...), these tests raise TypeError before the new assertions run
- **Proposed resolution**: Update the existing stubs to accept base_remote/base_ref or **kwargs, and remove the “existing tests unchanged” claim

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: plan.txt:41-54
- **Concern**: Planned base-threading test can conflict with the explicit non-goal to leave classify_bump on origin/main. Scenario: If test_apply_bump_receives_base asserts no origin/main calls across runner.calls, it either fails because classify_bump still fetches origin/main or pressures implementation to expand scope into classify_bump
- **Proposed resolution**: Constrain the assertion to apply_bump’s guard calls, or monkeypatch classify_bump so the test only verifies rebase passes base_remote/base_ref into apply_bump

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-port-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rebase.py:598; python/test_rebase.py:552-559,822-830
- **Concern**: The plan changes rebase_and_rebump to pass base_remote/base_ref into apply_bump but does not update existing monkeypatched apply_bump stubs that only accept cwd.. Scenario: make py-test will fail with TypeError in existing rebase tests once the planned unconditional keyword arguments are added.
- **Proposed resolution**: Include the two existing test stubs in python/test_rebase.py in the test update scope and let them accept base_remote/base_ref or **kwargs.

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-base-plumbing
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_rebase.py:552-557,822-827
- **Concern**: Plan wires base_remote/base_ref into apply_bump but omits updating two monkeypatched _apply stubs. Scenario: After rebase.py passes base_remote/base_ref to apply_bump, test_rebase_result_uses_apply_result_new_version and test_version_regression_guard_recomputes_target raise TypeError; contradicts plan claim that existing tests pass unchanged
- **Proposed resolution**: Add base_remote/base_ref (or **kwargs) to both _apply stubs in the UPDATED test_rebase.py section, or document that signature change explicitly

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-base-plumbing
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_rebase.py:552-557, python/test_rebase.py:822-827
- **Concern**: Existing monkeypatched apply_bump stubs do not accept the new base_remote/base_ref kwargs that the plan adds to the rebase call. Scenario: After python/rebase.py changes line 598 to call apply_bump(..., base_remote=base_remote, base_ref=base_ref, cwd=cwd), these tests raise TypeError before validating default behavior
- **Proposed resolution**: Update the existing _apply stubs to accept base_remote: str = "origin" and base_ref: str = "main" or **kwargs, and optionally assert the default values where useful

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-scope-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_rebase.py:552-558,822-830; plan.txt:96-99
- **Concern**: Gap #3 wires base_remote/base_ref into apply_bump but plan omits updating two existing apply_bump monkeypatch stubs and claims existing test_rebase.py stays unchanged. Scenario: After rebase.py passes base_remote/base_ref, test_rebase_result_uses_apply_result_new_version and test_version_regression_guard_recomputes_target will raise TypeError: unexpected keyword argument; contradicts plan claim that existing tests pass without edits
- **Proposed resolution**: Add stub updates (accept base_remote/base_ref or **kwargs) to the ### UPDATED: python/test_rebase.py section and drop the unchanged-and-passing claim for those cases

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-scope-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_rebase.py:552-558,822-830
- **Concern**: F1: Existing apply_bump monkeypatch stubs are outside the stated test-update scope but will receive new kwargs. Scenario: The plan changes rebase_and_rebump to call version_bump.apply_bump with base_remote and base_ref, while existing test stubs accept only cwd; make py-test will fail with unexpected keyword argument before the new parity tests run
- **Proposed resolution**: Update the plan to include adjusting these existing stubs to accept base_remote and base_ref or **kwargs, in addition to the new base-threading tests
