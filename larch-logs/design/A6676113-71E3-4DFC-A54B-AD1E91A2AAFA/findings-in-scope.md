### FINDING_1: Gate C renderer omits Other/debate affordance
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The Gate C renderer contract omits the mandatory Other/debate affordance that must appear in visible prompt text. Current Gate C requires `Use Other to request debate <decision>: <option A> vs <option B> (or debate <candidate-id> when fingerprint-valid candidates exist).` in prompt text (line 195), separate from the cap-aware QUESTION strings (lines 216-217). The plan moves prompt copy into `design render-gate` but only defines `HEADER`, `QUESTION`, and `OPTION_*` KVs and lists golden tests for cap/panel-failed variants, not this sentence. An implementer copying lines 216-217 into `QUESTION` drops operator-visible Other/debate guidance, breaking the issue acceptance criterion of byte-identical gate wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Specify in `design_gate_render.py` that Gate C `QUESTION` includes the Other/debate affordance (concatenated with the cap-aware question), or add a dedicated KV (e.g. `OTHER_AFFORDANCE=`) that orchestrator must pass through to `AskUserQuestion`. Add a golden test asserting the exact line-195 string is present in renderer output for below-cap and at-cap variants.

### FINDING_2: Stale cap-of-5 prose in Gate C loop semantics
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: A stale flattened cap of 5 remains in Gate C loop-semantics prose outside the planned Review-round cap section fix. The plan removes `Cap: 5` from the Review-round cap section and sources cap shaping from `ROUND_CAP`, but keeps Gate C loop exits unchanged and does not call out line 200 (`offer this only when the current review-round count is below the flattened cap of 5`). That normative prose still contradicts `plan_review_common.ROUND_CAP = 2` and Step 3 enforcement. Future edits or orchestrators reading behavior bullets instead of renderer KVs could reintroduce cap-5 semantics beside the corrected renderer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In the `approval-gates.md` update, replace the line-200 cap-of-5 prose with `ROUND_CAP` / `REVIEW_ROUND_CAP` authority (or state that option presence comes solely from `design render-gate`). Add a `test-design-structure.sh` `not_contains` pin for `flattened cap of 5` / `Cap: 5` anywhere in `approval-gates.md`.
