### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_monkeypatch_facade_binding.py
- **Concern**: Occurrence is assigned over all resolved setattr candidates, not violations only. Scenario: The plan counts every resolved repo-module monkeypatch.setattr with a literal attribute before classification. Sibling ratchets in lint_tempfile_dir.py and docs/linting.md increment occurrence only for matching violations. A test that adds a correct defining-module patch before a facade patch renumbers later violation occurrences and silently invalidates baseline rows.
- **Proposed resolution**: Increment occurrence only for findings that pass the import-only facade classifier, using the same nearest-scope lexical pre-order rules as docs/linting.md.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_monkeypatch_facade_binding.py
- **Concern**: facade_module identity is not canonicalized to source module paths. Scenario: The plan never requires normalizing facade_module to the dotted module path derived from the resolved python/ source file. The same facade can appear as run_logs, ship.run_logs chain spelling, or larch.report.run_logs across tests, producing duplicate baseline identities and inconsistent reports for one defect.
- **Proposed resolution**: Store facade_module as the canonical dotted module path from the resolved source file; keep import aliases and attribute-chain spellings diagnostic-only.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_monkeypatch_facade_binding.py
- **Concern**: Baseline identity tuple and qualified_symbol rules are still underspecified. Scenario: Suggested baseline fields list reason and defining_module alongside identity keys without stating which fields form Finding.key(). Sibling ratchets exclude reason from the key and document identity in docs/linting.md; qualified_symbol nesting is never defined here. Implementers can put reason or defining_module in the key or invent ad hoc qualified_symbol rules, breaking --write reason preservation and baseline stability on import refactors.
- **Proposed resolution**: Document identity as (file, qualified_symbol, facade_module, attribute, occurrence) with reason and defining_module stored but excluded from the key; define qualified_symbol with the same nested def/class/module prefix rules as docs/linting.md.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_monkeypatch_facade_binding.py
- **Concern**: Resolve monkeypatch targets with lexical scope, not a file-wide import map. Scenario: A test function can shadow an imported module name, or import an alias inside a narrower scope. A whole-file map would still treat `run_logs` or `ship` as the repo module and flag a legitimate patch, or miss that the string target points at a local alias rather than the imported module.
- **Proposed resolution**: Track bindings per lexical scope and resolve `Name` and dotted-string roots only against imports visible at the call site.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_monkeypatch_facade_binding.py
- **Concern**: The plan lists defining_module in baseline identity but never pins Finding.key() / duplicate-check tuple composition.. Scenario: Mirroring tempfile without an explicit key contract invites putting defining_module (or reason) in the ratchet key; import-path refactors then orphan baseline rows or duplicate identities while the same violation persists.
- **Proposed resolution**: Add an explicit Finding.key() -> (file, qualified_symbol, facade_module, attribute, occurrence); keep defining_module and reason out of the key; document BASELINE_KEYS as those five fields plus reason only.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_monkeypatch_facade_binding.py
- **Concern**: facade_module canonical naming is unspecified for Name vs attribute-chain targets.. Scenario: The same patch can serialize as run_logs vs larch.report.run_logs (or ship.run_logs vs larch.report.run_logs), churning baseline rows and weakening cross-test identity matching.
- **Proposed resolution**: Require facade_module to be the fully qualified module name of the resolved patch target (e.g. larch.report.run_logs), never the test-local import alias or attribute-chain prefix module.

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_monkeypatch_facade_binding.py
- **Concern**: Separate baseline dedup key from full record fields and exclude reason from key(). Scenario: The plan labels reason (and other report fields) as baseline identity without pinning Finding.key(); an implementer can put reason in the dedup tuple, breaking write-mode reason preservation and duplicate detection documented for sibling ratchets in docs/linting.md
- **Proposed resolution**: Specify Finding.key() explicitly, e.g. (file, qualified_symbol, facade_module, attribute, occurrence), keep defining_module and reason as stored-only fields, and mirror lint_tempfile_dir.py _record_key vs BASELINE_KEYS

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_monkeypatch_facade_binding.py
- **Concern**: Pin qualified_symbol and occurrence assignment rules. Scenario: Nearest lexical scope is underspecified versus docs/linting.md and lint_tempfile_dir._collect_scope, so two implementers can assign different occurrence indices for the same live site and baselines churn
- **Proposed resolution**: State qualified_symbol is the dotted enclosing test function/class path and occurrence counts every resolved literal-attr monkeypatch.setattr on a repo module in lexical pre-order within that scope, including non-violations, before suppression and baseline filtering
