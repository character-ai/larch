Deviation identified against the final plan:

- **G-Py-7** (wrap external CLIs as typed functions over the injected `Runner`): the plan's change to `materialize_implementation_diff` (and the untouched code around it in `closeout.py`) resolves `HEAD` via a raw `subprocess.run(["git", ...])` call rather than routing through `larch.core.proc.run`/`Runner`. This is a pre-existing pattern throughout both files (every existing git invocation in `architectural_guidelines.py` and `closeout.py` already uses raw `subprocess.run`), not a new pattern this fix introduces. A rejected plan-review finding (FINDING_1, corroborated by 4 reviewers) raised the same concern, framed as a "subprocess-via-runner ratchet" lint risk. The plan keeps the existing local style rather than partially adopting `Runner` for one new call while leaving the surrounding file unwrapped, since a file-wide `Runner` migration is out of scope for this targeted drift-race fix.

No other deviations identified.
